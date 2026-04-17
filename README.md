# Auxilia

Auxilia is an AI-powered parametric income-protection platform for gig workers. It combines a rider mobile app, an admin operations dashboard, and a FastAPI backend which monitors live disruption signals such as  rain, traffic, road incidents, and surge drops, to support dynamic protection, automated claims processing, and lastly real-time operational decision-making.

Live website: `https://auxilia.sabarixr.me`

Primary focus lies on the high-pressure Q-commerce and food-delivery riders, where 10 to 20 minute delivery promises, dense urban routing, and disruption-sensitive earnings create distinct risk profiles.

Coverage scope is strict that is, Auxilia covers **loss of income only**. It does not cover health, life, accidents as injury insurance, or vehicle repair costs.

---

## Project Overview

This repo contains three connected applications:

- `backend/` — FastAPI backend: auth, policies, claims, triggers, payments, AI agents, ML models, risk analysis, seeding
- `admin_dashboard/` — Next.js admin panel: riders, policies, claims, analytics, zone heatmaps, trigger monitoring
- `rider_app/` — Flutter app: onboarding, login, policy purchase, claims, map-based route risk

---

## Main Features

### Rider App

- Rider onboarding with persona selection (Q-commerce / Food Delivery), and full profile setup including age band, vehicle type, shift type, and tenure months
- Rider registration and login using phone number and password
- JWT-based session handling with secure token storage
- Weekly policy purchase with ML-backed premium quote, including a full breakdown of risk factors, zone conditions, and pricing note
- Razorpay checkout integration for live and sandbox payment flows, covering both new policy purchase and policy renewal
- Live policy status card showing coverage amount, days remaining, trigger status, and claim eligibility
- Claims submission flow tied to active policy and current trigger state
- Claims history with status tracking (pending, processing, approved, rejected, paid)
- Delivery check-in flow where riders submit their destination coordinates for zone-aware risk evaluation
- Interactive map-based route risk analysis with live traffic, weather samples along the corridor, and news-based incident overlays
- Destination pin selection and full route path visualisation using `flutter_map` and `latlong2`
- Route risk score breakdown: traffic risk, weather risk, incident risk, road closures
- Real-time trigger visibility per zone, including rain, traffic congestion, road disruptions, and surge status
- Profile screen with rider segment details and logout
- Push notification support via Firebase FCM for payout alerts

### Admin Dashboard

- Secure admin login with backend-issued JWTs, stored as HTTP-only cookies
- Protected routes redirect unauthenticated sessions to the login page
- Main dashboard with 8 live KPI stat cards: active policies, total claims, active riders, premium collected, claims paid, pending claims, active triggers, and average risk score
- 30-day claims chart showing total, approved, and rejected counts by date
- Zone distribution chart showing active policies per zone with risk coloring
- Zone heatmap with heat scores derived from rider count, active policies, open claims, and average risk score per zone
- Interactive zone map rendered with OpenStreetMap tiles
- Riders list with full profile — name, phone, persona, zone, age band, vehicle type, shift type, tenure, risk score, and status
- Add rider form for manual onboarding with all segment fields
- Claims list with filters by status and trigger type, and per-claim detail view including fraud assessment
- Manual claim approve and reject actions with admin confirmation
- Policies list with filters, per-policy detail view, and days-remaining indicator
- CSV export for both riders and policies
- Triggers page with live per-zone status for all four trigger types: rain (OpenWeatherMap), traffic (TomTom), road disruption (NewsAPI), and surge
- Per-zone drill-down for weather forecast, traffic incidents, news incidents, and surge forecast
- Trigger history log with zone and type filtering
- Trigger thresholds page showing configurable values for all trigger types
- Pricing alerts page surfacing weekly premium adjustment recommendations per zone based on live risk signals
- Analytics page with revenue metrics, loss ratio, rider persona breakdown, and trigger distribution charts
- Settings page showing JWT configuration, payout thresholds, and trigger configuration reference
- Live header notification panel fed from the dashboard alerts API (pending claims, expiring policies, active triggers)

### Backend

- Rider registration with real-time ML risk scoring at signup; risk score stored on the rider record
- Rider login and token refresh
- Admin login with static credential check and JWT issuance
- Role-based JWT validation, FastAPI dependencies protecting all sensitive routes
- Background trigger polling loop running on a configurable interval (default: 5 minutes), checking all configured zones for rain, traffic, surge, and road disruption signals
- Zone context resolution supporting explicit zone ID, nearest database zone from GPS coordinates, and dynamic reverse-geocoded fallback
- Premium calculation with an ML premium multiplier (Random Forest, `premium-rf-v1`), zone factor, weekly adjustment from live risk signals, duration factor, and GST
- Policy creation, renewal, and cancellation; active policy guard prevents double-purchase
- Simulated blockchain generated on every policy creation and claim payout for tamper-evident logging
- Razorpay order creation and payment confirmation with HMAC signature verification
- Claim submission: async background task runs fraud validation and payout processing after claim creation
- FraudAgent: five parallel validation checks — GPS location verification, duplicate claim detection, weekly claim frequency analysis, trigger verification, and behavioral anomaly detection — powered by an ML classifier
- PayoutAgent: graduated payout calculation based on trigger excess ratio and trigger-type multipliers; UPI payout via Razorpay Payouts API (sandbox fallback); push notification via Firebase FCM; blockchain record logging
- RiskAgent: composite risk scoring from zone base risk, live weather risk, live traffic risk, news incident risk, claim history, and rider demographic profile (age band, vehicle type, shift type, tenure); ML risk model; seasonal monsoon adjustment; persona factor
- Route risk analysis endpoint: samples weather and traffic along the full route path every 5 km, fetches traffic incidents within the route bounding box, pulls destination news via NewsAPI and Gemini, and returns an overall route risk score with breakdown
- Dashboard API: all KPIs, claims chart, zone stats, zone heatmap, live triggers, revenue metrics, rider persona breakdown, trigger distribution, and system alerts
- Weather API: current conditions and 24-hour forecast per zone via OpenWeatherMap
- Rider-level delivery risk endpoint that blends local zone risk with macro regional incident pressure from NewsAPI
- Reverse geocoding via Nominatim for dynamic zone resolution from GPS coordinates
- Segment analytics: per-rider segment summaries for age band, vehicle type, shift type, and tenure, with targeted risk recommendation generation
- Seeded demo data covering riders, zones, policies, claims, and trigger events

---

## AI Agents

Auxilia uses four purpose-built AI agents as the core of its automation layer:

### TriggerAgent
Runs a polling loop on startup. Every poll interval it calls OpenWeatherMap, TomTom, NewsAPI, and the surge service for each configured zone and computes whether each parametric condition (rain ≥ threshold mm/hr, congestion ≥ threshold level, incident count ≥ threshold, surge multiplier below threshold) is active. Results are cached in memory and served to the trigger status API and dashboard without hitting external APIs on every request.

### RiskAgent
Calculates a composite risk score (0.0–1.0) for each rider at registration and when computing policy premiums. Inputs: zone base risk (historical), live weather risk, live traffic risk, news incident risk, claim history risk, and demographic risk derived from age band, vehicle type, shift type, and tenure months. The gradient boosting ML model produces the base score, which is then calibrated by persona factor and seasonal monsoon factor.

### FraudAgent
Runs five validation checks in parallel when a claim is submitted: GPS location check (was the rider in the trigger zone?), duplicate detection (same zone and trigger type within 24 hours?), weekly frequency check (≤ 3 claims per week), trigger verification (was the trigger actually active?), and behavioral anomaly detection (unusual time-of-day or day-of-week patterns, high rejection rate). The Random Forest classifier fuses these signals into a fraud probability score. Claims above 0.9 are auto-rejected; claims above 0.7 require manual review.

### PayoutAgent
Determines whether an approved claim qualifies for payout, calculates a graduated payout percentage based on how far the trigger value exceeded the threshold (30% / 50% / 75% / 100%), applies trigger-type multipliers (road_disruption: ×1.2, rain: ×1.0, traffic: ×0.8, surge: ×0.6), processes the UPI payment via Razorpay Payouts API, sends a Firebase FCM push notification, and records a blockchain `tx_hash` for the payout.

---

## ML Models

Three scikit-learn models are trained and stored as `.pkl` artifacts under `backend/ml/`:

| Model | Algorithm | Purpose |
|---|---|---|
| `risk_model.pkl` | Gradient Boosting Regressor | Risk score (0–1) per rider and zone |
| `premium_model.pkl` | Random Forest Regressor | Weekly premium multiplier (0.75–1.85) |
| `fraud_model.pkl` | Random Forest Classifier | Fraud probability for claim validation |

Each model has a companion file recording version, training timestamp, row count, and feature names.

Models are auto-trained on startup if artifacts are missing. Manual training, verification, and inspection can be done.

---

## How Auxilia Works

1. A rider signs up on the mobile app. At registration, the RiskAgent runs a full risk assessment and assigns an initial risk score.
2. The rider purchases a weekly protection plan. The ML premium model prices the policy based on zone risk, personal segment, live disruption signals, and duration.
3. Razorpay processes payment. On confirmation, the backend creates the policy with a blockchain `tx_hash`.
4. The TriggerAgent continuously polls live data sources. When a parametric trigger crosses its threshold, the zone's trigger state is marked active.
5. When a rider submits a claim, the FraudAgent validates it in parallel across five checks and the PayoutAgent processes a graduated payout if eligible.
6. Claims, payouts, and trigger states are visible in the rider app and the admin dashboard.

---

## Risk Lens

Auxilia is built around disruption types that directly affect gig income:

- Heavy rain and flooding
- Traffic gridlock and road closures
- Road incidents and corridor slowdowns detected via NewsAPI + Gemini
- Surge drops and platform demand collapse
- EV charging delays and energy-dependent downtime

Risk is not explained only by geography. The backend models rider-segment exposure using age band, shift type, vehicle type, and delivery tenure to surface more precise pricing and recommendations.

Example pricing used in the project:

- Default baseline plan around **Rs 99/week**
- Weekly premium capped between Rs 65 and Rs 249 based on ML multiplier and live signals
- Q-commerce riders priced at a 15% persona premium over food delivery baseline due to tighter SLA pressure
- Late-night and newer riders receive stronger cautionary recommendations in elevated-risk corridors

Graduated payout tiers:

- Trigger just exceeded threshold → 30% of coverage
- 25% over threshold → 50% of coverage
- 50% over threshold → 75% of coverage
- Double or more → 100% of coverage

---

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy (async), Pydantic v2, aiosqlite (SQLite dev), JWT (python-jose), bcrypt, httpx, scikit-learn, joblib, numpy
- **Admin Dashboard**: Next.js 14 (App Router), React, TypeScript, Tailwind CSS, Recharts, Lucide icons
- **Rider App**: Flutter, Riverpod (state management), Dio (HTTP), GoRouter, flutter_map, Geolocator, Geocoding, Razorpay Flutter, flutter_secure_storage, Lottie, Google Fonts, Shimmer
- **Integrations**: Razorpay (payments and payouts), OpenWeatherMap (weather triggers), TomTom (traffic triggers and route data), NewsAPI + Gemini (road incident detection), Firebase FCM (push notifications), Nominatim/OpenStreetMap (reverse geocoding)

---

## Repository Structure

```text
Auxilia/
├── backend/
│   ├── app/
│   │   ├── agents/        # TriggerAgent, RiskAgent, FraudAgent, PayoutAgent
│   │   ├── core/          # config, database, security (JWT, bcrypt)
│   │   ├── models/        # SQLAlchemy models, Pydantic schemas
│   │   ├── routers/       # auth, riders, policies, claims, payments, triggers,
│   │   │                  # zones, dashboard, weather, route_risk
│   │   └── services/      # weather_service, traffic_service, news_service,
│   │                      # surge_service, location_service, ml_service
│   ├── ml/                # Model artifacts (.pkl + _meta.json)
│   ├── scripts/
│   │   ├── train_ml_models.py
│   │   ├── check_ml_models.py
│   │   └── seed_data.py
│   ├── main.py
│   ├── seed.py
│   └── requirements.txt
├── admin_dashboard/
│   ├── src/
│   │   ├── app/           # Next.js App Router pages
│   │   │   ├── page.tsx          # Dashboard
│   │   │   ├── login/
│   │   │   ├── riders/
│   │   │   ├── policies/
│   │   │   ├── claims/
│   │   │   ├── triggers/
│   │   │   ├── analytics/
│   │   │   └── settings/
│   │   ├── components/
│   │   │   ├── dashboard/        # StatCard, ClaimsChart, LiveTriggers, ZoneMap, etc.
│   │   │   └── layout/           # Sidebar, Navbar
│   │   ├── lib/           # API clients, auth helpers, utils
│   │   └── types/
│   └── package.json
├── rider_app/
│   ├── lib/
│   │   ├── core/          # router, services, providers, theme, constants
│   │   ├── features/
│   │   │   ├── splash/
│   │   │   ├── onboarding/
│   │   │   ├── home/
│   │   │   ├── policy/
│   │   │   ├── claims/
│   │   │   └── profile/
│   │   └── shared/
│   └── pubspec.yaml
├── .env.sample
└── README.md
```

---

## Local Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp ../.env.sample .env          # then fill in your API keys
python scripts/train_ml_models.py
python seed.py
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The training step creates:

- `backend/ml/risk_model.pkl` and `backend/ml/risk_model_meta.json`
- `backend/ml/premium_model.pkl` and `backend/ml/premium_model_meta.json`
- `backend/ml/fraud_model.pkl` and `backend/ml/fraud_model_meta.json`

If these model artifacts are missing, all three services auto-train baseline models on startup so risk, premium, and fraud calculations run in ML mode from the first request.

Backend API docs are available at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` (ReDoc).

Health check endpoint: `http://localhost:8000/health`

### ML Checkpoints and Verification

Run these commands from `backend/`:

```bash
# Train or refresh all three models
python scripts/train_ml_models.py

# Offline inference smoke check for risk, premium, and fraud (no external API calls)
python scripts/check_ml_models.py

# Optional live-mode check — requires valid API keys in .env
python scripts/check_ml_models.py --live
```

Inspect model metadata:

```bash
cat ml/risk_model_meta.json
cat ml/premium_model_meta.json
cat ml/fraud_model_meta.json
```

Each metadata file includes: `model_name`, `version`, `trained_at`, `train_rows`, `feature_names`.

### Reviewer Checklist (ML Mapping)

1. Train models: `python scripts/train_ml_models.py`
2. Run offline inference check: `python scripts/check_ml_models.py`
3. Confirm model artifacts exist: `ls ml` — you should see `risk_model.pkl`, `premium_model.pkl`, `fraud_model.pkl` and their `*_meta.json` files.
4. Confirm runtime usage:
   - Risk model → `RiskAssessment.final_risk_score` in `backend/app/agents/risk_agent.py`
   - Premium model → `premium_multiplier` and `final_premium` in `backend/app/routers/policies.py`
   - Fraud model → `fraud_score` / `fraud_probability` in `backend/app/agents/fraud_agent.py` and `backend/app/routers/claims.py`
5. Optional live validation: `python scripts/check_ml_models.py --live`

### Admin Dashboard

```bash
cd admin_dashboard
npm install
npm run dev
```

Dashboard runs on `http://localhost:3000`. Make sure `NEXT_PUBLIC_API_URL` in your `.env.local` points to the running backend.

### Rider App

```bash
cd rider_app
flutter pub get
flutter run
```

For emulator or physical device testing, set the API base URL in `rider_app/lib/core/services/api_service.dart` to the reachable backend host (e.g. your local machine IP on the same network, or the production URL).

Supported platforms: Android, iOS.

---

## Environment Setup

Use the root sample env file as the single source of truth:

```bash
cp .env.sample backend/.env
cp .env.sample admin_dashboard/.env.local
```

Then update only the variables each app needs.

### `.env.sample` Reference

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing secret (change before deploying) |
| `ALGORITHM` | JWT algorithm (default: HS256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes (default: 1440 = 24 hours) |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Admin login credentials |
| `DATABASE_URL` | SQLAlchemy async URL (default: SQLite; swap to PostgreSQL for production) |
| `OPENWEATHER_API_KEY` | Rain trigger data source |
| `TOMTOM_API_KEY` | Traffic congestion and route traffic data |
| `NEWS_API_KEY` | Road incident detection |
| `GEMINI_API_KEY` | Incident relevance scoring augmentation |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | Policy payment and claim payout processing |
| `RAZORPAY_ACCOUNT_NUMBER` | Required for Razorpay Payouts API |
| `FIREBASE_SERVER_KEY` | FCM push notifications for payout alerts |
| `BLOCKCHAIN_RPC_URL` / `CONTRACT_ADDRESS` / `WALLET_PRIVATE_KEY` | Optional on-chain claim ledger |
| `RAIN_THRESHOLD_MM` | Rain trigger threshold in mm/hr (default: 50.0) |
| `TRAFFIC_THRESHOLD_PERCENT` | Traffic congestion threshold 0–10 scale (default: 60.0) |
| `SURGE_THRESHOLD_MULTIPLIER` | Surge trigger fires when multiplier drops below this (default: 2.5) |
| `ROAD_DISRUPTION_THRESHOLD_COUNT` | Incident count threshold per zone (default: 3) |
| `TRIGGER_POLL_INTERVAL` | Seconds between trigger polling cycles (default: 300) |
| `RAIN_PAYOUT` / `TRAFFIC_PAYOUT` / `SURGE_PAYOUT` / `ROAD_DISRUPTION_PAYOUT` | Payout amounts in Rs per trigger type |
| `DEFAULT_CITY` / `DEFAULT_COUNTRY` | Fallback location for zone resolution |
| `NEXT_PUBLIC_API_URL` | Backend base URL for the admin dashboard |

All Razorpay, Firebase, and blockchain keys are optional. When not set, the backend runs in sandbox mode with simulated payouts and notifications.

---

## Seeded Demo Rider

After running `python seed.py`, log in on the rider app with:

- **Phone**: `+919876543200`
- **Password**: `rider123`

The seed also provisions Mumbai delivery zones, multiple riders with varied segment profiles (age band, vehicle type, shift type, tenure months), active policies, claims at different statuses, and historical trigger events for a realistic demo state.

---

## API Routes Summary

All routes are prefixed with `/api/v1`.

| Prefix | Tag | Notes |
|---|---|---|
| `/auth` | Auth | Rider register, rider login, rider me, admin login, admin me |
| `/riders` | Riders | CRUD, segment analytics, risk assessment, route risk, location history |
| `/policies` | Policies | Create, list, get, cancel, renew, calculate premium, pricing alerts, stats |
| `/claims` | Claims | Create, list, get, details, approve, reject, stats |
| `/payments` | Payments | Razorpay order creation and payment confirmation for new and renewal flows |
| `/triggers` | Triggers | Zone status, trigger check, active list, history, weather, traffic, news, surge, thresholds, affected policies |
| `/zones` | Zones | Zone management |
| `/dashboard` | Dashboard | Stats, claims chart, zone stats, zone heatmap, live triggers, revenue metrics, persona breakdown, alerts, architecture |
| `/weather` | Weather | Current conditions and forecast (separate from trigger weather) |

---

## Deployment Notes

The production site at `https://auxilia.sabarixr.me` runs with:

- Backend: FastAPI on a VPS behind a reverse proxy (Nginx/Caddy), served with `uvicorn`
- Admin Dashboard: deployed on Vercel with `NEXT_PUBLIC_API_URL` set to the production backend
- Rider App: Flutter build installed on Android device or emulator pointing to the production backend

For a PostgreSQL upgrade (recommended for production), install the postgres extras:

```bash
pip install -r requirements-postgres.txt
```

Then update `DATABASE_URL` in `.env`:

```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/auxilia
```

---

## Current Status

Auxilia is in strong demo-ready shape with working end-to-end flows across:

- Rider onboarding, registration, and JWT login
- ML-priced policy purchase via Razorpay
- Automated claim processing with fraud detection and graduated payouts
- Background trigger polling with live weather, traffic, incident, and surge data
- Map-based route risk analysis with live corridor sampling
- Admin dashboard with full operational visibility, live zone heatmaps, and pricing alert recommendations
