from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.analytics.models import LabelCorrection, Mention
from apps.core.models import AnalystProfile, Platform, Project, Tenant

User = get_user_model()


class SentimentCorrectionTest(TestCase):
    def setUp(self):
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.mention = Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@a",
            content_snippet="teks", sentiment=Mention.SENTIMENT_NEUTRAL,
            sentiment_model="lexicon-v1", emotion=Mention.EMOTION_TRUST,
            posted_at=timezone.now(),
        )
        self.super_admin = self._user("super", AnalystProfile.ROLE_SUPER_ADMIN)
        self.analyst = self._user("analis", AnalystProfile.ROLE_ANALYST)
        self.viewer = self._user("peninjau", AnalystProfile.ROLE_VIEWER)

    def _user(self, name, role):
        user = User.objects.create(username=name)
        AnalystProfile.objects.update_or_create(
            user=user, defaults={"tenant": self.tenant, "role": role}
        )
        return user

    def test_correction_updates_mention_and_marks_manual(self):
        self.client.force_login(self.super_admin)
        response = self.client.post(
            reverse("analytics:correct_sentiment", args=[self.mention.pk]),
            {"sentiment": Mention.SENTIMENT_NEGATIVE},
        )
        self.assertEqual(response.status_code, 302)
        self.mention.refresh_from_db()
        self.assertEqual(self.mention.sentiment, Mention.SENTIMENT_NEGATIVE)
        self.assertEqual(self.mention.sentiment_model, "manual")

    def test_correction_records_history(self):
        self.client.force_login(self.super_admin)
        self.client.post(
            reverse("analytics:correct_sentiment", args=[self.mention.pk]),
            {"sentiment": Mention.SENTIMENT_POSITIVE},
        )
        correction = LabelCorrection.objects.get(mention=self.mention)
        self.assertEqual(correction.field, "sentiment")
        self.assertEqual(correction.old_value, Mention.SENTIMENT_NEUTRAL)
        self.assertEqual(correction.new_value, Mention.SENTIMENT_POSITIVE)
        self.assertTrue(correction.corrected_by)

    def test_analyst_has_feed_write_access_by_default(self):
        # ISS-FW-001: sentiment correction (FR-5.3) is core Analyst work, so this
        # must succeed without any manual permission-matrix grant.
        self.client.force_login(self.analyst)
        response = self.client.post(
            reverse("analytics:correct_sentiment", args=[self.mention.pk]),
            {"sentiment": Mention.SENTIMENT_NEGATIVE},
        )
        self.assertEqual(response.status_code, 302)
        self.mention.refresh_from_db()
        self.assertEqual(self.mention.sentiment, Mention.SENTIMENT_NEGATIVE)

    def test_viewer_cannot_correct_sentiment(self):
        # Peninjau gets default read access to the feed (ISS-FW-001) but must
        # still be blocked from writing — require_writer_role closes that gap.
        self.client.force_login(self.viewer)
        response = self.client.post(
            reverse("analytics:correct_sentiment", args=[self.mention.pk]),
            {"sentiment": Mention.SENTIMENT_NEGATIVE},
        )
        self.assertEqual(response.status_code, 403)
        self.mention.refresh_from_db()
        self.assertEqual(self.mention.sentiment, Mention.SENTIMENT_NEUTRAL)

    def test_invalid_sentiment_rejected(self):
        self.client.force_login(self.super_admin)
        self.client.post(
            reverse("analytics:correct_sentiment", args=[self.mention.pk]),
            {"sentiment": "bogus"},
        )
        self.mention.refresh_from_db()
        self.assertEqual(self.mention.sentiment, Mention.SENTIMENT_NEUTRAL)
        self.assertFalse(LabelCorrection.objects.exists())
