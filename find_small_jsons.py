#!/usr/bin/env python3
"""
Utility script for scanning JSON files and reporting the ones that are
smaller than a given byte threshold. Defaults to 1000 bytes.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable, Tuple


def iter_small_json_files(root: Path, max_bytes: int) -> Iterable[Tuple[Path, int]]:
    """
    Yield (path, size) pairs for JSON files under max_bytes within root.
    """
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if not filename.lower().endswith(".json"):
                continue
            path = Path(dirpath) / filename
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size < max_bytes:
                yield (path, size)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List JSON files smaller than a size threshold."
    )
    parser.add_argument(
        "--root",
        default=Path(__file__).resolve().parent,
        type=Path,
        help="Directory to scan (defaults to repository root).",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=1000,
        help="Maximum file size in bytes (defaults to 1000).",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    matches = sorted(
        (
            (path.relative_to(root), size)
            for path, size in iter_small_json_files(root, args.max_bytes)
        ),
        key=lambda item: item[0].as_posix(),
    )

    if not matches:
        print(f"No JSON files under {args.max_bytes} bytes found in {root}.")
        return

    for rel_path, size in matches:
        print(f"{rel_path}\t{size} bytes")


if __name__ == "__main__":
    main()





