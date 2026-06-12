"""
Pydantic models for ReliabilityTradeoffLab API
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum


class RedundancyType(str, Enum):
    NONE = "none"
    ACTIVE = "active"       # N+1 active parallel
    STANDBY = "standby"     # Cold standby (k-of-n)


class ComponentConfig(BaseModel):
    name: str = Field(..., description="Component name", example="Power Supply")
    cost_usd: float = Field(..., gt=0, description="Unit cost in USD")
    mtbf_hours: float = Field(..., gt=0, description="Mean Time Between Failures (hours)")
    mttr_hours: float = Field(default=4.0, gt=0, description="Mean Time To Repair (hours)")
    quantity: int = Field(default=1, ge=1, le=10, description="Number of units")
    redundancy: RedundancyType = Field(default=RedundancyType.NONE)
    is_critical: bool = Field(default=True, description="System fails if this component fails")

    @validator("name")
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Component name cannot be empty")
        return v.strip()


class SystemDesign(BaseModel):
    name: str = Field(..., description="Design name", example="Budget Design")
    description: Optional[str] = Field(None, description="Design description")
    components: List[ComponentConfig] = Field(..., min_items=1, max_items=20)
    design_lifetime_years: float = Field(default=5.0, gt=0, le=30)
    maintenance_cost_annual_usd: float = Field(default=0.0, ge=0)
    downtime_cost_per_hour_usd: float = Field(default=1000.0, ge=0, description="Business cost per hour of downtime")


class SimulationRequest(BaseModel):
    designs: List[SystemDesign] = Field(..., min_items=1, max_items=5, description="System designs to compare")
    monte_carlo_iterations: int = Field(default=10_000, ge=1000, le=100_000)
    confidence_levels: List[float] = Field(
        default=[0.5, 0.9, 0.95, 0.99],
        description="Confidence levels for failure probability curves"
    )

    @validator("confidence_levels")
    def validate_confidence_levels(cls, v):
        for level in v:
            if not 0 < level < 1:
                raise ValueError("Confidence levels must be between 0 and 1")
        return sorted(v)


# ── Response Models ──────────────────────────────────────────────────────────

class ComponentResult(BaseModel):
    name: str
    cost_usd: float
    mtbf_hours: float
    availability: float
    failure_rate_per_year: float
    annual_expected_failures: float
    contribution_to_system_unreliability: float  # %


class ReliabilityCurvePoint(BaseModel):
    time_hours: float
    reliability: float          # P(no failure by t)
    failure_probability: float  # 1 - reliability
    confidence_lower: float
    confidence_upper: float


class CostBreakdown(BaseModel):
    initial_hardware_cost: float
    lifetime_maintenance_cost: float
    expected_downtime_cost: float
    total_lifecycle_cost: float
    cost_per_nine: float        # $ per "9" of availability (e.g., 99.9% = 3 nines)


class DesignResult(BaseModel):
    design_name: str
    description: Optional[str]

    # Reliability metrics
    system_availability: float          # e.g., 0.9995
    availability_nines: float           # e.g., 3.3
    mtbf_hours: float
    mttr_hours: float
    annual_failure_probability: float
    lifetime_failure_probability: float

    # Monte Carlo results
    simulated_failures_mean: float
    simulated_failures_p50: float
    simulated_failures_p90: float
    simulated_failures_p99: float
    simulation_confidence_interval: Dict[str, float]

    # Cost
    cost_breakdown: CostBreakdown

    # Curves
    reliability_curve: List[ReliabilityCurvePoint]
    failure_rate_curve: List[Dict[str, float]]

    # Component analysis
    component_results: List[ComponentResult]
    weakest_link: str
    single_points_of_failure: List[str]


class TradeoffMatrix(BaseModel):
    """Normalized comparison across designs"""
    design_name: str
    reliability_score: float    # 0-100
    cost_score: float           # 0-100 (lower cost = higher score)
    availability_score: float   # 0-100
    composite_score: float      # weighted average
    recommendation_tier: str    # "recommended" | "acceptable" | "avoid"


class RecommendationEngine(BaseModel):
    recommended_design: str
    reasoning: List[str]
    tradeoff_summary: str
    risk_assessment: str
    sensitivity_notes: List[str]


class SimulationResponse(BaseModel):
    status: str = "success"
    iterations_run: int
    design_results: List[DesignResult]
    tradeoff_matrix: List[TradeoffMatrix]
    recommendation: RecommendationEngine
    pareto_front: List[Dict[str, Any]]     # cost vs reliability Pareto-optimal designs
