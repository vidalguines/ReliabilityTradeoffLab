"""
Test suite for ReliabilityTradeoffLab API
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def single_component_request():
    return {
        "designs": [
            {
                "name": "Test Design",
                "design_lifetime_years": 5,
                "maintenance_cost_annual_usd": 1000,
                "downtime_cost_per_hour_usd": 500,
                "components": [
                    {
                        "name": "Widget",
                        "cost_usd": 100,
                        "mtbf_hours": 10000,
                        "mttr_hours": 4,
                        "quantity": 1,
                        "redundancy": "none",
                        "is_critical": True,
                    }
                ],
            }
        ],
        "monte_carlo_iterations": 1000,
    }


@pytest.fixture
def two_design_request():
    return {
        "designs": [
            {
                "name": "Budget",
                "design_lifetime_years": 3,
                "maintenance_cost_annual_usd": 2000,
                "downtime_cost_per_hour_usd": 1000,
                "components": [
                    {
                        "name": "Cheap Part",
                        "cost_usd": 500,
                        "mtbf_hours": 8000,
                        "mttr_hours": 6,
                        "quantity": 1,
                        "redundancy": "none",
                        "is_critical": True,
                    }
                ],
            },
            {
                "name": "Premium",
                "design_lifetime_years": 3,
                "maintenance_cost_annual_usd": 5000,
                "downtime_cost_per_hour_usd": 1000,
                "components": [
                    {
                        "name": "Premium Part",
                        "cost_usd": 5000,
                        "mtbf_hours": 100000,
                        "mttr_hours": 2,
                        "quantity": 2,
                        "redundancy": "active",
                        "is_critical": True,
                    }
                ],
            },
        ],
        "monte_carlo_iterations": 2000,
    }


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_check():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"


# ── Simulation ────────────────────────────────────────────────────────────────

def test_simulate_single_design(single_component_request):
    r = client.post("/api/v1/simulate", json=single_component_request)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert len(data["design_results"]) == 1
    dr = data["design_results"][0]
    assert 0 < dr["system_availability"] <= 1
    assert dr["availability_nines"] > 0
    assert dr["cost_breakdown"]["total_lifecycle_cost"] > 0


def test_simulate_two_designs_returns_recommendation(two_design_request):
    r = client.post("/api/v1/simulate", json=two_design_request)
    assert r.status_code == 200
    data = r.json()
    assert "recommendation" in data
    rec = data["recommendation"]
    assert rec["recommended_design"] in ["Budget", "Premium"]
    assert len(rec["reasoning"]) > 0


def test_tradeoff_matrix_scores_in_range(two_design_request):
    r = client.post("/api/v1/simulate", json=two_design_request)
    assert r.status_code == 200
    matrix = r.json()["tradeoff_matrix"]
    for entry in matrix:
        assert 0 <= entry["reliability_score"] <= 100
        assert 0 <= entry["cost_score"] <= 100
        assert 0 <= entry["availability_score"] <= 100
        assert 0 <= entry["composite_score"] <= 100
        assert entry["recommendation_tier"] in ["recommended", "acceptable", "avoid"]


def test_pareto_front_returned(two_design_request):
    r = client.post("/api/v1/simulate", json=two_design_request)
    assert r.status_code == 200
    pareto = r.json()["pareto_front"]
    assert len(pareto) >= 1
    for p in pareto:
        assert "pareto_optimal" in p


def test_premium_more_available_than_budget(two_design_request):
    r = client.post("/api/v1/simulate", json=two_design_request)
    assert r.status_code == 200
    results = {d["design_name"]: d for d in r.json()["design_results"]}
    assert results["Premium"]["system_availability"] > results["Budget"]["system_availability"]


def test_presets_endpoint():
    r = client.get("/api/v1/presets")
    assert r.status_code == 200
    data = r.json()
    assert "presets" in data
    assert len(data["presets"]) >= 1


def test_invalid_mtbf_rejected():
    bad_req = {
        "designs": [
            {
                "name": "Bad",
                "design_lifetime_years": 3,
                "maintenance_cost_annual_usd": 0,
                "downtime_cost_per_hour_usd": 0,
                "components": [
                    {
                        "name": "Part",
                        "cost_usd": 100,
                        "mtbf_hours": -1,   # invalid
                        "quantity": 1,
                        "is_critical": True,
                    }
                ],
            }
        ],
        "monte_carlo_iterations": 1000,
    }
    r = client.post("/api/v1/simulate", json=bad_req)
    assert r.status_code == 422


def test_reliability_curve_has_correct_shape(single_component_request):
    r = client.post("/api/v1/simulate", json=single_component_request)
    assert r.status_code == 200
    curve = r.json()["design_results"][0]["reliability_curve"]
    assert len(curve) > 0
    # Reliability should be monotonically decreasing
    reliabilities = [pt["reliability"] for pt in curve]
    assert all(reliabilities[i] >= reliabilities[i + 1] - 1e-6 for i in range(len(reliabilities) - 1))
    # First point should be near 1.0
    assert curve[0]["reliability"] == pytest.approx(1.0, abs=0.01)


def test_redundant_design_has_higher_availability():
    req = {
        "monte_carlo_iterations": 1000,
        "designs": [
            {
                "name": "No Redundancy",
                "design_lifetime_years": 3,
                "maintenance_cost_annual_usd": 0,
                "downtime_cost_per_hour_usd": 0,
                "components": [{
                    "name": "Part", "cost_usd": 100, "mtbf_hours": 10000,
                    "mttr_hours": 4, "quantity": 1, "redundancy": "none", "is_critical": True
                }],
            },
            {
                "name": "With Redundancy",
                "design_lifetime_years": 3,
                "maintenance_cost_annual_usd": 0,
                "downtime_cost_per_hour_usd": 0,
                "components": [{
                    "name": "Part", "cost_usd": 100, "mtbf_hours": 10000,
                    "mttr_hours": 4, "quantity": 2, "redundancy": "active", "is_critical": True
                }],
            },
        ],
    }
    r = client.post("/api/v1/simulate", json=req)
    assert r.status_code == 200
    results = {d["design_name"]: d for d in r.json()["design_results"]}
    assert results["With Redundancy"]["system_availability"] > results["No Redundancy"]["system_availability"]
