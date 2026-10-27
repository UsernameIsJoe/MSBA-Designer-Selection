"""Write the district, chart-cost, and spelling-pool contrasts.

Does not rewrite data/raw, does not refit the winner model, and does not merge
firm ids in the stored tables.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from msba_dsp.config import PROCESSED
from msba_dsp.research.local_contrasts import build_outputs, write_outputs


def main() -> None:
    competitors = pd.read_csv(PROCESSED / "competitors.csv", dtype=str, keep_default_na=False)
    events = pd.read_csv(PROCESSED / "selection_events.csv", dtype=str, keep_default_na=False)
    firms = pd.read_csv(PROCESSED / "firms.csv", dtype=str, keep_default_na=False)
    pairs = pd.read_csv(PROCESSED / "near_duplicate_firms.csv", dtype=str, keep_default_na=False)
    projects = pd.read_csv(PROCESSED / "chart_projects.csv", dtype=str, keep_default_na=False)
    applicants = pd.read_csv(PROCESSED / "selection_stage_applicants.csv", dtype=str, keep_default_na=False)
    outputs = build_outputs(competitors, events, firms, pairs, projects, applicants)
    write_outputs(outputs, PROCESSED)
    print(outputs["district_summary"])
    print(outputs["spelling_summary"])
    print(outputs["cost_summary"])
    print(outputs["pair_resolution"].to_string(index=False))
    print(outputs["spelling_recount"].to_string(index=False))
    print(outputs["cost_rates"].to_string(index=False))
    print(outputs["cost_detail"].to_string(index=False))
    print("district spelling variants", len(outputs["district_spellings"]))
    if len(outputs["district_spellings"]):
        print(outputs["district_spellings"].to_string(index=False))


if __name__ == "__main__":
    main()
