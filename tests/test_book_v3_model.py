from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "obsidian-manuscript-publisher" / "skills" / "obsidian-manuscript-publisher" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


from book_v3 import BookV3Error, parse_book_v3  # type: ignore[import-not-found]


def canonical_v3() -> dict:
    return {
        "output_profile": "book_a4",
        "template_version": 3,
        "editorial_quality_version": 3,
        "source_markdown": "chapter.md",
        "part": "Part 1",
        "chapter": "07",
        "title": "평가 자동화 웹앱 제작",
        "subtitle": "자료 분석부터 배포 확인까지",
        "chapter_intro": "실제 평가 기준을 바탕으로 웹앱 제작 과정을 구성합니다. 각 결과는 Codex와 함께 확인합니다.",
        "quick_reference": [
            {"category": "대상", "item": "평가 업무를 맡은 교사"},
            {"category": "활용 도구", "item": "Codex와 웹앱 도구"},
        ],
        "preview": {
            "summary": "채점 결과와 검토 항목을 한 화면에 정리합니다.",
            "qr_target": "https://example.invalid/preview",
            "visual": {"asset_id": "preview"},
        },
        "preparation": {
            "summary": "평가 기준과 예시 답안을 준비합니다.",
            "visual": {"asset_id": "preparation"},
        },
        "practice_blocks": [
            {
                "type": "step",
                "step_id": "step-01",
                "number": 1,
                "title": "평가 기준 분석",
                "body": "평가 기준과 예시 답안을 Codex에 전달해 분석을 요청합니다. Codex가 필요한 데이터 구조와 구현 범위를 제안합니다. 사용자는 제안이 실제 평가 기준과 맞는지 확인합니다.",
                "visual": {"asset_id": "step-01"},
            },
            {
                "type": "tip",
                "title": "기준 분리 점검",
                "body": "점수 규칙과 피드백 문구를 분리해 전달합니다. 서로 다른 기준이 섞이면 결과 검토가 어려워질 수 있습니다. 예시 답안은 개인정보를 지운 뒤 사용합니다.",
            },
            {
                "type": "step",
                "step_id": "step-02",
                "number": 2,
                "title": "검증 흐름 구현",
                "body": "Codex에게 입력 검증과 결과 저장 기능을 구현하도록 요청합니다. Codex가 테스트용 자료로 오류를 확인하고 수정합니다. 사용자는 결과 파일과 오류 메시지를 함께 점검합니다.",
                "visual": {"asset_id": "step-02"},
            },
        ],
        "real_world_use": "완성한 웹앱은 평가 전에 기준과 결과 형식을 점검하는 보조 도구로 활용합니다.",
        "real_world_use_panel": {
            "summary": "교사는 실제 평가표와 결과 파일을 비교해 최종 판단합니다.",
            "visual": {"asset_id": "real-world"},
        },
        "editorial_review": {"structure": 20, "specificity": 20, "voice": 15, "reproducibility": 15, "visuals": 10, "practice": 5, "safety": 5, "no_unverified_claims": True, "no_sensitive_data": True, "visuals_reviewed": True},
        "verification_note": "실제 도입 전에는 학교의 평가 기준과 개인정보 처리 원칙을 확인합니다.",
    }


class BookV3ModelTests(unittest.TestCase):
    def test_parses_canonical_list_rows_object_panels_and_string_bodies(self):
        view = parse_book_v3(canonical_v3())

        self.assertEqual([(row.category, row.item) for row in view.quick_reference], [
            ("대상", "평가 업무를 맡은 교사"),
            ("활용 도구", "Codex와 웹앱 도구"),
        ])
        self.assertEqual(view.preparation.summary, "평가 기준과 예시 답안을 준비합니다.")
        self.assertEqual(view.real_world_use_panel.summary, "교사는 실제 평가표와 결과 파일을 비교해 최종 판단합니다.")
        self.assertEqual([block.kind for block in view.practice_blocks], ["step", "tip", "step"])
        self.assertEqual(view.practice_blocks[0].body.split(". ")[0], "평가 기준과 예시 답안을 Codex에 전달해 분석을 요청합니다")

    def test_rejects_non_list_quick_reference_instead_of_guessing_a_v2_shape(self):
        payload = canonical_v3()
        payload["quick_reference"] = {"대상": "교사"}

        with self.assertRaisesRegex(BookV3Error, "quick_reference"):
            parse_book_v3(payload)

    def test_rejects_non_string_step_body_instead_of_joining_characters_or_items(self):
        payload = canonical_v3()
        payload["practice_blocks"][0]["body"] = ["첫 문장입니다.", "둘째 문장입니다."]

        with self.assertRaisesRegex(BookV3Error, "body"):
            parse_book_v3(payload)


if __name__ == "__main__":
    unittest.main()
