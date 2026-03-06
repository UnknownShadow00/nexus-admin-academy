import unittest

from app.routers.admin_quiz import _normalize_examcompass_title
from app.routers.study_tracker import _merge_scores_with_curriculum_titles, _title_key


class TitleMatchingTests(unittest.TestCase):
    def test_normalize_examcompass_title_strips_prefix_and_suffix(self):
        raw = "CompTIA A+ 220-1201 Practice Test: Mobile Device Hardware Servicing Quiz | ExamCompass"
        self.assertEqual(_normalize_examcompass_title(raw), "Mobile Device Hardware Servicing Quiz")

    def test_normalize_examcompass_title_falls_back_for_short_values(self):
        raw = "X:"
        self.assertEqual(_normalize_examcompass_title(raw), "X:")

    def test_title_key_normalizes_symbols_and_case(self):
        self.assertEqual(_title_key("Mobile Device Hardware Servicing Quiz"), "mobiledevicehardwareservicingquiz")
        self.assertEqual(_title_key("Mobile-Device: Hardware Servicing Quiz!"), "mobiledevicehardwareservicingquiz")

    def test_merge_scores_adds_fuzzy_curriculum_aliases(self):
        entry = {"score": 8, "total": 10, "pct": 80, "quiz_id": 7}
        scores_by_title = {"Mobile Device Hardware Servicing Quiz": entry}
        scores_by_title_key = {"mobiledevicehardwareservicingquiz": entry}
        curriculum_titles = [
            "Mobile Device Hardware Servicing Quiz",
            "Mobile-Device Hardware Servicing Quiz",
            "Networking Quiz",
        ]

        merged = _merge_scores_with_curriculum_titles(scores_by_title, scores_by_title_key, curriculum_titles)
        self.assertEqual(merged["Mobile Device Hardware Servicing Quiz"], entry)
        self.assertEqual(merged["Mobile-Device Hardware Servicing Quiz"], entry)
        self.assertNotIn("Networking Quiz", merged)


if __name__ == "__main__":
    unittest.main()
