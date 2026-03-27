from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class PhotoRecord:
    path: str
    size_bytes: int
    mtime_epoch: float
    taken_at: Optional[str]  # ISO-like string, e.g. "2020-01-02T03:04:05"
    camera_model: Optional[str]
    gps_lat: Optional[float]
    gps_lon: Optional[float]


@dataclass(frozen=True)
class PreviewRecord:
    photo_path: str
    preview_path: str
    preview_size: int


@dataclass(frozen=True)
class PhotoTagRecord:
    photo_path: str
    tag: str
    score: float
    model: str


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS photos (
          path TEXT PRIMARY KEY,
          size_bytes INTEGER NOT NULL,
          mtime_epoch REAL NOT NULL,
          taken_at TEXT,
          camera_model TEXT,
          gps_lat REAL,
          gps_lon REAL
        );

        CREATE TABLE IF NOT EXISTS previews (
          photo_path TEXT PRIMARY KEY,
          preview_path TEXT NOT NULL,
          preview_size INTEGER NOT NULL,
          FOREIGN KEY(photo_path) REFERENCES photos(path) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS photo_tags (
          photo_path TEXT NOT NULL,
          tag TEXT NOT NULL,
          score REAL NOT NULL,
          model TEXT NOT NULL,
          PRIMARY KEY(photo_path, tag, model),
          FOREIGN KEY(photo_path) REFERENCES photos(path) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_photos_taken_at ON photos(taken_at);
        CREATE INDEX IF NOT EXISTS idx_photo_tags_photo_path ON photo_tags(photo_path);
        """
    )
    conn.commit()


def upsert_photo(conn: sqlite3.Connection, rec: PhotoRecord) -> None:
    conn.execute(
        """
        INSERT INTO photos(path, size_bytes, mtime_epoch, taken_at, camera_model, gps_lat, gps_lon)
        VALUES(?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
          size_bytes=excluded.size_bytes,
          mtime_epoch=excluded.mtime_epoch,
          taken_at=excluded.taken_at,
          camera_model=excluded.camera_model,
          gps_lat=excluded.gps_lat,
          gps_lon=excluded.gps_lon
        ;
        """,
        (
            rec.path,
            rec.size_bytes,
            rec.mtime_epoch,
            rec.taken_at,
            rec.camera_model,
            rec.gps_lat,
            rec.gps_lon,
        ),
    )


def upsert_preview(conn: sqlite3.Connection, rec: PreviewRecord) -> None:
    conn.execute(
        """
        INSERT INTO previews(photo_path, preview_path, preview_size)
        VALUES(?, ?, ?)
        ON CONFLICT(photo_path) DO UPDATE SET
          preview_path=excluded.preview_path,
          preview_size=excluded.preview_size
        ;
        """,
        (rec.photo_path, rec.preview_path, rec.preview_size),
    )


def replace_photo_tags(conn: sqlite3.Connection, photo_path: str, tags: list[PhotoTagRecord]) -> None:
    conn.execute("DELETE FROM photo_tags WHERE photo_path = ?;", (photo_path,))
    if not tags:
        return
    conn.executemany(
        "INSERT INTO photo_tags(photo_path, tag, score, model) VALUES(?, ?, ?, ?);",
        [(t.photo_path, t.tag, float(t.score), t.model) for t in tags],
    )

