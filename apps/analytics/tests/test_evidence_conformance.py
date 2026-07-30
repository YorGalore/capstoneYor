"""Slice E: the guarantee that no KPI is a black box.

Every ``Metric`` this platform renders must be able to show its work — the method
that produced it, and the exact mentions behind it. These tests walk the real
selectors over a realistic corpus and fail the build if any metric cannot.

That is the point of the whole evidence spine: "avoid black-box analytics" is a
property enforced here, not a claim made in a slide.
"""
from django.test import TestCase
from django.utils import timezone

from apps.core.models import Platform, Project, Province, Regency, Tenant
from apps.analytics import (
    attribution, comment_intel, drivers, escalation, selectors,
)
from apps.analytics.metrics import LOW_CONFIDENCE, Metric, RESOLVERS, resolve_evidence
from apps.analytics.models import (
    AttributionTarget, Incident, Mention, MentionAttribution, OPD,
)


def walk_metrics(node, path="root"):
    """Yield every Metric reachable in a selector's return value."""
    if isinstance(node, Metric):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from walk_metrics(value, f"{path}.{key}")
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            yield from walk_metrics(value, f"{path}[{index}]")


class ConformanceTest(TestCase):
    """A corpus rich enough that every screen produces real metrics."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Pemkab Kulon Progo")
        self.project = Project.objects.create(tenant=self.tenant, name="Pemantauan")
        self.x = Platform.objects.create(
            slug="x", display_name="X (Twitter)", method=Platform.METHOD_INTERNAL
        )
        self.fb = Platform.objects.create(
            slug="fb", display_name="Facebook", method=Platform.METHOD_INTERNAL
        )
        province = Province.objects.create(name="DI Yogyakarta")
        self.regency = Regency.objects.create(province=province, name="Kulon Progo")
        self.opd = OPD.objects.create(
            project=self.project, name="Dinas Pekerjaan Umum", slug="pu", abbr="PU"
        )

        attribution.ensure_registry(self.project)
        drivers.ensure_drivers(self.project)
        self.own = AttributionTarget.objects.get(
            project=self.project, level=AttributionTarget.LEVEL_KABUPATEN
        )
        self.pusat = AttributionTarget.objects.get(
            project=self.project, level=AttributionTarget.LEVEL_PUSAT
        )
        self.pu_target = AttributionTarget.objects.get(name="Dinas Pekerjaan Umum")

        self.now = timezone.now()
        self.incident = Incident.objects.create(
            project=self.project, title="Jalan Rusak", regency=self.regency,
        )
        self._build_corpus()

    def _mention(self, text, sentiment, platform=None, hours=1, handle="@warga",
                 content_type=Mention.CONTENT_POST, parent=None):
        return Mention.objects.create(
            project=self.project, platform=platform or self.x, author_handle=handle,
            content_snippet=text, sentiment=sentiment, emotion=Mention.EMOTION_ANGER,
            posted_at=self.now - timezone.timedelta(hours=hours),
            engagement_count=25, regency=self.regency,
            content_type=content_type, parent=parent,
        )

    def _build_corpus(self):
        targets = [self.pusat, self.own, self.pu_target]
        for index in range(12):
            mention = self._mention(
                "jalan berlubang dibiarkan bertahun tahun",
                Mention.SENTIMENT_NEGATIVE,
                platform=self.x if index % 2 else self.fb,
                handle=f"@warga{index}",
                hours=index + 1,
            )
            MentionAttribution.objects.create(
                mention=mention, target=targets[index % 3],
                sentiment=Mention.SENTIMENT_NEGATIVE, confidence=0.85,
            )
            drivers.label(mention)
            self.incident.mentions.add(mention)

        root = self._mention(
            "pemkab resmikan ruas jalan baru", Mention.SENTIMENT_NEUTRAL,
            handle="@humas", hours=20,
        )
        MentionAttribution.objects.create(
            mention=root, target=self.own,
            sentiment=Mention.SENTIMENT_NEUTRAL, confidence=0.7,
        )
        for index in range(8):
            comment = self._mention(
                "bohong, jalan lain masih rusak parah" if index else "dasar bangsat goblok",
                Mention.SENTIMENT_NEGATIVE, handle=f"@komentator{index}",
                hours=19, content_type=Mention.CONTENT_COMMENT, parent=root,
            )
            comment_intel.enrich(comment)
        comment_intel.recompute_thread(root)
        escalation.assess_incident(self.incident)

    def _all_metrics(self):
        sources = {
            "ringkasan.attribution": selectors.attribution_summary(self.project),
            "ringkasan.drivers": selectors.driver_summary(self.project),
            "ringkasan.threads": selectors.thread_summary(self.project),
            "insiden.attribution": selectors.incident_attribution(self.incident),
        }
        found = []
        for name, payload in sources.items():
            found.extend(walk_metrics(payload, name))
        return found

    def test_the_corpus_actually_produces_metrics(self):
        """Guards the tests below: a conformance suite that walks nothing passes
        vacuously, which would be worse than having no suite at all."""
        metrics = self._all_metrics()
        self.assertGreaterEqual(len(metrics), 8)

    def test_every_metric_declares_how_it_was_computed(self):
        for path, metric in self._all_metrics():
            with self.subTest(metric=path):
                self.assertTrue(metric.method.strip(), f"{path} has no method")
                self.assertTrue(metric.label.strip(), f"{path} has no label")

    def test_every_metric_with_contributing_rows_has_resolvable_evidence(self):
        for path, metric in self._all_metrics():
            if not metric.contributing:
                continue
            with self.subTest(metric=path):
                self.assertIsNotNone(
                    metric.evidence, f"{path} counts rows but offers no evidence"
                )
                resolved = resolve_evidence(self.project, metric.evidence).count()
                self.assertGreater(
                    resolved, 0, f"{path} resolves to no supporting mentions"
                )

    def test_contributing_count_matches_the_evidence_it_links_to(self):
        """The bug class this catches: a displayed number and its drill-down
        quietly diverging, so a reader who checks finds different data."""
        for path, metric in self._all_metrics():
            if not metric.contributing:
                continue
            with self.subTest(metric=path):
                resolved = resolve_evidence(self.project, metric.evidence).count()
                self.assertEqual(
                    resolved, metric.contributing,
                    f"{path} claims {metric.contributing} rows but resolves {resolved}",
                )

    def test_every_metric_evidence_kind_is_registered(self):
        for path, metric in self._all_metrics():
            if metric.evidence is None:
                continue
            with self.subTest(metric=path):
                self.assertIn(metric.evidence.kind, RESOLVERS)

    def test_evidence_params_survive_a_querystring_round_trip(self):
        from apps.analytics.metrics import EvidenceRef

        for path, metric in self._all_metrics():
            if metric.evidence is None:
                continue
            with self.subTest(metric=path):
                params = dict(
                    pair.split("=", 1)
                    for pair in metric.evidence.to_query().split("&")
                )
                rebuilt = EvidenceRef.from_params(params)
                self.assertIsNotNone(rebuilt, f"{path} evidence does not round trip")
                self.assertEqual(rebuilt.kind, metric.evidence.kind)

    def test_confidence_is_reported_within_range(self):
        for path, metric in self._all_metrics():
            with self.subTest(metric=path):
                self.assertGreaterEqual(metric.confidence, 0.0)
                self.assertLessEqual(metric.confidence, 1.0)
                self.assertGreaterEqual(metric.low_confidence_pct, 0)
                self.assertLessEqual(metric.low_confidence_pct, 100)

    def test_confidence_band_is_never_silently_blank(self):
        for path, metric in self._all_metrics():
            with self.subTest(metric=path):
                self.assertIn(
                    metric.confidence_band,
                    {"tinggi", "sedang", "rendah", "tidak tersedia"},
                )

    def test_low_confidence_rows_are_counted_not_hidden(self):
        """Suppressing weak labels would misrepresent confidence itself, so a
        low-confidence attribution must still appear in both count and evidence."""
        weak = self._mention(
            "entah siapa yang salah", Mention.SENTIMENT_NEGATIVE, handle="@ragu"
        )
        MentionAttribution.objects.create(
            mention=weak, target=self.pusat,
            sentiment=Mention.SENTIMENT_NEGATIVE, confidence=LOW_CONFIDENCE - 0.2,
        )
        summary = selectors.attribution_summary(self.project)
        pusat_level = next(
            level for level in summary["levels"]
            if level["level"] == AttributionTarget.LEVEL_PUSAT
        )
        metric = pusat_level["metric"]
        self.assertGreater(metric.low_confidence_pct, 0)
        self.assertEqual(
            resolve_evidence(self.project, metric.evidence).count(),
            metric.contributing,
        )


class EscalationEvidenceTest(ConformanceTest):
    def test_every_available_escalation_signal_shows_its_working(self):
        assessment = escalation.latest_for(self.incident)
        self.assertIsNotNone(assessment)
        for signal in assessment.signals:
            with self.subTest(signal=signal["key"]):
                self.assertIn("weight", signal)
                self.assertIn("contribution", signal)
                self.assertTrue(signal["label"])
                if signal["available"]:
                    self.assertTrue(
                        signal["note"], f"{signal['key']} fired without explaining itself"
                    )

    def test_unavailable_signals_are_named_rather_than_scored_as_zero(self):
        assessment = escalation.latest_for(self.incident)
        for signal in assessment.signals:
            if not signal["available"]:
                self.assertEqual(signal["contribution"], 0)
                self.assertIn(signal["label"], assessment.why)

    def test_signal_evidence_kinds_are_registered(self):
        assessment = escalation.latest_for(self.incident)
        for signal in assessment.signals:
            if signal["evidence_kind"]:
                self.assertIn(signal["evidence_kind"], RESOLVERS)
