"""
Simulation API Router
"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models.schemas import SimulationRequest, SimulationResponse
from app.services.simulation_engine import SystemReliabilityEngine
from app.services.recommendation import (
    compute_tradeoff_matrix,
    compute_pareto_front,
    generate_recommendation,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/simulate", response_model=SimulationResponse)
async def run_simulation(request: SimulationRequest):
    """
    Run Monte Carlo reliability simulation across multiple system designs.

    Compares designs on:
    - System availability and MTBF
    - Failure probability curves
    - Total lifecycle cost (hardware + maintenance + downtime)
    - Component-level reliability contributions
    - Pareto-optimal trade-off analysis

    Returns an advisory recommendation with reasoning.
    """
    try:
        results = []
        for design in request.designs:
            logger.info(f"Simulating design: {design.name}")
            engine = SystemReliabilityEngine(design, request.monte_carlo_iterations)
            result = engine.run()
            result.design_lifetime_years = design.design_lifetime_years  # attach for recommendation
            results.append(result)

        matrix = compute_tradeoff_matrix(results)
        pareto = compute_pareto_front(results)
        recommendation = generate_recommendation(results, matrix)

        return SimulationResponse(
            status="success",
            iterations_run=request.monte_carlo_iterations,
            design_results=results,
            tradeoff_matrix=matrix,
            recommendation=recommendation,
            pareto_front=pareto,
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Simulation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.get("/presets")
async def get_presets():
    """
    Return built-in example design presets for quick demos.
    """
    return {
        "presets": [
            {
                "id": "budget_vs_premium",
                "name": "Budget vs Premium Components",
                "description": "Classic cost-reliability tradeoff with two server designs",
                "designs": [
                    {
                        "name": "Budget Design",
                        "description": "Low-cost commodity hardware",
                        "design_lifetime_years": 5,
                        "maintenance_cost_annual_usd": 5000,
                        "downtime_cost_per_hour_usd": 2000,
                        "components": [
                            {
                                "name": "Budget Server",
                                "cost_usd": 3000,
                                "mtbf_hours": 15000,
                                "mttr_hours": 8,
                                "quantity": 1,
                                "redundancy": "none",
                                "is_critical": True,
                            },
                            {
                                "name": "Cheap PSU",
                                "cost_usd": 200,
                                "mtbf_hours": 25000,
                                "mttr_hours": 2,
                                "quantity": 1,
                                "redundancy": "none",
                                "is_critical": True,
                            },
                            {
                                "name": "SATA HDD",
                                "cost_usd": 80,
                                "mtbf_hours": 20000,
                                "mttr_hours": 4,
                                "quantity": 1,
                                "redundancy": "none",
                                "is_critical": True,
                            },
                        ],
                    },
                    {
                        "name": "Standard Design",
                        "description": "Enterprise-grade with basic redundancy",
                        "design_lifetime_years": 5,
                        "maintenance_cost_annual_usd": 8000,
                        "downtime_cost_per_hour_usd": 2000,
                        "components": [
                            {
                                "name": "Enterprise Server",
                                "cost_usd": 8000,
                                "mtbf_hours": 45000,
                                "mttr_hours": 4,
                                "quantity": 1,
                                "redundancy": "none",
                                "is_critical": True,
                            },
                            {
                                "name": "Redundant PSU",
                                "cost_usd": 600,
                                "mtbf_hours": 80000,
                                "mttr_hours": 1,
                                "quantity": 2,
                                "redundancy": "active",
                                "is_critical": True,
                            },
                            {
                                "name": "RAID SSD Array",
                                "cost_usd": 1200,
                                "mtbf_hours": 100000,
                                "mttr_hours": 2,
                                "quantity": 2,
                                "redundancy": "active",
                                "is_critical": True,
                            },
                        ],
                    },
                    {
                        "name": "High Availability Design",
                        "description": "Full redundancy for mission-critical workloads",
                        "design_lifetime_years": 5,
                        "maintenance_cost_annual_usd": 20000,
                        "downtime_cost_per_hour_usd": 2000,
                        "components": [
                            {
                                "name": "HA Server Cluster",
                                "cost_usd": 16000,
                                "mtbf_hours": 60000,
                                "mttr_hours": 2,
                                "quantity": 2,
                                "redundancy": "active",
                                "is_critical": True,
                            },
                            {
                                "name": "Redundant PSU",
                                "cost_usd": 800,
                                "mtbf_hours": 100000,
                                "mttr_hours": 0.5,
                                "quantity": 2,
                                "redundancy": "active",
                                "is_critical": True,
                            },
                            {
                                "name": "NVMe SSD RAID-10",
                                "cost_usd": 2400,
                                "mtbf_hours": 150000,
                                "mttr_hours": 1,
                                "quantity": 4,
                                "redundancy": "active",
                                "is_critical": True,
                            },
                            {
                                "name": "UPS Battery Backup",
                                "cost_usd": 3000,
                                "mtbf_hours": 40000,
                                "mttr_hours": 4,
                                "quantity": 1,
                                "redundancy": "none",
                                "is_critical": False,
                            },
                        ],
                    },
                ],
            },
            {
                "id": "network_infrastructure",
                "name": "Network Infrastructure",
                "description": "Compare single vs redundant network paths",
                "designs": [
                    {
                        "name": "Single Path",
                        "description": "Single ISP, single router",
                        "design_lifetime_years": 3,
                        "maintenance_cost_annual_usd": 2000,
                        "downtime_cost_per_hour_usd": 5000,
                        "components": [
                            {
                                "name": "Core Router",
                                "cost_usd": 5000,
                                "mtbf_hours": 87600,
                                "mttr_hours": 4,
                                "quantity": 1,
                                "redundancy": "none",
                                "is_critical": True,
                            },
                            {
                                "name": "ISP Link",
                                "cost_usd": 500,
                                "mtbf_hours": 17520,
                                "mttr_hours": 8,
                                "quantity": 1,
                                "redundancy": "none",
                                "is_critical": True,
                            },
                        ],
                    },
                    {
                        "name": "Dual Path",
                        "description": "Redundant routers, dual ISP",
                        "design_lifetime_years": 3,
                        "maintenance_cost_annual_usd": 4000,
                        "downtime_cost_per_hour_usd": 5000,
                        "components": [
                            {
                                "name": "Core Router",
                                "cost_usd": 5000,
                                "mtbf_hours": 87600,
                                "mttr_hours": 2,
                                "quantity": 2,
                                "redundancy": "active",
                                "is_critical": True,
                            },
                            {
                                "name": "ISP Link",
                                "cost_usd": 1000,
                                "mtbf_hours": 17520,
                                "mttr_hours": 8,
                                "quantity": 2,
                                "redundancy": "active",
                                "is_critical": True,
                            },
                        ],
                    },
                ],
            },
        ]
    }
