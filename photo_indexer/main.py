from __future__ import annotations

import argparse
from pathlib import Path

from .db import connect, init_db
from .ml import supported_models, warmup
from .scanner import ScanOptions, scan_and_index


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Index photo archive into SQLite (EXIF + previews).")
    p.add_argument("--root", type=Path, required=True, help="Root directory to scan recursively")
    p.add_argument("--db", type=Path, default=Path("photo_index.db"), help="SQLite DB file path")
    p.add_argument(
        "--previews",
        type=Path,
        default=Path(".previews"),
        help="Directory to store generated previews (set empty to disable)",
    )
    p.add_argument("--size", type=int, default=512, help="Preview max side in pixels")
    p.add_argument(
        "--tags",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable object tags via a pretrained image classifier",
    )
    p.add_argument(
        "--model",
        type=str,
        default="mobilenet_v3_large",
        help="Classifier model: mobilenet_v3_large or resnet50",
    )
    p.add_argument("--topk", type=int, default=5, help="How many tags to store per photo")
    return p


def main() -> int:
    args = build_parser().parse_args()
    root: Path = args.root
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"--root must be an existing directory: {root}")

    if bool(args.tags):
        try:
            warmup(str(args.model))
        except Exception as e:
            models = ", ".join(supported_models())
            raise SystemExit(
                f"Failed to initialize tagger model '{args.model}'. Supported: {models}. Error: {e!r}"
            )

    previews_dir = args.previews
    # Allow disabling previews by passing: --previews ""
    if str(previews_dir).strip() == "":
        previews_dir = None

    conn = connect(args.db)
    init_db(conn)

    opts = ScanOptions(
        root=root,
        previews_dir=previews_dir,
        preview_size=int(args.size),
        tags_enabled=bool(args.tags),
        model_name=str(args.model),
        topk=int(args.topk),
    )
    count = 0
    for _ in scan_and_index(conn=conn, opts=opts):
        count += 1
        if count % 200 == 0:
            print(f"Indexed {count} photos...")
    print(f"Done. Indexed {count} photos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

