from django.test import TestCase
from django.utils import timezone

from apps.governance import regulatory
from apps.governance.models import RegulatoryDocument


class CorpusRetrievalTest(TestCase):
    def setUp(self):
        RegulatoryDocument.objects.create(
            title="Permensos 1/2024 tentang Penyaluran Bantuan Pangan",
            source_ref="Permensos No. 1/2024 Pasal 12",
            body=(
                "Penyaluran bantuan pangan kepada keluarga penerima manfaat dilakukan "
                "paling lambat 14 hari sejak penetapan. Keterlambatan penyaluran wajib "
                "dilaporkan kepada dinas sosial setempat."
            ),
        )
        RegulatoryDocument.objects.create(
            title="Perpres 91/2023 tentang Subsidi Energi",
            source_ref="Perpres No. 91/2023 Pasal 4",
            body=(
                "Subsidi energi diberikan kepada golongan tarif tertentu. Penyesuaian "
                "harga bahan bakar minyak ditetapkan oleh menteri."
            ),
        )
        self.retired = RegulatoryDocument.objects.create(
            title="Aturan lama yang sudah dicabut",
            source_ref="SK Lama",
            body="Penyaluran bantuan pangan mengikuti skema lama.",
            retired_at=timezone.now(),
        )

    def test_retrieves_most_relevant_passage(self):
        hits = regulatory.retrieve("keterlambatan penyaluran bantuan pangan", limit=1)
        self.assertEqual(len(hits), 1)
        self.assertIn("Permensos", hits[0]["document"].title)
        self.assertGreater(hits[0]["score"], 0)

    def test_retrieval_returns_the_source_passage_for_verification(self):
        # FR-31.4: the retrieved passage must be independently visible, never
        # hidden inside the model call.
        hits = regulatory.retrieve("subsidi energi bahan bakar", limit=1)
        self.assertIn("Subsidi energi", hits[0]["passage"])
        self.assertEqual(hits[0]["source_ref"], "Perpres No. 91/2023 Pasal 4")

    def test_retired_documents_are_excluded(self):
        hits = regulatory.retrieve("penyaluran bantuan pangan skema lama", limit=5)
        titles = [h["document"].title for h in hits]
        self.assertNotIn(self.retired.title, titles)

    def test_no_match_returns_empty_rather_than_a_bad_citation(self):
        # Better to cite nothing than to fabricate a plausible-sounding one.
        self.assertEqual(regulatory.retrieve("resep rendang padang", limit=3), [])

    def test_topically_matching_regulation_outranks_an_incidental_word_match(self):
        """A food-price issue must not cite the fuel-subsidy regulation first just
        because the phrase "harga bahan" incidentally overlaps "bahan bakar".
        A wrong top citation is the exact risk FR-31.4 exists to mitigate.
        """
        hits = regulatory.retrieve("harga pangan beras sembako harga bahan naik", limit=2)
        self.assertTrue(hits)
        self.assertIn("Pangan", hits[0]["document"].title)


class RiskLevelTest(TestCase):
    def test_high_risk_when_negative_and_coordinated(self):
        level = regulatory.classify_risk(
            negative_ratio=0.8, volume_change_pct=200, coordinated=True
        )
        self.assertEqual(level, regulatory.RISK_HIGH)

    def test_medium_risk_on_elevated_negativity_alone(self):
        level = regulatory.classify_risk(
            negative_ratio=0.55, volume_change_pct=10, coordinated=False
        )
        self.assertEqual(level, regulatory.RISK_MEDIUM)

    def test_low_risk_when_calm(self):
        level = regulatory.classify_risk(
            negative_ratio=0.1, volume_change_pct=0, coordinated=False
        )
        self.assertEqual(level, regulatory.RISK_LOW)

    def test_coordination_alone_raises_risk_above_low(self):
        level = regulatory.classify_risk(
            negative_ratio=0.1, volume_change_pct=0, coordinated=True
        )
        self.assertNotEqual(level, regulatory.RISK_LOW)

    def test_risk_labels_use_operational_terminology(self):
        self.assertEqual(regulatory.RISK_LABELS[regulatory.RISK_HIGH], "Tinggi")
        self.assertEqual(regulatory.RISK_LABELS[regulatory.RISK_MEDIUM], "Sedang")
        self.assertEqual(regulatory.RISK_LABELS[regulatory.RISK_LOW], "Rendah")
