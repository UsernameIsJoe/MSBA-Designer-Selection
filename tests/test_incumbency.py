import pandas as pd

from msba_dsp.research.incumbency import classify_school, experience_frame


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
    frame["winner"] = frame["winner"].astype(str)
    return frame


def test_school_names_are_not_split_by_a_substring_or_a_vocational_high_school():
    assert classify_school("Middleborough High School") == "high"
    assert classify_school("Putnam Vocational Technical High School") == "vocational"
    assert classify_school("Ayer-Shirley Regional Middle/High School") == "combined"
    assert classify_school("South High Community School") == "high"
    assert classify_school("Edward Devotion School") == "unspecified"
    assert classify_school("Chelsea, MA") == "unknown"
    assert classify_school("Essex North Shore Agricultural and Technical School") == "unspecified"


def test_same_day_results_and_future_wins_do_not_enter_the_history():
    events = _events(
        [
            {"selection_id": "s1", "selection_date": "2016-01-01", "selection_year": "2016", "school_name": "One Elementary School"},
            {"selection_id": "s2", "selection_date": "2016-01-01", "selection_year": "2016", "school_name": "Two Elementary School"},
            {"selection_id": "s3", "selection_date": "2020-06-01", "selection_year": "2020", "school_name": "Three Elementary School"},
            {"selection_id": "s4", "selection_date": "2022-06-01", "selection_year": "2022", "school_name": "Four Elementary School"},
        ]
    )
    competitors = _competitors(
        [
            {"selection_id": "s1", "firm_id": "a", "rank_num": "1", "winner": 1},
            {"selection_id": "s1", "firm_id": "b", "rank_num": "2", "winner": 0},
            {"selection_id": "s2", "firm_id": "a", "rank_num": "1", "winner": 1},
            {"selection_id": "s2", "firm_id": "c", "rank_num": "2", "winner": 0},
            {"selection_id": "s3", "firm_id": "a", "rank_num": "2", "winner": 0},
            {"selection_id": "s3", "firm_id": "b", "rank_num": "1", "winner": 1},
            {"selection_id": "s4", "firm_id": "a", "rank_num": "1", "winner": 1},
            {"selection_id": "s4", "firm_id": "b", "rank_num": "2", "winner": 0},
        ]
    )
    firms = pd.DataFrame({"firm_id": ["a", "b", "c"], "canonical_firm_name": ["A", "B", "C"]})
    frame = experience_frame(competitors, events, firms)
    same_day = frame.loc[frame["selection_date"].eq("2016-01-01")]
    assert set(same_day["prior_wins"]) == {0}
    later = frame.loc[frame["selection_id"].eq("s3") & frame["firm_id"].eq("a")].iloc[0]
    assert later["prior_wins"] == 2
    assert later["wins_previous_3y"] == 0
    assert later["wins_previous_5y"] == 2
    assert later["prior_same_wins"] == 2
    current = frame.loc[frame["selection_id"].eq("s4") & frame["firm_id"].eq("a")].iloc[0]
    assert current["wins_previous_5y"] == 0
    assert current["after_first_observed_win"] == 1


def test_stored_prior_wins_match_the_recomputed_history():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    competitors = pd.read_csv(root / "data" / "processed" / "competitors.csv", dtype=str, keep_default_na=False)
    events = pd.read_csv(root / "data" / "processed" / "selection_events.csv", dtype=str, keep_default_na=False)
    firms = pd.read_csv(root / "data" / "processed" / "firms.csv", dtype=str, keep_default_na=False)
    stored = pd.read_csv(root / "data" / "processed" / "model_frame.csv", dtype=str, keep_default_na=False)
    frame = experience_frame(competitors, events, firms)
    merged = frame.merge(
        stored[["selection_id", "firm_id", "prior_wins", "prior_finals", "wins_previous_3y"]],
        on=["selection_id", "firm_id"],
        suffixes=("", "_stored"),
    )
    assert len(merged) == len(frame)
    assert (merged["prior_wins"].astype(int) == merged["prior_wins_stored"].astype(int)).all()
    assert (merged["prior_finals"].astype(int) == merged["prior_finals_stored"].astype(int)).all()
    assert (merged["wins_previous_3y"].astype(int) == merged["wins_previous_3y_stored"].astype(int)).all()
