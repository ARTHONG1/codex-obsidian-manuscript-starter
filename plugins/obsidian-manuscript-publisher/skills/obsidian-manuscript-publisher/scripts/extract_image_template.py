from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageStat


MAX_PIXELS = 50_000_000


def extract_image_evidence(path: str | Path) -> dict[str, object]:
    with Image.open(path) as image:
        width, height = image.size
        if width * height > MAX_PIXELS:
            raise ValueError("template_source_too_large")
        stat = ImageStat.Stat(image.convert("RGB"))
        palette = [round(value, 3) for value in stat.mean]
    return {"width": width, "height": height, "orientation": "landscape" if width >= height else "portrait", "mean_rgb": palette}
