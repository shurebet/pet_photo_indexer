# API Documentation

This document describes all functions and data structures in the project.

## Module `photo_indexer.main`

### `build_parser() -> argparse.ArgumentParser`
- Creates and returns CLI argument parser.
- Configures flags for scan root, database path, preview settings, tag model, and top-k tags.

### `main() -> int`
- Entry point for the indexer CLI.
- Validates input directory, optionally warms up the ML model, initializes SQLite schema, and runs scanning.
- Returns `0` on success, raises `SystemExit` for invalid config or model initialization errors.

## Module `photo_indexer.scanner`

### `ScanOptions` (dataclass)
- `root: Path` - Root directory for recursive file scan.
- `previews_dir: Optional[Path]` - Output directory for previews, or `None` to disable previews.
- `preview_size: int` - Max side of preview image in pixels.
- `tags_enabled: bool` - Enables/disables object tagging.
- `model_name: str` - Model name passed to classifier (`mobilenet_v3_large` or `resnet50`).
- `topk: int` - Number of top tags to store per image.

### `iter_files(root: Path) -> Iterator[Path]`
- Recursively iterates all files under `root`.
- Yields each file path as `Path`.

### `scan_and_index(*, conn, opts: ScanOptions) -> Iterable[Path]`
- Main indexing pipeline.
- For each supported image file:
  - collects file stats,
  - extracts EXIF metadata,
  - upserts row in `photos`,
  - generates preview and upserts row in `previews` (if enabled),
  - classifies image and replaces rows in `photo_tags` (if enabled).
- Commits SQLite transaction per processed file.
- Yields each processed image path.

## Module `photo_indexer.db`

### `PhotoRecord` (dataclass)
- `path: str`
- `size_bytes: int`
- `mtime_epoch: float`
- `taken_at: Optional[str]` (ISO-like timestamp)
- `camera_model: Optional[str]`
- `gps_lat: Optional[float]`
- `gps_lon: Optional[float]`

### `PreviewRecord` (dataclass)
- `photo_path: str`
- `preview_path: str`
- `preview_size: int`

### `PhotoTagRecord` (dataclass)
- `photo_path: str`
- `tag: str`
- `score: float`
- `model: str`

### `connect(db_path: Path) -> sqlite3.Connection`
- Opens/creates SQLite database file.
- Ensures parent directory exists.
- Enables `WAL` journal mode and foreign keys.
- Returns configured SQLite connection.

### `init_db(conn: sqlite3.Connection) -> None`
- Creates required tables and indexes if they do not exist:
  - `photos`
  - `previews`
  - `photo_tags`
- Commits schema creation.

### `upsert_photo(conn: sqlite3.Connection, rec: PhotoRecord) -> None`
- Inserts or updates a row in `photos` by primary key `path`.

### `upsert_preview(conn: sqlite3.Connection, rec: PreviewRecord) -> None`
- Inserts or updates a row in `previews` by primary key `photo_path`.

### `replace_photo_tags(conn: sqlite3.Connection, photo_path: str, tags: list[PhotoTagRecord]) -> None`
- Deletes existing tags for `photo_path`.
- Inserts provided tag rows into `photo_tags`.
- No-op insert when `tags` is empty.

## Module `photo_indexer.exif`

### `ExifInfo` (dataclass)
- `taken_at: Optional[str]`
- `camera_model: Optional[str]`
- `gps_lat: Optional[float]`
- `gps_lon: Optional[float]`

### `_parse_exif_datetime(value: str) -> Optional[str]`
- Parses EXIF datetime format (`YYYY:MM:DD HH:MM:SS`).
- Returns ISO string (`YYYY-MM-DDTHH:MM:SS`) or `None`.

### `_ratio_to_float(r) -> Optional[float]`
- Converts EXIF rational number to float.
- Returns `None` on parse errors.

### `_dms_to_deg(values) -> Optional[float]`
- Converts DMS sequence (`deg, min, sec`) to decimal degrees.
- Returns `None` when values are missing/invalid.

### `_parse_gps(tags) -> Tuple[Optional[float], Optional[float]]`
- Extracts latitude/longitude from EXIF GPS tags.
- Applies hemisphere sign conversion (`S/W` -> negative).

### `read_exif(path: Path) -> ExifInfo`
- Reads EXIF tags from image file.
- Extracts capture datetime, camera model, and GPS coordinates.
- Returns empty `ExifInfo` fields if EXIF is unavailable or parsing fails.

## Module `photo_indexer.previews`

### `is_supported_image(path: Path) -> bool`
- Checks whether file extension is one of supported image types.

### `preview_output_path(previews_dir: Path, root_dir: Path, photo_path: Path) -> Path`
- Builds preview output path with a mirrored folder hierarchy.
- Keeps directory names identical to the scanned root hierarchy.
- Changes output extension to `<original_ext>.webp` (e.g. `img.jpg.webp`).

### `create_preview(photo_path: Path, out_path: Path, size: int) -> Optional[Path]`
- Opens image, applies EXIF orientation, resizes to thumbnail, converts modes if needed, saves as WEBP.
- Returns output path on success, otherwise `None`.

## Module `photo_indexer.ml`

### `Tag` (dataclass)
- `label: str`
- `score: float`
- `model: str`

### `_normalize_model_name(name: str) -> str`
- Normalizes aliases (for example `mobilenet`, `resnet`) to canonical model names.

### `_load_model_and_labels(model_name: str)`
- Lazily imports Torch/Torchvision.
- Loads pretrained model, preprocessing transform, category labels.
- Sets model to eval mode on CPU.
- Cached via `lru_cache`.

### `classify_image(path: Path, *, model_name: str = "mobilenet_v3_large", topk: int = 5) -> List[Tag]`
- Runs inference for a single image.
- Returns top-k predictions as list of `Tag` (label, probability, model name).

### `warmup(model_name: str = "mobilenet_v3_large") -> str`
- Preloads model and weights (may trigger one-time download).
- Returns canonical model name.

### `supported_models() -> Sequence[str]`
- Returns tuple of currently supported model names.

## Module `streamlit_app`

### `QueryParams` (dataclass)
- `db_path: Path`
- `tags_query: str`
- `match_all: bool`
- `date_from: Optional[date]`
- `date_to: Optional[date]`
- `limit: int`

### `_connect(db_path: Path) -> sqlite3.Connection`
- Opens SQLite connection for dashboard queries.
- Configures row factory as `sqlite3.Row`.

### `_tokenize_tags(q: str) -> List[str]`
- Splits tag query string by spaces/commas.
- Lowercases and de-duplicates tokens while preserving order.

### `_build_sql(params: QueryParams) -> Tuple[str, List[Any]]`
- Builds SQL query and bound parameters for dashboard filters.
- Supports date range filter and tag match mode (`any`/`all` tokens).
- Includes joined preview path and aggregated tag string.

### `_db_has_required_tables(conn: sqlite3.Connection) -> bool`
- Checks that required tables (`photos`, `photo_tags`) exist in selected DB.

### `main() -> None`
- Streamlit UI entry point.
- Renders controls, validates DB, executes query, and displays results as table + image grid.
