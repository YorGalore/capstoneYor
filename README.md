# PANTAU

Social media monitoring platform for tracking political/government narratives — collection,
sentiment analytics, coordinated-behavior (CIB) detection, alerting, and coordination
workflows for analysts.

Django app, deployed with **gunicorn**, **PostgreSQL**, and **WhiteNoise**. `runserver` +
SQLite are the local development path only.

## Apps

| App | Responsibility |
|---|---|
| `apps.core` | Shared models, auth, signals |
| `apps.analytics` | Sentiment/trend analytics, XLSX exports |
| `apps.coordination` | Coordinated inauthentic behavior (CIB) detection, clusters |
| `apps.governance` | Runtime settings, secrets (Fernet-encrypted), Apify token, audit |

A background **scheduler** process runs collection, alert evaluation, brief generation,
CIB detection, and the retention purge on configurable cadences — see
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Quick start (local dev)

```bash
python -m venv .venv
.venv/Scripts/activate      # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env        # fill DJANGO_SECRET_KEY at minimum
python manage.py migrate
python manage.py runserver
```

## Quick start (production-style, Docker)

```bash
cp .env.example .env        # fill DJANGO_SECRET_KEY and POSTGRES_PASSWORD
docker compose up -d --build
```

App is on <http://localhost:8000>. `GET /healthz/` is the readiness probe (checks the
database connection).

Full configuration reference, the `DJANGO_BEHIND_TLS` posture, scheduler details, and
known limits: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Documentation

- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — deployment, configuration, scheduler
- [`docs/APIFY_INTEGRATION.md`](docs/APIFY_INTEGRATION.md) — data collection integration
- [`docs/design/`](docs/design) — UI design references
- [`docs/diagrams/`](docs/diagrams) — architecture diagrams

## Configuration

All configuration is environment-driven (`pantau/env.py`) and fails at boot on
misconfiguration rather than at runtime. Never commit a filled `.env` — copy
`.env.example` and fill in real values locally/on the server only.
