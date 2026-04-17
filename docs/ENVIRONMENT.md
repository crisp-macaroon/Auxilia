# Environment Variables

Use root `.env.sample` as the source of truth.

```bash
cp .env.sample backend/.env
cp .env.sample admin_dashboard/.env.local
```

## Variable Reference

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing key |
| `ALGORITHM` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Admin login credentials |
| `DATABASE_URL` | Backend DB connection string |
| `OPENWEATHER_API_KEY` | Weather trigger source |
| `TOMTOM_API_KEY` | Traffic trigger source |
| `NEWS_API_KEY` | Incident/news trigger source |
| `GEMINI_API_KEY` | Optional incident relevance support |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | Payment + payout integration |
| `RAZORPAY_ACCOUNT_NUMBER` | Razorpay payout account identifier |
| `FIREBASE_SERVER_KEY` | FCM notifications |
| `RAIN_THRESHOLD_MM` | Rain trigger threshold |
| `TRAFFIC_THRESHOLD_PERCENT` | Traffic trigger threshold |
| `SURGE_THRESHOLD_MULTIPLIER` | Surge trigger threshold |
| `ROAD_DISRUPTION_THRESHOLD_COUNT` | Incident threshold |
| `TRIGGER_POLL_INTERVAL` | Trigger polling interval (seconds) |
| `RAIN_PAYOUT` / `TRAFFIC_PAYOUT` / `SURGE_PAYOUT` / `ROAD_DISRUPTION_PAYOUT` | Payout amounts by trigger type |
| `NEXT_PUBLIC_API_URL` | Admin dashboard backend URL override |

## Production Defaults in Code

- Admin dashboard defaults to `https://auxila-api.sabarixr.me/api/v1` in production.
- Rider app defaults to `https://auxila-api.sabarixr.me/api/v1` and supports `--dart-define=API_BASE_URL=...`.
