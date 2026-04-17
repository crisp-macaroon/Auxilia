# Deployment Notes

## Production Endpoints

- Dashboard: `https://auxilia.sabarixr.me`
- Backend API: `https://auxila-api.sabarixr.me`

## Container Build and Publish

Workflow: `.github/workflows/backend-image.yml`

- Builds backend image from `backend/Dockerfile`
- Publishes to GHCR on `main` changes under `backend/**`

## VM Runtime (Docker + Watchtower)

Backend is deployed as a standalone container and auto-updated by Watchtower.

Example stack:

```yaml
services:
  backend:
    image: ghcr.io/<owner>/auxilia-backend:latest
    restart: unless-stopped
    env_file:
      - /path/to/backend.env
    ports:
      - "8000:8000"

  watchtower:
    image: containrrr/watchtower:1.7.1
    restart: unless-stopped
    environment:
      - DOCKER_API_VERSION=1.41
    command: --interval 60 --cleanup --rolling-restart <backend-container-name>
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

## Reverse Proxy and TLS

Nginx proxies domain traffic to backend container:

- HTTP/HTTPS: `auxila-api.sabarixr.me`
- Upstream: `http://127.0.0.1:8000`

TLS is managed by certbot and auto-renew timer (`certbot.timer`).

## Notes

- Keep ports `80` and `443` open in VM/network rules.
- Keep `8000` private if all traffic goes through Nginx.
