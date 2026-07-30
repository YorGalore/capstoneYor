from django.test import TestCase
from django.utils import timezone

from apps.core.models import Platform, Project, Tenant
from apps.analytics import attribution, selectors
from apps.analytics.metrics import EvidenceRef, resolve_evidence
from apps.analytics.models import (
    OPD, AttributionTarget, LabelCorrection, Mention, MentionAttribution,
)


class AttributionTestBase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Pemkab Kulon Progo")
        self.project = Project.objects.create(tenant=self.tenant, name="Pemantauan Publik")
        self.platform = Platform.objects.create(
            slug="x", display_name="X (Twitter)", method=Platform.METHOD_INTERNAL
        )
        self.opd = OPD.objects.create(
            project=self.project, name="Dinas Pekerjaan Umum", slug="pu", abbr="PU"
        )
        self.levels = attribution.ensure_registry(self.project)
        self.own = self.levels[AttributionTarget.LEVEL_KABUPATEN]
        self.pusat = self.levels[AttributionTarget.LEVEL_PUSAT]
        self.pu_target = AttributionTarget.objects.get(name="Dinas Pekerjaan Umum")

    def mention(self, text="jalan rusak", sentiment=Mention.SENTIMENT_NEGATIVE, **kwargs):
        return Mention.objects.create(
            project=self.project,
            platform=self.platform,
            author_handle=kwargs.pop("handle", "@warga"),
            content_snippet=text,
            sentiment=sentiment,
            emotion=Mention.EMOTION_ANGER,
            posted_at=kwargs.pop("posted_at", timezone.now()),
            **kwargs,
        )


class RegistryTest(AttributionTestBase):
    def test_seeds_every_level_as_catch_all(self):
        levels = set(
            AttributionTarget.objects.filter(
                project=self.project, is_catch_all=True
            ).values_list("level", flat=True)
        )
        self.assertEqual(levels, {key for key, _ in AttributionTarget.LEVEL_CHOICES})

    def test_opd_becomes_an_entity_target_linked_back_to_the_opd(self):
        self.assertEqual(self.pu_target.opd, self.opd)
        self.assertEqual(self.pu_target.parent, self.own)
        self.assertFalse(self.pu_target.is_catch_all)

    def test_registry_is_idempotent(self):
        before = AttributionTarget.objects.filter(project=self.project).count()
        attribution.ensure_registry(self.project)
        self.assertEqual(
            AttributionTarget.objects.filter(project=self.project).count(), before
        )

    def test_opd_child_counts_as_own_government(self):
        self.assertTrue(self.own.counts_as_own_government)
        self.assertTrue(self.pu_target.counts_as_own_government)
        self.assertFalse(self.pusat.counts_as_own_government)


class CandidateTest(AttributionTestBase):
    def test_catch_alls_are_always_candidates(self):
        candidates = attribution.candidates_for(
            self.project, "jalan ini udah 3 tahun dibiarin", "@warga"
        )
        levels = {c.level for c in candidates if c.is_catch_all}
        self.assertEqual(levels, {key for key, _ in AttributionTarget.LEVEL_CHOICES})

    def test_named_entity_is_offered_before_catch_alls(self):
        candidates = attribution.candidates_for(
            self.project, "Dinas Pekerjaan Umum lambat sekali", "@warga"
        )
        self.assertEqual(candidates[0], self.pu_target)

    def test_matching_is_scoped_to_the_project(self):
        other = Project.objects.create(tenant=self.tenant, name="Proyek Lain")
        attribution.ensure_registry(other)
        candidates = attribution.candidates_for(other, "Dinas Pekerjaan Umum", "@a")
        self.assertNotIn(self.pu_target, candidates)


class StubProvider:
    """Returns whatever it was constructed with, or raises."""

    model_version = "stub"

    def __init__(self, results=None, error=None):
        self.results = results or []
        self.error = error

    def attribute(self, text, candidates, mention_sentiment, project=None):
        if self.error:
            raise self.error
        return self.results


class PipelineTest(AttributionTestBase):
    def test_falls_through_to_rules_when_the_model_fails(self):
        mention = self.mention("Dinas Pekerjaan Umum lambat")
        pipeline = attribution.AttributionPipeline(
            [StubProvider(error=RuntimeError("API down"))]
        )
        attribution.attribute(mention, pipeline=pipeline)
        rows = mention.attributions.all()
        self.assertEqual([r.target for r in rows], [self.pu_target])
        self.assertEqual(rows[0].model, "rule:attribution")

    def test_every_mention_ends_with_at_least_one_attribution(self):
        mention = self.mention("cuaca hari ini cerah sekali")
        pipeline = attribution.AttributionPipeline(
            [StubProvider(error=RuntimeError("API down"))]
        )
        attribution.attribute(mention, pipeline=pipeline)
        self.assertEqual(mention.attributions.count(), 1)
        self.assertEqual(
            mention.attributions.first().target.level,
            AttributionTarget.LEVEL_TIDAK_JELAS,
        )

    def test_rules_can_attribute_away_from_us_without_a_model(self):
        """Regression: the rule tier once matched only named entities. Since the
        only entities a tenant configures are its own agencies, every rule-tier
        attribution landed on the tenant and the platform reported that 100% of
        criticism was aimed at itself — inverting the feature's whole purpose."""
        mention = self.mention("pemerintah pusat lambat menangani ini")
        pipeline = attribution.AttributionPipeline(
            [StubProvider(error=RuntimeError("API down"))]
        )
        attribution.attribute(mention, pipeline=pipeline)
        targets = {row.target.level for row in mention.attributions.all()}
        self.assertIn(AttributionTarget.LEVEL_PUSAT, targets)
        self.assertNotIn(AttributionTarget.LEVEL_KABUPATEN, targets)

    def test_a_named_agency_suppresses_its_own_level_bucket(self):
        """Otherwise "Dinas PU" is counted once as the dinas and again as the
        generic OPD bucket, double-counting one complaint at the same tier."""
        mention = self.mention("Dinas Pekerjaan Umum lambat")
        pipeline = attribution.AttributionPipeline(
            [StubProvider(error=RuntimeError("API down"))]
        )
        attribution.attribute(mention, pipeline=pipeline)
        opd_rows = [
            row for row in mention.attributions.all()
            if row.target.level == AttributionTarget.LEVEL_OPD
        ]
        self.assertEqual(len(opd_rows), 1)
        self.assertEqual(opd_rows[0].target, self.pu_target)

    def test_unattributable_anger_is_not_recorded_as_negative(self):
        """A negative post naming nobody must not pad the negative-attribution
        denominator with sentiment that has no target."""
        mention = self.mention("hari ini sangat mengecewakan sekali")
        pipeline = attribution.AttributionPipeline(
            [StubProvider(error=RuntimeError("API down"))]
        )
        attribution.attribute(mention, pipeline=pipeline)
        row = mention.attributions.get()
        self.assertEqual(row.target.level, AttributionTarget.LEVEL_TIDAK_JELAS)
        self.assertEqual(row.sentiment, Mention.SENTIMENT_NEUTRAL)

    def test_model_output_outside_the_candidate_set_is_dropped(self):
        other = Project.objects.create(tenant=self.tenant, name="Proyek Lain")
        stranger = AttributionTarget.objects.create(
            project=other, name="Entitas Asing", level=AttributionTarget.LEVEL_PUSAT
        )
        payload = {
            "attributions": [
                {"id": stranger.id, "sentiment": "negative", "confidence": 0.9},
                {"id": self.pusat.id, "sentiment": "negative", "confidence": 0.8},
            ]
        }
        candidates = attribution.candidates_for(self.project, "pusat lambat", "@a")
        results = attribution._assessments(payload, candidates)
        self.assertEqual([r.target_id for r in results], [self.pusat.id])

    def test_malformed_model_output_raises_so_the_pipeline_falls_through(self):
        candidates = attribution.candidates_for(self.project, "x", "@a")
        with self.assertRaises(RuntimeError):
            attribution._assessments({"attributions": []}, candidates)

    def test_one_mention_can_target_several_entities_differently(self):
        mention = self.mention("pusat gagal tapi pemkab cepat tanggap")
        results = [
            attribution.TargetAssessment(self.pusat.id, Mention.SENTIMENT_NEGATIVE, 0.9),
            attribution.TargetAssessment(self.own.id, Mention.SENTIMENT_POSITIVE, 0.8),
        ]
        pipeline = attribution.AttributionPipeline([StubProvider(results=results)])
        attribution.attribute(mention, pipeline=pipeline)
        by_target = {r.target_id: r.sentiment for r in mention.attributions.all()}
        self.assertEqual(by_target[self.pusat.id], Mention.SENTIMENT_NEGATIVE)
        self.assertEqual(by_target[self.own.id], Mention.SENTIMENT_POSITIVE)

    def test_rerun_replaces_automatic_rows_but_keeps_manual_ones(self):
        mention = self.mention("pusat lambat")
        attribution.correct(mention, self.own, Mention.SENTIMENT_NEGATIVE, "analis")
        pipeline = attribution.AttributionPipeline(
            [StubProvider(results=[
                attribution.TargetAssessment(self.pusat.id, Mention.SENTIMENT_NEGATIVE, 0.9)
            ])]
        )
        attribution.attribute(mention, pipeline=pipeline)
        rows = {r.target_id: r for r in mention.attributions.all()}
        self.assertEqual(rows[self.own.id].source, MentionAttribution.SOURCE_MANUAL)
        self.assertEqual(rows[self.pusat.id].source, MentionAttribution.SOURCE_AUTO)


class CorrectionTest(AttributionTestBase):
    def test_correction_is_recorded_as_tuning_feedback(self):
        mention = self.mention("pusat lambat")
        pipeline = attribution.AttributionPipeline([StubProvider(results=[
            attribution.TargetAssessment(self.pusat.id, Mention.SENTIMENT_NEGATIVE, 0.9)
        ])])
        attribution.attribute(mention, pipeline=pipeline)

        attribution.correct(mention, self.own, Mention.SENTIMENT_NEGATIVE, "Analis A")
        correction = LabelCorrection.objects.get(field="attribution")
        self.assertEqual(correction.corrected_by, "Analis A")
        self.assertIn("Pemerintah Kabupaten", correction.new_value)

    def test_removing_the_last_attribution_restores_the_invariant(self):
        mention = self.mention("pusat lambat")
        pipeline = attribution.AttributionPipeline([StubProvider(results=[
            attribution.TargetAssessment(self.pusat.id, Mention.SENTIMENT_NEGATIVE, 0.9)
        ])])
        attribution.attribute(mention, pipeline=pipeline)

        attribution.remove(mention, self.pusat, "Analis A")
        self.assertEqual(mention.attributions.count(), 1)
        self.assertEqual(
            mention.attributions.first().target.level,
            AttributionTarget.LEVEL_TIDAK_JELAS,
        )


class BackfillTest(AttributionTestBase):
    def test_backfill_only_touches_unattributed_mentions(self):
        done = self.mention("sudah", posted_at=timezone.now())
        done.attributed_at = timezone.now()
        done.save(update_fields=["attributed_at"])
        self.mention("Dinas Pekerjaan Umum lambat")

        pipeline = attribution.AttributionPipeline([StubProvider(error=RuntimeError())])
        processed = attribution.backfill(self.project)
        self.assertEqual(processed, 1)
        self.assertEqual(done.attributions.count(), 0)


class AttributionSummaryTest(AttributionTestBase):
    def _attribute(self, mention, target, sentiment, confidence=0.9):
        MentionAttribution.objects.create(
            mention=mention, target=target, sentiment=sentiment, confidence=confidence
        )

    def test_own_government_share_reports_only_what_targets_us(self):
        for _ in range(8):
            self._attribute(self.mention(), self.pusat, Mention.SENTIMENT_NEGATIVE)
        self._attribute(self.mention(), self.own, Mention.SENTIMENT_NEGATIVE)
        self._attribute(self.mention(), self.pu_target, Mention.SENTIMENT_NEGATIVE)

        summary = selectors.attribution_summary(self.project)
        self.assertEqual(summary["total"], 10)
        # Our own node plus the dinas beneath it: 2 of 10.
        self.assertEqual(summary["own_government"].value, 20)
        self.assertEqual(summary["own_government"].contributing, 2)

    def test_metric_carries_its_method_and_confidence(self):
        self._attribute(self.mention(), self.pusat, Mention.SENTIMENT_NEGATIVE, 0.9)
        self._attribute(self.mention(), self.pusat, Mention.SENTIMENT_NEGATIVE, 0.3)
        summary = selectors.attribution_summary(self.project)
        metric = summary["levels"][0]["metric"]
        self.assertIn("÷", metric.method)
        self.assertEqual(metric.confidence, 0.6)
        self.assertEqual(metric.low_confidence_pct, 50)
        self.assertEqual(metric.confidence_band, "sedang")

    def test_empty_window_returns_a_zero_metric_not_a_crash(self):
        summary = selectors.attribution_summary(self.project)
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["own_government"].value, 0)

    def test_levels_are_ordered_by_tier_of_government_not_alphabetically(self):
        self._attribute(self.mention(), self.pusat, Mention.SENTIMENT_NEGATIVE)
        self._attribute(self.mention(), self.own, Mention.SENTIMENT_NEGATIVE)
        summary = selectors.attribution_summary(self.project)
        self.assertEqual(
            [level["level"] for level in summary["levels"]],
            [AttributionTarget.LEVEL_KABUPATEN, AttributionTarget.LEVEL_PUSAT],
        )

    def test_summary_is_scoped_to_the_project(self):
        other = Project.objects.create(tenant=self.tenant, name="Proyek Lain")
        attribution.ensure_registry(other)
        self._attribute(self.mention(), self.pusat, Mention.SENTIMENT_NEGATIVE)
        self.assertEqual(selectors.attribution_summary(other)["total"], 0)


class EvidenceTest(AttributionTestBase):
    def test_every_metric_resolves_to_the_rows_it_counted(self):
        for _ in range(3):
            MentionAttribution.objects.create(
                mention=self.mention(), target=self.pusat,
                sentiment=Mention.SENTIMENT_NEGATIVE, confidence=0.9,
            )
        MentionAttribution.objects.create(
            mention=self.mention(), target=self.own,
            sentiment=Mention.SENTIMENT_NEGATIVE, confidence=0.9,
        )
        summary = selectors.attribution_summary(self.project)
        for level in summary["levels"]:
            metric = level["metric"]
            resolved = resolve_evidence(self.project, metric.evidence).count()
            self.assertEqual(resolved, metric.contributing, metric.label)
        own = summary["own_government"]
        self.assertEqual(
            resolve_evidence(self.project, own.evidence).count(), own.contributing
        )

    def test_evidence_ref_survives_a_round_trip_through_a_querystring(self):
        ref = EvidenceRef("attribution", {"level": "pusat", "sentiment": "negative"})
        query = ref.to_query()
        self.assertIn("bukti=attribution", query)
        rebuilt = EvidenceRef.from_params(
            {"bukti": "attribution", "level": "pusat", "sentiment": "negative"}
        )
        self.assertEqual(rebuilt, ref)

    def test_unknown_evidence_kind_returns_nothing_rather_than_raising(self):
        self.assertIsNone(EvidenceRef.from_params({"bukti": "tidak-dikenal"}))
        self.assertEqual(resolve_evidence(self.project, None).count(), 0)
