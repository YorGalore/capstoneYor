from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.analytics import incidents
from apps.analytics.models import (
    Category, Incident, IncidentEvent, Issue, IssueLabel, Mention, OPD,
    SubCategory,
)
from apps.core.models import Platform, Project, Province, Regency, Tenant


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

    def test_incident_has_empty_draft_response_by_default(self):
        incident = Incident.objects.create(
            project=self.project, title="Jalan Rusak", severity=Incident.SEVERITY_HIGH,
        )
        self.assertEqual(incident.draft_response, "")
        self.assertEqual(incident.response_regulatory_context, [])
        self.assertIsNone(incident.response_generated_at)

    def test_incident_event_supports_response_drafted_kind(self):
        incident = Incident.objects.create(
            project=self.project, title="Sampah", severity=Incident.SEVERITY_MEDIUM,
        )
        event = IncidentEvent.objects.create(
            incident=incident, kind=IncidentEvent.KIND_RESPONSE_DRAFTED,
            description="Draf tanggapan disusun.", logged_by="Operator Satu",
        )
        self.assertEqual(event.get_kind_display(), "Tanggapan disusun")


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

    def test_a_surge_escalates_a_medium_band_issue_to_high(self):
        # 30-50% negative is the Medium band; a surge must escalate it too, not
        # only the >=50% High band (the docstring promises escalation applies
        # generally, but the branch had no escalation arm).
        self.assertEqual(
            incidents.severity_for(negative_pct=35, volume_change_pct=300),
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


class DetectionTest(TestCase):
    def setUp(self):
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.province = Province.objects.create(name="DI Yogyakarta")
        self.regency = Regency.objects.create(province=self.province, name="Depok")
        cat = Category.objects.create(name="Infrastruktur")
        sub = SubCategory.objects.create(category=cat, name="Jalan")
        self.issue = Issue.objects.create(subcategory=sub, name="Jalan Rusak")

    def _mention(self, sentiment, text="jalan berlubang", engagement=0):
        mention = Mention.objects.create(
            project=self.project, platform=self.platform, regency=self.regency,
            author_handle="@warga", content_snippet=text, sentiment=sentiment,
            emotion=Mention.EMOTION_ANGER, posted_at=timezone.now(),
            engagement_count=engagement,
        )
        IssueLabel.objects.create(
            mention=mention, issue=self.issue, source=IssueLabel.SOURCE_AUTO
        )
        return mention

    def test_ignores_clusters_below_the_volume_threshold(self):
        for _ in range(2):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        self.assertEqual(incidents.shortlist_candidates(self.project), [])

    def test_a_small_first_ever_cluster_is_not_treated_as_a_surge(self):
        # Every cluster has an empty prior window on a first-ever run. If that
        # counted as a surge, day one would mark the whole board Critical and the
        # tier would stop meaning anything.
        for _ in range(incidents.MIN_MENTIONS):
            self._mention(Mention.SENTIMENT_NEGATIVE)

        candidate = incidents.shortlist_candidates(self.project)[0]

        self.assertEqual(candidate["volume_change_pct"], 0.0)
        self.assertEqual(
            incidents.severity_for(
                negative_pct=candidate["negative_pct"],
                volume_change_pct=candidate["volume_change_pct"],
            ),
            Incident.SEVERITY_HIGH,
        )

    def test_a_large_first_ever_cluster_is_a_genuine_spike(self):
        # A flood that draws far more than the detection floor within hours has no
        # yesterday to compare against, and is a crisis on arrival.
        for _ in range(incidents.NEW_CLUSTER_SURGE_MENTIONS):
            self._mention(Mention.SENTIMENT_NEGATIVE)

        candidate = incidents.shortlist_candidates(self.project)[0]

        self.assertEqual(
            incidents.severity_for(
                negative_pct=candidate["negative_pct"],
                volume_change_pct=candidate["volume_change_pct"],
            ),
            Incident.SEVERITY_CRITICAL,
        )

    def test_ignores_high_volume_clusters_that_are_not_negative(self):
        for _ in range(10):
            self._mention(Mention.SENTIMENT_POSITIVE)
        self.assertEqual(incidents.shortlist_candidates(self.project), [])

    def test_surfaces_a_negative_cluster_with_measured_counts(self):
        for _ in range(8):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        for _ in range(2):
            self._mention(Mention.SENTIMENT_POSITIVE)

        candidates = incidents.shortlist_candidates(self.project)

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate["title"], "Jalan Rusak")
        self.assertEqual(candidate["total"], 10)
        self.assertEqual(candidate["negative_pct"], 80)
        self.assertEqual(candidate["regency_name"], "Depok")

    def test_quotes_the_highest_engagement_snippets_first(self):
        for _ in range(7):
            self._mention(Mention.SENTIMENT_NEGATIVE, text="biasa", engagement=1)
        self._mention(Mention.SENTIMENT_NEGATIVE, text="viral parah", engagement=999)

        candidate = incidents.shortlist_candidates(self.project)[0]

        self.assertEqual(candidate["snippets"][0], "viral parah")

    def test_ignores_mentions_outside_the_window(self):
        old = timezone.now() - timedelta(days=30)
        for _ in range(8):
            mention = self._mention(Mention.SENTIMENT_NEGATIVE)
            Mention.objects.filter(pk=mention.pk).update(posted_at=old)
        self.assertEqual(incidents.shortlist_candidates(self.project), [])

    def test_same_issue_in_two_regencies_yields_two_candidates(self):
        # Clustering is (issue x regency): the same complaint in two different
        # kecamatan must surface as two separate items, not one merged cluster.
        other_regency = Regency.objects.create(province=self.province, name="Sleman")
        for _ in range(8):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        for _ in range(8):
            mention = Mention.objects.create(
                project=self.project, platform=self.platform, regency=other_regency,
                author_handle="@warga", content_snippet="jalan berlubang parah",
                sentiment=Mention.SENTIMENT_NEGATIVE, emotion=Mention.EMOTION_ANGER,
                posted_at=timezone.now(),
            )
            IssueLabel.objects.create(
                mention=mention, issue=self.issue, source=IssueLabel.SOURCE_AUTO
            )

        candidates = incidents.shortlist_candidates(self.project)

        self.assertEqual(len(candidates), 2)
        regency_names = {c["regency_name"] for c in candidates}
        self.assertEqual(regency_names, {"Depok", "Sleman"})


class VolumeChangeTest(DetectionTest):
    """Fix 2: shortlist_candidates must compute volume_change_pct against the
    immediately preceding window of equal length, so the critical severity tier
    (which requires an escalation signal) is reachable."""

    def _mention_at(self, sentiment, posted_at, text="jalan berlubang"):
        mention = Mention.objects.create(
            project=self.project, platform=self.platform, regency=self.regency,
            author_handle="@warga", content_snippet=text, sentiment=sentiment,
            emotion=Mention.EMOTION_ANGER, posted_at=posted_at,
        )
        IssueLabel.objects.create(
            mention=mention, issue=self.issue, source=IssueLabel.SOURCE_AUTO
        )
        return mention

    def test_volume_tripled_against_prior_window_is_critical(self):
        now = timezone.now()
        since = now - timedelta(days=7)
        previous_start = since - timedelta(days=7)
        # Previous window: 3 negative mentions.
        for _ in range(3):
            self._mention_at(Mention.SENTIMENT_NEGATIVE, previous_start + timedelta(hours=1))
        # Current window: 9 negative mentions (tripled), highly negative.
        for _ in range(9):
            self._mention_at(Mention.SENTIMENT_NEGATIVE, since + timedelta(hours=1))

        candidates = incidents.shortlist_candidates(self.project, since=since, window_days=7)

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertGreaterEqual(candidate["volume_change_pct"], 200)
        severity = incidents.severity_for(
            negative_pct=candidate["negative_pct"],
            volume_change_pct=candidate["volume_change_pct"],
        )
        self.assertEqual(severity, Incident.SEVERITY_CRITICAL)

    def test_steady_volume_negative_cluster_stays_high(self):
        now = timezone.now()
        since = now - timedelta(days=7)
        previous_start = since - timedelta(days=7)
        for _ in range(8):
            self._mention_at(Mention.SENTIMENT_NEGATIVE, previous_start + timedelta(hours=1))
        for _ in range(8):
            self._mention_at(Mention.SENTIMENT_NEGATIVE, since + timedelta(hours=1))

        candidates = incidents.shortlist_candidates(self.project, since=since, window_days=7)

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertLess(candidate["volume_change_pct"], 200)
        severity = incidents.severity_for(
            negative_pct=candidate["negative_pct"],
            volume_change_pct=candidate["volume_change_pct"],
        )
        self.assertEqual(severity, Incident.SEVERITY_HIGH)


class RefreshTest(DetectionTest):
    def test_creates_an_unconfirmed_incident_with_a_detection_event(self):
        for _ in range(8):
            self._mention(Mention.SENTIMENT_NEGATIVE)

        created = incidents.refresh_candidates(self.project)

        self.assertEqual(len(created), 1)
        incident = created[0]
        self.assertFalse(incident.is_confirmed)
        self.assertEqual(incident.mention_count, 8)
        # 100% negative, but only 8 mentions from an empty prior window — below
        # NEW_CLUSTER_SURGE_MENTIONS, so it is a new grievance rather than a spike
        # and enters at the tier its sentiment earns.
        self.assertEqual(incident.severity, Incident.SEVERITY_HIGH)
        self.assertIn("DRAF", incident.ai_summary.upper())
        self.assertEqual(incident.events.filter(kind=IncidentEvent.KIND_DETECTED).count(), 1)

    def test_is_idempotent_rather_than_creating_duplicates(self):
        for _ in range(8):
            self._mention(Mention.SENTIMENT_NEGATIVE)

        incidents.refresh_candidates(self.project)
        incidents.refresh_candidates(self.project)

        self.assertEqual(Incident.objects.filter(project=self.project).count(), 1)

    def test_never_overwrites_an_operator_confirmed_incident(self):
        for _ in range(8):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        incident = incidents.refresh_candidates(self.project)[0]
        incident.is_confirmed = True
        incident.ai_summary = "Ditinjau dan disunting oleh operator."
        incident.title = "Judul hasil suntingan"
        incident.severity = Incident.SEVERITY_LOW
        incident.mention_count = 1
        incident.save()
        original_mention_ids = set(incident.mentions.values_list("id", flat=True))

        incidents.refresh_candidates(self.project)

        incident.refresh_from_db()
        self.assertEqual(incident.ai_summary, "Ditinjau dan disunting oleh operator.")
        self.assertEqual(incident.title, "Judul hasil suntingan")
        self.assertEqual(incident.severity, Incident.SEVERITY_LOW)
        self.assertEqual(incident.mention_count, 1)
        self.assertEqual(set(incident.mentions.values_list("id", flat=True)), original_mention_ids)

    def test_never_overwrites_an_unconfirmed_incident_that_has_been_assigned(self):
        # Fix 6: assign() advances an unconfirmed incident to `assigned` without
        # confirming it. A later refresh must not clobber that operator work.
        for _ in range(8):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        incident = incidents.refresh_candidates(self.project)[0]
        self.assertFalse(incident.is_confirmed)
        opd = OPD.objects.create(project=self.project, name="Dinas PU", slug="pu", abbr="PU")
        incidents.assign(incident, opd, by="Sekda")
        incident.refresh_from_db()
        self.assertEqual(incident.status, Incident.STATUS_ASSIGNED)
        incident.title = "Judul hasil suntingan"
        incident.severity = Incident.SEVERITY_LOW
        incident.mention_count = 1
        incident.save()
        original_mention_ids = set(incident.mentions.values_list("id", flat=True))

        # Add more matching mentions so a naive refresh would have something new
        # to overwrite with.
        for _ in range(8):
            self._mention(Mention.SENTIMENT_NEGATIVE)

        incidents.refresh_candidates(self.project)

        incident.refresh_from_db()
        self.assertEqual(incident.title, "Judul hasil suntingan")
        self.assertEqual(incident.severity, Incident.SEVERITY_LOW)
        self.assertEqual(incident.mention_count, 1)
        self.assertEqual(set(incident.mentions.values_list("id", flat=True)), original_mention_ids)

    def test_does_not_leak_incidents_across_tenants(self):
        for _ in range(8):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        other_tenant = Tenant.objects.create(name="Instansi B")
        other_project = Project.objects.create(tenant=other_tenant, name="Proyek B")

        incidents.refresh_candidates(self.project)

        self.assertEqual(Incident.objects.filter(project=other_project).count(), 0)


class LifecycleTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.opd = OPD.objects.create(
            project=self.project, name="Dinas Pekerjaan Umum", slug="pu", abbr="PU"
        )
        self.incident = Incident.objects.create(
            project=self.project, title="Jalan Rusak", severity=Incident.SEVERITY_HIGH,
        )

    def test_promoting_marks_confirmed_and_records_who_did_it(self):
        incidents.promote(self.incident, by="Operator A")

        self.incident.refresh_from_db()
        self.assertTrue(self.incident.is_confirmed)
        event = self.incident.events.last()
        self.assertEqual(event.logged_by, "Operator A")

    def test_assigning_sets_the_opd_and_advances_status(self):
        incidents.assign(self.incident, self.opd, by="Sekda")

        self.incident.refresh_from_db()
        self.assertEqual(self.incident.assigned_opd, self.opd)
        self.assertEqual(self.incident.status, Incident.STATUS_ASSIGNED)
        event = self.incident.events.filter(kind=IncidentEvent.KIND_ASSIGNED).last()
        self.assertIn("PU", event.description)

    def test_status_change_is_recorded_on_the_timeline(self):
        incidents.assign(self.incident, self.opd, by="Sekda")
        incidents.set_status(self.incident, Incident.STATUS_IN_PROGRESS, by="Dinas PU")

        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, Incident.STATUS_IN_PROGRESS)
        self.assertEqual(
            self.incident.events.filter(kind=IncidentEvent.KIND_STATUS_CHANGE).count(), 1
        )

    def test_closing_stamps_the_closing_time(self):
        incidents.assign(self.incident, self.opd, by="Sekda")
        incidents.set_status(self.incident, Incident.STATUS_IN_PROGRESS, by="PU")
        incidents.set_status(self.incident, Incident.STATUS_RESOLVED, by="PU")
        incidents.set_status(self.incident, Incident.STATUS_CLOSED, by="Sekda")

        self.incident.refresh_from_db()
        self.assertIsNotNone(self.incident.closed_at)
        self.assertFalse(self.incident.is_open)

    def test_rejects_skipping_the_lifecycle(self):
        # An incident cannot go straight from open to resolved: something must have
        # been assigned and worked, or the KPI record is fiction.
        with self.assertRaises(incidents.InvalidTransition):
            incidents.set_status(self.incident, Incident.STATUS_RESOLVED, by="X")

    def test_rejects_reopening_a_closed_incident(self):
        incidents.assign(self.incident, self.opd, by="Sekda")
        incidents.set_status(self.incident, Incident.STATUS_IN_PROGRESS, by="PU")
        incidents.set_status(self.incident, Incident.STATUS_RESOLVED, by="PU")
        incidents.set_status(self.incident, Incident.STATUS_CLOSED, by="Sekda")

        with self.assertRaises(incidents.InvalidTransition):
            incidents.set_status(self.incident, Incident.STATUS_IN_PROGRESS, by="PU")

    def test_open_can_be_dismissed_directly_to_closed(self):
        # The open->closed lifecycle path (dismissal without ever assigning) was
        # uncovered: ALLOWED_TRANSITIONS permits it explicitly.
        incidents.set_status(self.incident, Incident.STATUS_CLOSED, by="Operator A")

        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, Incident.STATUS_CLOSED)
        self.assertIsNotNone(self.incident.closed_at)
        self.assertFalse(self.incident.is_open)

    def test_note_is_appended_without_changing_status(self):
        incidents.log_note(self.incident, "Sudah dicek lapangan.", by="Operator A")

        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, Incident.STATUS_OPEN)
        self.assertEqual(self.incident.events.filter(kind=IncidentEvent.KIND_NOTE).count(), 1)
