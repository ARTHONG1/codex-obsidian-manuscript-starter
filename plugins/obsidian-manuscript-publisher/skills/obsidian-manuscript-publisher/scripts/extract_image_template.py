from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageStat, UnidentifiedImageError


MAX_PIXELS = 50_000_000
ALLOWED_FORMATS = ("PNG", "JPEG", "WEBP")


def extract_image_evidence(path: str | Path) -> dict[str, object]:
    if Path(path).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("unsupported_image_format")
    try:
        with Image.open(path, formats=ALLOWED_FORMATS) as image:
            if image.format not in ALLOWED_FORMATS:
                raise ValueError("unsupported_image_format")
            image.verify()
        with Image.open(path, formats=ALLOWED_FORMATS) as image:
            width, height = image.size
            if width * height > MAX_PIXELS:
                raise ValueError("template_source_too_large")
            image.load()
            stat = ImageStat.Stat(image.convert("RGB"))
            palette = [round(value, 3) for value in stat.mean]
    except ValueError:
        raise
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("invalid_image_source") from exc
    return {"width": width, "height": height, "orientation": "landscape" if width >= height else "portrait", "mean_rgb": palette}
