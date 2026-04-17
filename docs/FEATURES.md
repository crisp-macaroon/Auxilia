# Features

## Platform Features

- ML-based risk scoring and premium pricing for weekly income-protection policies.
- Fraud detection built for delivery: location checks, duplicate/frequency checks, behavioral signals, and trigger evidence.
- Payout simulation with Razorpay-compatible order/confirm flows.
- Separate interfaces for workers and admins, each scoped to what that role actually needs.
- Predictive analytics for insurer planning — next-week likely claim volume by zone.

## Rider App

- Onboarding and profile setup with risk context.
- Phone/password auth with persistent sessions.
- Weekly policy purchase and renewal.
- Premium preview showing what's driving the price.
- Claim submission and status tracking.
- Live policy card with active coverage and current trigger context.
- Delivery check-in with zone risk visibility.

### Rider Outcome

Workers can check their coverage, see why their premium changed, submit a claim in a few taps, and track the outcome — without having to contact anyone.

## Admin Dashboard

- Admin auth with protected routes.
- Rider, policy, and claim management with filters and detail views.
- Manual review queue for flagged claims.
- KPIs: earnings protected, active weekly coverage, loss ratio, next-week claim predictions.
- Trigger monitoring with zone-level breakdowns.

### Insurer Outcome

Admins can watch live risk signals, review flagged claims before they auto-resolve, and track portfolio health through KPIs and next-week forecasts.

## Backend

- REST APIs for auth, riders, policies, claims, payments, triggers, zones, and dashboard metrics.
- Trigger polling from weather, traffic, news, and surge sources.
- Agent-driven claim pipeline: risk scoring, fraud checks, payout.
- Predictive analytics endpoints for next-week claim volume.
- Seeded demo data and model artifacts for local setup.
### Engineering Outcome

Pricing, fraud checks, trigger states, and payout decisions each live in their own service layer. Easier to test, easier to change one without breaking the others.
