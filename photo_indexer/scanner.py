from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional

from . import db as dbmod
from .exif import read_exif
from .ml import classify_image
from .previews import create_preview, is_supported_image, preview_output_path


@dataclass(frozen=True)
class ScanOptions:
    root: Path
    previews_dir: Optional[Path]
    preview_size: int
    tags_enabled: bool
    model_name: str
    topk: int


def iter_files(root: Path) -> Iterator[Path]:
    for p in root.rglob("*"):
        if p.is_file():
            yield p


def scan_and_index(
    *,
    conn,
    opts: ScanOptions,
) -> Iterable[Path]:
    root = opts.root
    tag_errors_shown = 0
    for path in iter_files(root):
        if not is_supported_image(path):
            continue

        try:
            st = path.stat()
        except OSError:
            continue

        ex = read_exif(path)
        rec = dbmod.PhotoRecord(
            path=str(path),
            size_bytes=int(st.st_size),
            mtime_epoch=float(st.st_mtime),
            taken_at=ex.taken_at,
            camera_model=ex.camera_model,
            gps_lat=ex.gps_lat,
            gps_lon=ex.gps_lon,
        )
        dbmod.upsert_photo(conn, rec)

        if opts.previews_dir is not None:
            out = preview_output_path(opts.previews_dir, path)
            created = create_preview(path, out, size=opts.preview_size)
            if created is not None:
                dbmod.upsert_preview(
                    conn,
                    dbmod.PreviewRecord(
                        photo_path=str(path),
                        preview_path=str(created),
                        preview_size=int(opts.preview_size),
                    ),
                )

        if opts.tags_enabled:
            try:
                tags = classify_image(path, model_name=opts.model_name, topk=opts.topk)
            except Exception as e:
                # Don't silently wipe tags; show a few errors then continue.
                tag_errors_shown += 1
                if tag_errors_shown <= 5:
                    print(f"[tags] failed for {path}: {e!r}")
                tags = None

            if tags is not None:
                dbmod.replace_photo_tags(
                    conn,
                    str(path),
                    [
                        dbmod.PhotoTagRecord(
                            photo_path=str(path),
                            tag=t.label,
                            score=float(t.score),
                            model=t.model,
                        )
                        for t in tags
                    ],
                )

        conn.commit()
        yield path

