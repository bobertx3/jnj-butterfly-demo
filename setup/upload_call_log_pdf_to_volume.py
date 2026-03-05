"""Upload sample call log PDF(s) to Unity Catalog volume for pipeline ingestion."""

from __future__ import annotations

import subprocess
from pathlib import Path


CATALOG = "bx4"
SCHEMA = "butterfly"
VOLUME = "raw_landing"
VOLUME_DIR = "call_logs"
LOCAL_DIR = Path(__file__).resolve().parent / "sample_data" / "call_logs"


def _run(cmd: list[str]) -> None:
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def upload() -> None:
    if not LOCAL_DIR.exists():
        raise FileNotFoundError(f"Local folder not found: {LOCAL_DIR}")

    target = f"dbfs:/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/{VOLUME_DIR}"
    _run(["databricks", "fs", "mkdir", target])

    for pdf in sorted(LOCAL_DIR.glob("*.pdf")):
        _run(["databricks", "fs", "cp", str(pdf), f"{target}/{pdf.name}", "--overwrite"])
        print(f"Uploaded: {pdf.name}")


if __name__ == "__main__":
    upload()
