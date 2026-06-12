# ReliabilityTradeoffLab

> **Monte Carlo trade-off decision engine** — Compare system designs across cost, reliability, and availability to make advisory-level engineering decisions.

[![CI/CD](https://github.com/YOUR_USERNAME/reliability-tradeoff-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/reliability-tradeoff-lab/actions)

---

## What It Does

ReliabilityTradeoffLab simulates system designs under operational constraints using **Monte Carlo methods** and **analytical reliability models**, then generates human-readable advisory recommendations.

**Core analyses:**
- System availability (N nines) and MTBF modeling
- Monte Carlo failure simulation (up to 100,000 iterations)
- Lifecycle cost breakdown: hardware + maintenance + downtime losses
- Failure probability curves with 90% confidence intervals
- Pareto-optimal front across cost vs reliability
- Component-level unreliability attribution
- Single Point of Failure identification
- Weighted composite scoring with recommendation engine

---

## Architecture

```
reliability-tradeoff-lab/
├── backend/                    # FastAPI + NumPy/SciPy simulation engine
│   ├── app/
│   │   ├── api/                # HTTP route handlers
│   │   ├── core/               # Config, settings
│   │   ├── models/             # Pydantic schemas
│   │   └── services/           # Monte Carlo engine + recommendation engine
│   ├── tests/                  # Pytest test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # React + Vite + Plotly
│   ├── src/
│   │   ├── components/         # DesignBuilder, ResultsDashboard, PresetLoader
│   │   ├── api/                # API client
│   │   └── index.css           # Design system
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
└── .github/workflows/ci.yml
```

---

## Quick Start

### Option 1: Docker Compose (recommended)

```bash
git clone https://github.com/YOUR_USERNAME/reliability-tradeoff-lab.git
cd reliability-tradeoff-lab
docker compose up --build
```

- Frontend: http://localhost
- API docs: http://localhost:8000/api/docs

### Option 2: Local Development

**Backend**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# → http://localhost:8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## API Reference

### `POST /api/v1/simulate`

Run Monte Carlo simulation across multiple system designs.

**Request body:**
```json
{
  "monte_carlo_iterations": 10000,
  "designs": [
    {
      "name": "Budget Design",
      "design_lifetime_years": 5,
      "maintenance_cost_annual_usd": 5000,
      "downtime_cost_per_hour_usd": 2000,
      "components": [
        {
          "name": "Primary Server",
          "cost_usd": 3000,
          "mtbf_hours": 15000,
          "mttr_hours": 8,
          "quantity": 1,
          "redundancy": "none",
          "is_critical": true
        }
      ]
    }
  ]
}
```

**Redundancy options:** `none` | `active` (N+1 parallel) | `standby` (cold standby)

**Response includes:**
- System availability (N nines), MTBF, MTTR
- Failure probability curves (50 time points + CI bands)
- Lifecycle cost breakdown (hardware / maintenance / downtime)
- Monte Carlo percentiles: P50, P90, P95, P99
- Pareto front (cost vs reliability)
- Tradeoff scorecard with composite scores
- Advisory recommendation with reasoning

### `GET /api/v1/presets`

Returns built-in example designs for quick demos.

### `GET /api/health`

Health check endpoint.

Interactive docs: **http://localhost:8000/api/docs**

---

## Reliability Model

The simulation uses the **exponential failure model** (constant hazard rate, memoryless):

```
R(t) = e^(-λt)     where λ = 1/MTBF
A = MTBF / (MTBF + MTTR)
```

**Redundancy models:**

| Type | System failure condition | Effective availability |
|------|--------------------------|------------------------|
| None | Single unit fails | A |
| Active N+1 | All N+1 units fail simultaneously | 1 - (1-A)^N |
| Cold Standby | k-of-N units unavailable | 1 - (1-A)^N |

**Series system** (critical components):
```
A_sys = ∏ A_i      (all critical components)
λ_sys = Σ λ_i
```

**Monte Carlo process:**
1. For each simulation run, sample failures per component via Poisson process
2. Aggregate system-level failure counts
3. Compute percentile distribution across N iterations
4. Report P50/P90/P95/P99 and probability of zero failures

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt pytest pytest-cov
pytest tests/ -v --cov=app
```

Tests cover: simulation correctness, redundancy models, cost calculations, API validation, and recommendation engine logic.

---

## Deployment

### Railway / Render / Fly.io

Each service (backend, frontend) can be deployed independently. Set `VITE_API_URL` in the frontend environment to point at the deployed backend.

**Backend environment variables:**
```
DEBUG=false
ALLOWED_ORIGINS=https://your-frontend-domain.com
```

### GitHub Container Registry

On merge to `main`, GitHub Actions automatically builds and pushes Docker images to `ghcr.io`:

```bash
docker pull ghcr.io/YOUR_USERNAME/reliability-tradeoff-lab/backend:latest
docker pull ghcr.io/YOUR_USERNAME/reliability-tradeoff-lab/frontend:latest
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI 0.115, Python 3.12 |
| Simulation | NumPy 2.1, SciPy 1.14 |
| Validation | Pydantic v2 |
| Frontend | React 18, Vite 5 |
| Charts | Plotly.js 2.35 |
| Serving | Nginx 1.27 |
| Containers | Docker, Docker Compose |
| CI/CD | GitHub Actions |

---

## License

MIT
