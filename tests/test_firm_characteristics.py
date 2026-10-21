import pandas as pd

from msba_dsp.research.firm_characteristics import (
    age_at_selection,
    geography,
    staff_band,
    _fit_logit,
)


def test_ranges_are_not_converted_to_a_midpoint_and_open_ends_stay_blank():
    assert staff_band("11-50") == "11-50"
    assert staff_band("~20") == "11-50"
    assert staff_band("50+") == ""
    assert staff_band("~1,000") == "501-1000"
    assert staff_band("~1,000", thousand_with_larger=True) == "1001+"
    assert staff_band("1,001-5,000") == "1001+"
    assert staff_band("~230", drop_point_estimates=True) == ""
    assert staff_band("399", drop_point_estimates=True) == ""


def test_boston_branch_is_not_credited_before_its_recorded_opening_year():
    assert geography("Hartford CT", "Boston branch (opened 2010)", 2009) == "out_of_state_no_branch"
    assert geography("Hartford CT", "Boston branch (opened 2010)", 2010) == "out_of_state_boston_branch"
    assert geography("Manchester NH", "Boston branch (opened 2013)", 2012) == "out_of_state_no_branch"
    assert geography("Chicago IL", "Boston branch", 2015) == "out_of_state_branch_undated"
    assert geography("Chicago IL", "Boston branch", 2015, credit_undated_branch=True) == "out_of_state_boston_branch"
    assert geography("Columbus OH", "Boston branch if confirmed", 2020) == "unknown"
    assert geography("Omaha NE", "Branch if active Boston office", 2020) == "unknown"


def test_headquarters_groups_follow_the_city_and_not_a_project_reach_sentence():
    assert geography("Charlestown MA", "Boston neighborhood headquarters", 2016) == "boston_hq"
    assert geography("Boston MA", "HQ", 2016) == "boston_hq"
    assert geography("Cambridge MA", "Greater Boston headquarters", 2016) == "ma_outside_boston"
    assert geography("Cambridge MA", "Greater Boston headquarters", 2016, inner_core_as_boston=True) == "boston_hq"
    assert geography("Somerville MA", "Greater Boston HQ", 2016, inner_core_as_boston=True) == "boston_hq"
    assert geography("Burlington VT", "No Boston city office confirmed", 2016) == "out_of_state_no_branch"


def test_age_uses_the_selection_year_and_rejects_a_founding_year_after_it():
    assert age_at_selection(2010, "1961") == 49
    assert age_at_selection(2008, "2015") is None
    assert age_at_selection(2012, "") is None


def test_conditional_logit_gives_the_larger_group_a_positive_score_when_it_always_wins():
    rows = []
    for index in range(12):
        rows.append({"selection_id": f"s{index}", "firm_id": "large", "is_winner": 1, "group_201+": 1.0, "group_51-200": 0.0})
        rows.append({"selection_id": f"s{index}", "firm_id": "small", "is_winner": 0, "group_201+": 0.0, "group_51-200": 0.0})
    fitted = _fit_logit(pd.DataFrame(rows), ["group_201+", "group_51-200"])
    assert fitted is not None
    assert dict(zip(fitted["names"], fitted["beta"]))["group_201+"] > 0
