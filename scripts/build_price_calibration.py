"""Write the within-list price tables.

Does not rewrite data/raw, does not refit the winner model, and does not
change firm ids.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from msba_dsp.config import PROCESSED
from msba_dsp.evaluation.metrics import choice_log_loss
from msba_dsp.research.price_calibration import build_outputs, history_frame, write_outputs


def _as_model(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["winner"] = pd.to_numeric(out["winner"]).astype(int)
    out["selection_year"] = pd.to_numeric(out["selection_year"]).astype(int)
    return out


def main() -> None:
    competitors = pd.read_csv(PROCESSED / "competitors.csv", dtype=str, keep_default_na=False)
    events = pd.read_csv(PROCESSED / "selection_events.csv", dtype=str, keep_default_na=False)
    firms = pd.read_csv(PROCESSED / "firms.csv", dtype=str, keep_default_na=False)
    stored = _as_model(pd.read_csv(PROCESSED / "model_frame.csv", dtype=str, keep_default_na=False))
    history = history_frame(competitors, events, firms)
    check = history.merge(
        stored[["selection_id", "firm_id", "prior_wins", "prior_finals", "published_rank", "winner"]],
        on=["selection_id", "firm_id"],
        suffixes=("", "_stored"),
        validate="one_to_one",
    )
    if not check["prior_wins"].eq(pd.to_numeric(check["prior_wins_stored"])).all():
        raise SystemExit("rebuilt prior wins do not match model_frame")
    if not check["prior_finals"].eq(pd.to_numeric(check["prior_finals_stored"])).all():
        raise SystemExit("rebuilt prior finals do not match model_frame")
    if not check["rank_num"].eq(pd.to_numeric(check["published_rank"])).all():
        raise SystemExit("rebuilt ranks do not match model_frame")
    if not check["winner"].eq(check["winner_stored"]).all():
        raise SystemExit("rebuilt winners do not match model_frame")

    outputs = build_outputs(competitors, events, firms)
    test = stored.loc[stored["selection_year"].ge(2019)]
    equal_gap = abs(choice_log_loss(test, "p_equal") - _score(outputs, "test_2019_2026", "equal"))
    rate_gap = abs(choice_log_loss(test, "p_rate") - _score(outputs, "test_2019_2026", "shrunk_rate"))
    if equal_gap > 1e-9:
        raise SystemExit(f"equal-chance test loss disagrees with the stored prices by {equal_gap}")
    if rate_gap > 1e-9:
        raise SystemExit(f"shrunk-rate test loss disagrees with the stored prices by {rate_gap}")
    summary = outputs["summary"]
    if summary["test_rankings"] != int(test["selection_id"].nunique()):
        raise SystemExit("test ranking count disagrees with model_frame")
    if summary["described_rankings"] != 204:
        raise SystemExit(f"expected 204 rankings from 2012, found {summary['described_rankings']}")

    write_outputs(outputs, PROCESSED)
    print("alpha", summary["alpha"], "train loss", summary["alpha_train_log_loss"])
    print("rankings", summary["described_rankings"], "fit", summary["fit_rankings"], "test", summary["test_rankings"])
    print("favorite", summary["favorite"])
    print("place", summary["place_when_not_first"])
    print(outputs["scores"].to_string(index=False))
    print(outputs["gaps"].to_string(index=False))
    print(outputs["reliability_proportional"].to_string(index=False))
    print(outputs["reliability_damped_test"].to_string(index=False))
    print(outputs["leads"].to_string(index=False))
    print(outputs["examples"].to_string(index=False))
    print("priced >=0.60 and lost", summary["priced_at_least_60_and_lost"])
    print("priced >=0.75", summary["priced_at_least_75"], "lost", summary["priced_at_least_75_and_lost"])
    print("no unique favorite", summary["no_unique_favorite"])


def _score(outputs: dict, window: str, rule: str) -> float:
    scores = outputs["scores"]
    row = scores.loc[scores["window"].eq(window) & scores["rule"].eq(rule)].iloc[0]
    return float(row["log_loss"])


if __name__ == "__main__":
    main()
