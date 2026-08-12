#!/usr/bin/env python3
"""Run a deterministic local Book V3 publication smoke test in a temp output tree."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from PIL import Image


ROOT = Path(__file__).resolve().parent
VALIDATOR = ROOT / "validate_manuscript.py"
RENDERER = ROOT / "render_manuscript.py"
EXPORTER = ROOT / "export_publication_bundle.py"


def _package(root: Path) -> Path:
    version = root / "source" / "v0.1"
    assets = version / "assets"
    assets.mkdir(parents=True)
    definitions = [("preview", "result_preview"), ("preparation", "work_product"), ("step-01", "workflow_diagram")]
    records = []
    visuals = {}
    for index, (asset_id, visual_kind) in enumerate(definitions, start=1):
        path = assets / f"{asset_id}.png"
        Image.new("RGB", (1600, 900), (40 + index, 80 + index, 120 + index)).save(path)
        relative = f"assets/{path.name}"
        visual = {
            "asset_id": asset_id,
            "image": relative,
            "caption": f"그림 1-01-{index}. 검증된 제작 결과 {index}",
            "method": "generated_scene",
            "evidence_kind": "workflow",
            "visual_kind": visual_kind,
            "quality_review": {"purpose_match": True, "professional_layout": True, "legible_content": True, "no_generation_artifacts": True, "no_generic_ai_motifs": True, "review_note": "검증을 위한 전문 화면입니다."},
            "visual_brief": {"purpose": "검증", "screen_state": "ready", "visible_elements": ["파일"], "reader_check": "파일을 확인합니다.", "style": "editorial", "forbidden_overlays": ["red_box", "numbered_callout", "arrow"]},
        }
        visuals[asset_id] = visual
        records.append({"asset_id": asset_id, "output_path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "method": "generated_scene", "evidence_kind": "workflow", "visual_kind": visual_kind, "quality_review": visual["quality_review"], "prompt": "wide landscape composition, 16:9, professional editorial layout, realistic software work product, no robot, no hologram, no neon interface"})
    manuscript = {
        "output_profile": "book_a4", "template_version": 3, "editorial_quality_version": 3, "source_markdown": "chapter.md", "part": "Part 1", "chapter": "01", "title": "V3 검증 패키지", "chapter_intro": "검증 가능한 제작 흐름을 구성합니다. 결과를 다시 확인합니다.",
        "quick_reference": [{"category": "대상", "item": "초보 사용자"}, {"category": "활용 도구", "item": "Codex"}, {"category": "준비물", "item": "검증 자료"}, {"category": "핵심 기능", "item": "검증"}],
        "preview": {"summary": "검증 결과를 확인합니다.", "visual": visuals["preview"]}, "preparation": {"summary": "검증 자료를 준비합니다.", "visual": visuals["preparation"]},
        "practice_blocks": [{"type": "step", "number": 1, "title": "검증 패키지 구성", "body": "Codex에게 검증 패키지를 구성하도록 요청합니다. 결과 파일을 확인합니다.", "step_kind": "build", "build_action": "검증 패키지를 구성합니다.", "artifact": {"kind": "file", "name": "검증 패키지", "paths": ["chapter.md"], "status": "verified"}, "completion_check": "검증 파일이 생성됩니다.", "interaction": {"user_request": "검증 패키지를 구성해 달라고 요청합니다.", "codex_action": "검증 패키지를 생성합니다.", "user_check": "결과 파일을 확인합니다."}, "visual": visuals["step-01"]}],
        "real_world_use": "검증 결과를 출판 전 확인합니다.", "editorial_review": {"structure": 20, "specificity": 20, "voice": 15, "reproducibility": 15, "visuals": 15, "practice": 10, "safety": 5, "no_unverified_claims": True, "no_sensitive_data": True, "visuals_reviewed": True},
    }
    (version / "manuscript.json").write_text(json.dumps(manuscript, ensure_ascii=False, indent=2), encoding="utf-8")
    (version / "asset-manifest.json").write_text(json.dumps({"assets": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    (version / "chapter.md").write_text("# V3 검증 패키지\n", encoding="utf-8")
    (version / "production-plan.json").write_text('{"status":"verified"}\n', encoding="utf-8")
    return version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            for path in sorted(args.output.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
        args.output.mkdir(parents=True, exist_ok=True)
        version = _package(args.output)
        report = version / "asset-validation.json"
        for command in (
            [sys.executable, str(VALIDATOR), str(version / "manuscript.json"), str(version / "asset-manifest.json"), str(report)],
            [sys.executable, str(RENDERER), str(version / "manuscript.json"), str(version)],
        ):
            completed = subprocess.run(command, capture_output=True, text=True)
            if completed.returncode != 0:
                raise RuntimeError("v3_validation_or_render_failed")
        result = subprocess.run([sys.executable, str(EXPORTER), "--source-version-dir", str(version), "--publication-root", str(args.output / "Desktop" / "옵시디언 원고"), "--project-destination-root", "V3 Verification", "--vault-path", str(args.output / "Vault")], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("v3_desktop_export_failed")
        payload = json.loads(result.stdout)
        if payload.get("status") not in {"exported", "already_exported"}:
            raise RuntimeError("v3_desktop_export_not_verified")
        print(json.dumps({"status": "ready", "desktop_export": payload.get("status"), "source_version": "v0.1"}, ensure_ascii=False))
        return 0
    except Exception as error:
        print(json.dumps({"status": "failed", "code": "v3_release_verification_failed", "error": type(error).__name__}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
