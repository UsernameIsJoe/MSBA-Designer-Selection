import pandas as pd

from msba_dsp.research.incumbency import experience_frame
from msba_dsp.research.local_contrasts import (
    MIXED_STOP,
    _parse_millions,
    district_incumbent_frame,
    district_summary,
    resolve_near_duplicates,
    pooled_win_counts,
    _competition_rows,
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
    frame["winner"] = frame["winner"].astype(str)
    return frame


def _sample() -> tuple[pd.DataFrame, pd.DataFrame]:
    events = _events(
        [
            {"selection_id": "s1", "selection_date": "2014-01-01", "selection_year": "2014", "district": "Alpha", "school_name": "Alpha Elementary School"},
            {"selection_id": "s2", "selection_date": "2014-01-01", "selection_year": "2014", "district": "Alpha", "school_name": "Alpha Middle School"},
            {"selection_id": "s3", "selection_date": "2016-06-01", "selection_year": "2016", "district": "Alpha", "school_name": "Alpha High School"},
            {"selection_id": "s4", "selection_date": "2018-06-01", "selection_year": "2018", "district": "Beta", "school_name": "Beta Elementary School"},
        ]
    )
    competitors = _competitors(
        [
            {"selection_id": "s1", "firm_id": "a", "rank_num": "1", "winner": 1},
            {"selection_id": "s1", "firm_id": "b", "rank_num": "2", "winner": 0},
            {"selection_id": "s2", "firm_id": "a", "rank_num": "1", "winner": 1},
            {"selection_id": "s2", "firm_id": "c", "rank_num": "2", "winner": 0},
            {"selection_id": "s3", "firm_id": "b", "rank_num": "1", "winner": 1},
            {"selection_id": "s3", "firm_id": "a", "rank_num": "2", "winner": 0},
            {"selection_id": "s4", "firm_id": "a", "rank_num": "1", "winner": 1},
            {"selection_id": "s4", "firm_id": "b", "rank_num": "2", "winner": 0},
        ]
    )
    firms = pd.DataFrame({"firm_id": ["a", "b", "c"], "canonical_firm_name": ["A", "B", "C"]})
    return experience_frame(competitors, events, firms), events


def test_same_day_district_wins_do_not_make_a_firm_its_own_incumbent():
    frame, events = _sample()
    scored = district_incumbent_frame(frame, events)
    same_day = scored.loc[scored["selection_date"].eq("2014-01-01")]
    assert set(same_day["district_incumbent"]) == {0}
    later = scored.loc[scored["selection_id"].eq("s3") & scored["firm_id"].eq("a")].iloc[0]
    assert later["district_incumbent"] == 1
    other_district = scored.loc[scored["selection_id"].eq("s4")]
    assert set(other_district["district_incumbent"]) == {0}


def test_mixed_list_excess_is_withheld_below_the_stated_cell_size():
    frame, events = _sample()
    scored = district_incumbent_frame(frame, events)
    competitions = _competition_rows(scored)
    summary = district_summary(competitions, scored)
    assert summary["lists_with_incumbent"] == 1
    assert summary["mixed_with_incumbent"] < MIXED_STOP
    assert summary["mixed_excess"] is None


def test_a_printed_cost_range_uses_the_midpoint_in_millions():
    assert _parse_millions("$75 million - $100 million") == (75.0, 100.0, 87.5)
    assert _parse_millions("$138 million to $241.6 million") == (138.0, 241.6, 189.8)
    assert _parse_millions("") is None


def test_joint_venture_lines_stay_out_of_the_spelling_pool():
    firms = pd.DataFrame(
        {
            "firm_id": ["parent", "venture", "short", "long"],
            "canonical_firm_name": ["Miller Dyer Spears Inc.", "Miller Dyer Spears Inc./Sasaki", "LaVallee Brensinger", "LaVallee Brensinger Architects"],
            "canonical_key": ["miller dyer spears", "miller dyer spears sasaki", "lavallee brensinger", "lavallee brensinger architects"],
            "historical_names": ["", "", "", ""],
            "research_note": ["", "Joint submission / tied firms", "", ""],
        }
    )
    pairs = pd.DataFrame(
        {
            "firm_a": ["Miller Dyer Spears Inc.", "LaVallee Brensinger Architects", "CBT/Childs Bertman Tseckares Inc."],
            "firm_b": ["Miller Dyer Spears Inc./Sasaki", "LaVallee Brensinger", "CBT/Childs Bertram Tseckares, Inc."],
        }
    )
    firms = pd.concat(
        [
            firms,
            pd.DataFrame(
                {
                    "firm_id": ["cbt_a", "cbt_b"],
                    "canonical_firm_name": ["CBT/Childs Bertman Tseckares Inc.", "CBT/Childs Bertram Tseckares, Inc."],
                    "canonical_key": ["cbt childs bertman tseckares", "cbt childs bertram tseckares"],
                    "historical_names": ["", ""],
                    "research_note": ["", ""],
                }
            ),
        ],
        ignore_index=True,
    )
    resolved, spelling, _every = resolve_near_duplicates(pairs, firms)
    assert int(resolved.loc[resolved["firm_b"].str.contains("Sasaki"), "in_spelling_pool"].iloc[0]) == 0
    assert int(resolved.loc[resolved["firm_a"].str.contains("LaVallee"), "in_spelling_pool"].iloc[0]) == 1
    assert int(resolved.loc[resolved["firm_a"].str.contains("CBT"), "in_spelling_pool"].iloc[0]) == 1
    assert spelling["short"] == spelling["long"] or spelling["long"] == spelling["short"]
    frame = pd.DataFrame(
        {
            "selection_date": ["2019-01-01", "2019-01-01", "2023-01-01", "2023-01-01"],
            "selection_id": ["old", "old", "new", "new"],
            "firm_id": ["long", "other", "short", "long"],
            "winner": [1, 0, 1, 0],
        }
    )
    prior = pooled_win_counts(frame, spelling)
    short_row = prior.loc[frame["firm_id"].eq("short")].iloc[0]
    assert int(short_row) == 1
