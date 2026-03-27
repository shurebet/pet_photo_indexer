from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd
import streamlit as st


@dataclass(frozen=True)
class QueryParams:
    db_path: Path
    tags_query: str
    match_all: bool
    date_from: Optional[date]
    date_to: Optional[date]
    limit: int


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _tokenize_tags(q: str) -> List[str]:
    tokens = []
    for raw in (q or "").replace(",", " ").split():
        t = raw.strip().lower()
        if t:
            tokens.append(t)
    # de-dup while preserving order
    seen = set()
    out: List[str] = []
    for t in tokens:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out


def _build_sql(params: QueryParams) -> Tuple[str, List[Any]]:
    tokens = _tokenize_tags(params.tags_query)

    where: List[str] = ["1=1"]
    sql_params: List[Any] = []

    # Date filtering uses YYYY-MM-DD from ISO taken_at.
    if params.date_from:
        where.append("substr(p.taken_at, 1, 10) >= ?")
        sql_params.append(params.date_from.isoformat())
    if params.date_to:
        where.append("substr(p.taken_at, 1, 10) <= ?")
        sql_params.append(params.date_to.isoformat())

    # Tag filtering: any vs all tokens.
    # We store tags from ImageNet categories; use LIKE for partial matches.
    if tokens:
        if params.match_all:
            for tok in tokens:
                where.append(
                    "EXISTS (SELECT 1 FROM photo_tags t WHERE t.photo_path = p.path AND lower(t.tag) LIKE ?)"
                )
                sql_params.append(f"%{tok}%")
        else:
            ors: List[str] = []
            for tok in tokens:
                ors.append("lower(t.tag) LIKE ?")
                sql_params.append(f"%{tok}%")
            where.append(
                "EXISTS (SELECT 1 FROM photo_tags t WHERE t.photo_path = p.path AND (" + " OR ".join(ors) + "))"
            )

    sql = f"""
    SELECT
      p.path,
      p.taken_at,
      p.camera_model,
      p.gps_lat,
      p.gps_lon,
      pr.preview_path,
      (
        SELECT group_concat(t.tag || ':' || printf('%.3f', t.score), ', ')
        FROM photo_tags t
        WHERE t.photo_path = p.path
        ORDER BY t.score DESC
        LIMIT 20
      ) AS tags
    FROM photos p
    LEFT JOIN previews pr ON pr.photo_path = p.path
    WHERE {" AND ".join(where)}
    ORDER BY p.taken_at IS NULL, p.taken_at DESC, p.path
    LIMIT ?
    """
    sql_params.append(int(params.limit))
    return sql, sql_params


def _db_has_required_tables(conn: sqlite3.Connection) -> bool:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('photos','photo_tags');"
    ).fetchall()
    names = {r["name"] for r in rows}
    return "photos" in names and "photo_tags" in names


def main() -> None:
    st.set_page_config(page_title="Photo Indexer Dashboard", layout="wide")
    st.title("Photo Indexer — search by tags and date")

    with st.sidebar:
        st.header("Data source")
        db_path_str = st.text_input("SQLite DB path", value="photo_index.db")
        db_path = Path(db_path_str)

        st.header("Filters")
        tags_query = st.text_input("Tags (for example: dog beach)", value="")
        match_all = st.toggle("Require all words", value=False)

        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input("Date from", value=None)
        with col2:
            date_to = st.date_input("Date to", value=None)

        limit = st.slider("Result limit", min_value=20, max_value=500, value=200, step=20)

        run = st.button("Search", type="primary")

    if not run:
        st.caption("Set filters in the sidebar and click Search.")
        return

    if not db_path.exists():
        st.error(f"Database file not found: {db_path}")
        return

    params = QueryParams(
        db_path=db_path,
        tags_query=tags_query,
        match_all=match_all,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )

    try:
        conn = _connect(db_path)
    except Exception as e:
        st.exception(e)
        return

    with conn:
        if not _db_has_required_tables(conn):
            st.error(
                "Required tables `photos` and `photo_tags` were not found in this database. "
                "Run the indexer with tags enabled first."
            )
            return

        sql, sql_params = _build_sql(params)
        rows = conn.execute(sql, sql_params).fetchall()

    if not rows:
        st.info("No results found.")
        return

    df = pd.DataFrame([dict(r) for r in rows])
    st.subheader(f"Found: {len(df)}")
    st.dataframe(
        df.drop(columns=[c for c in ["preview_path"] if c in df.columns]),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Preview")
    cols = st.columns(4)
    for i, r in enumerate(rows):
        c = cols[i % 4]
        path = Path(r["path"])
        preview = Path(r["preview_path"]) if r["preview_path"] else None
        img_path = preview if preview and preview.exists() else (path if path.exists() else None)
        with c:
            st.caption(str(path))
            if img_path:
                st.image(str(img_path), use_container_width=True)
            else:
                st.write("(file not found)")
            if r["taken_at"]:
                st.write(f"Date: {r['taken_at']}")
            if r["tags"]:
                st.write(r["tags"])


if __name__ == "__main__":
    main()

