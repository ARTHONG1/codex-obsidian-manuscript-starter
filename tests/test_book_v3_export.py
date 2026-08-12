from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.test_blog_renderer import PYTHON
from tests.test_manuscript_v3 import BookV3PackageMixin
from tests import test_desktop_publication_export as export_support


class BookV3ExportTests(BookV3PackageMixin, unittest.TestCase):
    def test_canonical_v3_exports_list_rows_string_bodies_and_panel_images_in_render_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            version = root / "source" / "v0.1"
            version.mkdir(parents=True)
            manuscript, manifest, report = self.write_v3_package(version)
            validator = export_support.manuscript_support.VALIDATOR
            renderer = export_support.manuscript_support.RENDERER
            validation = subprocess.run([str(PYTHON), str(validator), str(manuscript), str(manifest), str(report)], capture_output=True, text=True)
            self.assertEqual(validation.returncode, 0, validation.stderr)
            rendered = subprocess.run([str(PYTHON), str(renderer), str(manuscript), str(version)], capture_output=True, text=True)
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            (version / "production-plan.json").write_text(json.dumps({"status": "verified"}), encoding="utf-8")

            request = export_support.exporter.ExportRequest(
                source_version_dir=version,
                publication_root=root / "Desktop" / "옵시디언 원고",
                project_destination_root="AAA AI Agent Automation",
                vault_path=root / "Codex-Wiki",
            )
            request.vault_path.mkdir()
            result = export_support.exporter.export_publication_bundle(request)
            latest = Path(result["latest_path"])
            copy_text = (latest / "01 본문-복사용.txt").read_text(encoding="utf-8")
            export_manifest = json.loads((latest / "_meta" / "export-manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "exported")
            self.assertIn("대상: 서술형 평가 업무를 맡은 교사", copy_text)
            self.assertIn("평가 기준과 예시 답안을 Codex에 전달해 분석을 요청합니다.", copy_text)
            self.assertNotIn("평 가 기 준 과", copy_text)
            self.assertLess(copy_text.index("[이미지 01 삽입: 미리보기]"), copy_text.index("[이미지 02 삽입: 실습 전 준비]"))
            self.assertLess(copy_text.index("[이미지 02 삽입: 실습 전 준비]"), copy_text.index("[이미지 03 삽입: 평가 기준 분석]"))
            self.assertIn("교사는 실제 평가표와 결과 파일을 비교해 최종 판단합니다.", copy_text)
            self.assertEqual(export_manifest["template_version"], 3)
            self.assertEqual(export_manifest["editorial_quality_version"], 3)


if __name__ == "__main__":
    unittest.main()
