import numpy as np
import pandas as pd

from msba_dsp.research.price_calibration import (
    BASE,
    history_frame,
    luce_prices,
    assign_price,
    fit_alpha,
    favorite_lists,
)


def _events(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for column in ("selection_round", "rank_method", "district", "project_label", "school_category"):
        if column not in frame:
            frame[column] = ""
    return frame


def _competitors(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["in_model_sample"] = "True"
    frame["joint_venture"] = "False"
    frame["project_id"] = "p"
    return frame


def _firms() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "firm_id": ["a", "b", "c"],
            "canonical_firm_name": ["Alpha", "Beta", "Gamma"],
        }
    )


def _history() -> pd.DataFrame:
    events = _events(
        [
            {"selection_id": "s1", "selection_date": "2012-01-01", "selection_year": "2012", "school_name": "One Elementary School"},
            {"selection_id": "s2", "selection_date": "2016-06-01", "selection_year": "2016", "school_name": "Two Elementary School"},
            {"selection_id": "s3", "selection_date": "2016-06-01", "selection_year": "2016", "school_name": "Three Elementary School"},
            {"selection_id": "s4", "selection_date": "2018-03-01", "selection_year": "2018", "school_name": "Four Elementary School"},
        ]
    )
    competitors = _competitors(
        [
            {"selection_id": "s1", "firm_id": "a", "rank_num": "1", "winner": "1"},
            {"selection_id": "s1", "firm_id": "b", "rank_num": "2", "winner": "0"},
            {"selection_id": "s2", "firm_id": "a", "rank_num": "1", "winner": "1"},
            {"selection_id": "s2", "firm_id": "b", "rank_num": "2", "winner": "0"},
            {"selection_id": "s3", "firm_id": "a", "rank_num": "2", "winner": "0"},
            {"selection_id": "s3", "firm_id": "c", "rank_num": "1", "winner": "1"},
            {"selection_id": "s4", "firm_id": "a", "rank_num": "2", "winner": "0"},
            {"selection_id": "s4", "firm_id": "b", "rank_num": "1", "winner": "1"},
            {"selection_id": "s4", "firm_id": "c", "rank_num": "3", "winner": "0"},
        ]
    )
    return history_frame(competitors, events, _firms())


def test_proportional_price_of_a_nine_win_favorite_against_two_newcomers():
    prices = luce_prices(np.array([9, 0, 0]), alpha=1.0)
    assert prices.sum() == 1.0
    assert prices[0] == (9 + BASE) / (9 + 3 * BASE)
    assert prices[1] == prices[2]


def test_exponent_zero_is_an_equal_chance_even_when_counts_differ():
    prices = luce_prices(np.array([12, 0, 1]), alpha=0.0)
    assert np.allclose(prices, np.full(3, 1 / 3))


def test_same_day_rank1_does_not_raise_the_second_list_price():
    frame = _history()
    same_day = frame.loc[frame["selection_date"].eq("2016-06-01") & frame["firm_id"].eq("a")]
    assert set(same_day["prior_wins"]) == {1}
    later = frame.loc[frame["selection_id"].eq("s4") & frame["firm_id"].eq("a")].iloc[0]
    assert later["prior_wins"] == 2


def test_a_tie_for_the_most_earlier_wins_is_not_a_favorite():
    frame = _history()
    favorites = favorite_lists(frame.loc[frame["selection_year"].ge(2012)])
    # On s4, Alpha has 2 earlier wins and the others have 0 and 1, so Alpha is the favorite.
    # On s2 and s3, Alpha has 1 and the other firm has 0.
    assert set(favorites["selection_id"]) == {"s2", "s3", "s4"}
    tied = frame.loc[frame["selection_id"].eq("s1")]
    assert tied["prior_wins"].max() == 0
    assert "s1" not in set(favorites["selection_id"])


def test_prices_on_a_list_sum_to_one_and_order_the_counts():
    frame = assign_price(_history(), alpha=1.0)
    totals = frame.groupby("selection_id")["p_price"].sum()
    assert np.allclose(totals.to_numpy(), 1.0)
    fourth = frame.loc[frame["selection_id"].eq("s4")].sort_values("p_price", ascending=False)
    assert list(fourth["firm_id"]) == ["a", "c", "b"]


def test_named_rules_keep_their_own_exponents():
    from msba_dsp.research.price_calibration import _rule_prices

    group = _history().loc[lambda frame: frame["selection_id"].eq("s4")]
    assert np.allclose(_rule_prices(group, "equal", 0.35), np.full(len(group), 1 / 3))
    assert not np.allclose(_rule_prices(group, "square_root", 0.35), _rule_prices(group, "train_minimum", 0.35))
    assert not np.allclose(_rule_prices(group, "proportional", 0.35), _rule_prices(group, "train_minimum", 0.35))


def test_fit_window_prefers_a_flat_price_when_the_leader_keeps_losing():
    events = _events(
        [
            {"selection_id": "early", "selection_date": "2012-01-01", "selection_year": "2012", "school_name": "Early Elementary School"},
            {"selection_id": "late1", "selection_date": "2014-01-01", "selection_year": "2014", "school_name": "Late One Elementary School"},
            {"selection_id": "late2", "selection_date": "2015-01-01", "selection_year": "2015", "school_name": "Late Two Elementary School"},
            {"selection_id": "heldout", "selection_date": "2019-01-01", "selection_year": "2019", "school_name": "Held Out Elementary School"},
        ]
    )
    competitors = _competitors(
        [
            {"selection_id": "early", "firm_id": "a", "rank_num": "1", "winner": "1"},
            {"selection_id": "early", "firm_id": "b", "rank_num": "2", "winner": "0"},
            {"selection_id": "late1", "firm_id": "a", "rank_num": "2", "winner": "0"},
            {"selection_id": "late1", "firm_id": "b", "rank_num": "1", "winner": "1"},
            {"selection_id": "late2", "firm_id": "a", "rank_num": "2", "winner": "0"},
            {"selection_id": "late2", "firm_id": "b", "rank_num": "1", "winner": "1"},
            {"selection_id": "heldout", "firm_id": "a", "rank_num": "1", "winner": "1"},
            {"selection_id": "heldout", "firm_id": "b", "rank_num": "2", "winner": "0"},
        ]
    )
    frame = history_frame(competitors, events, _firms())
    fitted = fit_alpha(frame)
    assert fitted["alpha"] == 0.0
    # The 2019 ranking is outside the fit window, so Alpha's held-out win cannot pull the exponent up.
    assert fitted["grid"][0]["competitions"] == 3
