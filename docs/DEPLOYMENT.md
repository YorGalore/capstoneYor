# Deployment

The image serves PANTAU with **gunicorn** (WSGI), **PostgreSQL**, and **WhiteNoise**
for static files. `runserver` and SQLite remain the local development path only.

## Quick start

```bash
cp .env.example .env      # then fill DJANGO_SECRET_KEY and POSTGRES_PASSWORD
docker compose up -d --build
```

Generate a secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

The app is on <http://localhost:8000>. `GET /healthz/` is the readiness probe: it opens a
database connection and returns 503 if that fails, so a worker that cannot reach Postgres
reports itself unhealthy instead of quietly serving errors.

## Configuration

All configuration is environment-driven (`pantau/env.py`). Misconfiguration fails at boot
rather than at runtime — the platform refuses to start rather than start insecurely.

| Variable | Default | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | — | **Required** when `DEBUG` is off. The development key is rejected outright, since it is published in this repository. |
| `DJANGO_DEBUG` | `0` | Production is the default. `manage.py` opts into `1` for local work; gunicorn never passes through `manage.py`, so forgetting to set this cannot expose tracebacks in production. |
| `DJANGO_ALLOWED_HOSTS` | — | **Required** when `DEBUG` is off. `*` is rejected: a wildcard disables Host-header validation, which is what enables poisoned password-reset links. |
| `DJANGO_BEHIND_TLS` | `1` | See below. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | Behind TLS, name the https origin (`https://pantau.go.id`) or Django rejects every POST. |
| `DATABASE_URL` | SQLite | `postgres://user:pass@host:5432/db`. Percent-encoded passwords are decoded. |
| `SEED_DEMO_DATA` | `0` | Seeds fabricated mentions and political actors. **Never enable in production** — on the dashboard it is indistinguishable from real intelligence. |
| `GUNICORN_WORKERS` | `2×CPU+1`, max 8 | |
| `GUNICORN_TIMEOUT` | `120` | Apify collection and brief generation are the slow paths. |

### `DJANGO_BEHIND_TLS`

One switch for the https redirect, the `Secure` flag on the session and CSRF cookies, and
HSTS. They are only ever correct together: a `Secure` cookie is never sent by a browser
over plain http, so leaving the cookies secure while disabling the redirect yields a login
that appears to succeed and then bounces the user back to the form, with nothing in the
logs. This hides in local testing because Chrome treats `http://localhost` as a secure
origin, so it only bites on a real hostname.

`docker-compose.yml` sets it to `0` because it ships no TLS terminator. **Any real
deployment leaves it at the default `1` and terminates TLS in front of gunicorn.**

Verify the production posture with Django's own audit:

```bash
docker compose exec -e DJANGO_BEHIND_TLS=1 web python manage.py check --deploy
# System check identified no issues (0 silenced).
```

## What the container does at start

`entrypoint.sh` waits for the database to answer a real query (not merely accept a TCP
connection, which races the first migration), applies migrations, optionally seeds, then
`exec`s gunicorn so signals reach PID 1 correctly.

Static files are collected at **build** time, so the artifact is complete and every
container starts identically. Filenames are content-hashed and served `immutable`.

## Known limits

- **Migrations run per container.** With more than one replica they will race. Move
  `migrate` into a release step before scaling out.
- **Collection runs execute in the web worker.** `GUNICORN_TIMEOUT` is the honest ceiling
  on a long Apify run; this belongs in a task queue.
- The image runs as the non-root `pantau` user.
