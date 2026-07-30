from django.test import TestCase
from django.utils import timezone

from apps.core.models import Platform, Project, Regency, Province, Tenant
from apps.analytics import escalation
from apps.analytics.briefs import DRAFT_BANNER
from apps.analytics.models import Author, EscalationAssessment, Incident, Mention


class EscalationTestBase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Pemkab Kulon Progo")
        self.project = Project.objects.create(tenant=self.tenant, name="Pemantauan")
        self.platform = Platform.objects.create(
            slug="x", display_name="X (Twitter)", method=Platform.METHOD_INTERNAL
        )
        self.platform2 = Platform.objects.create(
            slug="fb", display_name="Facebook", method=Platform.METHOD_INTERNAL
        )
        province = Province.objects.create(name="DI Yogyakarta")
        self.regency = Regency.objects.create(province=province, name="Kulon Progo")
        self.incident = Incident.objects.create(
            project=self.project, title="Jalan Rusak", regency=self.regency,
            severity=Incident.SEVERITY_LOW,
        )
        self.now = timezone.now()

    def mention(self, hours_ago=1, sentiment=Mention.SENTIMENT_NEGATIVE,
                platform=None, engagement=0, attach=True, **kwargs):
        mention = Mention.objects.create(
            project=self.project, platform=platform or self.platform,
            author_handle=kwargs.pop("handle", "@warga"),
            content_snippet=kwargs.pop("text", "jalan rusak"),
            sentiment=sentiment, emotion=Mention.EMOTION_ANGER,
            posted_at=self.now - timezone.timedelta(hours=hours_ago),
            engagement_count=engagement, **kwargs,
        )
        if attach:
            self.incident.mentions.add(mention)
        return mention


class SignalTest(EscalationTestBase):
    def test_velocity_rises_when_a_window_outpaces_the_one_before(self):
        for index in range(20):
            self.mention(hours_ago=1, handle=f"@a{index}")
        for index in range(2):
            self.mention(hours_ago=200, handle=f"@b{index}")

        signals = escalation.collect_signals(
            self.project, Mention.objects.filter(incidents=self.incident),
            self.now - timezone.timedelta(days=7), self.now,
        )
        velocity = next(s for s in signals if s.key == "velocity")
        self.assertTrue(velocity.available)
        self.assertGreater(velocity.normalized, 0.5)

    def test_single_platform_conversation_has_no_cross_platform_spread(self):
        for index in range(10):
            self.mention(handle=f"@a{index}")
        signals = escalation.collect_signals(
            self.project, Mention.objects.filter(incidents=self.incident),
            self.now - timezone.timedelta(days=7), self.now,
        )
        spread = next(s for s in signals if s.key == "cross_platform")
        self.assertTrue(spread.available)
        self.assertEqual(spread.normalized, 0.0)

    def test_evenly_spread_conversation_scores_cross_platform(self):
        for index in range(5):
            self.mention(handle=f"@a{index}")
            self.mention(handle=f"@b{index}", platform=self.platform2)
        signals = escalation.collect_signals(
            self.project, Mention.objects.filter(incidents=self.incident),
            self.now - timezone.timedelta(days=7), self.now,
        )
        spread = next(s for s in signals if s.key == "cross_platform")
        self.assertEqual(spread.normalized, 1.0)

    def test_toxicity_is_unavailable_when_no_comments_were_analysed(self):
        for index in range(5):
            self.mention(handle=f"@a{index}")
        signals = escalation.collect_signals(
            self.project, Mention.objects.filter(incidents=self.incident),
            self.now - timezone.timedelta(days=7), self.now,
        )
        toxicity = next(s for s in signals if s.key == "toxicity")
        self.assertFalse(toxicity.available)

    def test_influencer_needs_follower_data_to_be_available(self):
        for index in range(5):
            self.mention(handle=f"@a{index}")
        signals = escalation.collect_signals(
            self.project, Mention.objects.filter(incidents=self.incident),
            self.now - timezone.timedelta(days=7), self.now,
        )
        influencer = next(s for s in signals if s.key == "influencer")
        self.assertFalse(influencer.available)

    def test_influencer_fires_on_a_large_account(self):
        author = Author.objects.create(
            platform=self.platform, handle="@besar", follower_count=500_000
        )
        self.mention(handle="@besar", author=author)
        for index in range(5):
            small = Author.objects.create(
                platform=self.platform, handle=f"@kecil{index}", follower_count=50
            )
            self.mention(handle=f"@kecil{index}", author=small)

        signals = escalation.collect_signals(
            self.project, Mention.objects.filter(incidents=self.incident),
            self.now - timezone.timedelta(days=7), self.now,
        )
        influencer = next(s for s in signals if s.key == "influencer")
        self.assertTrue(influencer.available)
        self.assertGreater(influencer.normalized, 0)


class ScoringTest(EscalationTestBase):
    def _signals(self, **normalized):
        return [
            escalation.Signal(key, normalized=value, available=True)
            for key, value in normalized.items()
        ]

    def test_unavailable_signals_lower_confidence_not_the_score(self):
        """The property this whole design rests on: a project that collects no
        comments must not look calmer than one that does."""
        full = self._signals(**{k: 1.0 for k in escalation.DEFAULT_WEIGHTS})
        partial = self._signals(velocity=1.0, sentiment_trend=1.0)
        partial += [
            escalation.Signal(key, available=False)
            for key in escalation.DEFAULT_WEIGHTS
            if key not in {"velocity", "sentiment_trend"}
        ]

        full_score, full_conf, _ = escalation.score_signals(full)
        part_score, part_conf, _ = escalation.score_signals(partial)

        self.assertEqual(full_score, 100)
        self.assertEqual(part_score, 100)
        self.assertEqual(full_conf, 1.0)
        self.assertLess(part_conf, 0.5)

    def test_no_available_signals_yields_a_zero_score(self):
        signals = [
            escalation.Signal(key, available=False)
            for key in escalation.DEFAULT_WEIGHTS
        ]
        score, confidence, contributions = escalation.score_signals(signals)
        self.assertEqual(score, 0)
        self.assertEqual(confidence, 0.0)
        self.assertEqual(contributions, [])

    def test_tier_boundaries(self):
        self.assertEqual(escalation.tier_for(0), EscalationAssessment.TIER_LOW)
        self.assertEqual(escalation.tier_for(24), EscalationAssessment.TIER_LOW)
        self.assertEqual(escalation.tier_for(25), EscalationAssessment.TIER_WATCH)
        self.assertEqual(escalation.tier_for(49), EscalationAssessment.TIER_WATCH)
        self.assertEqual(escalation.tier_for(50), EscalationAssessment.TIER_HIGH)
        self.assertEqual(escalation.tier_for(74), EscalationAssessment.TIER_HIGH)
        self.assertEqual(escalation.tier_for(75), EscalationAssessment.TIER_CRITICAL)
        self.assertEqual(escalation.tier_for(100), EscalationAssessment.TIER_CRITICAL)

    def test_contributions_sum_to_the_score(self):
        signals = self._signals(velocity=1.0, sentiment_trend=0.5, toxicity=0.25)
        score, _conf, contributions = escalation.score_signals(signals)
        total = sum(c["contribution"] for c in contributions)
        self.assertAlmostEqual(total, score, delta=1)


class AssessmentTest(EscalationTestBase):
    def test_assessment_persists_the_full_working(self):
        for index in range(10):
            self.mention(handle=f"@a{index}", engagement=20)
        assessment = escalation.assess_incident(self.incident)

        self.assertEqual(len(assessment.signals), len(escalation.DEFAULT_WEIGHTS))
        for signal in assessment.signals:
            self.assertIn("weight", signal)
            self.assertIn("contribution", signal)
            self.assertIn("available", signal)

    def test_weights_are_persisted_so_a_past_score_stays_reproducible(self):
        self.mention()
        assessment = escalation.assess_incident(self.incident)
        weights = {s["key"]: s["weight"] for s in assessment.signals}
        self.assertEqual(weights, escalation.DEFAULT_WEIGHTS)

    def test_narratives_carry_the_draft_banner(self):
        self.mention()
        assessment = escalation.assess_incident(self.incident)
        for field in ("why", "impact_if_ignored", "recommended_response"):
            self.assertIn(DRAFT_BANNER, getattr(assessment, field))

    def test_why_names_the_signals_that_had_no_data(self):
        """Silence about missing signals is what makes a partial score
        misleading, so the explanation has to name them."""
        self.mention()
        assessment = escalation.assess_incident(self.incident)
        self.assertIn("Sinyal tanpa data", assessment.why)
        self.assertIn("Toksisitas diskusi", assessment.why)

    def test_low_confidence_is_disclosed_in_the_recommendation(self):
        self.mention()
        assessment = escalation.assess_incident(self.incident)
        if assessment.confidence < 0.6:
            self.assertIn("keyakinan rendah", assessment.recommended_response.lower())

    def test_tier_drives_incident_severity(self):
        for index in range(30):
            self.mention(hours_ago=1, handle=f"@a{index}", engagement=500,
                         platform=self.platform if index % 2 else self.platform2)
        escalation.assess_incident(self.incident)
        self.incident.refresh_from_db()
        assessment = escalation.latest_for(self.incident)
        self.assertEqual(self.incident.severity, assessment.severity)

    def test_severity_change_is_written_to_the_timeline(self):
        for index in range(30):
            self.mention(hours_ago=1, handle=f"@a{index}", engagement=500,
                         platform=self.platform if index % 2 else self.platform2)
        escalation.assess_incident(self.incident)
        self.incident.refresh_from_db()
        if self.incident.severity != Incident.SEVERITY_LOW:
            self.assertTrue(
                self.incident.events.filter(description__contains="Skor eskalasi").exists()
            )

    def test_assessment_history_stays_bounded(self):
        """Scoring runs hourly per open incident, so unpruned history would grow
        by ~720 rows per incident per month for no analytical gain."""
        self.mention()
        for _ in range(escalation.MAX_HISTORY + 5):
            escalation.assess_incident(self.incident)
        self.assertEqual(self.incident.escalations.count(), escalation.MAX_HISTORY)

    def test_pruning_keeps_the_newest_assessment(self):
        self.mention()
        for _ in range(escalation.MAX_HISTORY + 3):
            escalation.assess_incident(self.incident)
        latest = escalation.latest_for(self.incident)
        newest_id = self.incident.escalations.order_by("-computed_at", "-id").first().id
        self.assertEqual(latest.id, newest_id)

    def test_assess_project_skips_closed_incidents(self):
        self.mention()
        self.incident.status = Incident.STATUS_CLOSED
        self.incident.save(update_fields=["status"])
        self.assertEqual(escalation.assess_project(self.project), [])

    def test_assessment_is_scoped_to_the_project(self):
        other_tenant = Tenant.objects.create(name="Lain")
        other = Project.objects.create(tenant=other_tenant, name="Proyek Lain")
        self.mention()
        escalation.assess_incident(self.incident)
        self.assertEqual(
            EscalationAssessment.objects.filter(project=other).count(), 0
        )

    def test_unavailable_signals_are_listed_for_the_ui(self):
        self.mention()
        assessment = escalation.assess_incident(self.incident)
        self.assertIn("Toksisitas diskusi", assessment.unavailable_signals)
