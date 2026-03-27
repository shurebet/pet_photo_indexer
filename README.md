# photo-indexer

Индексатор архива фотографий: рекурсивно сканирует папку, извлекает EXIF (дата/гео), создаёт превью и сохраняет всё в SQLite.

## Установка

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Использование

```bash
python -m photo_indexer.main --root "D:\Photos" --db "photo_index.db" --previews ".previews" --size 512
```

Повторный запуск безопасен: записи обновляются по пути файла.

## Streamlit-дашборд (поиск по тегам и дате)

```bash
streamlit run streamlit_app.py
```

В дашборде укажите путь к вашей SQLite БД (например, `photo_index.db`) и задайте теги (`dog beach`) и/или диапазон дат.

## Схема БД

SQLite-файл содержит таблицы:
- `photos`: путь, размер, mtime, модель камеры, дата съёмки, GPS (lat/lon)
- `previews`: путь к превью и его размер
- `photo_tags`: теги (top-k) от предобученной модели (`mobilenet_v3_large`/`resnet50`) с вероятностью

