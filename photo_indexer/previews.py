from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps


def is_supported_image(path: Path) -> bool:
    return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}


def preview_output_path(previews_dir: Path, root_dir: Path, photo_path: Path) -> Path:
    """
    Builds preview output path with a mirrored folder hierarchy.

    For every directory level from `root_dir` to the photo's directory, we append `_min`.
    Example (Linux-like paths):
      root_dir:  /photos
      photo:     /photos/2020/beach/img.jpg
      previews:  .previews
      output:    .previews/photos_min/2020_min/beach_min/img.jpg.webp
    """
    relative = photo_path.relative_to(root_dir)
    rel_dir = relative.parent

    dir_parts = [f"{p}_min" for p in rel_dir.parts if p not in ("", ".")]
    root_name_min = f"{root_dir.name}_min"

    return (
        previews_dir.joinpath(root_name_min, *dir_parts).with_suffix(photo_path.suffix + ".webp")
    )


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

