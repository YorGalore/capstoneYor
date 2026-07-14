FROM python:3.13-slim

# Unbuffered stdout so logs reach the container runtime immediately rather than sitting
# in a buffer when the process is killed; no .pyc files in a layer nobody reuses.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Dependencies first: this layer is cached and only rebuilt when requirements change,
# so an application edit does not reinstall Postgres drivers and cryptography.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The repo lives on a Windows filesystem, which carries no exec bit, so without this the
# entrypoint fails with a bare "permission denied" that says nothing about why.
RUN chmod +x /app/entrypoint.sh

# Collect static at build time so the artifact is complete and every container starts
# identically. DJANGO_DEBUG=0 is required here, not incidental: it is what selects the
# hashing manifest storage, and manage.py would otherwise default to development mode
# and produce no manifest for WhiteNoise to serve from at runtime.
#
# These two values exist only for the duration of this RUN. They are not ENV, so they
# are not baked into the image and cannot become the runtime secret by accident — the
# real DJANGO_SECRET_KEY is supplied by the deployment.
RUN DJANGO_DEBUG=0 \
    DJANGO_SECRET_KEY=build-time-only-never-used-to-serve-traffic \
    DJANGO_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput

# Run as a non-root user: a container breakout starts from whatever the process is, and
# there is no reason for a Django worker to be root.
RUN useradd --system --create-home --uid 1001 pantau \
    && chown -R pantau:pantau /app
USER pantau

EXPOSE 8000

# Uses the app's own readiness probe, which checks the database rather than merely
# proving the socket is open. No curl in the image, so this goes through Python.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz/', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "pantau.wsgi:application", "--config", "gunicorn.conf.py"]
