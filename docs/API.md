# API Route Map

Base prefix: `/api/v1`

| Prefix | Scope |
|---|---|
| `/auth` | Rider and admin authentication |
| `/riders` | Rider profile, location, analytics |
| `/policies` | Policy creation, renewal, pricing, stats |
| `/claims` | Claim create/process/review/history |
| `/payments` | Payment order + confirmation flows |
| `/triggers` | Trigger checks, status, history |
| `/zones` | Zone configuration and lookup |
| `/dashboard` | KPIs, charts, analytics, forecasts |
| `/weather` | Weather lookups and forecasts |

## Important Endpoints

- Health: `GET /health`
- Swagger: `GET /docs`
- ReDoc: `GET /redoc`
- Dashboard predictive claims: `GET /api/v1/dashboard/predictive-claims`
- Pricing alerts: `GET /api/v1/policies/alerts/pricing`
