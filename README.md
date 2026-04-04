# Auxilia

Auxilia is a parametric income-protection platform for gig workers. It combines a rider mobile app, an admin operations dashboard, and a FastAPI backend that monitors live disruption signals like rain, traffic, and road incidents to support dynamic protection, claims, and operational decision-making.

Live website: `https://auxilia.sabarixr.me`

Primary focus: high-pressure Q-commerce and food-delivery riders, where 10-minute delivery promises, dense urban routing, and disruption-sensitive earnings create very different risk profiles.

Coverage scope is strict: Auxilia covers loss of income only. It does not cover health, life, accidents as injury insurance, or vehicle repair costs.

## Project Overview

This repo contains three connected applications:

- `backend/` - FastAPI API, auth, policies, claims, triggers, payments, risk analysis, seed data
- `admin_dashboard/` - Next.js admin panel for riders, policies, claims, analytics, and triggers
- `rider_app/` - Flutter app for onboarding, rider login, policy purchase, claims, and map-based route risk

## Main Features

### Rider App

- rider onboarding with persona selection and profile setup
- rider login with phone number and password
- weekly policy purchase and renewal aligned to gig-worker earning cycles
- Razorpay checkout integration
- live policy, claims, and trigger visibility
- delivery check-in support
- interactive map-based route risk analysis
- destination pin selection and route visualization
- profile settings and logout

### Admin Dashboard

- admin login protected with backend-issued JWTs
- riders, policies, claims, triggers, and analytics views
- add rider flow
- CSV export for riders and policies
- dynamic header notifications from live backend data
- dashboard metrics reflecting real claims and paid amounts

### Backend

- rider and admin authentication
- rider, zone, policy, claim, trigger, and dashboard APIs
- Razorpay order creation and payment confirmation
- live trigger polling for rain, traffic, surge, and road disruption
- dynamic risk evaluation
- rider-segment analysis using persona, age band, vehicle type, shift type, and tenure
- route risk analysis from rider location to delivery destination
- local seeding for demo and development data

## How Auxilia Works

1. A rider signs up or logs in on the mobile app.
2. The rider purchases a weekly protection plan.
3. The backend tracks live disruption signals and rider delivery context.
4. Risk is calculated using location, trigger data, incidents, and delivery path context.
5. Claims and operational activity become visible in both the rider app and admin dashboard.

All claim logic is tied to verified external disruptions that reduce earning ability. The system does not pay for medical treatment, accident injury, or vehicle repair.

## Risk Lens

Auxilia is designed around disruption types that directly affect gig income:

- heavy rain and flooding
- traffic gridlock and road closures
- road incidents and corridor slowdowns
- surge drops and demand collapse
- platform/app outages that pause dispatch flow
- EV charging delays and energy-dependent downtime

The backend now also models rider-segment exposure with additional context such as age band, shift type, vehicle type, and delivery tenure so risk is not explained only by geography.

Example positioning used in the project:

- food delivery baseline plan around `Rs 99/week`
- Q-commerce riders priced higher due to tighter SLA pressure and route urgency
- late-night and newer riders receive stronger cautionary recommendations in elevated-risk corridors

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Pydantic, SQLite, JWT auth
- Admin Dashboard: Next.js, React, TypeScript, Tailwind CSS
- Rider App: Flutter, Riverpod, Dio, GoRouter, flutter_map, Geolocator
- Integrations: Razorpay, OpenWeatherMap, TomTom, NewsAPI, Gemini

## Repository Structure

```text
Auxilia/
|- backend/
|- admin_dashboard/
|- rider_app/
|- .env.sample
|- README.md
```

## Local Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.sample .env
python seed.py
uvicorn main:app --host 0.0.0.0 --port 8000
```

Backend docs: `http://localhost:8000/docs`

### Admin Dashboard

```bash
cd admin_dashboard
npm install
npm run dev
```

Dashboard runs on `http://localhost:3000`

### Rider App

```bash
cd rider_app
flutter pub get
flutter run
```

For emulator/physical device testing, set the API base URL in `rider_app/lib/core/services/api_service.dart` to a reachable backend host.

## Environment Setup

Use the root sample env file as the single source of truth:

```bash
cp .env.sample backend/.env
cp .env.sample admin_dashboard/.env.local
```

Then update only the variables each app needs.

`.env.sample` includes:

- backend app and database settings
- JWT and admin credentials
- weather, traffic, incident, and AI provider keys
- Razorpay configuration
- payout and trigger thresholds
- admin dashboard API URL

## Seeded Demo Rider

After running `python seed.py`, you can log in with:

- phone: `+919876543200`
- password: `rider123`

Seeded rider records also include richer segment fields such as age band, vehicle type, shift type, and tenure months for demo analytics.

## Current Status

Auxilia is in strong demo-ready shape with working core flows across onboarding, rider login, policy purchase, admin visibility, trigger monitoring, and map-based route risk.
