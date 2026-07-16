"""The scheduler process (REQ-SC-02).

Runs as its own container alongside the web workers. Deliberately separate: a collection
run that takes four minutes would otherwise occupy a gunicorn worker that is supposed to
be answering an analyst's page request.
"""
import logging
import signal
import time

from django.core.management.base import BaseCommand

from apps.governance import scheduling

logger = logging.getLogger(__name__)

DEFAULT_TICK_SECONDS = 30


class Command(BaseCommand):
    help = "Run due scheduled jobs on a loop (collection, alerting, briefs, CIB, purge)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once", action="store_true",
            help="Run the due jobs a single time and exit (for cron or a manual kick).",
        )
        parser.add_argument("--tick", type=int, default=DEFAULT_TICK_SECONDS)

    def handle(self, *args, **options):
        if options["once"]:
            self._tick()
            return

        # A container is stopped with SIGTERM. Finish the job in flight, then exit — being
        # killed mid-collection would leave a CollectionRun stuck in "running" forever,
        # and the overlap-skip guard would then refuse every future run of that source.
        self._running = True

        def stop(signum, frame):
            self.stdout.write("Sinyal berhenti diterima — menyelesaikan siklus ini...")
            self._running = False

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

        self.stdout.write(
            self.style.SUCCESS(f"Penjadwal berjalan (tick {options['tick']}s). Ctrl-C untuk berhenti.")
        )
        while self._running:
            self._tick()
            # Sleep in short slices so a stop signal is honored promptly rather than after
            # a full tick.
            for _ in range(options["tick"]):
                if not self._running:
                    break
                time.sleep(1)

        self.stdout.write("Penjadwal berhenti.")

    def _tick(self):
        try:
            manual_requests = scheduling.run_pending_manual_collections()
            ran = scheduling.run_due()
        except Exception:
            # The loop itself must survive anything — a scheduler that dies on an
            # unexpected error stops the entire platform's monitoring silently.
            logger.exception("Siklus penjadwal gagal")
            return

        for request in manual_requests:
            detail = request.detail or "-"
            self.stdout.write(
                f"manual:{request.collection_type} [{request.project.name}] "
                f"{request.status}: {detail}"
            )

        for job in ran:
            detail = job.last_error or job.last_detail
            line = f"{job.job_type} [{job.project.name}] {job.last_status}: {detail}"
            if job.last_status == job.STATUS_FAILED:
                self.stderr.write(line)
            else:
                self.stdout.write(line)
