from django.test import TestCase
from django.utils import timezone

from apps.core.models import Platform, Project, Tenant
from apps.analytics import attribution, drivers, incidents, selectors
from apps.analytics.metrics import resolve_evidence
from apps.analytics.models import (
    AttributionTarget, DriverCandidate, Mention, MentionAttribution, MentionDriver,
    NegativeDriver,
)


class DriverTestBase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Pemkab Kulon Progo")
        self.project = Project.objects.create(tenant=self.tenant, name="Pemantauan")
        self.platform = Platform.objects.create(
            slug="x", display_name="X (Twitter)", method=Platform.METHOD_INTERNAL
        )
        drivers.ensure_drivers(self.project)
        self.jalan = NegativeDriver.objects.get(
            project=self.project, slug="infrastruktur-jalan"
        )
        self.lambat = NegativeDriver.objects.get(
            project=self.project, slug="respons-lambat"
        )

    def mention(self, text="jalan berlubang", sentiment=Mention.SENTIMENT_NEGATIVE):
        return Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@warga",
            content_snippet=text, sentiment=sentiment, emotion=Mention.EMOTION_ANGER,
            posted_at=timezone.now(),
        )


class SeedTest(DriverTestBase):
    def test_seeding_is_idempotent(self):
        before = NegativeDriver.objects.filter(project=self.project).count()
        drivers.ensure_drivers(self.project)
        self.assertEqual(
            NegativeDriver.objects.filter(project=self.project).count(), before
        )


class LabelingTest(DriverTestBase):
    def test_positive_mentions_get_no_driver(self):
        mention = self.mention("jalan mulus terima kasih", Mention.SENTIMENT_POSITIVE)
        self.assertEqual(drivers.label(mention), [])

    def test_a_mention_can_carry_several_reasons(self):
        mention = self.mention("jalan berlubang dibiarkan bertahun tahun")
        drivers.label(mention)
        labels = {d.driver.slug for d in mention.drivers.all()}
        self.assertIn("infrastruktur-jalan", labels)
        self.assertIn("respons-lambat", labels)

    def test_negative_attribution_alone_triggers_labeling(self):
        """A post praising the centre while blaming us still holds a complaint."""
        attribution.ensure_registry(self.project)
        own = AttributionTarget.objects.get(
            project=self.project, level=AttributionTarget.LEVEL_KABUPATEN
        )
        mention = self.mention("jalan berlubang", Mention.SENTIMENT_POSITIVE)
        MentionAttribution.objects.create(
            mention=mention, target=own, sentiment=Mention.SENTIMENT_NEGATIVE
        )
        drivers.label(mention)
        self.assertTrue(mention.drivers.exists())

    def test_rerun_keeps_manual_labels(self):
        mention = self.mention("jalan berlubang")
        MentionDriver.objects.create(
            mention=mention, driver=self.lambat,
            source=MentionDriver.SOURCE_MANUAL, confidence=1.0,
        )
        drivers.label(mention)
        manual = mention.drivers.get(driver=self.lambat)
        self.assertEqual(manual.source, MentionDriver.SOURCE_MANUAL)

    def test_labeling_is_scoped_to_the_project(self):
        other = Project.objects.create(tenant=self.tenant, name="Proyek Lain")
        self.assertEqual(drivers.candidates_for(other), [])


class StubProvider:
    model_version = "stub"

    def __init__(self, results=None, unmatched="", error=None):
        self.results = results or []
        self.unmatched = unmatched
        self.error = error

    def label(self, text, candidates):
        if self.error:
            raise self.error
        return self.results, self.unmatched


class CandidateTest(DriverTestBase):
    def test_model_ids_outside_the_candidate_set_are_dropped(self):
        other = Project.objects.create(tenant=self.tenant, name="Proyek Lain")
        stranger = NegativeDriver.objects.create(
            project=other, name="Asing", slug="asing"
        )
        candidates = drivers.candidates_for(self.project)
        results, _ = drivers._assessments(
            {"drivers": [
                {"id": stranger.id, "confidence": 0.9},
                {"id": self.jalan.id, "confidence": 0.8},
            ]},
            candidates,
        )
        self.assertEqual([r.driver_id for r in results], [self.jalan.id])

    def test_unmatched_phrase_becomes_a_reviewable_candidate(self):
        mention = self.mention("pungutan liar di sekolah negeri")
        pipeline = drivers.DriverPipeline(
            [StubProvider(unmatched="pungutan liar sekolah")]
        )
        drivers.label(mention, pipeline=pipeline)
        candidate = DriverCandidate.objects.get(project=self.project)
        self.assertEqual(candidate.phrase, "pungutan liar sekolah")
        self.assertIn(mention.pk, candidate.sample_mention_ids)

    def test_a_hostile_unmatched_phrase_is_rejected(self):
        """The phrase is free text a model produced while reading untrusted
        input, so it is sanitised before it can reach the review queue."""
        candidates = drivers.candidates_for(self.project)
        _results, unmatched = drivers._assessments(
            {"drivers": [{"id": self.jalan.id, "confidence": 0.5}],
             "unmatched": "<script>alert(1)</script>"},
            candidates,
        )
        self.assertEqual(unmatched, "")

    def test_candidate_only_reaches_the_queue_after_recurring(self):
        mention = self.mention("pungli sekolah")
        pipeline = drivers.DriverPipeline([StubProvider(unmatched="pungli sekolah")])
        drivers.label(mention, pipeline=pipeline)
        self.assertFalse(drivers.review_queue(self.project).exists())

        for _ in range(2):
            drivers.label(self.mention("pungli sekolah"), pipeline=pipeline)
        self.assertTrue(drivers.review_queue(self.project).exists())

    def test_promotion_creates_a_driver_and_labels_its_samples(self):
        mention = self.mention("pungli sekolah")
        pipeline = drivers.DriverPipeline([StubProvider(unmatched="pungli sekolah")])
        drivers.label(mention, pipeline=pipeline)
        candidate = DriverCandidate.objects.get(project=self.project)

        driver = drivers.promote_candidate(candidate, by="Analis A")
        self.assertTrue(
            MentionDriver.objects.filter(mention=mention, driver=driver).exists()
        )
        candidate.refresh_from_db()
        self.assertEqual(candidate.promoted_to, driver)

    def test_a_dismissed_candidate_never_returns_to_the_queue(self):
        mention = self.mention("pungli sekolah")
        pipeline = drivers.DriverPipeline([StubProvider(unmatched="pungli sekolah")])
        drivers.label(mention, pipeline=pipeline)
        candidate = DriverCandidate.objects.get(project=self.project)
        drivers.dismiss_candidate(candidate)

        for _ in range(4):
            drivers.label(self.mention("pungli sekolah"), pipeline=pipeline)
        self.assertFalse(drivers.review_queue(self.project).exists())

    def test_promotion_survives_a_slug_collision(self):
        NegativeDriver.objects.create(
            project=self.project, name="Pungli", slug="pungli-sekolah"
        )
        candidate = DriverCandidate.objects.create(
            project=self.project, phrase="pungli sekolah", count=3
        )
        driver = drivers.promote_candidate(candidate)
        self.assertEqual(driver.slug, "pungli-sekolah-2")


class DriverSummaryTest(DriverTestBase):
    def test_summary_reports_shares_and_coverage(self):
        for _ in range(3):
            drivers.label(self.mention("jalan berlubang parah"))
        # A negative mention with no matching reason: coverage must reflect it.
        self.mention("harga cabai naik terus")

        summary = selectors.driver_summary(self.project)
        top = summary["drivers"][0]
        self.assertEqual(top["metric"].value, 100)
        self.assertEqual(summary["total_negative"], 4)
        self.assertEqual(summary["coverage_pct"], 75)

    def test_metric_resolves_to_the_mentions_it_counted(self):
        for _ in range(3):
            drivers.label(self.mention("jalan berlubang parah"))
        summary = selectors.driver_summary(self.project)
        for row in summary["drivers"]:
            metric = row["metric"]
            self.assertEqual(
                resolve_evidence(self.project, metric.evidence).count(),
                metric.contributing,
                metric.label,
            )

    def test_summary_is_scoped_to_the_project(self):
        other = Project.objects.create(tenant=self.tenant, name="Proyek Lain")
        drivers.label(self.mention("jalan berlubang"))
        self.assertEqual(selectors.driver_summary(other)["total_negative"], 0)


class IncidentRootCauseTest(DriverTestBase):
    def test_root_cause_states_measured_reasons(self):
        mentions = [self.mention("jalan berlubang parah") for _ in range(3)]
        for mention in mentions:
            drivers.label(mention)

        candidate = {
            "title": "Jalan Rusak", "total": 3, "negative_pct": 100,
            "regency_name": "Kulon Progo", "snippets": ["jalan berlubang parah"],
            "mention_ids": [m.pk for m in mentions],
        }
        narrative = incidents.compose_incident_narrative(candidate)
        self.assertIn("Infrastruktur jalan", narrative["root_cause"])
        self.assertIn("verifikasi", narrative["root_cause"].lower())

    def test_root_cause_admits_when_no_reason_was_measured(self):
        candidate = {
            "title": "Jalan Rusak", "total": 3, "negative_pct": 100,
            "regency_name": "Kulon Progo", "snippets": ["ada masalah"],
            "mention_ids": [],
        }
        narrative = incidents.compose_incident_narrative(candidate)
        self.assertIn("belum", narrative["root_cause"].lower())
