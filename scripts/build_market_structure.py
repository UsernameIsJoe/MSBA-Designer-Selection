"""Write Phase 1 market-structure tables and figures from the processed rankings.

Does not read or rewrite data/raw.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from msba_dsp.config import PROCESSED, REPORTS
from msba_dsp.research.market_structure import build_outputs, write_outputs


def main() -> None:
    competitors = pd.read_csv(PROCESSED / "competitors.csv", dtype=str, keep_default_na=False)
    events = pd.read_csv(PROCESSED / "selection_events.csv", dtype=str, keep_default_na=False)
    firms = pd.read_csv(PROCESSED / "firms.csv", dtype=str, keep_default_na=False)
    outputs = build_outputs(competitors, events, firms)
    write_outputs(outputs, PROCESSED, REPORTS)
    full = outputs["bootstrap"]
    print(
        "competitions",
        outputs["audit"]["model_competitions"],
        "rows",
        outputs["audit"]["model_finalist_rows"],
        "firms",
        outputs["audit"]["model_firms"],
        "hhi",
        full.get("hhi"),
        "top5",
        full.get("top5_share"),
        "through",
        outputs["archive_end"],
    )


if __name__ == "__main__":
    main()
