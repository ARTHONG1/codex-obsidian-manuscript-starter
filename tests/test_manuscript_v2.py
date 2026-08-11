from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "plugins" / "obsidian-manuscript-publisher" / "skills" / "obsidian-manuscript-publisher"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("validate_manuscript_v2", SKILL_ROOT / "scripts" / "validate_manuscript.py")
RENDERER = load_module("render_manuscript_v2", SKILL_ROOT / "scripts" / "render_manuscript.py")


class ManuscriptV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._assets = {}
        for asset_id in ("preview", "preparation", "step-01", "step-02"):
            path = self.root / "assets" / f"{asset_id}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (1200, 800), (235, 240, 245)).save(path)
            self._assets[asset_id] = path

    def tearDown(self):
        self.temp.cleanup()

    def _visual(self, asset_id: str, sequence: int, kind="work_product"):
        path = self._assets[asset_id]
        return {
            "asset_id": asset_id,
            "evidence_kind": "workflow",
            "method": "generated_scene",
            "image": f"assets/{asset_id}.png",
            "visual_kind": kind,
            "caption": f"그림 1-01-{sequence}. 제작 상태와 확인 기준",
            "quality_review": {
                "purpose_match": True,
                "professional_layout": True,
                "legible_content": True,
                "no_generation_artifacts": True,
                "no_generic_ai_motifs": True,
                "review_note": "전문적인 작업 화면으로 확인했습니다.",
            },
        }

    def _asset(self, asset_id: str, prompt=True, visual_kind="work_product"):
        path = self._assets[asset_id]
        return {
            "asset_id": asset_id,
            "output_path": f"assets/{asset_id}.png",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "evidence_kind": "workflow",
            "method": "generated_scene",
            "prompt": (
                "wide landscape composition, 16:9, professional editorial software UI, "
                "no robot, no hologram, no neon interface"
                if prompt else "bad prompt"
            ),
            "visual_kind": visual_kind,
            "quality_review": self._visual(asset_id, 1)["quality_review"],
        }

    def _step(self, number: int, asset_id: str, body: list[str]):
        return {
            "type": "step",
            "number": number,
            "title": f"제작 결과 {number} 확인",
            "body": body,
            "step_kind": "build",
            "build_action": "AI 에이전트가 제작 결과를 생성합니다.",
            "artifact": {"kind": "file", "name": "결과 파일", "paths": ["result.md"], "status": "verified"},
            "completion_check": "결과 파일이 생성되고 검증됩니다.",
            "interaction": {
                "user_request": "AI 에이전트에게 필요한 결과를 만들어 달라고 요청합니다.",
                "codex_action": "AI 에이전트가 파일을 생성하고 테스트합니다.",
                "user_check": "사용자가 결과와 완료 조건을 확인합니다.",
            },
            "visual": self._visual(asset_id, number + 2),
        }

    def _tip(self, after_step: int):
        return {
            "type": "tip",
            "after_step": after_step,
            "title": f"{after_step}단계 결과를 먼저 확인합니다",
            "body": ["다음 요청 전에 생성된 파일과 오류 메시지를 확인합니다.", "문제가 있으면 해당 결과를 그대로 AI 에이전트에 전달합니다."],
        }

    def _package(self, bad_body=False, bad_tip=False):
        step1_body = ["자료와 목표를 AI 에이전트에 전달합니다.", "AI 에이전트가 제작 구조를 제안하고 파일을 생성합니다."]
        step2_body = ["검증 기준과 예외 조건을 추가로 전달합니다.", "AI 에이전트가 테스트를 실행하고 결과를 수정합니다.", "사용자는 완료 조건과 실제 업무 적합성을 확인합니다."]
        if bad_body:
            step1_body = ["문장 하나만 있습니다."]
        blocks = [self._step(1, "step-01", step1_body), self._tip(1), self._step(2, "step-02", step2_body)]
        if bad_tip:
            blocks = [blocks[0], blocks[2]]
        manuscript = {
            "output_profile": "book_a4",
            "template_version": 2,
            "source_markdown": "chapter.md",
            "part": "Part 1",
            "chapter": "01",
            "title": "AI 에이전트 제작",
            "chapter_intro": "이번 장에서는 AI 에이전트 제작 과정을 익힙니다. 실제 결과를 확인하며 수정합니다.",
            "quick_reference": {"대상": "교사", "활용 도구": "AI 에이전트", "준비물": "업무 자료", "핵심 기능": "자동화"},
            "preview": {"result_title": "완성 결과", "result_summary": "결과를 확인합니다.", "visual": self._visual("preview", 1, "result_preview")},
            "practice_preparation": {"title": "실습 사전 준비", "body": "자료를 준비합니다.", "visual": self._visual("preparation", 2, "ui_screen")},
            "practice_blocks": blocks,
            "real_world_use": "학교 업무에 적용합니다. 실제 규정과 결과를 확인합니다.",
            "verification_note": "실제 적용 전 업무 규정을 확인합니다.",
        }
        assets = [
            self._asset("preview", visual_kind="result_preview"),
            self._asset("preparation", visual_kind="ui_screen"),
            self._asset("step-01"),
            self._asset("step-02"),
        ]
        return manuscript, {"assets": assets}

    def test_v2_validates_two_or_three_sentence_steps_and_interleaved_tips(self):
        manuscript, manifest = self._package()
        result = VALIDATOR.validate_package(manuscript, manifest, self.root)
        self.assertEqual(result["status"], "ready", result)

    def test_v2_rejects_step_with_one_sentence(self):
        manuscript, manifest = self._package(bad_body=True)
        result = VALIDATOR.validate_package(manuscript, manifest, self.root)
        self.assertIn("step_body_sentence_count", {issue["code"] for issue in result["errors"]})

    def test_v2_requires_one_tip_between_each_pair_of_steps(self):
        manuscript, manifest = self._package(bad_tip=True)
        result = VALIDATOR.validate_package(manuscript, manifest, self.root)
        self.assertIn("inter_step_tip_required", {issue["code"] for issue in result["errors"]})

    def test_v2_html_preserves_step_visual_caption_tip_order(self):
        manuscript, manifest = self._package()
        result = VALIDATOR.validate_package(manuscript, manifest, self.root)
        self.assertEqual(result["status"], "ready", result)
        html = RENDERER.render_html(manuscript, self.root / "manuscript.json", self.root)
        self.assertLess(html.index("Step 1."), html.index("[꿀팁 더하기]"))
        self.assertLess(html.index("[꿀팁 더하기]"), html.index("Step 2."))
        self.assertEqual(html.count("<figcaption>"), 4)

    def test_v2_renderer_creates_html_and_pdf(self):
        manuscript, manifest = self._package()
        manuscript["source_markdown"] = "chapter.md"
        manuscript_path = self.root / "manuscript.json"
        (self.root / "chapter.md").write_text("# V2", encoding="utf-8")
        manifest_path = self.root / "asset-manifest.json"
        manuscript_path.write_text(json.dumps(manuscript, ensure_ascii=False), encoding="utf-8")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        validation = VALIDATOR.validate_package(manuscript, manifest, self.root)
        validation["validated_inputs"] = {
            "manuscript_sha256": hashlib.sha256(manuscript_path.read_bytes()).hexdigest(),
            "asset_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        }
        (self.root / "asset-validation.json").write_text(json.dumps(validation), encoding="utf-8")
        RENDERER.main(manuscript_path, self.root)
        self.assertTrue((self.root / "manuscript.html").is_file())
        self.assertTrue((self.root / "manuscript.pdf").is_file())
        self.assertGreater((self.root / "manuscript.pdf").stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
