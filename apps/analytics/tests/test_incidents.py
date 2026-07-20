from django.test import TestCase

from apps.analytics.models import Incident, IncidentEvent, OPD
from apps.core.models import Project, Province, Regency, Tenant


class IncidentModelTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.province = Province.objects.create(name="DI Yogyakarta")
        self.regency = Regency.objects.create(province=self.province, name="Sleman")

    def test_incident_defaults_to_open_and_unconfirmed(self):
        opd = OPD.objects.create(project=self.project, name="Dinas PU", slug="pu", abbr="PU")
        incident = Incident.objects.create(
            project=self.project, title="Jalan Rusak", regency=self.regency,
            severity=Incident.SEVERITY_HIGH, assigned_opd=opd,
        )
        self.assertEqual(incident.status, Incident.STATUS_OPEN)
        self.assertFalse(incident.is_confirmed)
        self.assertEqual(incident.mention_count, 0)

    def test_event_records_who_and_what(self):
        incident = Incident.objects.create(
            project=self.project, title="Sampah", severity=Incident.SEVERITY_MEDIUM,
        )
        event = IncidentEvent.objects.create(
            incident=incident, kind=IncidentEvent.KIND_DETECTED,
            description="Terdeteksi otomatis", logged_by="sistem",
        )
        self.assertEqual(list(incident.events.all()), [event])
        self.assertIsNotNone(event.occurred_at)

    def test_board_order_puts_the_most_urgent_incident_first(self):
        for severity in [
            Incident.SEVERITY_LOW, Incident.SEVERITY_CRITICAL,
            Incident.SEVERITY_MEDIUM, Incident.SEVERITY_HIGH,
        ]:
            Incident.objects.create(
                project=self.project, title=severity, severity=severity,
            )

        ordered = [i.severity for i in Incident.objects.all()]

        self.assertEqual(ordered, [
            Incident.SEVERITY_CRITICAL, Incident.SEVERITY_HIGH,
            Incident.SEVERITY_MEDIUM, Incident.SEVERITY_LOW,
        ])

    def test_partial_save_of_severity_still_reorders_the_board(self):
        incident = Incident.objects.create(
            project=self.project, title="Naik", severity=Incident.SEVERITY_LOW,
        )
        other = Incident.objects.create(
            project=self.project, title="Tetap", severity=Incident.SEVERITY_MEDIUM,
        )

        incident.severity = Incident.SEVERITY_CRITICAL
        incident.save(update_fields=["severity"])

        self.assertEqual(list(Incident.objects.all()), [incident, other])
