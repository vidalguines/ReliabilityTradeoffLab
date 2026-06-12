"""
Recommendation Engine
=====================
Scores designs across reliability, cost, and availability dimensions.
Generates human-readable advisory recommendations.
"""
from typing import List, Dict, Any, Tuple
import numpy as np

from app.models.schemas import DesignResult, TradeoffMatrix, RecommendationEngine


def normalize(values: List[float], higher_is_better: bool = True) -> List[float]:
    """Min-max normalize a list to [0, 100]."""
    arr = np.array(values, dtype=float)
    mn, mx = arr.min(), arr.max()
    if mx == mn:
        return [50.0] * len(values)
    normed = (arr - mn) / (mx - mn) * 100
    if not higher_is_better:
        normed = 100 - normed
    return normed.tolist()


def compute_tradeoff_matrix(
    results: List[DesignResult],
    weights: Dict[str, float] = None,
) -> List[TradeoffMatrix]:
    """
    Weights default: reliability=0.4, cost=0.35, availability=0.25
    """
    if weights is None:
        weights = {"reliability": 0.40, "cost": 0.35, "availability": 0.25}

    # Extract raw metrics
    reliabilities = [1.0 - r.lifetime_failure_probability for r in results]
    costs = [r.cost_breakdown.total_lifecycle_cost for r in results]
    availabilities = [r.system_availability for r in results]

    rel_scores = normalize(reliabilities, higher_is_better=True)
    cost_scores = normalize(costs, higher_is_better=False)   # lower cost = better
    avail_scores = normalize(availabilities, higher_is_better=True)

    matrix = []
    for i, result in enumerate(results):
        composite = (
            weights["reliability"] * rel_scores[i]
            + weights["cost"] * cost_scores[i]
            + weights["availability"] * avail_scores[i]
        )

        if composite >= 70:
            tier = "recommended"
        elif composite >= 45:
            tier = "acceptable"
        else:
            tier = "avoid"

        matrix.append(TradeoffMatrix(
            design_name=result.design_name,
            reliability_score=round(rel_scores[i], 1),
            cost_score=round(cost_scores[i], 1),
            availability_score=round(avail_scores[i], 1),
            composite_score=round(composite, 1),
            recommendation_tier=tier,
        ))

    return matrix


def compute_pareto_front(results: List[DesignResult]) -> List[Dict[str, Any]]:
    """
    Find Pareto-optimal designs in (cost, reliability) space.
    A design is Pareto-optimal if no other design is cheaper AND more reliable.
    """
    points = []
    for r in results:
        points.append({
            "name": r.design_name,
            "cost": r.cost_breakdown.total_lifecycle_cost,
            "reliability": 1.0 - r.lifetime_failure_probability,
            "availability": r.system_availability,
        })

    pareto = []
    for i, p in enumerate(points):
        dominated = False
        for j, q in enumerate(points):
            if i == j:
                continue
            # q dominates p if q is cheaper AND more reliable
            if q["cost"] <= p["cost"] and q["reliability"] >= p["reliability"]:
                if q["cost"] < p["cost"] or q["reliability"] > p["reliability"]:
                    dominated = True
                    break
        if not dominated:
            pareto.append({**p, "pareto_optimal": True})

    # Mark all designs
    pareto_names = {p["name"] for p in pareto}
    all_points = []
    for p in points:
        all_points.append({**p, "pareto_optimal": p["name"] in pareto_names})

    return all_points


def generate_recommendation(
    results: List[DesignResult],
    matrix: List[TradeoffMatrix],
) -> RecommendationEngine:
    """Generate advisory-level recommendation with reasoning."""

    # Best composite score
    best = max(matrix, key=lambda x: x.composite_score)
    best_result = next(r for r in results if r.design_name == best.design_name)

    # Cheapest
    cheapest = min(results, key=lambda r: r.cost_breakdown.total_lifecycle_cost)
    # Most reliable
    most_reliable = min(results, key=lambda r: r.lifetime_failure_probability)

    reasoning = []

    # Availability assessment
    nines = best_result.availability_nines
    if nines >= 4:
        reasoning.append(
            f"{best.design_name} achieves {nines:.1f} nines of availability "
            f"({best_result.system_availability*100:.4f}%), suitable for mission-critical systems."
        )
    elif nines >= 3:
        reasoning.append(
            f"{best.design_name} achieves {nines:.1f} nines of availability "
            f"({best_result.system_availability*100:.3f}%), appropriate for most business applications."
        )
    else:
        reasoning.append(
            f"{best.design_name} achieves only {nines:.1f} nines of availability — "
            f"consider adding redundancy for production workloads."
        )

    # Cost insight
    cost = best_result.cost_breakdown
    reasoning.append(
        f"Total lifecycle cost of ${cost.total_lifecycle_cost:,.0f} breaks down as: "
        f"${cost.initial_hardware_cost:,.0f} hardware, "
        f"${cost.lifetime_maintenance_cost:,.0f} maintenance, "
        f"${cost.expected_downtime_cost:,.0f} expected downtime losses."
    )

    # SPOFs
    if best_result.single_points_of_failure:
        reasoning.append(
            f"⚠️  Single points of failure identified: {', '.join(best_result.single_points_of_failure)}. "
            f"Adding redundancy to these components would most improve reliability."
        )

    # Weakest link
    reasoning.append(
        f"The weakest link is '{best_result.weakest_link}', contributing disproportionately "
        f"to system unreliability. Upgrading this component yields the highest reliability ROI."
    )

    # Failure probability
    fp = best_result.lifetime_failure_probability
    reasoning.append(
        f"Simulated {best_result.simulated_failures_mean:.1f} failures expected over the design lifetime "
        f"(P99 = {best_result.simulated_failures_p99:.0f} failures). "
        f"Probability of at least one failure: {fp*100:.1f}%."
    )

    # Tradeoff summary
    if best.design_name == cheapest.design_name == most_reliable.design_name:
        tradeoff = f"{best.design_name} dominates all dimensions — it is both cheapest and most reliable."
    elif best.design_name == most_reliable.design_name:
        cost_premium = (
            best_result.cost_breakdown.total_lifecycle_cost
            - cheapest.cost_breakdown.total_lifecycle_cost
        )
        tradeoff = (
            f"The most reliable option ({most_reliable.design_name}) costs "
            f"${cost_premium:,.0f} more than the cheapest ({cheapest.design_name}) over the design lifetime. "
            f"This represents a ${cost_premium/best_result.design_lifetime_years if hasattr(best_result, 'design_lifetime_years') else cost_premium:.0f} "
            f"annual premium for higher assurance."
        )
    else:
        tradeoff = (
            f"{best.design_name} offers the best overall value when reliability, cost, "
            f"and availability are weighted together. The most reliable design is "
            f"{most_reliable.design_name}, while the cheapest is {cheapest.design_name}."
        )

    # Risk assessment
    p99 = best_result.simulated_failures_p99
    if p99 == 0:
        risk = "LOW — Under worst-case (P99) simulation, zero failures are expected."
    elif p99 <= 2:
        risk = f"MEDIUM — Worst-case (P99) scenario shows {p99:.0f} failure(s). Maintain spares inventory."
    else:
        risk = f"HIGH — Worst-case (P99) scenario shows {p99:.0f} failures. Consider design revision."

    # Sensitivity notes
    sensitivity = [
        "Downtime cost assumption heavily drives lifecycle cost — verify actual business impact per outage hour.",
        "MTBF estimates from manufacturer datasheets often reflect ideal conditions; field MTBF may be 50-70% lower.",
        f"Increasing Monte Carlo iterations beyond {10_000:,} improves tail probability accuracy for P99 estimates.",
        "Environmental factors (temperature, humidity, vibration) can reduce component MTBF by 30-80% — consider derating.",
    ]

    return RecommendationEngine(
        recommended_design=best.design_name,
        reasoning=reasoning,
        tradeoff_summary=tradeoff,
        risk_assessment=risk,
        sensitivity_notes=sensitivity,
    )
