# Auxilia

Auxilia is income protection for gig workers — the ones doing Q-commerce and food delivery, who lose shift earnings when disruptions hit and currently have nowhere to turn.

It has three parts: a rider mobile app, an admin ops dashboard, and a FastAPI backend that monitors live disruption signals (rain, traffic, road incidents, demand drops) to handle pricing, claim validation, and payouts.

Riders buy weekly coverage. The backend watches triggers continuously. Claims go through fraud checks. Eligible payouts go out through a simulated instant-settlement flow. That's the whole loop.

Repository components:
- [backend](backend/) (FastAPI): auth, policies, claims, fraud checks, payouts, trigger monitoring
- [admin_dashboard](admin_dashboard/) (Next.js): insurer/admin operations and analytics
- [rider_app](rider_app/) (Flutter): rider onboarding, policy purchase, claims, live status

Live links:
- Web dashboard: [https://auxilia.sabarixr.me](https://auxilia.sabarixr.me)
- Backend API: [https://auxila-api.sabarixr.me](https://auxila-api.sabarixr.me)

Project docs:
- Presentation deck: [`docs/Auxilia.pptx`](docs/Auxilia.pptx)



## Scope

Loss of income from operational disruptions. Not health, life, or vehicle damage.

## How it works

- Riders onboard, pick a weekly policy, and submit claims through the app with a visible status trail at each step. On the insurer side, admins get rider/policy/claim management, a flagged-claim review queue, and analytics covering coverage and payouts.

- Pricing runs on ML-backed risk scoring that pulls in live disruption signals, rider history, and zone context. Claims go through four checks — location validity, trigger evidence, duplicate/frequency patterns, behavioral signals — before a payout decision gets made.

Detailed feature mapping is available in [docs/FEATURES.md](docs/FEATURES.md).

## What Makes It Different

- Most parametric products price on city-wide averages. Auxilia works at the delivery-zone level. Two zones a kilometer apart in a dense city can have very different disruption profiles, and averaging them together produces bad decisions for everyone.

- It's also not rain-only, which most weather protection products are. Auxilia combines rainfall, traffic congestion, road incidents, and demand-surge drops — a closer approximation of what actually disrupts a delivery shift.

- The claim flow shows its work. Each check is named and visible to the worker. They can see where their claim is and why it's there. That part matters more than it sounds.
## Reviewer Snapshot

- This repo covers the full parametric lifecycle: purchase, monitoring, validation, payout. It's built for delivery workers in disruption-heavy urban areas.

- What's working right now: live dashboard, live API, trigger monitoring, seeded demo data, reproducible local setup.

- Start at docs/SETUP.md for run steps and credentials. Then docs/ARCHITECTURE.md for how it all connects.

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

- Features: [docs/FEATURES.md](docs/FEATURES.md) - full capability breakdown.
- Architecture and flow diagrams: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - system map and usage flow.
- Setup and demo credentials: [docs/SETUP.md](docs/SETUP.md) - local run + demo credentials.
- Environment variables (`.env.sample`): [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) - .env variable reference.
- API route map: [docs/API.md](docs/API.md) - route groups and endpoints.
- Deployment notes: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - GHCR, VM, Nginx, TLS.

## Visuals

Architecture and product flow Mermaid diagrams are already included in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). PNG/SVG screenshots and flow images can be added later without changing this structure.

## API Docs

When running locally:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`
