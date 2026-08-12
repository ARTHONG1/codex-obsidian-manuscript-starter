from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image as PillowImage
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(os.environ.get("CODEX_BUNDLED_PYTHON", sys.executable))
SCRIPTS = ROOT / "plugins" / "obsidian-manuscript-publisher" / "skills" / "obsidian-manuscript-publisher" / "scripts"
RENDERER = SCRIPTS / "render_manuscript.py"
VALIDATOR = SCRIPTS / "validate_manuscript.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def _quality_review() -> dict:
    return {
        "purpose_match": True,
        "professional_layout": True,
        "legible_content": True,
        "no_generation_artifacts": True,
        "no_generic_ai_motifs": True,
        "review_note": "화면의 결과와 확인 기준이 한눈에 구분됩니다.",
    }


def _brief() -> dict:
    return {
        "purpose": "검증 가능한 제작 단계 설명",
        "screen_state": "검증 완료",
        "visible_elements": ["파일", "테스트 결과"],
        "reader_check": "결과가 요청한 구조와 일치하는지 확인합니다.",
        "style": "editorial",
        "forbidden_overlays": ["red_box", "numbered_callout", "arrow"],
    }


class BookV3PackageMixin:
    def write_v3_package(self, directory: Path, *, include_real_panel: bool = True) -> tuple[Path, Path, Path]:
        assets_dir = directory / "assets"
        assets_dir.mkdir()
        visuals: dict[str, dict] = {}
        records = []
        asset_definitions = [
            ("preview", "result_preview", "그림 1-07-1. 평가 자동화 결과 화면의 검토 항목 예시"),
            ("preparation", "work_product", "그림 1-07-2. 평가 기준과 예시 답안을 정리한 준비 자료"),
            ("step-01", "workflow_diagram", "그림 1-07-3. Codex가 제안한 평가 기준 분석 흐름"),
            ("step-02", "ui_screen", "그림 1-07-4. 입력 검증과 결과 저장을 확인하는 화면"),
        ]
        if include_real_panel:
            asset_definitions.append(("real-world", "field_scene", "그림 1-07-5. 교사가 결과 파일을 비교해 최종 판단하는 장면"))
        for sequence, (asset_id, visual_kind, caption) in enumerate(asset_definitions, start=1):
            image_path = assets_dir / f"{asset_id}.png"
            PillowImage.new("RGB", (1600, 900), (65 + sequence, 105 + sequence, 155 + sequence)).save(image_path)
            relative = f"assets/{image_path.name}"
            visual = {
                "asset_id": asset_id,
                "image": relative,
                "rel_path": relative,
                "caption": caption,
                "method": "generated_scene",
                "evidence_kind": "workflow",
                "visual_kind": visual_kind,
                "quality_review": _quality_review(),
                "visual_brief": _brief(),
            }
            visuals[asset_id] = visual
            records.append({
                "asset_id": asset_id,
                "output_path": relative,
                "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                "method": "generated_scene",
                "evidence_kind": "workflow",
                "visual_kind": visual_kind,
                "quality_review": _quality_review(),
                "prompt": "wide landscape composition, 16:9, professional editorial layout for a realistic Korean software work screen, no robot, no hologram, no neon interface",
            })

        manuscript = {
            "output_profile": "book_a4",
            "template_version": 3,
            "editorial_quality_version": 3,
            "source_markdown": "chapter.md",
            "part": "Part 1",
            "chapter": "07",
            "title": "평가 자동화 웹앱 제작",
            "subtitle": "기준 분석부터 결과 검토까지",
            "chapter_intro": "평가 기준을 실제 자료와 함께 정리해 웹앱 제작 범위를 분명히 합니다. Codex가 제안한 구조를 검토하며 필요한 기능을 완성합니다.",
            "quick_reference": [
                {"category": "대상", "item": "서술형 평가 업무를 맡은 교사"},
                {"category": "활용 도구", "item": "Codex와 웹앱 개발 환경"},
                {"category": "준비물", "item": "개인정보를 제거한 평가 기준과 예시 답안"},
                {"category": "핵심 기능", "item": "입력 검증, 결과 저장, 검토 흐름"},
            ],
            "preview": {"summary": "평가 기준과 검토 결과를 한 화면에서 비교합니다.", "qr_target": "https://example.invalid/preview", "visual": visuals["preview"]},
            "preparation": {"summary": "평가 기준과 예시 답안을 먼저 준비합니다.", "visual": visuals["preparation"]},
            "practice_blocks": [
                {
                    "type": "step", "step_id": "step-01", "number": 1, "title": "평가 기준 분석",
                    "body": "평가 기준과 예시 답안을 Codex에 전달해 분석을 요청합니다. Codex가 필요한 데이터 구조와 구현 범위를 제안합니다. 사용자는 제안이 실제 평가 기준과 맞는지 확인합니다.",
                    "step_kind": "build", "build_action": "평가 기준을 구조화하고 데이터 모델을 제안합니다.",
                    "artifact": {"kind": "data_model", "name": "평가 기준 데이터 모델", "paths": ["criteria.json"], "status": "verified"},
                    "completion_check": "평가 기준의 필수 항목과 예외가 목록으로 확인됩니다.",
                    "interaction": {"user_request": "평가 기준을 분석해 데이터 구조를 제안해 달라고 Codex에 요청합니다.", "codex_action": "Codex가 항목과 예외를 분석해 데이터 구조를 제안합니다.", "user_check": "사용자는 실제 평가표와 제안된 항목을 비교합니다."},
                    "visual": visuals["step-01"],
                },
                {"type": "tip", "title": "기준 분리 점검", "body": "점수 규칙과 피드백 문구를 분리해 전달합니다. 서로 다른 기준이 섞이면 결과 검토가 어려워질 수 있습니다. 예시 답안은 개인정보를 지운 뒤 사용합니다."},
                {
                    "type": "step", "step_id": "step-02", "number": 2, "title": "검증 흐름 구현",
                    "body": "Codex에게 입력 검증과 결과 저장 기능을 구현하도록 요청합니다. Codex가 테스트용 자료로 오류를 확인하고 수정합니다. 사용자는 결과 파일과 오류 메시지를 함께 점검합니다.",
                    "step_kind": "build", "build_action": "입력 검증과 결과 저장 기능을 구현하고 테스트합니다.",
                    "artifact": {"kind": "feature", "name": "입력 검증과 결과 저장", "paths": ["app.py"], "status": "verified"},
                    "completion_check": "오류 입력이 차단되고 결과 파일이 저장됩니다.",
                    "interaction": {"user_request": "입력 검증과 결과 저장 기능을 만들어 달라고 Codex에 요청합니다.", "codex_action": "Codex가 기능을 구현하고 테스트 자료로 오류를 수정합니다.", "user_check": "사용자는 결과 파일과 오류 메시지를 확인합니다."},
                    "visual": visuals["step-02"],
                },
            ],
            "real_world_use": "완성한 웹앱은 평가 전에 기준과 결과 형식을 점검하는 보조 도구로 활용합니다.",
            "real_world_use_panel": {"summary": "교사는 실제 평가표와 결과 파일을 비교해 최종 판단합니다.", "visual": visuals["real-world"]} if include_real_panel else {"summary": "교사는 실제 평가표와 결과 파일을 비교해 최종 판단합니다."},
            "editorial_review": {"structure": 20, "specificity": 20, "voice": 15, "reproducibility": 15, "visuals": 15, "practice": 10, "safety": 5, "no_unverified_claims": True, "no_sensitive_data": True, "visuals_reviewed": True},
        }
        manuscript_path = directory / "manuscript.json"
        manifest_path = directory / "asset-manifest.json"
        report_path = directory / "asset-validation.json"
        manuscript_path.write_text(json.dumps(manuscript, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest_path.write_text(json.dumps({"assets": records}, ensure_ascii=False, indent=2), encoding="utf-8")
        (directory / "chapter.md").write_text("# 평가 자동화 웹앱 제작\n", encoding="utf-8")
        return manuscript_path, manifest_path, report_path

    def validate_v3_package(self, manuscript: Path, manifest: Path, report: Path):
        result = subprocess.run(
            [str(PYTHON), str(VALIDATOR), str(manuscript), str(manifest), str(report)],
            capture_output=True,
            text=True,
        )
        payload = json.loads(report.read_text(encoding="utf-8"))
        return result.returncode, payload


class NativeV3RendererTests(BookV3PackageMixin, unittest.TestCase):
    def test_validator_accepts_canonical_v3_shape_and_renderer_does_not_call_v2_functions(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            manuscript, manifest, report = self.write_v3_package(version_dir)
            status, validation = self.validate_v3_package(manuscript, manifest, report)
            self.assertEqual(status, 0, validation)
            renderer = _module(RENDERER, "native_v3_renderer")
            data = json.loads(manuscript.read_text(encoding="utf-8"))

            with (
                mock.patch.object(renderer, "render_v2_html", side_effect=AssertionError("V2 HTML must not render V3")),
                mock.patch.object(renderer, "render_v2_pdf", side_effect=AssertionError("V2 PDF must not render V3")),
            ):
                html = renderer.render_html(data, manuscript, version_dir)
                renderer.render_pdf(data, manuscript, version_dir / "manuscript.pdf")

            self.assertIn("평가 기준 분석", html)
            self.assertIn("[실습 전 준비]", html)
            self.assertIn("[꿀팁 더하기]", html)
            self.assertIn("교사는 실제 평가표와 결과 파일을 비교해 최종 판단합니다.", html)
            self.assertTrue((version_dir / "manuscript.pdf").is_file())
            self.assertGreater(len(PdfReader(str(version_dir / "manuscript.pdf")).pages), 0)

    def test_optional_v3_real_world_visual_does_not_create_an_image_requirement(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            manuscript, manifest, report = self.write_v3_package(version_dir, include_real_panel=False)
            status, validation = self.validate_v3_package(manuscript, manifest, report)
            self.assertEqual(status, 0, validation)
            renderer = _module(RENDERER, "native_v3_optional_real_renderer")
            html = renderer.render_html(json.loads(manuscript.read_text(encoding="utf-8")), manuscript, version_dir)

            self.assertIn("교사는 실제 평가표와 결과 파일을 비교해 최종 판단합니다.", html)
            self.assertNotIn("real-world.png", html)


if __name__ == "__main__":
    unittest.main()
