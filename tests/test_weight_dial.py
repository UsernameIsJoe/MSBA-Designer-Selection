import numpy as np
import pandas as pd

from msba_dsp.research.weight_dial import DIAL_GRID, choose_dial, prepare, score_frame, window


def _frame() -> pd.DataFrame:
    rows = []
    for year, selection_id, winner in (
        (2014, "early", "a"),
        (2016, "middle", "a"),
        (2019, "late", "b"),
    ):
        for firm, rank, wins in (("a", 1, 4), ("b", 2, 0), ("c", 3, 1)):
            rows.append(
                {
                    "selection_id": selection_id,
                    "selection_year": year,
                    "firm_id": firm,
                    "published_rank": rank if firm != winner else 1 if False else rank,
                    "winner": int(firm == winner),
                    "prior_wins": wins,
                    "prior_grade_wins": 0,
                    "prior_finals": wins,
                    "newcomer": int(wins == 0),
                    "n_finalists": 3,
                    "school_category": "elementary",
                    "wins_previous_3y": 0,
                    "budget_mid": "",
                }
            )
    # The winner's published rank must be 1 for the sort the logit uses.
    frame = pd.DataFrame(rows)
    frame.loc[frame["winner"].eq(1), "published_rank"] = 1
    frame.loc[frame["winner"].eq(0) & frame["firm_id"].eq("a"), "published_rank"] = 2
    return prepare(frame)


def test_dial_zero_gives_every_firm_the_same_chance():
    frame = _frame()
    beta = np.array([1.5])
    scored = score_frame(frame, beta, ["prior_wins"], dial=0.0)
    assert np.allclose(scored["winner_probability"], 1 / 3)
    assert set(scored["unique_pick"]) == {0}


def test_a_positive_weight_on_wins_names_the_firm_with_more_wins():
    frame = _frame()
    scored = score_frame(frame, np.array([1.0]), ["prior_wins"], dial=1.0)
    early = scored.loc[scored["selection_id"].eq("early")].iloc[0]
    assert early["named_the_winner"] == 1
    assert early["winner_probability"] > 1 / 3


def test_the_dial_is_chosen_without_the_later_years():
    frame = _frame()
    validation = window(frame, 2016, 2018)
    assert set(validation["selection_id"]) == {"middle"}
    assert window(frame, None, 2015)["selection_year"].max() == 2014
    beta = np.array([0.0])
    chosen, curve = choose_dial(validation, beta, ["prior_wins"])
    assert chosen == DIAL_GRID[0]
    assert set(curve["dial"]) == set(DIAL_GRID)


def test_a_tie_on_the_dial_stays_closer_to_an_equal_chance():
    frame = _frame()
    # A zero weight makes every dial identical, so the tie goes to dial 0.
    chosen, _curve = choose_dial(window(frame, 2016, 2018), np.array([0.0]), ["prior_wins"])
    assert chosen == 0.0
