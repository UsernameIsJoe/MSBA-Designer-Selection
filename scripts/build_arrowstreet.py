"""Arrowstreet's lists against seat share and against a similar-volume peer group.

Does not rewrite data/raw, does not refit the winner model, and does not merge
the team submissions into Arrowstreet's id.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from msba_dsp.config import PROCESSED
from msba_dsp.research.arrowstreet import build_outputs, write_outputs


def main() -> None:
    competitors = pd.read_csv(PROCESSED / "competitors.csv", dtype=str, keep_default_na=False)
    events = pd.read_csv(PROCESSED / "selection_events.csv", dtype=str, keep_default_na=False)
    firms = pd.read_csv(PROCESSED / "firms.csv", dtype=str, keep_default_na=False)
    outputs = build_outputs(competitors, events, firms)
    write_outputs(outputs, PROCESSED)
    print(outputs["summary"])
    print(outputs["peers"][["firm_name", "lists", "rank1", "expected_rank1", "excess_wins", "excess_per_list", "excess_low", "excess_high"]].to_string(index=False))
    print(outputs["cases"][["selection_date", "school_name", "arrowstreet_ranked_first", "arrowstreet_prior_wins", "firms_with_more_prior_wins", "winner_had_more_prior_wins", "arrowstreet_unique_leader", "winner_name"]].to_string(index=False))
    print(outputs["teams"].to_string(index=False))


if __name__ == "__main__":
    main()
