import os
from pathlib import Path

from pantau import env

BASE_DIR = Path(__file__).resolve().parent.parent

# Production is the default. Turning DEBUG on has to be a deliberate act, so that
# forgetting to set it can never be what exposes tracebacks and settings to the world.
DEBUG = env.get_bool("DJANGO_DEBUG", default=False)
SECRET_KEY = env.get_secret_key(debug=DEBUG)
ALLOWED_HOSTS = env.get_allowed_hosts(debug=DEBUG)

# Django validates the Origin header against this on unsafe methods, and behind a TLS
# terminator the scheme it sees is http, so the https origin must be named explicitly.
CSRF_TRUSTED_ORIGINS = env.get_list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.analytics",
    "apps.coordination",
    "apps.governance",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Gunicorn does not serve static files and DEBUG=False disables Django's static
    # handler, so WhiteNoise is what stops every stylesheet 404ing in production. It
    # sits directly below SecurityMiddleware: any higher and static responses would
    # skip the security headers; any lower and it would do session and auth work it
    # has no use for before returning a file from disk.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
]

ROOT_URLCONF = "pantau.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.tenant_context",
            ],
        },
    },
]

WSGI_APPLICATION = "pantau.wsgi.application"

DATABASES = {
    "default": env.database_config(os.environ.get("DATABASE_URL"), base_dir=BASE_DIR),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "analytics:ringkasan"
LOGOUT_REDIRECT_URL = "login"

LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# collectstatic writes here at image build time; WhiteNoise serves from it at runtime.
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # In production, hash filenames and pre-compress so assets can be cached
        # forever with no stale-asset problem on deploy. The manifest backend refuses
        # to resolve a file that collectstatic has not seen, which is a useful failure
        # in the image and a useless one in dev and tests, where no manifest exists —
        # hence the split.
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Outbound notification email (FR-12.2). Defaults to the console backend so an
# undeployed relay can never make alert evaluation fail; point DJANGO_EMAIL_BACKEND
# at the SMTP backend and set the host variables to actually deliver.
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env.get_bool("DJANGO_EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_DEFAULT_FROM_EMAIL", "pantau@localhost")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{levelname} {asctime} {name} {message}", "style": "{"}},
    "handlers": {
        # Log to stdout, not a file: in a container the collector reads the stream, and
        # a log file inside a replaced container is a log nobody will ever read.
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": env.get_list("DJANGO_LOG_LEVEL", default=["INFO"])[0]},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}

if not DEBUG:
    # One switch, because these settings are only correct together. A Secure cookie is
    # simply never sent by a browser over plain http, so turning off the https redirect
    # while leaving the cookies Secure produces a login that appears to succeed and then
    # bounces the user straight back to the form, with nothing in the logs to explain it.
    # (This hides well in local testing: Chrome treats http://localhost as a secure
    # origin, so it only bites on a real hostname.) Default on — turning TLS off has to
    # be a deliberate act.
    BEHIND_TLS = env.get_bool("DJANGO_BEHIND_TLS", default=True)

    # Gunicorn sits behind a TLS terminator, so Django must learn the original scheme
    # from the proxy — otherwise it thinks every request is plaintext and the redirect
    # below becomes an infinite loop.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = BEHIND_TLS
    # The container's own health probe speaks plain HTTP to localhost and must not be
    # answered with a 301 to https, which would make a healthy worker look unhealthy.
    SECURE_REDIRECT_EXEMPT = [r"^healthz/?$"]

    SESSION_COOKIE_SECURE = BEHIND_TLS
    CSRF_COOKIE_SECURE = BEHIND_TLS
    SECURE_HSTS_SECONDS = 31536000 if BEHIND_TLS else 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = BEHIND_TLS
    SECURE_HSTS_PRELOAD = BEHIND_TLS

    SESSION_COOKIE_HTTPONLY = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

    X_FRAME_OPTIONS = "DENY"
