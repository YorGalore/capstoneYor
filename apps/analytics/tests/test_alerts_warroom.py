from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.analytics import alerting
from apps.analytics.models import (
    Alert, AlertRule, Mention, PoliticalIssue, ResponseAction,
)
from apps.core.models import AnalystProfile, Platform, Project, Tenant

User = get_user_model()


class AlertEngineTest(TestCase):
    def setUp(self):
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.issue = PoliticalIssue.objects.create(
            title="Distribusi Pangan", opened_at=timezone.now(), owner_label="Humas"
        )
        self.rule = AlertRule.objects.create(
            name="Lonjakan sentimen negatif",
            condition_summary="Rasio negatif > 60% dalam 60 menit",
            channel=AlertRule.CHANNEL_EMAIL,
            condition_type=AlertRule.CONDITION_NEGATIVE_RATIO,
            threshold=0.6, window_minutes=60,
        )

    def _mention(self, sentiment, minutes_ago=5):
        return Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@a",
            content_snippet="teks", sentiment=sentiment, emotion=Mention.EMOTION_TRUST,
            issue=self.issue, posted_at=timezone.now() - timedelta(minutes=minutes_ago),
        )

    def test_rule_triggers_when_negative_ratio_breaches_threshold(self):
        for _ in range(7):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        for _ in range(3):
            self._mention(Mention.SENTIMENT_POSITIVE)

        triggered = alerting.evaluate_rules(self.project)

        self.assertEqual(len(triggered), 1)
        alert = triggered[0]
        self.assertEqual(alert.rule, self.rule)
        self.assertEqual(alert.status, Alert.STATUS_ACTIVE)
        self.assertIn("70", alert.detail)  # 70% negative

    def test_rule_does_not_trigger_below_threshold(self):
        for _ in range(2):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        for _ in range(8):
            self._mention(Mention.SENTIMENT_POSITIVE)

        self.assertEqual(alerting.evaluate_rules(self.project), [])
        self.assertEqual(Alert.objects.count(), 0)

    def test_mentions_outside_window_are_ignored(self):
        for _ in range(9):
            self._mention(Mention.SENTIMENT_NEGATIVE, minutes_ago=180)  # older than window
        self._mention(Mention.SENTIMENT_POSITIVE, minutes_ago=5)

        self.assertEqual(alerting.evaluate_rules(self.project), [])

    def test_inactive_rule_is_skipped(self):
        self.rule.is_active = False
        self.rule.save()
        for _ in range(9):
            self._mention(Mention.SENTIMENT_NEGATIVE)

        self.assertEqual(alerting.evaluate_rules(self.project), [])

    def test_does_not_duplicate_an_already_active_alert(self):
        for _ in range(9):
            self._mention(Mention.SENTIMENT_NEGATIVE)

        alerting.evaluate_rules(self.project)
        alerting.evaluate_rules(self.project)  # second pass, same breach

        self.assertEqual(Alert.objects.filter(rule=self.rule, status=Alert.STATUS_ACTIVE).count(), 1)

    def test_volume_spike_rule(self):
        spike = AlertRule.objects.create(
            name="Lonjakan volume", condition_summary="Volume > 5 dalam 60 menit",
            channel=AlertRule.CHANNEL_PUSH, condition_type=AlertRule.CONDITION_VOLUME_SPIKE,
            threshold=5, window_minutes=60,
        )
        self.rule.is_active = False
        self.rule.save()
        for _ in range(6):
            self._mention(Mention.SENTIMENT_NEUTRAL)

        triggered = alerting.evaluate_rules(self.project)

        self.assertEqual([a.rule for a in triggered], [spike])


class WarRoomResponseLogTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.issue = PoliticalIssue.objects.create(
            title="Distribusi Pangan", opened_at=timezone.now(), owner_label="Humas"
        )
        self.user = User.objects.create(username="humas")
        AnalystProfile.objects.update_or_create(
            user=self.user, defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_ANALYST}
        )

    def test_logging_a_response_action_appears_on_the_timeline(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("analytics:log_response", args=[self.issue.pk]), {
            "action_type": ResponseAction.ACTION_CLARIFICATION,
            "description": "Klarifikasi resmi diterbitkan",
        })
        self.assertEqual(response.status_code, 302)

        action = ResponseAction.objects.get(issue=self.issue)
        self.assertEqual(action.action_type, ResponseAction.ACTION_CLARIFICATION)
        self.assertEqual(action.description, "Klarifikasi resmi diterbitkan")
        self.assertTrue(action.logged_by)

        page = self.client.get(reverse("analytics:war_room"))
        self.assertContains(page, "Klarifikasi resmi diterbitkan")

    def test_empty_description_is_rejected(self):
        self.client.force_login(self.user)
        self.client.post(reverse("analytics:log_response", args=[self.issue.pk]), {
            "action_type": ResponseAction.ACTION_STATEMENT, "description": "",
        })
        self.assertEqual(ResponseAction.objects.count(), 0)
