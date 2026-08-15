from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image as PillowImage
from PIL import ImageDraw


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(os.environ.get("CODEX_BUNDLED_PYTHON", sys.executable))
SKILL_ROOT = (
    REPOSITORY_ROOT
    / "plugins"
    / "obsidian-manuscript-publisher"
    / "skills"
    / "obsidian-manuscript-publisher"
)
VALIDATOR = SKILL_ROOT / "scripts" / "validate_blog.py"
RENDERER = SKILL_ROOT / "scripts" / "render_blog.py"


def same_file_target(left: Path, right: Path) -> bool:
    """Compare Windows paths by file identity, not 8.3/long spelling."""
    try:
        return os.path.samefile(left, right)
    except (FileNotFoundError, OSError):
        return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))

MODE_SECTIONS = {
    "practical_guide": [
        ("problem", "계획서를 다시 쓰게 되는 지점", ["학교 계획서는 형식보다 반복되는 확인 작업에서 시간이 더 걸립니다."]),
        ("principle", "자동화보다 먼저 세운 기준", ["핵심은 문장을 빨리 만드는 일이 아니라 누락을 검증할 기준을 고정하는 일입니다.", "실제 양식과 업무 규칙을 먼저 비교하면 자동화 범위를 좁힐 수 있습니다."]),
        ("method", "Codex에 맡긴 제작 과정", ["양식 파일과 필수 항목을 전달하고 생성 규칙과 예외를 설명합니다."]),
        ("evidence", "테스트에서 드러난 수정 지점", ["첫 실행에서는 날짜 형식 오류가 발견되어 검증 규칙을 추가했습니다."]),
        ("application", "학교 업무에 적용하는 기준", ["샘플 결과를 원본 양식과 비교한 뒤 실제 자료에 적용합니다."]),
    ],
    "case_story": [
        ("before", "반복 작성이 남긴 문제", ["같은 형식의 계획서를 매번 복사하면서 누락 항목이 생겼습니다."]),
        ("turning_point", "자동화 범위를 바꾼 판단", ["문장 생성보다 양식 검증을 먼저 자동화하기로 결정했습니다.", "이 선택으로 사람이 확인할 지점도 분명해졌습니다."]),
        ("process", "규칙을 파일로 옮긴 과정", ["실제 양식과 오류 사례를 Codex에 전달해 검사 기능을 만들었습니다."]),
        ("result", "테스트로 확인한 변화", ["날짜와 필수 항목 누락을 실행 단계에서 찾을 수 있었습니다."]),
        ("lesson", "다음 작업에 남은 기준", ["자동화의 범위는 사람이 확인할 기준과 함께 정해야 합니다."]),
    ],
    "insight_column": [
        ("observation", "빠른 생성 뒤에 남는 일", ["초안이 빨리 만들어져도 확인 기준이 없으면 검토 시간은 줄지 않습니다."]),
        ("contrast", "생성과 검증의 차이", ["생성은 빈 문서를 채우지만 검증은 실제 업무에 쓸 수 있는지를 가릅니다.", "두 작업을 하나로 부르면 자동화의 한계가 흐려집니다."]),
        ("principle", "사람이 맡아야 할 판단", ["학교별 규칙과 예외는 사용자가 최종 확인해야 합니다."]),
        ("example", "계획서 자동화에서 본 장면", ["날짜 형식 오류는 문장이 자연스러워도 결과를 사용할 수 없게 만들었습니다."]),
        ("implication", "도구를 평가하는 새로운 질문", ["무엇을 생성했는지보다 무엇을 검증했는지를 먼저 물어야 합니다."]),
    ],
}


def quality_review() -> dict:
    return {
        "purpose_match": True,
        "professional_layout": True,
        "legible_content": True,
        "no_generation_artifacts": True,
        "no_generic_ai_motifs": True,
        "review_note": "자동화 결과와 확인 지점이 화면 중심에 분명하게 보입니다.",
    }


def humanity_review() -> dict:
    return {
        "source_grounded_opening": True,
        "central_idea_consistency": True,
        "concrete_evidence": True,
        "visible_judgment": True,
        "varied_rhythm": True,
        "no_fabricated_experience": True,
        "review_note": "실제 오류와 선택 이유를 근거로 전개하고 과장된 경험을 만들지 않았습니다.",
    }


class BlogPackageMixin:
    def write_valid_package(
        self,
        directory: Path,
        *,
        mode: str = "practical_guide",
        include_section_visual: bool = True,
        section_visual_count: int | None = None,
        hero_method: str = "provided_asset",
        dimensions: tuple[int, int] = (1600, 900),
    ) -> tuple[Path, Path, Path]:
        assets_dir = directory / "assets"
        assets_dir.mkdir()
        asset_records = []

        def add_visual(asset_id: str, filename: str, method: str, caption: str, alt_text: str) -> dict:
            image_path = assets_dir / filename
            PillowImage.linear_gradient("L").resize(dimensions).convert("RGB").save(image_path)
            relative_path = f"assets/{filename}"
            record = {
                "asset_id": asset_id,
                "output_path": relative_path,
                "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                "evidence_kind": "software_result",
                "method": method,
                "visual_kind": "result_preview",
                "privacy_status": "cleared",
                "alt_text": alt_text,
                "quality_review": quality_review(),
            }
            if method == "generated_scene":
                record["prompt"] = (
                    "wide landscape composition, 16:9, professional editorial layout, "
                    "realistic school automation result, no robot, no hologram, no glowing brain, "
                    "no neon interface, no floating icons, no invented menus, no unreadable Korean"
                )
                record["disclosure"] = "AI 생성 설명 이미지"
            else:
                record["source"] = {
                    "kind": "conversation_attachment",
                    "reference": "conversation-turn-18",
                }
            asset_records.append(record)
            visual = {
                "asset_id": asset_id,
                "evidence_kind": "software_result",
                "method": method,
                "image": relative_path,
                "visual_kind": "result_preview",
                "privacy_status": "cleared",
                "alt_text": alt_text,
                "caption": caption,
                "quality_review": quality_review(),
            }
            if method == "generated_scene":
                visual["disclosure"] = "AI 생성 설명 이미지"
            return visual

        hero = add_visual(
            "hero",
            "hero.png",
            hero_method,
            "계획서 자동화 결과와 검증 항목을 함께 보여 주는 화면",
            "계획서 자동화 결과 옆에 날짜와 필수 항목 검증 결과가 표시된 화면",
        )
        visual_count = section_visual_count if section_visual_count is not None else (1 if include_section_visual else 0)
        section_visuals = [
            add_visual(
                f"evidence-result-{index + 1}",
                f"evidence-result-{index + 1}.png",
                "generated_scene",
                f"검증 근거 {index + 1}을 확인하는 설명 이미지",
                f"자동화 결과의 검증 근거 {index + 1}을 비교해 보여 주는 화면",
            )
            for index in range(visual_count)
        ]

        sections = []
        for index, (role, heading, paragraphs) in enumerate(MODE_SECTIONS[mode]):
            section = {
                "heading": heading,
                "role": role,
                "paragraphs": paragraphs,
                "evidence_refs": ["evidence-artifact" if index < 3 else "evidence-error"],
            }
            if index < len(section_visuals):
                section["visual"] = section_visuals[index]
            sections.append(section)

        blog = {
            "output_profile": "adaptive_blog",
            "mode": mode,
            "mode_reason": "실제 제작 과정과 오류 수정 근거가 있어 실행 중심 구조가 적합합니다.",
            "title": "계획서 자동화에서 먼저 정해야 할 검증 기준",
            "slug": "school-plan-validation",
            "audience": "반복되는 학교 문서 업무를 줄이려는 교사와 교육 실무자",
            "dek": "문장을 빨리 만드는 일보다 실제 양식과 오류를 확인하는 기준을 먼저 설계한 과정을 정리합니다.",
            "lead": "계획서를 자동으로 만들었는데 날짜 한 칸 때문에 다시 작성해야 했습니다. 검증 가능한 자동화는 생성 속도보다 확인 기준에서 시작합니다.",
            "core_idea": "검증 가능한 자동화",
            "lead_evidence_refs": ["evidence-error"],
            "sections": sections,
            "evidence_points": [
                {
                    "evidence_id": "evidence-artifact",
                    "kind": "artifact",
                    "detail": "실제 계획서 양식과 필수 항목 목록을 입력 자료로 사용했습니다.",
                    "source_refs": ["conversation-turn-12", "files/plan-template.docx"],
                    "verification": "원본 양식의 항목명과 생성 결과를 대조했습니다.",
                },
                {
                    "evidence_id": "evidence-error",
                    "kind": "error",
                    "detail": "첫 실행에서 날짜 형식 오류가 발견되었습니다.",
                    "source_refs": ["conversation-turn-18", "tests/test_plan_output.py"],
                    "verification": "수정 후 동일 테스트가 통과했습니다.",
                },
            ],
            "next_action": "사용 중인 양식 한 건과 자주 빠지는 항목을 먼저 정리해 봅니다.",
            "closing": "검증 가능한 자동화는 더 많은 문장을 만드는 기술이 아니라 다시 확인할 지점을 줄이는 설계입니다.",
            "tags": ["AI 에이전트", "학교 업무", "문서 자동화"],
            "meta_description": "실제 학교 계획서 양식과 오류 사례를 바탕으로 생성보다 검증 기준을 먼저 설계한 문서 자동화 과정을 설명합니다.",
            "hero_visual": hero,
            "humanity_review": humanity_review(),
        }
        blog_path = directory / "blog.json"
        manifest_path = directory / "asset-manifest.json"
        report_path = directory / "blog-validation.json"
        blog_path.write_text(json.dumps(blog, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest_path.write_text(json.dumps({"assets": asset_records}, ensure_ascii=False, indent=2), encoding="utf-8")
        return blog_path, manifest_path, report_path

    def validate_package(self, blog_path: Path, manifest_path: Path, report_path: Path) -> tuple[subprocess.CompletedProcess, dict]:
        result = subprocess.run(
            [str(PYTHON), str(VALIDATOR), str(blog_path), str(manifest_path), str(report_path)],
            capture_output=True,
            text=True,
        )
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {"status": "missing", "errors": []}
        return result, report

    @staticmethod
    def mutate_json(path: Path, mutate) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        mutate(payload)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def set_public_field(payload: dict, field: str, value: object) -> None:
        if field in {"title", "dek", "lead", "meta_description", "next_action", "closing"}:
            payload[field] = value
        elif field == "section_heading":
            payload["sections"][0]["heading"] = value
        elif field == "section_paragraph":
            payload["sections"][0]["paragraphs"][0] = value
        elif field == "caption":
            payload["hero_visual"]["caption"] = value
        elif field == "alt_text":
            payload["hero_visual"]["alt_text"] = value
        elif field == "tag":
            payload["tags"][0] = value
        else:
            raise AssertionError(f"unknown public field: {field}")


class BlogValidatorTests(BlogPackageMixin, unittest.TestCase):
    def assert_validation_error(self, mutation, expected_code: str, *, manifest: bool = False, **fixture_options) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            blog_path, manifest_path, report_path = self.write_valid_package(Path(temporary), **fixture_options)
            self.mutate_json(manifest_path if manifest else blog_path, mutation)
            result, report = self.validate_package(blog_path, manifest_path, report_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(expected_code, {issue["code"] for issue in report["errors"]})

    def test_accepts_each_supported_editorial_mode(self):
        for mode in MODE_SECTIONS:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                blog, manifest, report = self.write_valid_package(Path(temporary), mode=mode)
                result, validation = self.validate_package(blog, manifest, report)
                self.assertEqual(result.returncode, 0, validation)
                self.assertEqual(validation["status"], "ready")

    def test_accepts_seven_sections_when_roles_repeat_in_mode_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(
                Path(temporary),
                include_section_visual=False,
            )
            self.mutate_json(
                blog,
                lambda data: data.update(
                    sections=[
                        {
                            "heading": f"검증 흐름 {index}",
                            "role": role,
                            "paragraphs": [
                                "검증 가능한 자동화에 필요한 실제 판단 근거를 정리합니다."
                            ] + (["오류와 수정 결과를 함께 확인합니다."] if index in {3, 6} else []),
                            "evidence_refs": ["evidence-artifact" if index < 5 else "evidence-error"],
                        }
                        for index, role in enumerate(
                            ["problem", "problem", "principle", "method", "evidence", "evidence", "application"],
                            start=1,
                        )
                    ]
                ),
            )
            result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(result.returncode, 0, validation)

    def test_accepts_hero_without_section_visuals(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary), include_section_visual=False)
            result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(result.returncode, 0, validation)

    def test_accepts_generated_hero_with_professional_prompt(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary), hero_method="generated_scene")
            result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(result.returncode, 0, validation)

    def test_rejects_wrong_output_profile(self):
        self.assert_validation_error(lambda data: data.update(output_profile="book_a4"), "blog_profile_required")

    def test_reports_invalid_blog_root_without_crashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary))
            blog.write_text("[]", encoding="utf-8")
            result, validation = self.validate_package(blog, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(validation["status"], "invalid")
            self.assertEqual({issue["code"] for issue in validation["errors"]}, {"blog_root_invalid"})

    def test_reports_invalid_manifest_root_without_crashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary))
            manifest.write_text("[]", encoding="utf-8")
            result, validation = self.validate_package(blog, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(validation["status"], "invalid")
            self.assertEqual({issue["code"] for issue in validation["errors"]}, {"asset_manifest_root_invalid"})

    def test_reports_malformed_nested_json_deterministically_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary))
            self.mutate_json(blog, lambda data: data["sections"].__setitem__(0, ["not", "an", "object"]))

            reports = []
            for _ in range(2):
                result = subprocess.run(
                    [str(PYTHON), str(VALIDATOR), str(blog), str(manifest), str(report)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 1)
                self.assertNotIn("traceback", result.stderr.lower())
                self.assertTrue(report.is_file(), result.stderr)
                reports.append(json.loads(report.read_text(encoding="utf-8")))

            self.assertEqual(reports[0], reports[1])
            self.assertEqual(reports[0]["status"], "invalid")
            self.assertIn("blog_section_invalid", {issue["code"] for issue in reports[0]["errors"]})

    def test_validator_refuses_to_write_report_outside_blog_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            version = root / "version"
            version.mkdir()
            blog, manifest, _ = self.write_valid_package(version)
            outside_report = root / "outside.json"
            outside_report.write_text("preserve me", encoding="utf-8")

            result = subprocess.run(
                [str(PYTHON), str(VALIDATOR), str(blog), str(manifest), str(outside_report)],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(outside_report.read_text(encoding="utf-8"), "preserve me")
            self.assertIn("blog-validation.json", result.stderr)

    def test_rejects_mode_without_required_roles(self):
        self.assert_validation_error(lambda data: data["sections"].pop(), "mode_roles_incomplete")

    def test_rejects_required_roles_in_wrong_order(self):
        self.assert_validation_error(
            lambda data: data["sections"].__setitem__(slice(0, 2), [data["sections"][1], data["sections"][0]]),
            "mode_roles_out_of_order",
        )

    def test_rejects_unknown_section_role(self):
        self.assert_validation_error(lambda data: data["sections"][0].update(role="mystery"), "section_role_invalid")

    def test_rejects_legacy_plural_section_roles(self):
        def use_legacy_roles(data):
            data["sections"][0]["roles"] = [data["sections"][0].pop("role")]

        self.assert_validation_error(use_legacy_roles, "section_role_required")

    def test_rejects_legacy_plural_section_roles_alongside_singular_role(self):
        self.assert_validation_error(
            lambda data: data["sections"][0].update(roles=[data["sections"][0]["role"]]),
            "section_roles_forbidden",
        )

    def test_rejects_noncontiguous_role_repetition(self):
        def repeat_problem_after_principle(data):
            repeated = dict(data["sections"][0])
            repeated["heading"] = "원칙 뒤에 되돌아간 문제"
            data["sections"].insert(2, repeated)

        self.assert_validation_error(repeat_problem_after_principle, "mode_roles_out_of_order")

    def test_rejects_less_than_two_evidence_points(self):
        self.assert_validation_error(lambda data: data.update(evidence_points=data["evidence_points"][:1]), "insufficient_evidence")

    def test_rejects_duplicate_evidence_ids(self):
        self.assert_validation_error(
            lambda data: data["evidence_points"][1].update(evidence_id="evidence-artifact"),
            "duplicate_evidence_id",
        )

    def test_rejects_missing_lead_evidence_reference(self):
        self.assert_validation_error(
            lambda data: data.update(lead_evidence_refs=["missing-evidence"]),
            "evidence_reference_missing",
        )

    def test_rejects_canned_ai_opening(self):
        self.assert_validation_error(lambda data: data.update(lead="안녕하세요. 오늘은 계획서 자동화에 대해 알아보겠습니다."), "canned_prose_forbidden")

    def test_accepts_today_and_so_far_when_they_carry_real_information(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary))
            self.mutate_json(
                blog,
                lambda data: data.update(
                    lead="오늘은 제출 마감일이지만 검증 가능한 자동화 덕분에 누락 항목을 먼저 찾았습니다.",
                    closing="지금까지 확인된 두 오류는 검증 가능한 자동화의 기준을 더 분명하게 만들었습니다.",
                ),
            )
            result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(result.returncode, 0, validation)

    def test_accepts_contextual_today_without_canned_intro(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary))
            self.mutate_json(blog, lambda data: data.update(next_action="오늘은 실제 양식 한 건으로 검증 범위를 정해 봅니다."))
            result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(result.returncode, 0, validation)

    def test_rejects_clickbait_title(self):
        self.assert_validation_error(lambda data: data.update(title="단 몇 분 만에 완벽한 계획서 자동화"), "clickbait_title_forbidden")

    def test_rejects_unsupported_first_person_experience(self):
        self.assert_validation_error(lambda data: data.update(lead="제가 직접 해보니 검증 가능한 자동화가 가장 중요했습니다."), "unsupported_first_person_experience")

    def test_accepts_first_person_when_source_observation_exists(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary))
            self.mutate_json(blog, lambda data: (
                data.update(lead="제가 직접 해보니 검증 가능한 자동화는 확인 기준에서 시작했습니다."),
                data["evidence_points"].append({
                    "evidence_id": "evidence-observation",
                    "kind": "observation",
                    "detail": "작성자가 실제 샘플을 실행하고 결과를 기록했습니다.",
                    "source_refs": ["conversation-turn-21"],
                    "verification": "실행 로그와 결과 파일을 확인했습니다.",
                }),
                data.update(first_person_evidence_refs=["evidence-observation"]),
            ))
            result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(result.returncode, 0, validation)

    def test_rejects_uniform_section_rhythm(self):
        self.assert_validation_error(
            lambda data: [section.update(paragraphs=[section["paragraphs"][0]]) for section in data["sections"]],
            "uniform_section_rhythm",
        )

    def test_rejects_missing_hero_alt_text(self):
        self.assert_validation_error(lambda data: data["hero_visual"].update(alt_text=""), "visual_alt_text_required")

    def test_rejects_non_string_text_paragraph_tag_id_and_reference_fields(self):
        cases = (
            ("text", lambda data: data.update(title=42), "title_required"),
            ("paragraph", lambda data: data["sections"][0].update(paragraphs=[42]), "section_paragraphs_required"),
            ("tag", lambda data: data.update(tags=[42]), "blog_tags_required"),
            ("evidence id", lambda data: data["evidence_points"][0].update(evidence_id=42), "evidence_id_required"),
            ("evidence source ref", lambda data: data["evidence_points"][0].update(source_refs=[42]), "evidence_source_required"),
            ("lead evidence ref", lambda data: data.update(lead_evidence_refs=[42]), "lead_evidence_refs_required"),
            ("section evidence ref", lambda data: data["sections"][0].update(evidence_refs=[42]), "section_evidence_refs_required"),
            ("visual id", lambda data: data["hero_visual"].update(asset_id=42), "visual_asset_id_required"),
            ("visual alt", lambda data: data["hero_visual"].update(alt_text={"text": "not a string"}), "visual_alt_text_required"),
            ("visual caption", lambda data: data["hero_visual"].update(caption=["not a string"]), "visual_caption_required"),
        )
        for label, mutation, expected_code in cases:
            with self.subTest(field=label):
                self.assert_validation_error(mutation, expected_code)

        manifest_cases = (
            ("manifest id", lambda data: data["assets"][0].update(asset_id=42), "asset_id_required"),
            ("manifest alt", lambda data: data["assets"][0].update(alt_text=["not a string"]), "asset_alt_text_required"),
            ("provided source ref", lambda data: data["assets"][0]["source"].update(reference=42), "provided_asset_source_required"),
        )
        for label, mutation, expected_code in manifest_cases:
            with self.subTest(field=label):
                self.assert_validation_error(mutation, expected_code, manifest=True)

    def test_first_person_policy_scans_every_rendered_public_field(self):
        fields = (
            "title",
            "dek",
            "lead",
            "section_heading",
            "section_paragraph",
            "caption",
            "alt_text",
            "tag",
            "meta_description",
            "next_action",
            "closing",
        )
        for field in fields:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                blog, manifest, report = self.write_valid_package(Path(temporary))
                value = "제가 직접 확인했습니다. 검증 결과와 판단 근거를 설명합니다."
                self.mutate_json(blog, lambda data, field=field: self.set_public_field(data, field, value))
                if field == "alt_text":
                    self.mutate_json(manifest, lambda data: data["assets"][0].update(alt_text=value))
                result, validation = self.validate_package(blog, manifest, report)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unsupported_first_person_experience", {issue["code"] for issue in validation["errors"]})

    def test_generated_actual_screen_policy_scans_every_rendered_public_field(self):
        fields = (
            "title",
            "dek",
            "lead",
            "section_heading",
            "section_paragraph",
            "caption",
            "alt_text",
            "tag",
            "meta_description",
            "next_action",
            "closing",
        )
        for field in fields:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                blog, manifest, report = self.write_valid_package(Path(temporary))
                value = "검증 결과를 보여 주는 actual screenshot 자료"
                self.mutate_json(blog, lambda data, field=field: self.set_public_field(data, field, value))
                if field == "alt_text":
                    self.mutate_json(manifest, lambda data: data["assets"][0].update(alt_text=value))
                result, validation = self.validate_package(blog, manifest, report)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("generated_visual_actual_screenshot_claim", {issue["code"] for issue in validation["errors"]})

    def test_rejects_duplicate_manifest_asset_ids(self):
        self.assert_validation_error(lambda data: data["assets"].append(dict(data["assets"][0])), "duplicate_asset_id", manifest=True)

    def test_rejects_duplicate_manifest_output_paths(self):
        self.assert_validation_error(
            lambda data: data["assets"][1].update(output_path=data["assets"][0]["output_path"]),
            "duplicate_asset_output_path",
            manifest=True,
        )

    def test_rejects_asset_path_outside_version(self):
        self.assert_validation_error(lambda data: data["assets"][0].update(output_path="../hero.png"), "asset_path_not_version_local", manifest=True)

    def test_rejects_windows_asset_path_escape(self):
        self.assert_validation_error(lambda data: data["assets"][0].update(output_path="assets\\..\\hero.png"), "asset_path_not_version_local", manifest=True)

    def test_rejects_drive_absolute_asset_path(self):
        self.assert_validation_error(lambda data: data["assets"][0].update(output_path="C:/temp/hero.png"), "asset_path_not_version_local", manifest=True)

    def test_rejects_unc_asset_path(self):
        self.assert_validation_error(lambda data: data["assets"][0].update(output_path="\\\\server\\share\\hero.png"), "asset_path_not_version_local", manifest=True)

    def test_rejects_unsafe_blog_slug(self):
        self.assert_validation_error(lambda data: data.update(slug="../other-topic"), "blog_slug_invalid")

    def test_rejects_visual_manifest_path_mismatch(self):
        self.assert_validation_error(lambda data: data["hero_visual"].update(image="assets/other.png"), "visual_output_path_mismatch")

    def test_rejects_missing_section_evidence_reference(self):
        self.assert_validation_error(lambda data: data["sections"][0].update(evidence_refs=["missing-evidence"]), "evidence_reference_missing")

    def test_rejects_unlinked_first_person_evidence(self):
        self.assert_validation_error(
            lambda data: (
                data.update(lead="제가 직접 확인한 결과입니다."),
                data.update(first_person_evidence_refs=["evidence-artifact"]),
            ),
            "unsupported_first_person_experience",
        )

    def test_rejects_non_observation_first_person_reference_even_without_first_person_copy(self):
        self.assert_validation_error(
            lambda data: data.update(first_person_evidence_refs=["evidence-artifact"]),
            "unsupported_first_person_experience",
        )

    def test_first_person_experience_requires_resolvable_evidence_references(self):
        for refs in (None, ["missing-evidence"]):
            with self.subTest(refs=refs):
                def add_first_person_claim(data, refs=refs):
                    data.update(lead="제가 직접 확인한 결과입니다.")
                    if refs is not None:
                        data.update(first_person_evidence_refs=refs)

                self.assert_validation_error(add_first_person_claim, "evidence_reference_missing")

    def test_rejects_fewer_than_five_sections(self):
        self.assert_validation_error(lambda data: data.update(sections=data["sections"][:4]), "blog_section_count_invalid")

    def test_rejects_more_than_seven_sections(self):
        def add_three_repeated_sections(data):
            for index in range(3):
                repeated = dict(data["sections"][0])
                repeated["heading"] = f"추가 문제 {index + 1}"
                data["sections"].insert(index + 1, repeated)

        self.assert_validation_error(add_three_repeated_sections, "blog_section_count_invalid")

    def test_rejects_raw_markdown_list_and_code_blocks(self):
        for paragraph in ("- 검증 항목", "1. 첫 번째 작업", "```python\nprint('unsafe')\n```"):
            with self.subTest(paragraph=paragraph):
                self.assert_validation_error(
                    lambda data, value=paragraph: data["sections"][0]["paragraphs"].__setitem__(0, value),
                    "paragraph_block_format_invalid",
                )

    def test_rejects_raw_html_in_paragraph_blocks(self):
        self.assert_validation_error(
            lambda data: data["sections"][0]["paragraphs"].__setitem__(0, "<strong>검증 기준</strong>을 확인합니다."),
            "paragraph_block_format_invalid",
        )

    def test_rejects_generated_visual_without_disclosure(self):
        self.assert_validation_error(
            lambda data: data["assets"][1].pop("disclosure"),
            "generated_visual_disclosure_required",
            manifest=True,
        )

    def test_rejects_generated_visual_metadata_without_disclosure(self):
        self.assert_validation_error(
            lambda data: data["sections"][0]["visual"].pop("disclosure"),
            "generated_visual_disclosure_required",
        )

    def test_rejects_generated_visual_claimed_as_an_actual_screenshot(self):
        for claim in ("실제 화면", "실제 캡처", "실제 스크린샷", "actual screenshot"):
            with self.subTest(claim=claim):
                self.assert_validation_error(
                    lambda data, claim=claim: data["hero_visual"].update(caption=f"자동화 도구의 {claim}"),
                    "generated_visual_actual_screenshot_claim",
                    hero_method="generated_scene",
                )

    def test_rejects_internal_generated_visual_disclosure_in_public_alt_or_caption(self):
        for field in ("alt_text", "caption"):
            with self.subTest(field=field):
                self.assert_validation_error(
                    lambda data, field=field: data["hero_visual"].update(**{field: "AI 생성 설명 이미지"}),
                    "generated_visual_public_disclosure_forbidden",
                    hero_method="generated_scene",
                )

    def test_accepts_paraphrased_core_idea_when_humanity_review_confirms_consistency(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary))
            self.mutate_json(
                blog,
                lambda data: data.update(
                    lead="생성 직후의 문서를 다시 확인할 수 있어야 자동화가 업무에 남습니다.",
                    closing="빠른 초안보다 재검토 지점을 줄이는 설계가 신뢰할 수 있는 작업 흐름을 만듭니다.",
                ),
            )
            result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(result.returncode, 0, validation)

    def test_rejects_false_or_missing_central_idea_review(self):
        for review in (False, None):
            with self.subTest(review=review):
                def remove_consistency_review(data, review=review):
                    if review is None:
                        data["humanity_review"].pop("central_idea_consistency")
                    else:
                        data["humanity_review"]["central_idea_consistency"] = review

                self.assert_validation_error(remove_consistency_review, "humanity_review_required")

    def test_rejects_generated_visual_without_professional_prompt(self):
        self.assert_validation_error(
            lambda data: data["assets"][1].update(prompt="robot and hologram illustration"),
            "unprofessional_prompt_contract",
            manifest=True,
        )

    def test_rejects_generated_prompts_that_allow_new_prohibited_motifs(self):
        for motif in ("floating icons", "invented menus", "unreadable Korean"):
            with self.subTest(motif=motif):
                self.assert_validation_error(
                    lambda data, motif=motif: data["assets"][1].update(
                        prompt=data["assets"][1]["prompt"].replace(f"no {motif}", motif)
                    ),
                    "unprofessional_prompt_contract",
                    manifest=True,
                )

    def test_rejects_provided_visual_without_source_provenance(self):
        self.assert_validation_error(
            lambda data: data["assets"][0].pop("source"),
            "provided_asset_source_required",
            manifest=True,
        )

    def test_rejects_failed_visual_quality_review(self):
        self.assert_validation_error(
            lambda data: data["assets"][0]["quality_review"].update(professional_layout=False),
            "asset_quality_review_required",
            manifest=True,
        )

    def test_accepts_four_section_visuals_and_rejects_five(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary), section_visual_count=4)
            result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(result.returncode, 0, validation)
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary), section_visual_count=5)
            result, validation = self.validate_package(blog, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("section_visual_limit_exceeded", {issue["code"] for issue in validation["errors"]})

    def test_rejects_flat_placeholder_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog, manifest, report = self.write_valid_package(version_dir)
            hero_path = version_dir / "assets" / "hero.png"
            PillowImage.new("RGB", (1600, 900), "white").save(hero_path)
            self.mutate_json(
                manifest,
                lambda data: data["assets"][0].update(sha256=hashlib.sha256(hero_path.read_bytes()).hexdigest()),
            )
            result, validation = self.validate_package(blog, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("visual_low_information", {issue["code"] for issue in validation["errors"]})

    def test_accepts_legitimate_flat_color_diagram(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog, manifest, report = self.write_valid_package(version_dir)
            hero_path = version_dir / "assets" / "hero.png"
            diagram = PillowImage.new("RGB", (1600, 900), "white")
            draw = ImageDraw.Draw(diagram)
            draw.rounded_rectangle((100, 180, 600, 720), radius=40, fill="#2f6fed")
            draw.rounded_rectangle((1000, 180, 1500, 720), radius=40, fill="#f2b134")
            draw.line((600, 450, 1000, 450), fill="#222222", width=24)
            draw.polygon(((960, 410), (1040, 450), (960, 490)), fill="#222222")
            diagram.save(hero_path)
            self.mutate_json(
                manifest,
                lambda data: data["assets"][0].update(sha256=hashlib.sha256(hero_path.read_bytes()).hexdigest()),
            )

            result, validation = self.validate_package(blog, manifest, report)

            self.assertEqual(result.returncode, 0, validation)
            self.assertEqual(validation["status"], "ready")

    def test_rejects_uninformative_alt_text_conservatively(self):
        for alt_text in ("image", "hero.png", "사진"):
            with self.subTest(alt_text=alt_text), tempfile.TemporaryDirectory() as temporary:
                blog, manifest, report = self.write_valid_package(Path(temporary))
                self.mutate_json(blog, lambda data, value=alt_text: data["hero_visual"].update(alt_text=value))
                self.mutate_json(manifest, lambda data, value=alt_text: data["assets"][0].update(alt_text=value))

                result, validation = self.validate_package(blog, manifest, report)

                self.assertNotEqual(result.returncode, 0)
                codes = {issue["code"] for issue in validation["errors"]}
                self.assertIn("visual_alt_text_uninformative", codes)
                self.assertIn("asset_alt_text_uninformative", codes)

    def test_uses_exif_oriented_dimensions_for_validation_and_rendering(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog, manifest, report = self.write_valid_package(version_dir)
            hero_path = version_dir / "assets" / "hero.jpg"
            image = PillowImage.linear_gradient("L").resize((900, 1600)).convert("RGB")
            exif = image.getexif()
            exif[274] = 6
            image.save(hero_path, exif=exif)
            self.mutate_json(blog, lambda data: data["hero_visual"].update(image="assets/hero.jpg"))
            self.mutate_json(
                manifest,
                lambda data: data["assets"][0].update(
                    output_path="assets/hero.jpg",
                    sha256=hashlib.sha256(hero_path.read_bytes()).hexdigest(),
                ),
            )

            validation_result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(validation_result.returncode, 0, validation)
            render_result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(blog), str(version_dir)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(render_result.returncode, 0, render_result.stderr)

    def test_rejects_exif_oriented_portrait_dimensions(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog, manifest, report = self.write_valid_package(version_dir)
            hero_path = version_dir / "assets" / "hero.jpg"
            image = PillowImage.linear_gradient("L").resize((1600, 900)).convert("RGB")
            exif = image.getexif()
            exif[274] = 6
            image.save(hero_path, exif=exif)
            self.mutate_json(blog, lambda data: data["hero_visual"].update(image="assets/hero.jpg"))
            self.mutate_json(
                manifest,
                lambda data: data["assets"][0].update(
                    output_path="assets/hero.jpg",
                    sha256=hashlib.sha256(hero_path.read_bytes()).hexdigest(),
                ),
            )

            result, validation = self.validate_package(blog, manifest, report)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("landscape_image_required", {issue["code"] for issue in validation["errors"]})

    def test_accepts_exact_landscape_ratio_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary), dimensions=(1200, 800))
            result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(result.returncode, 0, validation)

    def test_rejects_below_landscape_ratio_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary), dimensions=(1200, 801))
            result, validation = self.validate_package(blog, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("landscape_image_required", {issue["code"] for issue in validation["errors"]})

    def test_rejects_asset_hash_mismatch(self):
        self.assert_validation_error(lambda data: data["assets"][0].update(sha256="0" * 64), "asset_hash_mismatch", manifest=True)

    def test_rejects_portrait_visual(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary), dimensions=(900, 1600))
            result, validation = self.validate_package(blog, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("landscape_image_required", {issue["code"] for issue in validation["errors"]})

    def test_rejects_low_resolution_visual(self):
        with tempfile.TemporaryDirectory() as temporary:
            blog, manifest, report = self.write_valid_package(Path(temporary), dimensions=(1100, 700))
            result, validation = self.validate_package(blog, manifest, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("visual_minimum_resolution_required", {issue["code"] for issue in validation["errors"]})


class BlogRendererTests(BlogPackageMixin, unittest.TestCase):
    @staticmethod
    def load_renderer_module():
        spec = importlib.util.spec_from_file_location("adaptive_blog_renderer", RENDERER)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_renders_portable_markdown_and_semantic_html(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog, manifest, report = self.write_valid_package(version_dir)
            validation_result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(validation_result.returncode, 0, validation)
            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(blog), str(version_dir)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = (version_dir / "blog.md").read_text(encoding="utf-8")
            html = (version_dir / "blog.html").read_text(encoding="utf-8")
            self.assertIn("# 계획서 자동화에서 먼저 정해야 할 검증 기준", markdown)
            self.assertIn("![계획서 자동화 결과 옆에 날짜와 필수 항목 검증 결과가 표시된 화면](assets/hero.png)", markdown)
            self.assertIn("<article", html)
            self.assertIn("<header", html)
            self.assertIn("<section", html)
            self.assertIn("<figure", html)
            self.assertIn("<footer", html)
            self.assertIn('alt="계획서 자동화 결과 옆에 날짜와 필수 항목 검증 결과가 표시된 화면"', html)
            self.assertNotIn("<script", html.lower())
            self.assertNotIn("mode_reason", html)
            self.assertNotIn("humanity_review", html)

    def test_renderer_records_hashes_for_the_installed_blog_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog, manifest, report = self.write_valid_package(version_dir)
            validation_result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(validation_result.returncode, 0, validation)

            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(blog), str(version_dir)],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            updated_report = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(
                updated_report["validated_outputs"],
                {
                    "blog.md": hashlib.sha256((version_dir / "blog.md").read_bytes()).hexdigest(),
                    "blog.html": hashlib.sha256((version_dir / "blog.html").read_bytes()).hexdigest(),
                },
            )
            self.assertRegex(updated_report["validated_outputs"]["blog.md"], r"^[0-9a-f]{64}$")

    def test_renderer_rejects_stale_validation_after_source_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog, manifest, report = self.write_valid_package(version_dir)
            validation_result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(validation_result.returncode, 0, validation)
            self.mutate_json(blog, lambda data: data.update(title="검증 뒤 변경된 제목"))
            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(blog), str(version_dir)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("stale", result.stderr.lower())
            self.assertFalse((version_dir / "blog.md").exists())
            self.assertFalse((version_dir / "blog.html").exists())

    def test_renderer_rejects_asset_mutation_after_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog, manifest, report = self.write_valid_package(version_dir)
            validation_result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(validation_result.returncode, 0, validation)
            PillowImage.linear_gradient("L").transpose(PillowImage.Transpose.FLIP_TOP_BOTTOM).resize((1600, 900)).convert("RGB").save(version_dir / "assets" / "hero.png")
            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(blog), str(version_dir)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("stale", result.stderr.lower())
            self.assertFalse((version_dir / "blog.md").exists())
            self.assertFalse((version_dir / "blog.html").exists())

    def test_renderer_escapes_untrusted_public_text_in_html_and_markdown(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog, manifest, report = self.write_valid_package(version_dir)
            self.mutate_json(
                blog,
                lambda data: (
                    data.update(title='<script>alert("title")</script> 검증 가능한 자동화'),
                    data["hero_visual"].update(alt_text='결과 화면" onerror="alert(2)'),
                ),
            )
            self.mutate_json(
                manifest,
                lambda data: data["assets"][0].update(alt_text='결과 화면" onerror="alert(2)'),
            )
            validation_result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(validation_result.returncode, 0, validation)
            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(blog), str(version_dir)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = (version_dir / "blog.md").read_text(encoding="utf-8")
            page = (version_dir / "blog.html").read_text(encoding="utf-8")
            self.assertNotIn("<script", page.lower())
            self.assertNotIn('onerror="', page.lower())
            self.assertIn("&lt;script&gt;", page)
            self.assertNotIn("<script", markdown.lower())
            self.assertIn("&lt;script&gt;", markdown)

    def test_renderer_neutralizes_markdown_link_injection(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog, manifest, report = self.write_valid_package(version_dir)
            self.mutate_json(
                blog,
                lambda data: data["sections"][0]["paragraphs"].__setitem__(0, "[위험 링크](javascript:alert(3))를 그대로 실행하지 않습니다."),
            )
            validation_result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(validation_result.returncode, 0, validation)
            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(blog), str(version_dir)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = (version_dir / "blog.md").read_text(encoding="utf-8")
            self.assertNotIn("](javascript:", markdown.lower())
            self.assertIn("&#91;위험 링크&#93;", markdown)

    def test_renderer_neutralizes_block_injection_in_every_markdown_text_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog, manifest, report = self.write_valid_package(version_dir)

            def inject_blocks(data):
                values = {
                    "title": "검증 제목\n- BLOCK_TITLE",
                    "dek": "검증 요약\n- BLOCK_DEK",
                    "lead": "검증 도입\n- BLOCK_LEAD",
                    "section_heading": "검증 절\n- BLOCK_HEADING",
                    "section_paragraph": "검증 본문\n    BLOCK_PARAGRAPH",
                    "caption": "검증 설명\n- BLOCK_CAPTION",
                    "alt_text": "검증 결과 화면\n- BLOCK_ALT",
                    "next_action": "검증 행동\n1. BLOCK_NEXT",
                    "closing": "검증 맺음말\n    BLOCK_CLOSING",
                }
                for field, value in values.items():
                    self.set_public_field(data, field, value)
                data["tags"][0] = "검증 태그\n- BLOCK_TAG"

            self.mutate_json(blog, inject_blocks)
            self.mutate_json(
                manifest,
                lambda data: data["assets"][0].update(alt_text="검증 결과 화면\n- BLOCK_ALT"),
            )
            validation_result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(validation_result.returncode, 0, validation)

            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(blog), str(version_dir)],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = (version_dir / "blog.md").read_text(encoding="utf-8")
            for marker in (
                "BLOCK_TITLE",
                "BLOCK_DEK",
                "BLOCK_LEAD",
                "BLOCK_HEADING",
                "BLOCK_PARAGRAPH",
                "BLOCK_CAPTION",
                "BLOCK_ALT",
                "BLOCK_NEXT",
                "BLOCK_CLOSING",
                "BLOCK_TAG",
            ):
                matching_line = next(line for line in markdown.splitlines() if marker in line)
                self.assertIsNone(
                    __import__("re").match(r"^(?: {4}|[-+]\s+|\d+[.)]\s+)", matching_line),
                    matching_line,
                )

    def test_atomic_pair_restores_existing_outputs_when_second_replace_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            markdown_path = output / "blog.md"
            html_path = output / "blog.html"
            markdown_path.write_text("old-markdown", encoding="utf-8")
            html_path.write_text("old-html", encoding="utf-8")
            renderer = self.load_renderer_module()
            real_replace = os.replace
            failed = False

            def fail_html_once(source, destination):
                nonlocal failed
                if Path(destination).name == "blog.html" and str(source).endswith(".tmp") and not failed:
                    failed = True
                    raise OSError("simulated second replace failure")
                return real_replace(source, destination)

            with mock.patch.object(renderer.os, "replace", side_effect=fail_html_once):
                with self.assertRaises(OSError):
                    renderer._atomic_write_pair(output, "new-markdown", "new-html")
            self.assertEqual(markdown_path.read_text(encoding="utf-8"), "old-markdown")
            self.assertEqual(html_path.read_text(encoding="utf-8"), "old-html")
            self.assertEqual(sorted(path.name for path in output.iterdir()), ["blog.html", "blog.md"])

    def test_report_update_failure_restores_previous_blog_outputs_and_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog, manifest, report = self.write_valid_package(version_dir)
            validation_result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(validation_result.returncode, 0, validation)
            previous_report = report.read_bytes()
            (version_dir / "blog.md").write_text("old-markdown", encoding="utf-8")
            (version_dir / "blog.html").write_text("old-html", encoding="utf-8")
            renderer = self.load_renderer_module()
            real_replace = os.replace
            failed = False

            def fail_report_once(source, destination):
                nonlocal failed
                if same_file_target(Path(destination), report) and str(source).endswith(".tmp") and not failed:
                    failed = True
                    raise OSError("simulated report replace failure")
                return real_replace(source, destination)

            with mock.patch.object(renderer.os, "replace", side_effect=fail_report_once):
                with self.assertRaisesRegex(OSError, "report replace failure"):
                    renderer.main(blog, version_dir)

            self.assertEqual((version_dir / "blog.md").read_text(encoding="utf-8"), "old-markdown")
            self.assertEqual((version_dir / "blog.html").read_text(encoding="utf-8"), "old-html")
            self.assertEqual(report.read_bytes(), previous_report)
            self.assertNotIn("validated_outputs", json.loads(report.read_text(encoding="utf-8")))
            self.assertTrue(failed)

    def test_renderer_refuses_wrong_profile_without_partial_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog, _, _ = self.write_valid_package(version_dir)
            self.mutate_json(blog, lambda data: data.update(output_profile="book_a4"))
            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(blog), str(version_dir)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("adaptive_blog", result.stderr)
            self.assertFalse((version_dir / "blog.md").exists())
            self.assertFalse((version_dir / "blog.html").exists())

    def test_renderer_requires_output_directory_to_equal_blog_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            version_dir = root / "version"
            version_dir.mkdir()
            outside = root / "outside"
            outside.mkdir()
            marker = outside / "preserve.txt"
            marker.write_text("preserve me", encoding="utf-8")
            blog, manifest, report = self.write_valid_package(version_dir)
            validation_result, validation = self.validate_package(blog, manifest, report)
            self.assertEqual(validation_result.returncode, 0, validation)

            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(blog), str(outside)],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("output directory", result.stderr.lower())
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve me")
            self.assertFalse((outside / "blog.md").exists())
            self.assertFalse((outside / "blog.html").exists())
            self.assertFalse((version_dir / "blog.md").exists())
            self.assertFalse((version_dir / "blog.html").exists())

    def test_renderer_reports_json_array_root_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            blog = version_dir / "blog.json"
            blog.write_text("[]", encoding="utf-8")
            result = subprocess.run(
                [str(PYTHON), str(RENDERER), str(blog), str(version_dir)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("adaptive_blog", result.stderr)
            self.assertIn("root", result.stderr.lower())
            self.assertNotIn("traceback", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
