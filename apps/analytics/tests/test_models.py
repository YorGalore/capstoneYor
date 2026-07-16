from django.test import TestCase
from django.utils import timezone

from apps.core.models import Platform, Project, Tenant
from apps.analytics.models import Alert, AlertRule, Coalition, Mention, PoliticalIssue


class AnalyticsModelsTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Kemenko PMK")
        self.project = Project.objects.create(tenant=self.tenant, name="Program Pangan Rakyat")
        self.platform = Platform.objects.create(
            slug="x", display_name="X (Twitter)", method=Platform.METHOD_INTERNAL
        )

    def test_mention_str_and_defaults(self):
        mention = Mention.objects.create(
            project=self.project,
            platform=self.platform,
            author_handle="@warga_peduli21",
            content_snippet="Contoh sebutan",
            sentiment=Mention.SENTIMENT_NEGATIVE,
            emotion=Mention.EMOTION_ANGER,
            posted_at=timezone.now(),
        )
        self.assertIn("@warga_peduli21", str(mention))
        self.assertFalse(mention.is_political)

    def test_coalition_and_issue(self):
        coalition = Coalition.objects.create(
            name="Koalisi Nusantara Raya", slug="nusantara-raya",
            stance=Coalition.STANCE_PETAHANA, color="#4656C9",
        )
        issue = PoliticalIssue.objects.create(
            project=self.project,
            title="Distribusi Pangan Wilayah Timur", opened_at=timezone.now(),
            owner_label="Tim Respons Cepat",
        )
        mention = Mention.objects.create(
            project=self.project,
            platform=self.platform,
            author_handle="@gerakmaju_net",
            content_snippet="Isu politik",
            sentiment=Mention.SENTIMENT_NEUTRAL,
            emotion=Mention.EMOTION_TRUST,
            posted_at=timezone.now(),
            is_political=True,
            coalition=coalition,
            issue=issue,
        )
        self.assertEqual(mention.coalition, coalition)
        self.assertEqual(mention.issue, issue)

    def test_alert_ordering_is_most_recent_first(self):
        rule = AlertRule.objects.create(
            project=self.project,
            name="Rasio-Neg-3J", condition_summary="Negatif > 55% dalam 3 jam",
            channel=AlertRule.CHANNEL_WEBHOOK,
        )
        older = Alert.objects.create(
            project=self.project, rule=rule, severity=Alert.SEVERITY_WARNING, title="Lama", detail="...",
            triggered_at=timezone.now() - timezone.timedelta(hours=2),
        )
        newer = Alert.objects.create(
            project=self.project, rule=rule, severity=Alert.SEVERITY_CRITICAL, title="Baru", detail="...",
            triggered_at=timezone.now(),
        )
        self.assertEqual(list(Alert.objects.all()), [newer, older])
