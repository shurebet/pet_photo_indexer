from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps


def is_supported_image(path: Path) -> bool:
    return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}


def preview_output_path(previews_dir: Path, photo_path: Path) -> Path:
    # Deterministic and collision-resistant (keeps some structure).
    # Example: previews_dir / "D_/Photos/2020/img.jpg.webp" on Windows-like roots.
    parts = list(photo_path.parts)
    safe_parts = []
    for p in parts:
        if len(p) == 2 and p[1] == ":":
            safe_parts.append(p[0].upper() + "_")
        else:
            safe_parts.append(p)
    return previews_dir.joinpath(*safe_parts).with_suffix(photo_path.suffix + ".webp")


def create_preview(photo_path: Path, out_path: Path, size: int) -> Optional[Path]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(photo_path) as im:
            im = ImageOps.exif_transpose(im)  # respect orientation
            im.thumbnail((size, size))
            if im.mode in ("RGBA", "P"):
                im = im.convert("RGB")
            im.save(out_path, format="WEBP", quality=82, method=6)
        return out_path
    except Exception:
        return None

