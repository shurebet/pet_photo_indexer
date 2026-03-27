# photo-indexer

Photo archive indexer: recursively scans a folder, extracts EXIF data (date/GPS), creates previews, and stores everything in SQLite.

## Installation

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python -m photo_indexer.main --root "D:\Photos" --db "photo_index.db" --previews ".previews" --size 512
```

Re-running is safe: records are updated by file path.

## Streamlit dashboard (search by tags and date)

```bash
streamlit run streamlit_app.py
```

In the dashboard, provide the path to your SQLite database (for example, `photo_index.db`) and set tags (`dog beach`) and/or a date range.

## Database schema

The SQLite file contains the following tables:
- `photos`: path, size, mtime, camera model, capture date, GPS (lat/lon)
- `previews`: preview path and preview size
- `photo_tags`: top-k tags from a pretrained model (`mobilenet_v3_large`/`resnet50`) with confidence score

