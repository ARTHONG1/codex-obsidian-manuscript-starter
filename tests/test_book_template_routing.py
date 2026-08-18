from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "obsidian-manuscript-publisher" / "skills" / "obsidian-manuscript-publisher" / "scripts" / "select_book_template.py"


def load_module():
    spec = importlib.util.spec_from_file_location("select_book_template", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BookTemplateRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = load_module()

    def test_generic_a4_request_selects_v3(self):
        result = self.router.select_book_template("이 대화를 바탕으로 A4 원고를 만들어줘")
        self.assertEqual(result["template_version"], 3)
        self.assertEqual(result["reason"], "default_new_book_a4")

    def test_generic_next_version_request_selects_v3(self):
        result = self.router.select_book_template("다음 버전의 원고를 만들어줘")
        self.assertEqual(result["template_version"], 3)

    def test_explicit_v2_request_selects_v2(self):
        result = self.router.select_book_template("V2 양식으로 원고를 만들어줘")
        self.assertEqual(result["template_version"], 2)

    def test_explicit_v3_wins_over_legacy_text(self):
        result = self.router.select_book_template(
            "V1 내용을 비교",
            requested_template_version=3,
        )
        self.assertEqual(result["template_version"], 3)

    def test_v10_does_not_match_v1(self):
        result = self.router.select_book_template("V10 테스트")
        self.assertEqual(result["template_version"], 3)

    def test_explicit_v1_and_v2_override_conflicting_text(self):
        self.assertEqual(
            self.router.select_book_template(
                "V2 양식",
                requested_template_version=1,
            )["template_version"],
            1,
        )
        self.assertEqual(
            self.router.select_book_template(
                "V1 양식",
                requested_template_version=2,
            )["template_version"],
            2,
        )

    def test_case_insensitive_token_markers_route_legacy_versions(self):
        self.assertEqual(
            self.router.select_book_template("please use v1")["template_version"],
            1,
        )
        self.assertEqual(
            self.router.select_book_template("please use V2")["template_version"],
            2,
        )

    def test_explicit_legacy_request_selects_v1(self):
        result = self.router.select_book_template("기존 레거시 V1 양식으로 다시 렌더링해줘")
        self.assertEqual(result["template_version"], 1)
        self.assertEqual(result["reason"], "explicit_legacy_request")

    def test_unknown_template_version_is_rejected(self):
        with self.assertRaises(ValueError):
            self.router.select_book_template("A4 원고", requested_template_version=4)

    def test_new_v3_contract_rejects_legacy_shape(self):
        with self.assertRaisesRegex(ValueError, "book_template_contract_mismatch"):
            self.router.assert_new_book_a4_contract({
                "output_profile": "book_a4",
                "template_version": 3,
                "editorial_quality_version": 3,
                "editorial_review": {},
                "practice_preparation": {"body": "준비"},
                "practice_blocks": [{"type": "step"}],
                "steps": [],
            })

    def test_new_v3_contract_requires_review_and_blocks(self):
        with self.assertRaisesRegex(ValueError, "book_template_contract_mismatch"):
            self.router.assert_new_book_a4_contract({
                "output_profile": "book_a4",
                "template_version": 3,
            })


if __name__ == "__main__":
    unittest.main()
