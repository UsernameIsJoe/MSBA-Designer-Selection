"""Hash local snapshots. Dates are file timestamps, not claimed download times."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from msba_dsp.config import ROOT
from msba_dsp.ingestion.sources import SOURCES


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest() -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for source in SOURCES:
        local = source["local_path"]
        path = ROOT / local if local else None
        present = bool(path and path.is_file())
        observed = ""
        digest = ""
        size = ""
        if present and path is not None:
            stat = path.stat()
            observed = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            digest = _sha256(path)
            size = str(stat.st_size)
        rows.append(
            {
                "source_id": source["source_id"],
                "title": source["title"],
                "url": source["url"],
                "local_path": local,
                "format": source["format"],
                "role": source["role"],
                "file_present": str(present),
                "bytes": size,
                "sha256": digest,
                "local_mtime_utc": observed,
                "publication_date": "",
                "notes": (
                    "sha256 of the local snapshot. local_mtime_utc is the file "
                    "modification time, not an independently logged retrieval date. "
                    "publication_date is blank when the file does not state one."
                    if present
                    else "No local snapshot. Analyses that need this source are omitted."
                ),
            }
        )
    return pd.DataFrame(rows)
