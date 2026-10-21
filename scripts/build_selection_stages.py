"""Write Phase 4 applicant, interview, and rank-1 tables.

Does not rewrite data/raw or refit the stored winner model.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from msba_dsp.config import PROCESSED, REPORTS
from msba_dsp.research.selection_stages import build_outputs, write_outputs


def main() -> None:
    projects = pd.read_csv(PROCESSED / "chart_projects.csv", dtype=str, keep_default_na=False)
    chart_firms = pd.read_csv(PROCESSED / "chart_firms.csv", dtype=str, keep_default_na=False)
    competitors = pd.read_csv(PROCESSED / "competitors.csv", dtype=str, keep_default_na=False)
    events = pd.read_csv(PROCESSED / "selection_events.csv", dtype=str, keep_default_na=False)
    firms = pd.read_csv(PROCESSED / "firms.csv", dtype=str, keep_default_na=False)
    shortlists = pd.read_csv(PROCESSED / "shortlists.csv", dtype=str, keep_default_na=False)
    outputs = build_outputs(projects, chart_firms, competitors, events, firms, shortlists)
    write_outputs(outputs, PROCESSED, REPORTS)
    print("projects", len(outputs["projects"]), "applicants", len(outputs["applicants"]))
    print(outputs["field"])


if __name__ == "__main__":
    main()
