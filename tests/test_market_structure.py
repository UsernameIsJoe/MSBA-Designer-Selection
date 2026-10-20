import numpy as np
import pandas as pd

from msba_dsp.research.market_structure import (
    bootstrap_concentration,
    concentration,
    head_to_head,
    model_rows,
    period_turnover,
    rolling_table,
)


def test_hhi_of_equal_and_monopoly_shares():
    equal = concentration(["a", "b", "c", "d"])
    assert equal["hhi"] == 0.25
    assert equal["effective_winners"] == 4
    assert equal["normalized_hhi"] == 0
    assert equal["top1_share"] == 0.25
    monopoly = concentration(["a", "a", "a"])
    assert monopoly["hhi"] == 1
    assert monopoly["effective_winners"] == 1
    assert monopoly["normalized_hhi"] is None
    assert monopoly["top5_share"] == 1


def test_top_shares_are_ordered_and_use_a_stable_tie_break():
    stats = concentration(["b", "a", "b", "a", "c"])
    assert stats["top1_share"] <= stats["top3_share"] <= stats["top5_share"] <= stats["top10_share"]
    # Two firms tie at two wins. The earlier firm id supplies the top-1 share.
    assert stats["top1_share"] == 2 / 5


def test_rolling_window_does_not_include_outside_years():
    competitions = pd.DataFrame(
        {
            "selection_year": [2007, 2008, 2012],
            "winner_firm_id": ["a", "a", "b"],
            "n_finalists": [2, 2, 2],
        }
    )
    rows = pd.DataFrame(
        {
            "selection_year": [2007, 2008, 2012],
            "firm_id": ["a", "a", "b"],
        }
    )
    rolling = rolling_table(competitions, rows, width=5)
    early = rolling.loc[rolling["window"] == "2007-2011"].iloc[0]
    assert early["competitions"] == 2
    assert early["unique_winners"] == 1
    later = rolling.loc[rolling["window"] == "2008-2012"].iloc[0]
    assert later["competitions"] == 2
    assert later["unique_winners"] == 2


def test_first_period_newcomers_are_marked_left_censored():
    rows = pd.DataFrame(
        {
            "firm_id": ["a", "b", "b"],
            "selection_year": [2008, 2014, 2018],
        }
    )
    competitions = pd.DataFrame(
        {
            "selection_year": [2008, 2014, 2018],
            "winner_firm_id": ["a", "b", "b"],
        }
    )
    periods = period_turnover(rows, competitions)
    first = periods.iloc[0]
    assert bool(first["left_censored"])
    assert first["archive_newcomers"] == 1
    assert first["finalists_not_seen_in_a_later_period"] == 1
    last = periods.iloc[-1]
    assert bool(last["right_censored"])
    assert last["finalists_not_seen_in_a_later_period"] == 0


def test_head_to_head_counts_the_better_rank_and_not_a_third_party_win():
    rows = pd.DataFrame(
        [
            {"selection_id": "s1", "firm_id": "a", "rank_num": 1, "is_winner": True, "canonical_firm_name": "A"},
            {"selection_id": "s1", "firm_id": "b", "rank_num": 2, "is_winner": False, "canonical_firm_name": "B"},
            {"selection_id": "s2", "firm_id": "a", "rank_num": 2, "is_winner": False, "canonical_firm_name": "A"},
            {"selection_id": "s2", "firm_id": "b", "rank_num": 3, "is_winner": False, "canonical_firm_name": "B"},
            {"selection_id": "s2", "firm_id": "c", "rank_num": 1, "is_winner": True, "canonical_firm_name": "C"},
        ]
    )
    pairs = head_to_head(rows, minimum=1)
    pair = pairs.loc[pairs["firm_a_id"].eq("a") & pairs["firm_b_id"].eq("b")].iloc[0]
    assert pair["shared_rankings"] == 2
    assert pair["a_finished_ahead"] == 2
    assert pair["b_finished_ahead"] == 0
    assert pair["a_ranked_first"] == 1
    assert pair["someone_else_ranked_first"] == 1


def test_bootstrap_interval_contains_the_point_and_is_seeded():
    competitions = pd.DataFrame({"winner_firm_id": ["a", "a", "b", "c", "a"]})
    first = bootstrap_concentration(competitions, draws=200, seed=7)
    second = bootstrap_concentration(competitions, draws=200, seed=7)
    assert first["hhi_low"] <= first["hhi"] <= first["hhi_high"]
    assert first["top5_share_low"] == second["top5_share_low"]


def test_period_contrast_interval_is_reproducible_for_a_fixed_sample():
    from msba_dsp.research.market_structure import period_contrasts

    years = (
        [2009] * 20
        + [2010] * 20
        + [2019] * 20
        + [2020] * 20
    )
    winners = ["a"] * 30 + ["b"] * 10 + ["c"] * 10 + ["d"] * 10 + ["e"] * 10 + ["f"] * 10
    fields = [3] * 40 + [2] * 40
    competitions = pd.DataFrame(
        {"selection_year": years, "winner_firm_id": winners, "n_finalists": fields}
    )
    first = period_contrasts(competitions, draws=50, seed=3)
    second = period_contrasts(competitions, draws=50, seed=3)
    assert first["top5_difference_low"] == second["top5_difference_low"]
    assert first["two_firm_difference_low"] <= first["two_firm_difference"] <= first["two_firm_difference_high"]


def test_published_archive_matches_the_winner_model_sample():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    competitors = pd.read_csv(root / "data" / "processed" / "competitors.csv", dtype=str, keep_default_na=False)
    events = pd.read_csv(root / "data" / "processed" / "selection_events.csv", dtype=str, keep_default_na=False)
    firms = pd.read_csv(root / "data" / "processed" / "firms.csv", dtype=str, keep_default_na=False)
    rows = model_rows(competitors, events, firms)
    assert rows["selection_id"].nunique() == 273
    assert len(rows) == 794
    assert rows["firm_id"].nunique() == 82
    assert int(rows.groupby("selection_id")["is_winner"].sum().eq(1).all())


def test_same_day_history_in_the_stored_model_frame_does_not_leak():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    frame = pd.read_csv(root / "data" / "processed" / "model_frame.csv", dtype=str, keep_default_na=False)
    frame["selection_date"] = pd.to_datetime(frame["selection_date"])
    frame["prior_wins"] = frame["prior_wins"].astype(int)
    frame["winner"] = frame["winner"].astype(int)
    for firm_id, group in frame.groupby("firm_id"):
        ordered = group.sort_values(["selection_date", "selection_id"], kind="mergesort")
        for _, row in ordered.iterrows():
            earlier = ordered.loc[ordered["selection_date"] < row["selection_date"]]
            assert int(row["prior_wins"]) == int(earlier["winner"].sum()), firm_id
