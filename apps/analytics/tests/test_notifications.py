import json
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.analytics import alerting, authors, notifications
from apps.analytics.models import (
    Alert, AlertRule, Author, BrowserPushSubscription, DailyBrief, DailyBriefIssue,
    Mention, NotificationDelivery,
)
from apps.core.models import AnalystProfile, Platform, Project, Tenant
from apps.governance import scheduling
from apps.governance.models import ScheduledJob


def _setup_project():
    tenant = Tenant.objects.create(name="Tenant Uji")
    project = Project.objects.create(tenant=tenant, name="Proyek Uji")
    platform = Platform.objects.create(slug="x-uji", display_name="X Uji")
    user = User.objects.create_user("analis.uji", email="analis@uji.go.id")
    # A core signal may auto-create the profile; either way, pin it to our tenant.
    AnalystProfile.objects.update_or_create(user=user, defaults={"tenant": tenant})
    return project, platform


def _mention(project, platform, **kwargs):
    defaults = dict(
        project=project, platform=platform, author_handle="akun_uji",
        content_snippet="uji", sentiment=Mention.SENTIMENT_NEGATIVE,
        emotion=Mention.EMOTION_ANGER, posted_at=timezone.now(),
        reach_estimate=1000, engagement_count=50,
    )
    defaults.update(kwargs)
    return Mention.objects.create(**defaults)


class AlertDeliveryTests(TestCase):
    def test_triggered_email_rule_delivers_and_records(self):
        project, platform = _setup_project()
        AlertRule.objects.create(
            project=project, name="Rasio negatif", condition_summary="x",
            channel=AlertRule.CHANNEL_EMAIL,
            condition_type=AlertRule.CONDITION_NEGATIVE_RATIO,
            threshold=0.5, window_minutes=60,
        )
        _mention(project, platform)

        triggered = alerting.evaluate_rules(project)

        self.assertEqual(len(triggered), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("analis@uji.go.id", mail.outbox[0].to)
        delivery = NotificationDelivery.objects.get(alert=triggered[0])
        self.assertEqual(delivery.status, NotificationDelivery.STATUS_SENT)
        self.assertEqual(delivery.kind, NotificationDelivery.KIND_ALERT)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"
    )
    def test_console_email_backend_is_not_recorded_as_sent(self):
        project, platform = _setup_project()
        rule = AlertRule.objects.create(
            project=project,
            name="Email belum dikonfigurasi",
            condition_summary="x",
            channel=AlertRule.CHANNEL_EMAIL,
            condition_type=AlertRule.CONDITION_VOLUME_SPIKE,
            threshold=1,
            window_minutes=60,
        )
        _mention(project, platform)

        alerting.evaluate_rules(project)

        delivery = NotificationDelivery.objects.get(alert__rule=rule)
        self.assertEqual(delivery.status, NotificationDelivery.STATUS_SKIPPED)
        self.assertIn("SMTP belum dikonfigurasi", delivery.detail)
        self.assertEqual(len(mail.outbox), 0)

    def test_webhook_rule_without_url_is_recorded_as_skipped(self):
        project, platform = _setup_project()
        rule = AlertRule.objects.create(
            project=project, name="Webhook", condition_summary="x",
            channel=AlertRule.CHANNEL_WEBHOOK,
            condition_type=AlertRule.CONDITION_VOLUME_SPIKE,
            threshold=1, window_minutes=60,
        )
        _mention(project, platform)

        alerting.evaluate_rules(project)

        delivery = NotificationDelivery.objects.get(alert__rule=rule)
        self.assertEqual(delivery.status, NotificationDelivery.STATUS_SKIPPED)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        WEBPUSH_VAPID_PUBLIC_KEY="public-test-key",
        WEBPUSH_VAPID_PRIVATE_KEY="private-test-key",
        WEBPUSH_VAPID_CONTACT="mailto:ops@example.test",
    )
    @mock.patch("pywebpush.webpush")
    def test_push_rule_delivers_to_opted_in_tenant_browser(self, webpush):
        project, platform = _setup_project()
        user = User.objects.get(username="analis.uji")
        BrowserPushSubscription.objects.create(
            project=project,
            user=user,
            endpoint="https://push.example.test/subscription/one",
            p256dh="public-client-key",
            auth="client-auth",
        )
        rule = AlertRule.objects.create(
            project=project,
            name="Push nyata",
            condition_summary="x",
            channel=AlertRule.CHANNEL_PUSH,
            condition_type=AlertRule.CONDITION_VOLUME_SPIKE,
            threshold=1,
            window_minutes=60,
        )
        _mention(project, platform)

        alerting.evaluate_rules(project)

        delivery = NotificationDelivery.objects.get(alert__rule=rule)
        self.assertEqual(delivery.status, NotificationDelivery.STATUS_SENT)
        self.assertIn("1/1 browser", delivery.detail)
        webpush.assert_called_once()
        self.assertEqual(
            webpush.call_args.kwargs["subscription_info"]["endpoint"],
            "https://push.example.test/subscription/one",
        )


class BrowserPushSubscriptionViewTests(TestCase):
    def setUp(self):
        self.project, _platform = _setup_project()
        self.user = User.objects.get(username="analis.uji")
        self.client.force_login(self.user)
        self.payload = {
            "endpoint": "https://push.example.test/subscription/browser-a",
            "keys": {"p256dh": "public-client-key", "auth": "client-auth"},
        }

    def test_browser_can_opt_in_and_out(self):
        response = self.client.post(
            reverse("analytics:push_subscribe"),
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        subscription = BrowserPushSubscription.objects.get(user=self.user)
        self.assertTrue(subscription.is_active)
        self.assertEqual(subscription.project, self.project)

        response = self.client.post(
            reverse("analytics:push_unsubscribe"),
            data=json.dumps({"endpoint": self.payload["endpoint"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        subscription.refresh_from_db()
        self.assertFalse(subscription.is_active)

    def test_invalid_non_https_endpoint_is_rejected(self):
        self.payload["endpoint"] = "http://push.example.test/subscription"
        response = self.client.post(
            reverse("analytics:push_subscribe"),
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(BrowserPushSubscription.objects.exists())

    def test_service_worker_is_public_and_root_scoped(self):
        self.client.logout()
        response = self.client.get(
            reverse("analytics:push_service_worker"), secure=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        self.assertContains(response, 'self.addEventListener("push"')

    @override_settings(
        WEBPUSH_VAPID_PUBLIC_KEY="public-test-key",
        WEBPUSH_VAPID_PRIVATE_KEY="private-test-key",
        WEBPUSH_VAPID_CONTACT="mailto:ops@example.test",
    )
    def test_dashboard_exposes_opt_in_only_when_delivery_is_configured(self):
        response = self.client.get(reverse("analytics:ringkasan"))
        self.assertContains(response, "Aktifkan notifikasi")
        self.assertContains(response, "public-test-key")


class BriefDistributionTests(TestCase):
    def _final_brief(self, project):
        brief = DailyBrief.objects.create(
            project=project,
            brief_date=timezone.localdate() - timezone.timedelta(days=1),
            status=DailyBrief.STATUS_FINAL, finalized_by="Uji",
            finalized_at=timezone.now(),
        )
        DailyBriefIssue.objects.create(
            brief=brief, title="Isu Uji", content="Isi", approved=True,
        )
        return brief

    def test_send_brief_emails_once(self):
        project, _platform = _setup_project()
        brief = self._final_brief(project)

        delivery = notifications.send_brief(brief)

        self.assertEqual(delivery.status, NotificationDelivery.STATUS_SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(notifications.brief_already_sent(brief))

    def test_draft_brief_is_not_distributed(self):
        project, _platform = _setup_project()
        brief = DailyBrief.objects.create(
            project=project, brief_date=timezone.now().date(),
            status=DailyBrief.STATUS_DRAFT,
        )
        delivery = notifications.send_brief(brief)
        self.assertEqual(delivery.status, NotificationDelivery.STATUS_SKIPPED)
        self.assertEqual(len(mail.outbox), 0)

    def test_scheduled_job_distributes_final_brief_exactly_once(self):
        project, _platform = _setup_project()
        self._final_brief(project)
        job = ScheduledJob.objects.create(
            project=project, job_type=ScheduledJob.JOB_SEND_BRIEF, cadence_minutes=60,
        )

        scheduling.run_job(job)
        self.assertEqual(len(mail.outbox), 1)

        job.next_run_at = timezone.now()
        job.save()
        scheduling.run_job(job)
        self.assertEqual(len(mail.outbox), 1)  # dedup: not sent twice
        self.assertIn("sudah terdistribusi", job.last_detail)


class AuthorEnrichmentTests(TestCase):
    def test_enrich_links_mentions_and_scores_authors(self):
        project, platform = _setup_project()
        _mention(project, platform, author_handle="akun_a", external_id="a1")
        _mention(project, platform, author_handle="akun_a", external_id="a2", source_url="https://x/a2")
        _mention(project, platform, author_handle="akun_b", external_id="b1", source_url="https://x/b1")

        result = authors.enrich(project)

        self.assertEqual(result["linked"], 3)
        self.assertEqual(result["scored"], 2)
        author_a = Author.objects.get(platform=platform, handle="akun_a")
        author_b = Author.objects.get(platform=platform, handle="akun_b")
        self.assertGreater(author_a.influence_score, author_b.influence_score)
        self.assertEqual(Mention.objects.filter(author__isnull=True).count(), 0)

    def test_enrich_is_idempotent(self):
        project, platform = _setup_project()
        _mention(project, platform)
        authors.enrich(project)
        result = authors.enrich(project)
        self.assertEqual(result["linked"], 0)
        self.assertEqual(Author.objects.count(), 1)
