from django.test import TestCase

from apps.analytics import incidents
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


class SeverityTest(TestCase):
    def test_calm_low_volume_issue_is_low(self):
        self.assertEqual(incidents.severity_for(negative_pct=10), Incident.SEVERITY_LOW)

    def test_majority_negative_is_at_least_medium(self):
        self.assertEqual(incidents.severity_for(negative_pct=55), Incident.SEVERITY_MEDIUM)

    def test_overwhelmingly_negative_is_high(self):
        self.assertEqual(incidents.severity_for(negative_pct=75), Incident.SEVERITY_HIGH)

    def test_negative_plus_coordinated_surge_is_critical(self):
        # High negativity AND a volume surge is the shape of a crisis, not a grumble.
        self.assertEqual(
            incidents.severity_for(negative_pct=85, volume_change_pct=250, coordinated=True),
            Incident.SEVERITY_CRITICAL,
        )

    def test_a_surge_escalates_a_merely_negative_issue(self):
        self.assertEqual(
            incidents.severity_for(negative_pct=55, volume_change_pct=250),
            Incident.SEVERITY_HIGH,
        )

    def test_coordinated_activity_lifts_a_calm_issue_above_low(self):
        # Calm sentiment plus coordination is what a manufactured narrative looks
        # like early on, so it must not sit at Low.
        self.assertEqual(
            incidents.severity_for(negative_pct=5, coordinated=True),
            Incident.SEVERITY_MEDIUM,
        )


class CompositionTest(TestCase):
    def _candidate(self, **overrides):
        candidate = {
            "title": "Jalan Rusak", "issue_id": 1, "regency_id": 1,
            "regency_name": "Sleman", "total": 312, "negative_pct": 95,
            "snippets": ["jalan kaliurang km 12 berlubang parah"], "mention_ids": [1, 2],
        }
        candidate.update(overrides)
        return candidate

    def test_every_narrative_field_carries_the_draft_banner(self):
        result = incidents.compose_incident_narrative(self._candidate())
        for field in ("ai_summary", "root_cause", "impact", "recommendation"):
            self.assertIn("DRAF", result[field].upper(), f"{field} missing draft banner")

    def test_summary_states_measured_numbers_and_location(self):
        result = incidents.compose_incident_narrative(self._candidate())
        self.assertIn("312", result["ai_summary"])
        self.assertIn("95", result["ai_summary"])
        self.assertIn("Sleman", result["ai_summary"])

    def test_summary_quotes_source_snippet_rather_than_inventing_narrative(self):
        result = incidents.compose_incident_narrative(self._candidate())
        self.assertIn("jalan kaliurang km 12 berlubang parah", result["ai_summary"])

    def test_recommendation_is_advisory_not_an_automated_action(self):
        result = incidents.compose_incident_narrative(self._candidate())
        # The composer proposes; a human assigns. It must never claim to have acted.
        self.assertIn("disarankan", result["recommendation"].lower())

    def test_composition_does_not_invent_a_root_cause_it_cannot_know(self):
        # Grounding discipline: with no evidence, say so rather than guess.
        result = incidents.compose_incident_narrative(self._candidate(snippets=[]))
        self.assertIn("belum", result["root_cause"].lower())
