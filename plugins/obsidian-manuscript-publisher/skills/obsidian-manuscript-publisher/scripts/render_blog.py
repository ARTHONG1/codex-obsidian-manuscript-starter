#!/usr/bin/env python3
"""Render a validated adaptive blog package as portable Markdown and HTML."""

from __future__ import annotations

import html
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image as PillowImage
from PIL import ImageOps


OUTPUT_PROFILE = "adaptive_blog"
MIN_IMAGE_WIDTH = 1200
MIN_LANDSCAPE_RATIO = 1.5


def _text(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _markdown_text(value: object) -> str:
    normalized = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    # A content newline must never create a Markdown list, quote, heading, or
    # indented code block. Paragraph boundaries come from the JSON block list,
    # not from control syntax embedded in a text field.
    normalized = " ".join(line.strip() for line in normalized.split("\n"))
    escaped = html.escape(normalized, quote=False)
    entities = {
        "[": "&#91;",
        "]": "&#93;",
        "(": "&#40;",
        ")": "&#41;",
        "!": "&#33;",
        "*": "&#42;",
        "`": "&#96;",
        "#": "&#35;",
    }
    return "".join(entities.get(character, character) for character in escaped)


def _markdown_alt(value: object) -> str:
    return _markdown_text(value).replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _validate_profile(blog: object) -> None:
    if not isinstance(blog, dict):
        raise ValueError("adaptive_blog root must be a JSON object")
    if blog.get("output_profile") != OUTPUT_PROFILE:
        raise ValueError("render_blog.py requires output_profile adaptive_blog")


def _load_validator():
    validator_path = Path(__file__).resolve().with_name("validate_blog.py")
    spec = importlib.util.spec_from_file_location("obsidian_adaptive_blog_validator", validator_path)
    if spec is None or spec.loader is None:
        raise ValueError("adaptive_blog validator could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validation_ready(blog_path: Path, blog: dict) -> tuple[Path, dict]:
    report_path = blog_path.parent / "blog-validation.json"
    manifest_path = blog_path.parent / "asset-manifest.json"
    if not report_path.is_file():
        raise ValueError("blog-validation.json is required before rendering adaptive_blog")
    if not manifest_path.is_file():
        raise ValueError("asset-manifest.json is required before rendering adaptive_blog")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "ready":
        raise ValueError("adaptive_blog validation status must be ready before rendering")
    validated_inputs = report.get("validated_inputs")
    current_blog_hash = hashlib.sha256(blog_path.read_bytes()).hexdigest()
    current_manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if not isinstance(validated_inputs, dict) or (
        validated_inputs.get("blog_sha256") != current_blog_hash
        or validated_inputs.get("asset_manifest_sha256") != current_manifest_hash
    ):
        raise ValueError("adaptive_blog validation is stale; validate the current package again")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fresh_report = _load_validator().validate_package(blog, manifest, blog_path.parent)
    if fresh_report.get("status") != "ready":
        raise ValueError("adaptive_blog package is stale or invalid; validate it again")
    return report_path, report


def _resolve_visual(visual: object, blog_path: Path, output_directory: Path, label: str) -> tuple[str, str, str]:
    if not isinstance(visual, dict):
        raise ValueError(f"{label} visual is invalid")
    source = str(visual.get("image") or "").strip()
    alt_text = str(visual.get("alt_text") or "").strip()
    caption = str(visual.get("caption") or "").strip()
    if not source or not alt_text or not caption:
        raise ValueError(f"{label} visual requires image, alt_text, and caption")

    version_root = blog_path.parent.resolve()
    candidate = (version_root / source).resolve()
    try:
        candidate.relative_to(version_root)
    except ValueError as error:
        raise ValueError(f"{label} image must stay inside the blog version") from error
    if not candidate.is_file() or candidate.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise ValueError(f"{label} image must be an existing PNG or JPEG")
    try:
        with PillowImage.open(candidate) as image:
            oriented = ImageOps.exif_transpose(image)
            width, height = oriented.size
            if oriented is not image:
                oriented.close()
    except OSError as error:
        raise ValueError(f"{label} image is unreadable") from error
    if width < MIN_IMAGE_WIDTH:
        raise ValueError(f"{label} image must be at least {MIN_IMAGE_WIDTH}px wide")
    if not height or width / height < MIN_LANDSCAPE_RATIO:
        raise ValueError(f"{label} image must be landscape")

    relative = Path(os.path.relpath(candidate, output_directory.resolve())).as_posix()
    return relative, alt_text, caption


def _markdown_figure(visual: dict, blog_path: Path, output_directory: Path, label: str) -> str:
    image, alt_text, caption = _resolve_visual(visual, blog_path, output_directory, label)
    return f"![{_markdown_alt(alt_text)}]({image})\n\n*{_markdown_text(caption)}*"


def _html_figure(visual: dict, blog_path: Path, output_directory: Path, label: str) -> str:
    image, alt_text, caption = _resolve_visual(visual, blog_path, output_directory, label)
    return (
        '<figure class="article-figure">'
        f'<img src="{_text(image)}" alt="{_text(alt_text)}" loading="lazy">'
        f"<figcaption>{_text(caption)}</figcaption>"
        "</figure>"
    )


def render_markdown(blog: dict, blog_path: Path, output_directory: Path) -> str:
    parts = [
        f"# {_markdown_text(blog['title'])}",
        f"**{_markdown_text(blog['dek'])}**",
        _markdown_figure(blog["hero_visual"], blog_path, output_directory, "hero"),
        _markdown_text(blog["lead"]),
    ]
    for index, section in enumerate(blog["sections"], start=1):
        block = [f"## {_markdown_text(section['heading'])}"]
        block.extend(_markdown_text(paragraph) for paragraph in section["paragraphs"])
        if section.get("visual") is not None:
            block.append(_markdown_figure(section["visual"], blog_path, output_directory, f"section {index}"))
        parts.append("\n\n".join(block))
    parts.extend(
        [
            f"## 지금 적용해 볼 일\n\n{_markdown_text(blog['next_action'])}",
            _markdown_text(blog["closing"]),
            " ".join(f"#{_markdown_text(tag).replace(' ', '_')}" for tag in blog["tags"]),
        ]
    )
    return "\n\n".join(parts).rstrip() + "\n"


def render_html(blog: dict, blog_path: Path, output_directory: Path) -> str:
    sections = []
    for index, section in enumerate(blog["sections"], start=1):
        paragraphs = "".join(f"<p>{_text(paragraph)}</p>" for paragraph in section["paragraphs"])
        figure = ""
        if section.get("visual") is not None:
            figure = _html_figure(section["visual"], blog_path, output_directory, f"section {index}")
        sections.append(
            f'<section class="article-section" data-role="{_text(section["role"])}">'
            f"<h2>{_text(section['heading'])}</h2>{paragraphs}{figure}</section>"
        )
    tags = "".join(f"<li>{_text(tag)}</li>" for tag in blog["tags"])
    return f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{_text(blog['meta_description'])}">
  <title>{_text(blog['title'])}</title>
  <style>
    :root {{ color-scheme: light; --ink:#202124; --muted:#5f6368; --line:#dadce0; --accent:#1769aa; --paper:#ffffff; --wash:#f7f8fa; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--wash); color:var(--ink); font-family:"Malgun Gothic","맑은 고딕",system-ui,sans-serif; font-size:17px; line-height:1.82; letter-spacing:0; }}
    article {{ width:min(100% - 32px, 820px); margin:40px auto; padding:clamp(24px,5vw,64px); background:var(--paper); border:1px solid var(--line); }}
    header {{ margin-bottom:36px; }}
    h1 {{ margin:0 0 16px; font-size:clamp(30px,5vw,48px); line-height:1.25; letter-spacing:0; }}
    h2 {{ margin:48px 0 16px; font-size:26px; line-height:1.4; letter-spacing:0; }}
    p {{ margin:0 0 20px; }}
    .dek {{ color:var(--muted); font-size:19px; }}
    .lead {{ font-size:19px; }}
    .article-figure {{ margin:28px 0 36px; }}
    .article-figure img {{ display:block; width:100%; height:auto; border:1px solid var(--line); }}
    figcaption {{ margin-top:8px; color:var(--muted); font-size:14px; line-height:1.6; }}
    .next-action {{ margin-top:48px; padding:22px 24px; border-left:4px solid var(--accent); background:var(--wash); }}
    footer {{ margin-top:48px; padding-top:24px; border-top:1px solid var(--line); }}
    .tags {{ display:flex; flex-wrap:wrap; gap:8px 14px; padding:0; margin:20px 0 0; list-style:none; color:var(--muted); font-size:14px; }}
    @media (max-width:600px) {{ body {{ font-size:16px; }} article {{ width:100%; margin:0; padding:24px 20px 40px; border:0; }} h1 {{ font-size:30px; }} h2 {{ font-size:23px; }} }}
  </style>
</head>
<body>
<article>
  <header>
    <h1>{_text(blog['title'])}</h1>
    <p class="dek">{_text(blog['dek'])}</p>
    {_html_figure(blog['hero_visual'], blog_path, output_directory, 'hero')}
    <p class="lead">{_text(blog['lead'])}</p>
  </header>
  {''.join(sections)}
  <aside class="next-action" aria-labelledby="next-action-title">
    <h2 id="next-action-title">지금 적용해 볼 일</h2>
    <p>{_text(blog['next_action'])}</p>
  </aside>
  <footer>
    <p>{_text(blog['closing'])}</p>
    <ul class="tags" aria-label="태그">{tags}</ul>
  </footer>
</article>
</body>
</html>
'''


def _atomic_replace_files(files: tuple[tuple[Path, bytes], ...]) -> None:
    temporary_paths: list[Path] = []
    backup_paths: dict[Path, Path] = {}
    installed_paths: list[Path] = []
    try:
        for final_path, content in files:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            handle, temporary_name = tempfile.mkstemp(
                prefix=f".{final_path.name}.", suffix=".tmp", dir=final_path.parent
            )
            temporary_path = Path(temporary_name)
            temporary_paths.append(temporary_path)
            with os.fdopen(handle, "wb") as stream:
                stream.write(content)
        for final_path, _ in files:
            if final_path.exists():
                handle, backup_name = tempfile.mkstemp(
                    prefix=f".{final_path.name}.", suffix=".bak", dir=final_path.parent
                )
                os.close(handle)
                backup_path = Path(backup_name)
                shutil.copy2(final_path, backup_path)
                backup_paths[final_path] = backup_path
        for temporary_path, (final_path, _) in zip(temporary_paths, files, strict=True):
            os.replace(temporary_path, final_path)
            installed_paths.append(final_path)
    except Exception:
        for final_path in reversed(installed_paths):
            backup_path = backup_paths.get(final_path)
            if backup_path is not None and backup_path.exists():
                os.replace(backup_path, final_path)
            elif final_path.exists():
                final_path.unlink()
        raise
    finally:
        for temporary_path in temporary_paths:
            if temporary_path.exists():
                temporary_path.unlink()
        for backup_path in backup_paths.values():
            if backup_path.exists():
                backup_path.unlink()


def _atomic_write_pair(output_directory: Path, markdown: str, page: str) -> None:
    _atomic_replace_files(
        (
            (output_directory / "blog.md", markdown.encode("utf-8")),
            (output_directory / "blog.html", page.encode("utf-8")),
        )
    )


def _write_validated_render(
    output_directory: Path,
    markdown: str,
    page: str,
    report_path: Path,
    report: dict,
) -> None:
    markdown_bytes = markdown.encode("utf-8")
    page_bytes = page.encode("utf-8")
    updated_report = dict(report)
    updated_report["validated_outputs"] = {
        "blog.md": hashlib.sha256(markdown_bytes).hexdigest(),
        "blog.html": hashlib.sha256(page_bytes).hexdigest(),
    }
    report_bytes = (json.dumps(updated_report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _atomic_replace_files(
        (
            (output_directory / "blog.md", markdown_bytes),
            (output_directory / "blog.html", page_bytes),
            (report_path, report_bytes),
        )
    )


def main(blog_path: Path, output_directory: Path) -> None:
    blog_path = blog_path.resolve()
    output_directory = output_directory.resolve()
    if output_directory != blog_path.parent:
        raise ValueError("output directory must be the directory containing blog.json")
    blog = json.loads(blog_path.read_text(encoding="utf-8"))
    _validate_profile(blog)
    report_path, report = _validation_ready(blog_path, blog)
    markdown = render_markdown(blog, blog_path, output_directory)
    page = render_html(blog, blog_path, output_directory)
    _write_validated_render(output_directory, markdown, page, report_path, report)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: render_blog.py <blog.json> <output-directory>")
    try:
        main(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
