"""Write the Phase 5 panel-snapshot audit.

Does not rewrite data/raw, does not refit the winner model, and does not treat
the inferred roster as a ballot.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from msba_dsp.config import PROCESSED, REPORTS
from msba_dsp.research.panel_history import build_outputs, write_outputs


def main() -> None:
    competitors = pd.read_csv(PROCESSED / "competitors.csv", dtype=str, keep_default_na=False)
    events = pd.read_csv(PROCESSED / "selection_events.csv", dtype=str, keep_default_na=False)
    firms = pd.read_csv(PROCESSED / "firms.csv", dtype=str, keep_default_na=False)
    roster = pd.read_csv(PROCESSED / "dsp_roster_inferred.csv", dtype=str, keep_default_na=False)
    outputs = build_outputs(competitors, events, firms, roster)
    write_outputs(outputs, PROCESSED, REPORTS)
    print("competitions", len(outputs["competitions"]), "unassigned", int(outputs["competitions"]["era"].eq("").sum()))
    print(outputs["page"])
    print(outputs["overlap"][["earlier_era", "later_era", "retained", "only_earlier", "only_later", "jaccard"]].to_string(index=False))
    keep = outputs["metrics"]["metric"].isin(
        ["competitions", "hhi", "top5_share", "two_firm_share", "mean_field", "mixed_competitions", "incumbent_excess", "zero_prior_rank1_rate", "any_prior_rank1_rate", "ma_hq_share_of_located_rank1", "rank1_location_unknown", "staff_201_share_of_banded_rank1", "rank1_staff_unknown", "dominant_known_school_type"]
    )
    print(outputs["metrics"].loc[keep, ["era", "metric", "estimate", "low", "high", "numerator", "denominator"]].to_string(index=False))
    print(outputs["contrasts"].to_string(index=False))


if __name__ == "__main__":
    main()
