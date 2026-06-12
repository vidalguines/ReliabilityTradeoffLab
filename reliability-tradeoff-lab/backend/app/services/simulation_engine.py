"""
Monte Carlo Reliability Simulation Engine
==========================================
Simulates system reliability using exponential failure models,
computes availability, lifecycle cost, and failure probability distributions.
"""

import numpy as np
from scipy import stats
from typing import List, Tuple, Dict, Any
import logging

from app.models.schemas import (
    SystemDesign, ComponentConfig, RedundancyType,
    DesignResult, ComponentResult, CostBreakdown,
    ReliabilityCurvePoint,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

HOURS_PER_YEAR = 8_760


class ComponentSimulator:
    """Simulates a single component's failure behavior."""

    def __init__(self, config: ComponentConfig):
        self.config = config
        self.failure_rate = 1.0 / config.mtbf_hours  # λ (failures/hour)
        self.repair_rate = 1.0 / config.mttr_hours   # μ (repairs/hour)

    @property
    def inherent_availability(self) -> float:
        """Steady-state availability A = MTBF / (MTBF + MTTR)"""
        return self.config.mtbf_hours / (self.config.mtbf_hours + self.config.mttr_hours)

    def effective_availability(self) -> float:
        """Availability after redundancy."""
        a = self.inherent_availability
        q = self.config.quantity
        r = self.config.redundancy

        if r == RedundancyType.NONE or q == 1:
            return a

        if r == RedundancyType.ACTIVE:
            # All q units active; system fails only if ALL fail
            # P(system unavailable) = P(all units down) = (1-a)^q
            return 1.0 - (1.0 - a) ** q

        if r == RedundancyType.STANDBY:
            # k-of-n (1-of-q needed). Same formula for cold standby approximation.
            return 1.0 - (1.0 - a) ** q

        return a

    def simulate_failures(self, hours: float, n_sim: int, rng: np.random.Generator) -> np.ndarray:
        """
        Returns array of shape (n_sim,) with the number of failures per simulation run
        over `hours` operational hours using a Poisson process.
        """
        q = self.config.quantity
        r = self.config.redundancy

        if r == RedundancyType.NONE or q == 1:
            expected = self.failure_rate * hours
            return rng.poisson(expected, size=n_sim)

        # Redundant systems: system failure only when required units fail simultaneously.
        # Simplified model: effective failure rate via combination
        if r in (RedundancyType.ACTIVE, RedundancyType.STANDBY):
            # System failure rate ≈ q * λ * (1-a)^(q-1)  [active parallel]
            a = self.inherent_availability
            eff_rate = q * self.failure_rate * ((1 - a) ** (q - 1))
            return rng.poisson(eff_rate * hours, size=n_sim)

        return rng.poisson(self.failure_rate * hours, size=n_sim)

    def reliability_at(self, t_hours: float) -> float:
        """R(t) = e^(-λt) for exponential distribution."""
        eff_rate = self.failure_rate
        if self.config.redundancy != RedundancyType.NONE and self.config.quantity > 1:
            a = self.inherent_availability
            q = self.config.quantity
            eff_rate = q * self.failure_rate * ((1 - a) ** (q - 1))
        return np.exp(-eff_rate * t_hours)


class SystemReliabilityEngine:
    """
    Computes system-level reliability metrics via analytical models
    and Monte Carlo simulation.
    """

    def __init__(self, design: SystemDesign, n_iterations: int):
        self.design = design
        self.n_iter = min(n_iterations, settings.MONTE_CARLO_MAX_ITERATIONS)
        self.rng = np.random.default_rng(seed=42)
        self.simulators = [ComponentSimulator(c) for c in design.components]
        self.lifetime_hours = design.design_lifetime_years * HOURS_PER_YEAR

    # ── System-level aggregates ──────────────────────────────────────────────

    def system_availability(self) -> float:
        """
        Series system: A_sys = product of individual availabilities for critical components.
        Non-critical components don't propagate failure.
        """
        a = 1.0
        for sim in self.simulators:
            if sim.config.is_critical:
                a *= sim.effective_availability()
        return a

    def system_mtbf(self) -> float:
        """1 / sum(failure rates of critical components in series)"""
        total_rate = sum(
            1.0 / sim.config.mtbf_hours
            for sim in self.simulators
            if sim.config.is_critical
        )
        return 1.0 / total_rate if total_rate > 0 else float("inf")

    def system_mttr(self) -> float:
        """Weighted average MTTR by failure rate contribution."""
        critical = [s for s in self.simulators if s.config.is_critical]
        if not critical:
            return 0.0
        total_rate = sum(1.0 / s.config.mtbf_hours for s in critical)
        if total_rate == 0:
            return 0.0
        return sum(
            (1.0 / s.config.mtbf_hours / total_rate) * s.config.mttr_hours
            for s in critical
        )

    def system_reliability_at(self, t_hours: float) -> float:
        """Series reliability: R_sys(t) = product of R_i(t) for critical components."""
        r = 1.0
        for sim in self.simulators:
            if sim.config.is_critical:
                r *= sim.reliability_at(t_hours)
        return r

    # ── Monte Carlo ──────────────────────────────────────────────────────────

    def run_monte_carlo(self) -> Dict[str, Any]:
        """
        Simulate `n_iter` system lifetimes.
        Returns failure count statistics across all simulations.
        """
        logger.info(f"Running Monte Carlo: {self.n_iter} iterations for '{self.design.name}'")

        # Each row = one simulation, each col = one component
        total_system_failures = np.zeros(self.n_iter, dtype=float)

        for sim in self.simulators:
            if not sim.config.is_critical:
                continue
            comp_failures = sim.simulate_failures(self.lifetime_hours, self.n_iter, self.rng)
            # System fails on any critical component failure (first failure ends the run? No —
            # count total outage events, each repaired via MTTR)
            total_system_failures += comp_failures

        return {
            "failures_per_lifetime": total_system_failures,
            "mean": float(np.mean(total_system_failures)),
            "std": float(np.std(total_system_failures)),
            "p50": float(np.percentile(total_system_failures, 50)),
            "p90": float(np.percentile(total_system_failures, 90)),
            "p95": float(np.percentile(total_system_failures, 95)),
            "p99": float(np.percentile(total_system_failures, 99)),
            "prob_zero_failures": float(np.mean(total_system_failures == 0)),
            "prob_gt5_failures": float(np.mean(total_system_failures > 5)),
            "ci_95_lower": float(np.percentile(total_system_failures, 2.5)),
            "ci_95_upper": float(np.percentile(total_system_failures, 97.5)),
        }

    # ── Reliability Curve ────────────────────────────────────────────────────

    def build_reliability_curve(self, n_points: int = 50) -> List[ReliabilityCurvePoint]:
        """Build time-series reliability curve with bootstrap confidence intervals."""
        t_max = self.lifetime_hours
        times = np.linspace(0, t_max, n_points)
        curve = []

        # Bootstrap CI via parametric uncertainty on failure rates
        n_bootstrap = 200
        bootstrap_reliabilities = np.zeros((n_bootstrap, n_points))

        for b in range(n_bootstrap):
            r_boot = np.ones(n_points)
            for sim in self.simulators:
                if not sim.config.is_critical:
                    continue
                # Perturb MTBF slightly (±20% epistemic uncertainty)
                perturbed_rate = sim.failure_rate * self.rng.uniform(0.8, 1.2)
                r_boot *= np.exp(-perturbed_rate * times)
            bootstrap_reliabilities[b] = r_boot

        ci_lower = np.percentile(bootstrap_reliabilities, 5, axis=0)
        ci_upper = np.percentile(bootstrap_reliabilities, 95, axis=0)
        r_nominal = np.array([self.system_reliability_at(t) for t in times])

        for i, t in enumerate(times):
            curve.append(ReliabilityCurvePoint(
                time_hours=round(float(t), 1),
                reliability=round(float(r_nominal[i]), 6),
                failure_probability=round(1.0 - float(r_nominal[i]), 6),
                confidence_lower=round(float(ci_lower[i]), 6),
                confidence_upper=round(float(ci_upper[i]), 6),
            ))

        return curve

    def build_failure_rate_curve(self, n_points: int = 50) -> List[Dict[str, float]]:
        """Instantaneous failure rate (hazard function) h(t) = f(t)/R(t) for exponential = λ."""
        t_max = self.lifetime_hours
        times = np.linspace(0, t_max, n_points)
        curve = []
        sys_mtbf = self.system_mtbf()
        sys_rate = 1.0 / sys_mtbf if sys_mtbf != float("inf") else 0.0

        for t in times:
            # Constant hazard rate for exponential distribution (memoryless)
            curve.append({
                "time_hours": round(float(t), 1),
                "hazard_rate": round(sys_rate, 8),
                "cumulative_failures": round(sys_rate * float(t), 4),
            })
        return curve

    # ── Cost Model ───────────────────────────────────────────────────────────

    def compute_costs(self, mc_results: Dict[str, Any]) -> CostBreakdown:
        initial = sum(
            c.cost_usd * c.quantity for c in self.design.components
        )
        maintenance = self.design.maintenance_cost_annual_usd * self.design.design_lifetime_years

        # Expected downtime cost: E[failures] * MTTR * cost/hr
        sys_mttr = self.system_mttr()
        expected_failures = mc_results["mean"]
        downtime_cost = (
            expected_failures * sys_mttr * self.design.downtime_cost_per_hour_usd
        )

        total = initial + maintenance + downtime_cost

        a = self.system_availability()
        nines = -np.log10(1 - a) if a < 1.0 else 5.0
        cost_per_nine = total / nines if nines > 0 else float("inf")

        return CostBreakdown(
            initial_hardware_cost=round(initial, 2),
            lifetime_maintenance_cost=round(maintenance, 2),
            expected_downtime_cost=round(downtime_cost, 2),
            total_lifecycle_cost=round(total, 2),
            cost_per_nine=round(cost_per_nine, 2),
        )

    # ── Component Analysis ───────────────────────────────────────────────────

    def analyze_components(self) -> Tuple[List[ComponentResult], str, List[str]]:
        results = []
        sys_rate = sum(
            1.0 / s.config.mtbf_hours
            for s in self.simulators if s.config.is_critical
        )

        spofs = []
        worst = None
        worst_contrib = -1.0

        for sim in self.simulators:
            c = sim.config
            avail = sim.effective_availability()
            comp_rate = 1.0 / c.mtbf_hours
            contribution = (comp_rate / sys_rate * 100) if sys_rate > 0 else 0.0
            annual_failures = comp_rate * HOURS_PER_YEAR

            if c.is_critical and c.redundancy == RedundancyType.NONE and c.quantity == 1:
                spofs.append(c.name)

            if contribution > worst_contrib:
                worst_contrib = contribution
                worst = c.name

            results.append(ComponentResult(
                name=c.name,
                cost_usd=c.cost_usd * c.quantity,
                mtbf_hours=c.mtbf_hours,
                availability=round(avail, 6),
                failure_rate_per_year=round(comp_rate * HOURS_PER_YEAR, 4),
                annual_expected_failures=round(annual_failures, 4),
                contribution_to_system_unreliability=round(contribution, 2),
            ))

        return results, worst or "Unknown", spofs

    # ── Main Entry Point ─────────────────────────────────────────────────────

    def run(self) -> DesignResult:
        mc = self.run_monte_carlo()
        a_sys = self.system_availability()
        mtbf = self.system_mtbf()
        mttr = self.system_mttr()
        lifetime_years = self.design.design_lifetime_years

        nines = -np.log10(max(1 - a_sys, 1e-10))

        # Annual and lifetime failure probabilities
        annual_fp = 1.0 - self.system_reliability_at(HOURS_PER_YEAR)
        lifetime_fp = 1.0 - self.system_reliability_at(self.lifetime_hours)

        cost = self.compute_costs(mc)
        rel_curve = self.build_reliability_curve()
        fr_curve = self.build_failure_rate_curve()
        comp_results, weakest, spofs = self.analyze_components()

        return DesignResult(
            design_name=self.design.name,
            description=self.design.description,
            system_availability=round(a_sys, 7),
            availability_nines=round(float(nines), 2),
            mtbf_hours=round(mtbf, 1) if mtbf != float("inf") else 999_999,
            mttr_hours=round(mttr, 2),
            annual_failure_probability=round(annual_fp, 6),
            lifetime_failure_probability=round(lifetime_fp, 6),
            simulated_failures_mean=round(mc["mean"], 3),
            simulated_failures_p50=round(mc["p50"], 1),
            simulated_failures_p90=round(mc["p90"], 1),
            simulated_failures_p99=round(mc["p99"], 1),
            simulation_confidence_interval={
                "lower_95": mc["ci_95_lower"],
                "upper_95": mc["ci_95_upper"],
                "prob_zero_failures": round(mc["prob_zero_failures"], 4),
                "prob_gt5_failures": round(mc["prob_gt5_failures"], 4),
            },
            cost_breakdown=cost,
            reliability_curve=rel_curve,
            failure_rate_curve=fr_curve,
            component_results=comp_results,
            weakest_link=weakest,
            single_points_of_failure=spofs,
        )
