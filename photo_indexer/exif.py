from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import exifread


@dataclass(frozen=True)
class ExifInfo:
    taken_at: Optional[str]
    camera_model: Optional[str]
    gps_lat: Optional[float]
    gps_lon: Optional[float]


def _parse_exif_datetime(value: str) -> Optional[str]:
    # Typical: "2019:12:31 23:59:59"
    try:
        dt = datetime.strptime(value.strip(), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None
    return dt.isoformat(timespec="seconds")


def _ratio_to_float(r) -> Optional[float]:
    try:
        return float(r.num) / float(r.den)
    except Exception:
        try:
            return float(r)
        except Exception:
            return None


def _dms_to_deg(values) -> Optional[float]:
    if not values or len(values) < 3:
        return None
    d = _ratio_to_float(values[0])
    m = _ratio_to_float(values[1])
    s = _ratio_to_float(values[2])
    if d is None or m is None or s is None:
        return None
    return d + (m / 60.0) + (s / 3600.0)


def _parse_gps(tags) -> Tuple[Optional[float], Optional[float]]:
    lat = lon = None

    lat_vals = tags.get("GPS GPSLatitude")
    lat_ref = tags.get("GPS GPSLatitudeRef")
    lon_vals = tags.get("GPS GPSLongitude")
    lon_ref = tags.get("GPS GPSLongitudeRef")

    if lat_vals and lon_vals:
        lat = _dms_to_deg(getattr(lat_vals, "values", None))
        lon = _dms_to_deg(getattr(lon_vals, "values", None))

        if lat is not None and lat_ref:
            ref = str(getattr(lat_ref, "values", [lat_ref])[0]).upper()
            if ref.startswith("S"):
                lat = -lat

        if lon is not None and lon_ref:
            ref = str(getattr(lon_ref, "values", [lon_ref])[0]).upper()
            if ref.startswith("W"):
                lon = -lon

    return lat, lon


def read_exif(path: Path) -> ExifInfo:
    try:
        with path.open("rb") as f:
            tags = exifread.process_file(f, details=False, strict=True)
    except Exception:
        return ExifInfo(taken_at=None, camera_model=None, gps_lat=None, gps_lon=None)

    dt = None
    for key in ("EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime"):
        if key in tags:
            dt = _parse_exif_datetime(str(tags[key]))
            if dt:
                break

    model = None
    if "Image Model" in tags:
        model = str(tags["Image Model"]).strip() or None

    lat, lon = _parse_gps(tags)
    return ExifInfo(taken_at=dt, camera_model=model, gps_lat=lat, gps_lon=lon)

