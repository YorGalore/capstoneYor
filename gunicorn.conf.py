"""Gunicorn configuration for the PANTAU production image."""
import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Sync workers: this app is ordinary blocking Django (Postgres reads, template renders)
# with no async views, so gevent/uvicorn would add a failure mode and buy nothing.
worker_class = "sync"
workers = int(os.environ.get("GUNICORN_WORKERS", 0)) or min(
    (multiprocessing.cpu_count() * 2) + 1, 8
)
threads = int(os.environ.get("GUNICORN_THREADS", 2))

# Apify collection runs and brief generation are the slow paths; the default 30s would
# kill a worker mid-run. Long collections belong in a task queue eventually — until then
# this is the honest ceiling.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
graceful_timeout = 30
# Keep the socket warm for a proxy in front of us.
keepalive = 5

# Recycle workers periodically so a slow leak in a long-lived process cannot accumulate.
max_requests = 1000
max_requests_jitter = 100

# Trust the reverse proxy's X-Forwarded-Proto so Django sees the original https scheme
# (SECURE_PROXY_SSL_HEADER). Gunicorn only trusts 127.0.0.1 by default, and a proxy in a
# separate container is never 127.0.0.1 from here. Set this to the proxy's address in a
# deployment where the network is not already trusted.
forwarded_allow_ips = os.environ.get("GUNICORN_FORWARDED_ALLOW_IPS", "*")

# Log to stdout/stderr; the container runtime owns log collection.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
# Health probes hit /healthz/ constantly and would otherwise drown the access log.
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(M)sms "%(a)s"'

# Load the app before forking: workers then share the parsed code via copy-on-write,
# cutting memory and making boot failures surface once, at startup, instead of per worker.
preload_app = True
