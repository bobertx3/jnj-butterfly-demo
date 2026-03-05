"""Parse PDF call logs from volume and write transcript chunks to a Unity Catalog table."""

from __future__ import annotations

import io
import os
import re
from datetime import datetime, timezone

from pypdf import PdfReader
from pyspark.sql import SparkSession


CATALOG = os.getenv("CATALOG", "bx4")
SCHEMA = os.getenv("SCHEMA", "butterfly")
RAW_VOLUME = os.getenv("RAW_VOLUME", "raw_landing")
SOURCE_DIR = f"/Volumes/{CATALOG}/{SCHEMA}/{RAW_VOLUME}/call_logs"
TARGET_TABLE = os.getenv("CALL_LOG_SOURCE_TABLE", f"{CATALOG}.{SCHEMA}.gold_call_log_chunks")


def _slug_from_doc_name(doc_name: str) -> str:
    stem = re.sub(r"_call_transcript.*$", "", doc_name, flags=re.IGNORECASE)
    return stem.strip("_").lower()


def _chunk_text(text: str, max_chars: int = 1200) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: list[str] = []
    current = ""
    for p in parts:
        if len(current) + len(p) + 1 <= max_chars:
            current = f"{current}\n{p}".strip()
        else:
            if current:
                out.append(current)
            current = p
    if current:
        out.append(current)
    return [c for c in out if len(c) >= 80]


def main() -> None:
    spark = SparkSession.builder.getOrCreate()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

    files_df = spark.read.format("binaryFile").load(SOURCE_DIR).select("path", "content")
    files = files_df.collect()

    rows: list[dict[str, object]] = []
    ts = datetime.now(timezone.utc).isoformat()
    for file_row in files:
        source_path = file_row["path"]
        content = bytes(file_row["content"])
        document_name = source_path.rstrip("/").split("/")[-1].replace(".pdf", "")
        customer_slug = _slug_from_doc_name(document_name)

        reader = PdfReader(io.BytesIO(content))
        full_text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
        chunks = _chunk_text(full_text)
        for idx, chunk in enumerate(chunks):
            rows.append(
                {
                    "chunk_id": f"{document_name}_{idx:04d}",
                    "source_path": source_path,
                    "document_name": document_name,
                    "customer_slug": customer_slug,
                    "chunk_index": idx,
                    "chunk_text": chunk,
                    "_updated_at": ts,
                }
            )

    if not rows:
        print(f"No transcript chunks produced from {SOURCE_DIR}.")
        return

    out_df = spark.createDataFrame(rows)
    out_df.write.mode("overwrite").saveAsTable(TARGET_TABLE)
    spark.sql(f"ALTER TABLE {TARGET_TABLE} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
    print(f"Wrote {len(rows)} chunks to {TARGET_TABLE}")


if __name__ == "__main__":
    main()
