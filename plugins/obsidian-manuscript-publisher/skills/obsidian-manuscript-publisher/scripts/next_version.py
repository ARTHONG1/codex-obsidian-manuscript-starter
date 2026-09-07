"""Print the next non-destructive manuscript draft directory name."""

from __future__ import annotations

import re
import sys
from pathlib import Path


VERSION = re.compile(r"^v(\d+)\.(\d+)$")


def next_version(chapter_directory: Path) -> str:
    highest = 0
    if chapter_directory.exists():
        for child in chapter_directory.iterdir():
            match = VERSION.match(child.name)
            if child.is_dir() and match and int(match.group(1)) == 0:
                highest = max(highest, int(match.group(2)))
    return f"v0.{highest + 1}"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: next_version.py <chapter-directory>")
    print(next_version(Path(sys.argv[1])))
