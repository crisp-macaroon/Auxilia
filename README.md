# Auxilia

Auxilia is an income protection platform for gig workers, built around one frustrating reality: when a rider can't earn because of rain, a traffic jam, or a road closure, they shouldn't have to fill out forms and wait.

---

## What this project does

Three apps working together:

- `rider_app` (Flutter): what riders see — onboarding, their policy, live conditions, and filing a claim.
- `admin_dashboard` (Next.js): ops-side view for policies, claims, triggers, riders, and analytics.
- `backend` (FastAPI): the core — risk evaluation, trigger logic, fraud checks, payouts, zone data.

Current focus: Q-commerce riders, Rs 99/week, covering loss of income.

---

## Why Auxilia exists

Gig workers get hit by short, local disruptions that can wipe out a day's pay:

- heavy rain or flooding
- traffic gridlock
- road-level incidents
- demand dropping out

Normal insurance wasn't built for this. It's slow, document-heavy, and doesn't care that the disruption was two hours long and very real. Auxilia tries to evaluate these events fast, using live signals instead of paperwork.

---

## How it works

1. Rider is onboarded with an active weekly policy.
2. Their location and delivery check-in data are used to build delivery context.
3. The backend evaluates live triggers — weather, traffic, incidents, surge.
4. Risk and fraud checks run before any payout decision.
5. Claims and metrics show up in both the rider app and admin dashboard.

The backend exposes routes under `/api/v1` covering riders, policies, claims, triggers, zones, dashboard, and weather. Health check at `/health`, API docs at `/docs`.

---

## AI in the backend (the practical part)

Four agent-style components handle the heavy lifting:

- **TriggerAgent** — watches live conditions for valid trigger events.
- **RiskAgent** — computes dynamic risk from location and context.
- **FraudAgent** — checks claim consistency and flags suspicious patterns.
- **PayoutAgent** — handles the payout decision path and records transaction evidence.

We also pull external signals (incident feeds, news) to catch disruptions that raw weather or traffic data might miss.

---

## Anti-spoofing

A single GPS coordinate can be faked. So we don't rely on one.

### How we tell genuine riders from spoofers

We look at consistency across time, not a single data point:

- Does the movement make physical sense? Natural routes vs impossible jumps.
- Does the check-in timing line up with the trigger window?
- What's the rider's behavior pattern during claim windows?
- Are multiple riders in the same zone all claiming at the same moment?

### Signals beyond raw coordinates

- Sequential location stream — speed, stops, distance deltas
- Delivery check-in coordinates and order timestamps
- Active trigger context at the time of the claim
- Claim frequency, cooldown violations, duplicates
- Cluster-level synchronization patterns that suggest coordinated abuse

### Keeping it fair for honest riders

Bad network coverage is real. We don't hard-reject riders because their GPS was spotty.

Three outcomes:

1. Verified → fast payout
2. Uncertain → lightweight review
3. High-risk → hold + manual escalation

---

## Repo structure

```
Auxilia/
├── backend/           FastAPI backend, agents, routers, services, seed script
├── admin_dashboard/   Next.js admin app
├── rider_app/         Flutter rider app
└── README.md
```

---

## Local setup

### 1) Backend

From `backend/`:

1. Create and activate a Python virtual environment.
2. `pip install -r requirements.txt`
3. `cp .env.example .env`
4. Fill in API keys (OpenWeatherMap, TomTom, NewsAPI, Gemini).
5. `python main.py`

Runs on `http://localhost:8000`. Docs at `/docs`.

Optional seed data: `python scripts/seed_data.py`

### 2) Admin dashboard

From `admin_dashboard/`:

1. `npm install`
2. Set `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` if on localhost.
3. `npm run dev`

Runs on `http://localhost:3000`.

### 3) Rider app

From `rider_app/`:

1. `flutter pub get`
2. In `rider_app/lib/core/services/api_service.dart`, replace the base URL with your machine's local IP — something like `http://192.168.x.x:8000`. Don't use `localhost`; the Android device won't resolve it.
3. `flutter run -d <YOUR_DEVICE_ID>`

---

## Current status

This is a live hackathon build. Things move fast. As of now all the basic UI and backend architecture are done, at present working on making the fraud detection and better zone based method improvement.

Demo video: [watch here](https://youtu.be/o00wG1vSz_Q)
