"""Mention data export (FR-20): CSV and XLSX with a configurable row cap and
server-side batched retrieval so an ad-hoc export can never issue one unbounded
query or return more than the cap (FR-20.3).
"""
import csv
from io import BytesIO, StringIO

from openpyxl import Workbook

MAX_ROWS_DEFAULT = 10000
BATCH_SIZE = 100

COLUMNS = [
    ("id", "mention_id"),
    ("platform__display_name", "platform"),
    ("author_handle", "author"),
    ("sentiment", "sentiment"),
    ("emotion", "emotion"),
    ("posted_at", "posted_at"),
    ("engagement_count", "engagement"),
    ("matched_keyword", "matched_keyword"),
    ("source_url", "source_url"),
    ("content_snippet", "content"),
]
HEADERS = [label for _field, label in COLUMNS]
_FIELDS = [field for field, _label in COLUMNS]


def iter_export_rows(queryset, max_rows=MAX_ROWS_DEFAULT, batch_size=BATCH_SIZE):
    """Yield up to ``max_rows`` rows, fetched from the database in slices of
    ``batch_size`` (never a single unbounded query)."""
    queryset = queryset.order_by("id")
    fetched = 0
    while fetched < max_rows:
        remaining = max_rows - fetched
        window = min(batch_size, remaining)
        batch = list(queryset.values(*_FIELDS)[fetched:fetched + window])
        if not batch:
            break
        for item in batch:
            yield [_stringify(item[field]) for field in _FIELDS]
        fetched += len(batch)
        if len(batch) < window:
            break


def _stringify(value):
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def rows_to_csv(rows):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADERS)
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    for row in rows:
        writer.writerow(row)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


def rows_to_xlsx(rows):
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("mentions")
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()
