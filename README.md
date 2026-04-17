# Auxilia

Auxilia is an AI-powered parametric income-protection platform for gig workers.

Gig workers lose earnings when disruptions hit, even when they are actively on shift. Auxilia addresses that gap with a weekly protection model designed for Q-commerce and food-delivery workflows.

The platform combines a rider mobile app, an admin operations dashboard, and a FastAPI backend that monitors live disruption signals (rain, traffic, road incidents, and low-demand surge windows) to support risk-aware pricing, claim validation, and fast payout decisions.

In short: riders buy weekly coverage, triggers are monitored continuously, claims are validated through fraud checks, and eligible payouts are processed through a simulated instant-settlement flow.

Repository components:
- [backend](backend/) (FastAPI): auth, policies, claims, fraud checks, payouts, trigger monitoring
- [admin_dashboard](admin_dashboard/) (Next.js): insurer/admin operations and analytics
- [rider_app](rider_app/) (Flutter): rider onboarding, policy purchase, claims, live status

Live links:
- Web dashboard: [https://auxilia.sabarixr.me](https://auxilia.sabarixr.me)
- Backend API: [https://auxila-api.sabarixr.me](https://auxila-api.sabarixr.me)

## Core Scope

Auxilia covers **loss of income** from operational disruptions (rain, traffic, road incidents, low-demand surge windows). It is not a health/life/vehicle damage insurance product.

## Key Features

- **Rider experience**: structured onboarding, weekly policy purchase and renewal, policy health visibility, and claim submission with transparent status progression.
- **Insurer operations**: centralized rider/policy/claim control, flagged-claim review workflows, and operational analytics for coverage and payouts.
- **Risk and pricing intelligence**: ML-backed risk scoring and premium computation using live disruption signals plus rider and zone context.
- **Fraud and payout automation**: delivery-specific validation checks (location, trigger evidence, duplicate/frequency patterns, behavior) followed by an instant payout simulation path for eligible claims.

Detailed feature mapping is available in [docs/FEATURES.md](docs/FEATURES.md).

## What Makes It Different

- **Zone-first protection logic**: Auxilia evaluates risk and claim eligibility at the delivery-zone level, not with a one-size-fits-all city average. This makes policy decisions more realistic for dense urban operations where two nearby areas can have very different disruption profiles.
- **Built for short delivery windows**: pricing and claim logic are tuned for high-pressure 10-20 minute delivery cycles, where even short disruptions can erase a worker's expected shift earnings.
- **Multi-trigger parametric model**: the platform is not rain-only. It combines rainfall intensity, traffic congestion, road disruption signals, and low-demand surge drops to represent real working conditions.
- **Fast, explainable claim path**: each claim moves through transparent checks (location validity, trigger evidence, duplicate/frequency, behavior), then into payout simulation for eligible cases.
- **Worker + insurer aligned metrics**: worker-facing coverage outcomes (earnings protected, active weekly coverage) are paired with insurer-facing controls (loss ratio, fraud posture, next-week likely claim forecasts).

## Reviewer Snapshot

- **What this project demonstrates**: end-to-end parametric coverage lifecycle from policy purchase to claim validation to payout.
- **Who it is for**: delivery workers operating in disruption-heavy urban zones.
- **What is production-ready in this repo**: live dashboard + API deployment, trigger monitoring, seeded demo data, and reproducible local setup.
- **Where to validate quickly**: [docs/SETUP.md](docs/SETUP.md) for run steps and demo credentials, then [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system and user flow.

## Navigate This Repo

- Product code: [backend/](backend/), [admin_dashboard/](admin_dashboard/), [rider_app/](rider_app/)
- Project docs: [docs/README.md](docs/README.md), [docs/FEATURES.md](docs/FEATURES.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/API.md](docs/API.md), [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md), [docs/SETUP.md](docs/SETUP.md), [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## Demo Access

For local or hosted demo walkthroughs, use:
- Admin: `admin` / `auxilia123` (or values from `backend/.env`)
- Rider: `+919876543200` / `rider123`

## Quick Start

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.sample .env
python scripts/train_ml_models.py
python seed.py
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Admin dashboard
cd ../admin_dashboard
npm install
npm run dev

# Rider app
cd ../rider_app
flutter pub get
flutter run
```

## Documentation

Start here: [docs/README.md](docs/README.md)

- Features: [docs/FEATURES.md](docs/FEATURES.md) - complete capability breakdown across rider app, admin dashboard, and backend.
- Architecture and flow diagrams: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - high-level system map plus product usage flow.
- Setup and demo credentials: [docs/SETUP.md](docs/SETUP.md) - local run commands and seeded login details.
- Environment variables (`.env.sample`): [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) - practical variable reference and defaults.
- API route map: [docs/API.md](docs/API.md) - route groups and important endpoints.
- Deployment notes: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - GHCR, VM runtime, Nginx, and TLS setup.

## Visuals

Architecture and product flow Mermaid diagrams are already included in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). PNG/SVG screenshots and flow images can be added later without changing this structure.

## API Docs

When backend is running locally:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`
