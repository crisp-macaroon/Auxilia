# Ops Automation Setup

This repo now includes automation for:

1. Syncing `main` to your fork on every push.
2. Building Rider APK and publishing to GitHub Releases on every push to `main`.
3. Running backend in Docker.

## 1) Fork Sync

Workflow: `.github/workflows/sync-fork.yml`

Required GitHub repo secrets:

- `FORK_REPO`: `owner/repo` of your fork
- `FORK_TOKEN`: personal access token with `repo` permissions for the fork

Behavior:

- On push to `main`, this workflow pushes `main` to the fork remote.

## 2) APK Release

Workflow: `.github/workflows/release-apk.yml`

Behavior:

- On push to `main` (or manual dispatch), it builds:
  - `rider_app/build/app/outputs/flutter-apk/app-release.apk`
- Publishes a GitHub Release with a timestamp tag like `apk-YYYYMMDD-HHMMSS`.

No extra secrets needed for normal public/private repo release creation because workflow has `contents: write` permission.

## 3) Docker Backend

Added files:

- `backend/Dockerfile`
- `backend/.dockerignore`
- `docker-compose.yml`

Run backend container:

```bash
docker compose up --build
```

Backend will be available at:

- `http://localhost:8000`

Notes:

- Uses `backend/.env` via compose `env_file`.
- Mounts `./backend:/app` for easier local iteration.
