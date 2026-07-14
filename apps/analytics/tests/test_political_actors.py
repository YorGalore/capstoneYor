from django.test import TestCase
from django.utils import timezone

from apps.analytics import actors
from apps.analytics.models import (
    Camp, GovernmentProgram, Mention, PoliticalActor,
)
from apps.core.models import Platform, Project, Tenant


class ActorTaggingTest(TestCase):
    def setUp(self):
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")

        # Camps are purely user-defined — nothing is hard-coded by the platform (FR-24.3).
        self.camp_a = Camp.objects.create(project=self.project, name="Koalisi Petahana")
        self.camp_b = Camp.objects.create(project=self.project, name="Koalisi Penantang")

        self.actor_a = PoliticalActor.objects.create(
            project=self.project, name="Partai Alfa", actor_type=PoliticalActor.TYPE_PARTY,
            camp=self.camp_a, keywords=["partai alfa", "#alfa"], handles=["@partaialfa"],
        )
        self.actor_b = PoliticalActor.objects.create(
            project=self.project, name="Partai Beta", actor_type=PoliticalActor.TYPE_PARTY,
            camp=self.camp_b, keywords=["partai beta"], handles=["@partaibeta"],
        )

    def _mention(self, text, handle="@warga"):
        return Mention.objects.create(
            project=self.project, platform=self.platform, author_handle=handle,
            content_snippet=text, sentiment=Mention.SENTIMENT_NEUTRAL,
            emotion=Mention.EMOTION_TRUST, posted_at=timezone.now(),
        )

    def test_tags_mention_by_keyword(self):
        m = self._mention("dukungan untuk Partai Alfa meningkat")
        tagged = actors.tag_mention(m)
        self.assertEqual(set(tagged), {self.actor_a})
        self.assertIn(self.actor_a, m.political_actors.all())

    def test_tags_mention_by_official_handle(self):
        m = self._mention("pernyataan resmi hari ini", handle="@partaibeta")
        tagged = actors.tag_mention(m)
        self.assertEqual(set(tagged), {self.actor_b})

    def test_mention_can_match_multiple_actors(self):
        m = self._mention("debat Partai Alfa vs Partai Beta memanas")
        tagged = actors.tag_mention(m)
        self.assertEqual(set(tagged), {self.actor_a, self.actor_b})

    def test_mention_with_no_actor_stays_untagged(self):
        m = self._mention("cuaca cerah hari ini")
        self.assertEqual(actors.tag_mention(m), [])
        self.assertEqual(m.political_actors.count(), 0)

    def test_is_political_flag_set_when_tagged(self):
        m = self._mention("Partai Alfa bicara pangan")
        actors.tag_mention(m)
        m.refresh_from_db()
        self.assertTrue(m.is_political)


class CampShareOfVoiceTest(ActorTaggingTest):
    def test_share_of_voice_is_symmetric_per_camp(self):
        for _ in range(3):
            actors.tag_mention(self._mention("Partai Alfa unggul"))
        actors.tag_mention(self._mention("Partai Beta merespons"))

        sov = actors.share_of_voice(self.project)
        by_name = {row["camp"].name: row for row in sov}
        self.assertEqual(by_name["Koalisi Petahana"]["count"], 3)
        self.assertEqual(by_name["Koalisi Penantang"]["count"], 1)
        self.assertEqual(by_name["Koalisi Petahana"]["share_pct"], 75)
        self.assertEqual(by_name["Koalisi Penantang"]["share_pct"], 25)

    def test_share_of_voice_handles_no_data(self):
        self.assertEqual(
            [row["share_pct"] for row in actors.share_of_voice(self.project)], [0, 0]
        )


class GovernmentProgramTest(ActorTaggingTest):
    def test_program_tagging_and_sentiment_trend(self):
        program = GovernmentProgram.objects.create(
            project=self.project, name="Program Pangan Rakyat", keywords=["pangan rakyat"],
        )
        m = self._mention("Program Pangan Rakyat gagal di daerah")
        m.sentiment = Mention.SENTIMENT_NEGATIVE
        m.save()

        actors.tag_program(m)

        m.refresh_from_db()
        self.assertEqual(m.program, program)
        summary = actors.program_summary(program)
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["negative_pct"], 100)
