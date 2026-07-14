#!/bin/sh
# Container entrypoint: get the database ready, then hand the process over to gunicorn.
set -eu

# Postgres accepts TCP connections before it is ready to answer queries, so a plain
# port check races with the first migration. Ask Django itself whether the database
# will talk to us.
if [ -n "${DATABASE_URL:-}" ]; then
  echo "Waiting for the database..."
  attempts=0
  until python -c "
import django, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pantau.settings')
django.setup()
from django.db import connection
connection.ensure_connection()
" 2>/dev/null; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 30 ]; then
      echo "Database did not become reachable after 30 attempts; giving up." >&2
      exit 1
    fi
    sleep 2
  done
  echo "Database is up."
fi

# Migrations run here rather than in the image build, because a build has no database
# and because the schema belongs to the deployment, not the artifact. With more than
# one replica this needs to move to a release step so that N containers do not race.
#
# Sidecars that share this image (the scheduler) set RUN_MIGRATIONS=0: two containers
# applying the same migration concurrently is a race with a corrupt-schema ending, and
# only one of them should own it.
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "Applying migrations..."
  python manage.py migrate --noinput
else
  echo "RUN_MIGRATIONS=0 -- another container owns migrations; waiting for the schema."
  # Do not start work against a half-migrated schema.
  attempts=0
  until python manage.py migrate --check >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 60 ]; then
      echo "Schema is still not migrated after 60 attempts; giving up." >&2
      exit 1
    fi
    sleep 2
  done
  echo "Schema is up to date."
fi

# Demo data is opt-in. Seeding a real deployment with fabricated mentions and fake
# political actors would be indistinguishable from real intelligence to anyone reading
# the dashboard, so this must never be the default.
if [ "${SEED_DEMO_DATA:-0}" = "1" ]; then
  echo "SEED_DEMO_DATA=1 -- seeding demo data (do not enable this in production)."
  python manage.py seed_demo_data
fi

exec "$@"
