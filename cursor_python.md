# Python project structure for photo indexing
_Exported on 3/27/2026 at 00:17:49 GMT from Cursor (2.6.21)_

---

**User**

Create a Python project structure for indexing a photo archive. I need:
A script to scan a folder of photos (recursively).
Extract EXIF ​​metadata (date, geolocation).
Use the PIL or Pillow library to generate previews.
An SQLite database to store paths and metadata.
Create a basic file structure and requirements.txt

---

**Cursor**

I'll create a minimal but working project skeleton: the photo_indexer package, a CLI script for recursive scanning, an EXIF ​​module (date/geo), preview generation via Pillow, a SQLite layer (schema + upsert), and requirements.txt/README. First, I'll look at what's already in the folder to avoid overwriting anything.

The project folder is empty—it's safe to create the structure from scratch. Now I'll add the basic files: the photo_indexer package (scanner/EXIF/preview/DB), main.py CLI, requirements.txt, and a short README with a runtime example.

I've created basic dependencies and a database skeleton (SQLite + WAL + upsert). Next, I'll add modules for EXIF ​​(date/GPS), a preview generator using Pillow, and a main script that recursively traverses the folder and writes everything to the database.

The framework is ready; now I'll quickly test the CLI launch after installing the dependencies (to ensure the imports/entrypoints are correct).

### What's been created (project structure)

- **Dependencies**: `requirements.txt` (Pillow for previews, `exifread` for EXIF)
- **Package**: `photo_indexer/`
- `main.py`: CLI for running scanning
- `scanner.py`: recursive folder traversal, writing to the database, generating previews
- `exif.py`: extracting shooting date and GPS (lat/lon)
- `previews.py`: creating previews (WEBP) via Pillow
- `db.py`: SQLite schema + upsert for photos/previews
- `__init__.py`
- **Documentation**: `README.md`

Current structure:

- `requirements.txt`
- `README.md`
- `photo_indexer/__init__.py`
- `photo_indexer/main.py`
- `photo_indexer/scanner.py`
- `photo_indexer/exif.py`
- `photo_indexer/previews.py`
- `photo_indexer/db.py`

### How to run

```bash
python -m pip install -r requirements.txt
python -m photo_indexer.main --root "D:\Photos" --db "photo_index.db" --previews ".previews" --size 512
```

- **SQLite** stores the file path and metadata (EXIF date, GPS, camera model), as well as the preview path.
- **Previews** are generated in `.previews/`, preserving the original path structure.

---

**User**

Add object recognition capability to the project (for example, using a pre-trained MobileNet or ResNet model from PyTorch/Torchvision).
Update the database schema to store the detected tags for each photo.
Integrate this into the scanning process.

---

**Cursor**

I'll add an ML classification module (PyTorch/Torchvision with a pre-trained MobileNet/ResNet), extend the SQLite schema with a table for tags, and enable recognition in `scanner.py` (with lazy model loading and storing the top-k tags for each photo). First, I'll read the current files to carefully make edits.

OK: I'll update requirements.txt (torch/torchvision), add the photo_indexer/ml.py module, extend photo_indexer/db.py with the photo_tags table, and include this in scanner.py + the CLI options in main.py. After that, I'll run --help to make sure everything imports.

### What's Added

- Object/Tag Recognition: New photo_indexer/ml.py module, which classifies images using a pre-trained Torchvision model (mobilenet_v3_large or resnet50) and returns the top-k tags with their probabilities. - **Updated SQLite schema**: added the **`photo_tags`** table and the `replace_photo_tags(...)` function to `photo_indexer/db.py`.

### New DB schema (addition)

`photo_tags` table:

- `photo_path` (FK → `photos.path`)
- `tag` (string)
- `score` (REAL)
- `model` (model name)
- primary key: `(photo_path, tag, model)`

### Scan integration

In `photo_indexer/scanner.py`, after writing `photos`/`previews`, classification is performed (if enabled) and tags are saved to `photo_tags` (old photo tags are replaced with new ones).

### CLI options

Added to `photo_indexer/main.py`:

- `--tags` / --no-tags` (enabled by default)
- `--model` (`mobilenet_v3_large` or `resnet50`)
- `--topk` (number of tags to keep, 5 by default)

Example:

```bash
python -m photo_indexer.main --root "D:\Photos" --db "photo_index.db" --previews ".previews" --size 512 --model resnet50 --topk 7
```

### Dependencies

Added to `requirements.txt`:

- `torch`
- `torchvision`

Note: Torchvision model weights are usually **downloaded during the first classification run**.

---

**User**

Create a simple Streamlit dashboard so I can search photos by tags (e.g., 'dog', 'beach') or by date from my database.

---

**Cursor**

I'll create a separate Streamlit script that reads your SQLite database, filters photos by tags (a few words) and date range, and displays the results in a table with previews/images. First, I'll update the dependencies and add the app file.

### Stream added