#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pantau.settings")
    # manage.py is the developer entry point, so it defaults to development mode.
    # Gunicorn loads pantau.wsgi directly and never passes through here, which is what
    # keeps production DEBUG-off by default: forgetting to set a variable can't be what
    # exposes tracebacks in production. Deployments set DJANGO_DEBUG=0 explicitly, and
    # setdefault leaves that alone.
    os.environ.setdefault("DJANGO_DEBUG", "1")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
