# Documentation

This folder contains focused project documentation so the root `README.md` stays clean and demo-friendly.

If you are reviewing quickly, start with architecture and setup first, then move to API and deployment details.

## Index

- [FEATURES.md](FEATURES.md) - Feature breakdown across rider app, dashboard, and backend
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture, data flow, and agent pipeline (with Mermaid diagrams)
  - Core diagrams: [AI Core](ARCHITECTURE.md#ai-core-diagram), [Fraud Core](ARCHITECTURE.md#fraud-core-diagram)
- [SETUP.md](SETUP.md) - Local setup, run commands, and demo login credentials
- [ENVIRONMENT.md](ENVIRONMENT.md) - `.env.sample` variable reference and usage guidance
- [API.md](API.md) - API route groups and endpoint responsibilities
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment notes (VM, Docker, GHCR, Nginx, TLS)

## Recommended Reading Order

1. [ARCHITECTURE.md](ARCHITECTURE.md)
2. [FEATURES.md](FEATURES.md)
3. [SETUP.md](SETUP.md)
4. [ENVIRONMENT.md](ENVIRONMENT.md)
5. [API.md](API.md)
6. [DEPLOYMENT.md](DEPLOYMENT.md)
