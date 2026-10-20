import numpy as np
import pandas as pd

from msba_dsp.evaluation.metrics import attach_probabilities, probability_sums
from msba_dsp.models.analysis import fit_logit
from msba_dsp.processing.build import add_decision_date_features


def test_equal_probabilities_are_not_counted_as_a_unique_favorite():
    frame = pd.DataFrame(
        {
            "selection_id": ["a", "a", "a"],
            "firm_id": ["w", "x", "y"],
            "winner": [1, 0, 0],
            "probability": [1 / 3, 1 / 3, 1 / 3],
        }
    )
    from msba_dsp.evaluation.metrics import top_choice_accuracy

    assert top_choice_accuracy(frame, "probability") == 0


def test_softmax_sums_to_one():
    frame = pd.DataFrame(
        {
            "selection_id": ["a", "a", "a", "b", "b"],
            "score": [1.0, 0.0, 0.0, 2.0, 2.0],
        }
    )
    scored = attach_probabilities(frame, "score", "probability")
    assert probability_sums(scored, "probability")
    paired = scored.loc[scored["selection_id"] == "b", "probability"].tolist()
    assert np.allclose(paired, [0.5, 0.5])


def test_history_does_not_use_same_day_or_future_results():
    events = pd.DataFrame(
        [
            {
                "selection_id": "s1",
                "selection_date": "2016-01-01",
                "selection_year": "2016",
                "school_category": "elementary",
                "district": "A",
                "school_name": "One",
                "source_url": "",
                "rank_method": "explicit_number",
                "selection_round": "final_ranking",
                "estimated_cost_low": "",
                "estimated_cost_high": "",
                "project_label": "One",
            },
            {
                "selection_id": "s2",
                "selection_date": "2016-01-01",
                "selection_year": "2016",
                "school_category": "elementary",
                "district": "B",
                "school_name": "Two",
                "source_url": "",
                "rank_method": "explicit_number",
                "selection_round": "final_ranking",
                "estimated_cost_low": "",
                "estimated_cost_high": "",
                "project_label": "Two",
            },
        ]
    )
    competitors = pd.DataFrame(
        [
            {"selection_id": "s1", "project_id": "p1", "firm_id": "winner", "firm_raw": "Winner", "canonical_key": "winner", "rank_num": 1, "winner": 1, "joint_venture": False, "in_model_sample": True, "match_confidence": "high"},
            {"selection_id": "s1", "project_id": "p1", "firm_id": "other", "firm_raw": "Other", "canonical_key": "other", "rank_num": 2, "winner": 0, "joint_venture": False, "in_model_sample": True, "match_confidence": "high"},
            {"selection_id": "s2", "project_id": "p2", "firm_id": "winner", "firm_raw": "Winner", "canonical_key": "winner", "rank_num": 1, "winner": 1, "joint_venture": False, "in_model_sample": True, "match_confidence": "high"},
            {"selection_id": "s2", "project_id": "p2", "firm_id": "other", "firm_raw": "Other", "canonical_key": "other", "rank_num": 2, "winner": 0, "joint_venture": False, "in_model_sample": True, "match_confidence": "high"},
        ]
    )
    featured = add_decision_date_features(competitors, events)
    assert set(featured["prior_wins"]) == {0}
    assert set(featured["prior_finals"]) == {0}


def test_logit_recovers_a_positive_experience_association():
    rows = []
    for index in range(25):
        for firm, wins, winner, rank in (("strong", 4, 1, 1), ("mid", 1, 0, 2), ("new", 0, 0, 3)):
            rows.append(
                {
                    "selection_id": f"s{index}",
                    "published_rank": rank,
                    "winner": winner,
                    "prior_wins": wins,
                    "prior_grade_wins": 0,
                    "prior_finals": wins,
                    "newcomer": int(wins == 0),
                    "n_finalists": 3,
                    "selection_year": 2018,
                    "school_category": "elementary",
                    "wins_previous_3y": 0,
                    "budget_mid": "",
                }
            )
    fitted = fit_logit(pd.DataFrame(rows))
    estimate = dict(zip(fitted["names"], fitted["beta"]))["prior_wins"]
    assert estimate > 0
