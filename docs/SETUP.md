# Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 20+
- Flutter SDK

## Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.sample .env
python scripts/train_ml_models.py
python seed.py
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Useful local endpoints:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Admin Dashboard

```bash
cd admin_dashboard
npm install
npm run dev
```

Runs at `http://localhost:3000`.

## Rider App

```bash
cd rider_app
flutter pub get
flutter run
```

## Demo Login Credentials

Seed these from `python seed.py`.

- Admin
  - Username: `admin`
  - Password: `auxilia123`
- Rider
  - Phone: `+919876543200`
  - Password: `rider123`
