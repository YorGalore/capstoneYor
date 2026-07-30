"""View-level coverage for the early-warning features: attribution on Ringkasan,
evidence drill-down on Umpan, driver review, and escalation on Insiden."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.analytics import attribution, drivers, escalation
from apps.analytics.metrics import EvidenceRef
from apps.analytics.models import (
    AttributionTarget, DriverCandidate, Incident, LabelCorrection, Mention,
    MentionAttribution, MentionDriver, NegativeDriver, OPD,
)
from apps.core.models import (
    AnalystProfile, PagePermission, Platform, Project, Tenant,
)


class IntelligenceViewTestBase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Pemkab Kulon Progo")
        self.project = Project.objects.create(tenant=self.tenant, name="Pemantauan")
        self.platform = Platform.objects.create(
            slug="x", display_name="X (Twitter)", method=Platform.METHOD_INTERNAL
        )
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

        self.user = get_user_model().objects.create_user(
            username="analis", password="rahasia123"
        )
        AnalystProfile.objects.update_or_create(
            user=self.user,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_ANALYST},
        )
        self.client.force_login(self.user)

    def mention(self, text="jalan berlubang", target=None,
                sentiment=Mention.SENTIMENT_NEGATIVE, handle="@warga"):
        mention = Mention.objects.create(
            project=self.project, platform=self.platform, author_handle=handle,
            content_snippet=text, sentiment=sentiment, emotion=Mention.EMOTION_ANGER,
            posted_at=timezone.now(),
        )
        if target is not None:
            MentionAttribution.objects.create(
                mention=mention, target=target, sentiment=sentiment, confidence=0.9
            )
        return mention


class RingkasanAttributionViewTest(IntelligenceViewTestBase):
    def test_ringkasan_reports_the_share_aimed_at_us(self):
        for _ in range(4):
            self.mention(target=self.pusat)
        self.mention(target=self.own)

        response = self.client.get(reverse("analytics:ringkasan"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sasaran Kritik")
        self.assertEqual(response.context["attribution"]["own_government"].value, 20)

    def test_ringkasan_renders_without_attribution_data(self):
        response = self.client.get(reverse("analytics:ringkasan"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["attribution"]["total"], 0)

    def test_ringkasan_shows_why_negative_when_drivers_exist(self):
        for _ in range(3):
            drivers.label(self.mention("jalan berlubang parah"))
        response = self.client.get(reverse("analytics:ringkasan"))
        self.assertContains(response, "Mengapa Negatif")


class EvidenceDrilldownViewTest(IntelligenceViewTestBase):
    def test_feed_filters_to_the_mentions_behind_a_metric(self):
        ours = self.mention("pemkab lambat", target=self.own, handle="@a")
        theirs = self.mention("pusat lambat", target=self.pusat, handle="@b")

        ref = EvidenceRef(
            "attribution",
            {"target": self.own.pk, "sentiment": Mention.SENTIMENT_NEGATIVE},
        )
        response = self.client.get(f"{reverse('analytics:feed')}?{ref.to_query()}")
        self.assertEqual(response.status_code, 200)
        listed = [m.pk for m in response.context["page_obj"]]
        self.assertIn(ours.pk, listed)
        self.assertNotIn(theirs.pk, listed)

    def test_feed_announces_that_it_is_showing_evidence(self):
        self.mention(target=self.own)
        ref = EvidenceRef("attribution", {"own_government": "1"})
        response = self.client.get(f"{reverse('analytics:feed')}?{ref.to_query()}")
        self.assertContains(response, "sebutan pendukung")

    def test_an_unknown_evidence_kind_shows_the_normal_feed(self):
        self.mention(target=self.own)
        response = self.client.get(f"{reverse('analytics:feed')}?bukti=mengarang")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["evidence_ref"])
        self.assertEqual(len(response.context["page_obj"]), 1)

    def test_evidence_cannot_reach_another_tenants_mentions(self):
        other_tenant = Tenant.objects.create(name="Instansi B")
        other_project = Project.objects.create(tenant=other_tenant, name="Proyek B")
        other_target = AttributionTarget.objects.create(
            project=other_project, name="Rahasia", level=AttributionTarget.LEVEL_PUSAT
        )
        secret = Mention.objects.create(
            project=other_project, platform=self.platform, author_handle="@x",
            content_snippet="rahasia tetangga", sentiment=Mention.SENTIMENT_NEGATIVE,
            emotion=Mention.EMOTION_ANGER, posted_at=timezone.now(),
        )
        MentionAttribution.objects.create(
            mention=secret, target=other_target, sentiment=Mention.SENTIMENT_NEGATIVE
        )
        ref = EvidenceRef("attribution", {"target": other_target.pk})
        response = self.client.get(f"{reverse('analytics:feed')}?{ref.to_query()}")
        self.assertNotContains(response, "rahasia tetangga")


class AttributionCorrectionViewTest(IntelligenceViewTestBase):
    def test_analyst_can_correct_who_is_being_blamed(self):
        mention = self.mention(target=self.pusat)
        response = self.client.post(
            reverse("analytics:correct_attribution", args=[mention.pk]),
            {"target": self.own.pk, "sentiment": Mention.SENTIMENT_NEGATIVE},
        )
        self.assertEqual(response.status_code, 302)
        row = mention.attributions.get(target=self.own)
        self.assertEqual(row.source, MentionAttribution.SOURCE_MANUAL)
        self.assertTrue(LabelCorrection.objects.filter(field="attribution").exists())

    def test_invalid_sentiment_is_rejected(self):
        mention = self.mention(target=self.pusat)
        self.client.post(
            reverse("analytics:correct_attribution", args=[mention.pk]),
            {"target": self.own.pk, "sentiment": "mengarang"},
        )
        self.assertFalse(mention.attributions.filter(target=self.own).exists())

    def test_a_target_from_another_project_is_rejected(self):
        other_tenant = Tenant.objects.create(name="Instansi B")
        other_project = Project.objects.create(tenant=other_tenant, name="Proyek B")
        stranger = AttributionTarget.objects.create(
            project=other_project, name="Asing", level=AttributionTarget.LEVEL_PUSAT
        )
        mention = self.mention(target=self.pusat)
        response = self.client.post(
            reverse("analytics:correct_attribution", args=[mention.pk]),
            {"target": stranger.pk, "sentiment": Mention.SENTIMENT_NEGATIVE},
        )
        self.assertEqual(response.status_code, 404)

    def test_a_viewer_cannot_correct_attribution(self):
        AnalystProfile.objects.update_or_create(
            user=self.user,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_VIEWER},
        )
        mention = self.mention(target=self.pusat)
        response = self.client.post(
            reverse("analytics:correct_attribution", args=[mention.pk]),
            {"target": self.own.pk, "sentiment": Mention.SENTIMENT_NEGATIVE},
        )
        self.assertIn(response.status_code, (302, 403))
        self.assertFalse(
            mention.attributions.filter(
                target=self.own, source=MentionAttribution.SOURCE_MANUAL
            ).exists()
        )


class DriverReviewViewTest(IntelligenceViewTestBase):
    def setUp(self):
        super().setUp()
        # "drivers" is an operational tool page, so it stays denied by default
        # (FR-1A.1) and a tenant admin grants it — exactly as with "taxonomy".
        PagePermission.objects.update_or_create(
            role=AnalystProfile.ROLE_ANALYST, page="drivers",
            defaults={"can_access": True},
        )

    def test_the_page_is_denied_until_an_admin_grants_it(self):
        PagePermission.objects.filter(page="drivers").update(can_access=False)
        response = self.client.get(reverse("analytics:driver_review"))
        self.assertEqual(response.status_code, 403)

    def test_review_page_lists_pending_candidates(self):
        DriverCandidate.objects.create(
            project=self.project, phrase="pungli sekolah", count=5
        )
        response = self.client.get(reverse("analytics:driver_review"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pungli sekolah")

    def test_promoting_a_candidate_creates_a_driver(self):
        candidate = DriverCandidate.objects.create(
            project=self.project, phrase="pungli sekolah", count=5
        )
        response = self.client.post(
            reverse("analytics:driver_promote", args=[candidate.pk]),
            {"name": "Pungutan liar sekolah"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            NegativeDriver.objects.filter(
                project=self.project, name="Pungutan liar sekolah"
            ).exists()
        )

    def test_dismissing_a_candidate_removes_it_from_the_queue(self):
        candidate = DriverCandidate.objects.create(
            project=self.project, phrase="tidak relevan", count=5
        )
        self.client.post(reverse("analytics:driver_dismiss", args=[candidate.pk]))
        candidate.refresh_from_db()
        self.assertTrue(candidate.dismissed)

    def test_another_tenants_candidate_is_not_reachable(self):
        other_tenant = Tenant.objects.create(name="Instansi B")
        other_project = Project.objects.create(tenant=other_tenant, name="Proyek B")
        candidate = DriverCandidate.objects.create(
            project=other_project, phrase="rahasia", count=5
        )
        response = self.client.post(
            reverse("analytics:driver_promote", args=[candidate.pk])
        )
        self.assertEqual(response.status_code, 404)


class EscalationViewTest(IntelligenceViewTestBase):
    def setUp(self):
        super().setUp()
        self.incident = Incident.objects.create(
            project=self.project, title="Jalan Rusak", is_confirmed=True,
        )
        for index in range(6):
            mention = self.mention(handle=f"@w{index}", target=self.own)
            self.incident.mentions.add(mention)

    def test_detail_shows_the_escalation_breakdown(self):
        escalation.assess_incident(self.incident)
        response = self.client.get(
            reverse("analytics:insiden_detail", args=[self.incident.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Potensi eskalasi")
        self.assertContains(response, "Kecepatan percakapan")

    def test_detail_names_signals_that_had_no_data(self):
        escalation.assess_incident(self.incident)
        response = self.client.get(
            reverse("analytics:insiden_detail", args=[self.incident.pk])
        )
        self.assertContains(response, "Toksisitas diskusi")
        self.assertContains(response, "tidak ada data")

    def test_detail_renders_before_any_assessment_exists(self):
        response = self.client.get(
            reverse("analytics:insiden_detail", args=[self.incident.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Belum ada penilaian eskalasi")

    def test_recompute_creates_an_assessment(self):
        response = self.client.post(
            reverse("analytics:insiden_escalation", args=[self.incident.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.incident.escalations.exists())

    def test_board_shows_the_escalation_chip(self):
        escalation.assess_incident(self.incident)
        response = self.client.get(reverse("analytics:insiden"))
        self.assertContains(response, "escalation-chip")

    def test_incident_detail_suggests_the_opd_people_are_naming(self):
        pu_target = AttributionTarget.objects.get(name="Dinas Pekerjaan Umum")
        for index in range(4):
            mention = self.mention(handle=f"@pu{index}", target=pu_target)
            self.incident.mentions.add(mention)
        response = self.client.get(
            reverse("analytics:insiden_detail", args=[self.incident.pk])
        )
        self.assertEqual(
            response.context["attribution"]["suggested_opd"], self.opd
        )
