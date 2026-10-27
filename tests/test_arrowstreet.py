import pandas as pd

from msba_dsp.research.arrowstreet import PEER_HIGH, PEER_LOW, firm_excess, list_gaps


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "selection_id": ["s1", "s1", "s2", "s2", "s3", "s3"],
            "selection_date": ["2016-01-01", "2016-01-01", "2018-01-01", "2018-01-01", "2020-01-01", "2020-01-01"],
            "firm_id": ["arrow", "other", "arrow", "other", "arrow", "other"],
            "firm_name": ["Arrowstreet", "Other", "Arrowstreet", "Other", "Arrowstreet", "Other"],
            "winner": [0, 1, 1, 0, 1, 0],
            "n_finalists": [2, 2, 2, 2, 4, 4],
            "prior_wins": [0, 3, 0, 1, 1, 0],
            "school_name": ["One Elementary School"] * 6,
            "category": ["elementary"] * 6,
        }
    )


def test_the_gap_is_a_win_minus_one_seats_share():
    gaps = list_gaps(_frame().loc[_frame()["firm_id"].eq("arrow")])
    assert list(gaps["seat_share"]) == [0.5, 0.5, 0.25]
    assert list(gaps["gap"]) == [-0.5, 0.5, 0.75]


def test_excess_wins_equal_rank1_results_minus_the_sum_of_seat_shares():
    summary = firm_excess(_frame(), "arrow")
    assert summary["lists"] == 3
    assert summary["rank1"] == 2
    assert summary["expected_rank1"] == 1.25
    assert summary["excess_wins"] == 0.75


def test_peer_window_is_fifteen_to_twenty_five_lists():
    assert (PEER_LOW, PEER_HIGH) == (15, 25)
