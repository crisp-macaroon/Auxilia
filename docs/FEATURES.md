# Features

## Platform Features

- ML-based risk scoring and premium pricing for weekly income-protection policies.
- Delivery-specific fraud detection with location checks, duplicate/frequency checks, behavior checks, and trigger evidence validation.
- Instant payout simulation with Razorpay-compatible order/confirm and payout workflows.
- Role-based operational visibility for workers and insurers through dedicated rider and admin interfaces.
- Predictive analytics for insurer-side planning, including next-week likely claim volume by zone.

## Rider App

- Onboarding and profile setup with persona/risk context.
- Phone/password authentication with persistent session handling.
- Weekly policy purchase and renewal flows.
- Premium preview with risk-aware pricing signals.
- Claim submission and claim status tracking.
- Live policy card with coverage and active trigger context.
- Delivery check-in and route/zone risk visibility.

### Rider Outcome

The rider view is optimized for confidence and speed: know your coverage, understand why pricing changed, submit claims quickly, and see payout outcomes without relying on manual support loops.

## Admin Dashboard

- Secure admin auth and protected routes.
- Rider, policy, and claim management with filters and detail views.
- Fraud review and manual claim decisions for flagged claims.
- KPI and analytics views including earnings protected, active weekly coverage, loss ratio, and next-week claim predictions.
- Trigger monitoring with zone-level operational insights.

### Insurer Outcome

The admin experience prioritizes decision quality and responsiveness: monitor live risk pressure, review questionable claims, and track portfolio health using live KPIs and forecasts.

## Backend

- REST APIs for auth, riders, policies, claims, payments, triggers, zones, and dashboard metrics.
- Trigger polling from weather/traffic/news/surge sources.
- Agent-driven claim processing pipeline (risk, fraud, payout).
- Predictive analytics endpoints for insurer planning (next-week likely claims).
- Seeded demo data and model artifacts for quick demo setup.

### Engineering Outcome

The backend keeps business logic explicit and testable: pricing, claims, fraud checks, trigger states, and payout decisions are separated into clear APIs and service layers for easier iteration.
