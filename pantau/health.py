"""Container health probe.

Answers honestly about whether this worker can actually serve traffic. A process that
is accepting sockets but cannot reach Postgres is not healthy, and reporting it as
healthy is how a broken deploy gets rolled out to every replica.
"""
from django.contrib.auth.decorators import login_not_required
from django.db import OperationalError, connection
from django.http import JsonResponse


@login_not_required
def healthz(request):
    """Readiness probe — exempt from LoginRequiredMiddleware on purpose.

    Without the exemption the probe is answered with a 302 to the login page, which
    an orchestrator reads as unhealthy and some load balancers read as healthy.
    """
    try:
        connection.ensure_connection()
    except OperationalError:
        return JsonResponse({"status": "error", "database": "error"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})
