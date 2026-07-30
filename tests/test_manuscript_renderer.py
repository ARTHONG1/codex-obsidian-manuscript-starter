from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

from PIL import Image as PillowImage
from pypdf import PdfReader


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(os.environ.get("CODEX_BUNDLED_PYTHON", sys.executable))
SKILL_ROOT = REPOSITORY_ROOT / "plugins" / "obsidian-manuscript-publisher" / "skills" / "obsidian-manuscript-publisher"
RENDERER = SKILL_ROOT / "scripts" / "render_manuscript.py"
VALIDATOR = SKILL_ROOT / "scripts" / "validate_manuscript.py"
VERSIONER = SKILL_ROOT / "scripts" / "next_version.py"
class ManuscriptRendererTests(unittest.TestCase):
    def write_valid_package(self, directory: Path, *, dimensions=(1600, 900), remove_interaction_field=None):
        assets = directory / "assets"
        assets.mkdir()
        records = []
        visuals = {}
        visual_metadata = {
            "preview": ("result_preview", "그림 1-01-1. 완성된 자동화 Skill의 구성 예시 화면"),
            "step-01": ("work_product", "그림 1-01-2. Skill 파일과 실행 스크립트 구현 예시 화면"),
            "real-world-use": ("field_scene", "그림 1-01-3. 완성된 Skill을 학교 업무에 적용하는 예시 이미지"),
        }
        quality_review = {
            "purpose_match": True,
            "professional_layout": True,
            "legible_content": True,
            "no_generation_artifacts": True,
            "no_generic_ai_motifs": True,
            "review_note": "작업 목적과 결과물이 화면 중심에 명확하게 보입니다.",
        }
        for asset_id in ("preview", "step-01", "real-world-use"):
            visual_kind, caption = visual_metadata[asset_id]
            output_path = assets / f"{asset_id}.png"
            PillowImage.new("RGB", dimensions, "#5A78B5").save(output_path)
            relative_path = f"assets/{output_path.name}"
            payload = output_path.read_bytes()
            records.append({
                "asset_id": asset_id,
                "output_path": relative_path,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "evidence_kind": "workflow",
                "method": "generated_scene",
                "visual_kind": visual_kind,
                "quality_review": quality_review,
                "prompt": "wide landscape composition, 16:9, professional editorial layout for a realistic Korean IT textbook work screen, no robot, no hologram, no neon interface",
            })
            visuals[asset_id] = {
                "asset_id": asset_id,
                "evidence_kind": "workflow",
                "method": "generated_scene",
                "image": relative_path,
                "visual_kind": visual_kind,
                "quality_review": quality_review,
                "caption": caption,
            }

        interaction = {
            "user_request": "Codex에게 자동화 Skill을 만들어 달라고 요청합니다.",
            "codex_action": "Codex가 Skill 파일과 실행 스크립트를 생성합니다.",
            "user_check": "사용자는 생성 결과와 테스트 상태를 확인합니다.",
        }
        if remove_interaction_field:
            interaction.pop(remove_interaction_field)
        manuscript = {
            "part": "Part 1",
            "chapter": "01",
            "title": "Codex로 자동화 Skill 만들기",
            "chapter_intro": "Codex와 함께 업무 자동화 Skill을 제작합니다.",
            "quick_reference": {"대상": "교사", "활용 도구": "Codex", "준비물": "업무 규칙", "핵심 기능": "Skill 제작"},
            "preview": {"visual": visuals["preview"]},
            "steps": [{
                "title": "자동화 Skill 구조와 실행 스크립트 구현",
                "body": "이 문단은 구조화된 대화 문단으로 대체되어야 합니다.",
                "step_kind": "build",
                "build_action": "Skill 파일과 실행 스크립트를 생성하고 테스트합니다.",
                "artifact": {"kind": "file", "name": "자동화 Skill", "paths": ["SKILL.md"], "status": "verified"},
                "completion_check": "테스트가 통과합니다.",
                "interaction": interaction,
                "visual": visuals["step-01"],
            }],
            "real_world_use": "완성한 Skill을 실제 업무에 적용합니다.",
            "real_world_use_visual": visuals["real-world-use"],
            "tip": "업무 규칙과 예외를 먼저 전달합니다.",
            "verification_note": "실제 사용 전 결과를 확인합니다.",
        }
        manuscript_path = directory / "manuscript.json"
        manifest_path = directory / "asset-manifest.json"
        report_path = directory / "asset-validation.json"
        manuscript_path.write_text(json.dumps(manuscript, ensure_ascii=False), encoding="utf-8")
        manifest_path.write_text(json.dumps({"assets": records}, ensure_ascii=False), encoding="utf-8")
        return manuscript_path, manifest_path, report_path

    def validate_package(self, manuscript_path: Path, manifest_path: Path, report_path: Path):
        result = subprocess.run(
            [str(PYTHON), str(VALIDATOR), str(manuscript_path), str(manifest_path), str(report_path)],
            capture_output=True,
            text=True,
        )
        return result, json.loads(report_path.read_text(encoding="utf-8"))

    def test_validator_rejects_step_without_codex_user_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            manuscript, manifest, report = self.write_valid_package(Path(temporary), remove_interaction_field="user_request")
            result, validation = self.validate_package(manuscript, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("interaction_user_request_required", {issue["code"] for issue in validation["errors"]})

    def test_validator_rejects_portrait_generated_visuals(self):
        with tempfile.TemporaryDirectory() as temporary:
            manuscript, manifest, report = self.write_valid_package(Path(temporary), dimensions=(900, 1600))
            result, validation = self.validate_package(manuscript, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("landscape_image_required", {issue["code"] for issue in validation["errors"]})

    def test_validator_rejects_sentence_style_step_titles(self):
        with tempfile.TemporaryDirectory() as temporary:
            manuscript, manifest, report = self.write_valid_package(Path(temporary))
            payload = json.loads(manuscript.read_text(encoding="utf-8"))
            payload["steps"][0]["title"] = "Codex에게 제작 목표를 전달합니다"
            manuscript.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result, validation = self.validate_package(manuscript, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("step_title_sentence_style_forbidden", {issue["code"] for issue in validation["errors"]})

    def test_validator_rejects_verb_style_step_titles(self):
        with tempfile.TemporaryDirectory() as temporary:
            manuscript, manifest, report = self.write_valid_package(Path(temporary))
            payload = json.loads(manuscript.read_text(encoding="utf-8"))
            payload["steps"][0]["title"] = "뉴스 브리핑 규칙 설계하기"
            manuscript.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result, validation = self.validate_package(manuscript, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("step_title_sentence_style_forbidden", {issue["code"] for issue in validation["errors"]})

    def test_validator_accepts_nominal_step_titles(self):
        titles = [
            "실제 업무 자료 준비",
            "업무 규칙 분석과 자동화 설계",
            "CSV 생성 기능 구현",
            "외부 서비스 연결",
            "예약 실행 환경 설정",
            "생성 결과 검증과 오류 수정",
            "완성된 Skill 설치와 활용",
        ]
        for title in titles:
            with self.subTest(title=title), tempfile.TemporaryDirectory() as temporary:
                manuscript, manifest, report = self.write_valid_package(Path(temporary))
                payload = json.loads(manuscript.read_text(encoding="utf-8"))
                payload["steps"][0]["title"] = title
                manuscript.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                result, validation = self.validate_package(manuscript, manifest, report)
                self.assertEqual(result.returncode, 0, validation)

    def test_validator_rejects_report_style_step_prose(self):
        with tempfile.TemporaryDirectory() as temporary:
            manuscript, manifest, report = self.write_valid_package(Path(temporary))
            payload = json.loads(manuscript.read_text(encoding="utf-8"))
            payload["steps"][0]["interaction"]["codex_action"] = "Codex가 Skill 파일과 실행 스크립트를 구현했습니다."
            manuscript.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result, validation = self.validate_package(manuscript, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("step_report_tense_forbidden", {issue["code"] for issue in validation["errors"]})

    def test_validator_rejects_visual_without_purpose_kind(self):
        with tempfile.TemporaryDirectory() as temporary:
            manuscript, manifest, report = self.write_valid_package(Path(temporary))
            payload = json.loads(manuscript.read_text(encoding="utf-8"))
            payload["steps"][0]["visual"].pop("visual_kind")
            manuscript.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result, validation = self.validate_package(manuscript, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("visual_kind_required", {issue["code"] for issue in validation["errors"]})

    def test_validator_rejects_visual_without_quality_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            manuscript, manifest, report = self.write_valid_package(Path(temporary))
            payload = json.loads(manuscript.read_text(encoding="utf-8"))
            payload["steps"][0]["visual"].pop("quality_review")
            manuscript.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result, validation = self.validate_package(manuscript, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("visual_quality_review_required", {issue["code"] for issue in validation["errors"]})

    def test_validator_rejects_asset_without_quality_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            manuscript, manifest, report = self.write_valid_package(Path(temporary))
            manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
            manifest_payload["assets"][1].pop("quality_review")
            manifest.write_text(json.dumps(manifest_payload, ensure_ascii=False), encoding="utf-8")
            result, validation = self.validate_package(manuscript, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("asset_quality_review_required", {issue["code"] for issue in validation["errors"]})

    def test_validator_rejects_low_resolution_visuals(self):
        with tempfile.TemporaryDirectory() as temporary:
            manuscript, manifest, report = self.write_valid_package(Path(temporary), dimensions=(1100, 733))
            result, validation = self.validate_package(manuscript, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("visual_minimum_resolution_required", {issue["code"] for issue in validation["errors"]})

    def test_validator_rejects_unprofessional_visual_prompt(self):
        with tempfile.TemporaryDirectory() as temporary:
            manuscript, manifest, report = self.write_valid_package(Path(temporary))
            manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
            manifest_payload["assets"][1]["prompt"] = "wide landscape image of a robot with neon holograms"
            manifest.write_text(json.dumps(manifest_payload, ensure_ascii=False), encoding="utf-8")
            result, validation = self.validate_package(manuscript, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unprofessional_prompt_contract", {issue["code"] for issue in validation["errors"]})

    def test_validator_requires_prompt_to_exclude_generic_ai_motifs(self):
        with tempfile.TemporaryDirectory() as temporary:
            manuscript, manifest, report = self.write_valid_package(Path(temporary))
            manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
            manifest_payload["assets"][1]["prompt"] = "wide landscape composition, 16:9, professional editorial layout for a realistic Korean IT textbook work screen"
            manifest.write_text(json.dumps(manifest_payload, ensure_ascii=False), encoding="utf-8")
            result, validation = self.validate_package(manuscript, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unprofessional_prompt_contract", {issue["code"] for issue in validation["errors"]})

    def test_validator_rejects_unnumbered_visual_caption(self):
        with tempfile.TemporaryDirectory() as temporary:
            manuscript, manifest, report = self.write_valid_package(Path(temporary))
            payload = json.loads(manuscript.read_text(encoding="utf-8"))
            payload["steps"][0]["visual"]["caption"] = "예시 이미지: 작업 결과를 확인합니다."
            manuscript.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result, validation = self.validate_package(manuscript, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("figure_caption_format_required", {issue["code"] for issue in validation["errors"]})

    def test_renderer_uses_codex_dialogue_and_keeps_caption_with_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            manuscript, manifest, report = self.write_valid_package(temporary_path)
            output = temporary_path / "v0.1"
            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(manuscript), str(output)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (output / "manuscript.html").read_text(encoding="utf-8")
            self.assertIn("Codex에게 자동화 Skill을 만들어 달라고 요청합니다.", html)
            self.assertNotIn("이 문단은 구조화된 대화 문단으로 대체되어야 합니다.", html)
            self.assertIn('<figure class="visual-unit">', html)
            first_figure = html.index('<figure class="visual-unit">')
            first_caption = html.index("<figcaption>", first_figure)
            self.assertGreater(first_caption, first_figure)

    def test_renderer_accepts_numbered_caption_without_example_label(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            manuscript, _, _ = self.write_valid_package(temporary_path)
            payload = json.loads(manuscript.read_text(encoding="utf-8"))
            payload["steps"][0]["visual"]["caption"] = "그림 1-01-2. Skill 파일과 실행 스크립트 구현 화면"
            manuscript.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            output = temporary_path / "v0.1"
            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(manuscript), str(output)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (output / "manuscript.html").read_text(encoding="utf-8")
            self.assertIn("그림 1-01-2. Skill 파일과 실행 스크립트 구현 화면", html)

    def test_renderer_refuses_portrait_visuals_even_when_called_directly(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            manuscript, _, _ = self.write_valid_package(temporary_path, dimensions=(900, 1600))
            output = temporary_path / "v0.1"
            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(manuscript), str(output)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("landscape", result.stderr.lower())

    def test_renderer_creates_a4_html_and_pdf_with_all_steps(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            manuscript, _, _ = self.write_valid_package(temporary_path)
            output = temporary_path / "v0.1"
            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(manuscript), str(output)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (output / "manuscript.html").read_text(encoding="utf-8")
            self.assertIn("@page", html)
            self.assertIn("Codex로 자동화 Skill 만들기", html)
            self.assertIn("Step 1.", html)
            self.assertIn("이번 챕터에서는", html)
            self.assertTrue((output / "manuscript.pdf").is_file())
            self.assertGreater((output / "manuscript.pdf").stat().st_size, 10_000)
            pages = PdfReader(str(output / "manuscript.pdf")).pages
            self.assertGreater(len(pages[-1].extract_text().strip()), 100)

    def test_next_version_never_reuses_an_existing_draft_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            chapter = Path(temporary) / "Part 1" / "01"
            (chapter / "v0.1").mkdir(parents=True)
            (chapter / "v0.2").mkdir()
            result = subprocess.run(
                [str(PYTHON), str(VERSIONER), str(chapter)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual("v0.3", result.stdout.strip())
            self.assertTrue((chapter / "v0.1").is_dir())
            self.assertTrue((chapter / "v0.2").is_dir())


if __name__ == "__main__":
    unittest.main()
