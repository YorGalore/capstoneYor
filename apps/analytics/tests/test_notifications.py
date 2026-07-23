from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from apps.analytics import alerting, authors, notifications
from apps.analytics.models import (
    Alert, AlertRule, Author, DailyBrief, DailyBriefIssue, Mention, NotificationDelivery,
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
