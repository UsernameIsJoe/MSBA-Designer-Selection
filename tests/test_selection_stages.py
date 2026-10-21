import pandas as pd

from msba_dsp.research.selection_stages import stage_frame


def _firms(*pairs: tuple[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "firm_id": [firm_id for firm_id, _ in pairs],
            "canonical_firm_name": [name for _, name in pairs],
            "verification_status": "Verified via cited source",
            "staff_size": "11-50",
            "hq_location": "Boston MA",
            "boston_role": "HQ",
            "joint_venture": "False",
        }
    )


def _blank_inputs():
    competitors = pd.DataFrame(columns=["selection_id", "firm_id", "winner", "in_model_sample"])
    events = pd.DataFrame(columns=["selection_id", "selection_date", "school_name"])
    return competitors, events


def test_a_different_printed_spelling_still_counts_as_interviewed():
    projects = pd.DataFrame(
        [
            {
                "project_id": "p",
                "status_note": "",
                "application_review_date": "2026-01-01",
                "interview_date": "2026-01-15",
                "district": "Town",
                "school": "Example Elementary School",
                "comments": "",
            }
        ]
    )
    chart = pd.DataFrame(
        [
            {"project_id": "p", "stage": "application", "firm_raw": "Raymond Design Associates, Inc.", "rank": "1"},
            {"project_id": "p", "stage": "application", "firm_raw": "Other Architects", "rank": ""},
            {"project_id": "p", "stage": "final", "firm_raw": "Raymond Design Associates", "rank": "1"},
        ]
    )
    competitors, events = _blank_inputs()
    firms = _firms(("f_x", "Raymond Design Associates"), ("f_y", "Other Architects"))
    project_table, applicants = stage_frame(projects, chart, competitors, events, firms)
    raymond = applicants.loc[applicants["firm_raw"].str.startswith("Raymond")].iloc[0]
    other = applicants.loc[applicants["firm_raw"].eq("Other Architects")].iloc[0]
    assert int(raymond["shortlisted"]) == 1
    assert int(other["shortlisted"]) == 0
    assert int(raymond["rank1"]) == 1
    assert project_table.iloc[0]["status"] == "interview_ranked"
    assert int(project_table.iloc[0]["finalists_missing_from_applicants"]) == 0
    assert int(project_table.iloc[0]["raw_spelling_mismatches"]) == 1


def test_a_blank_final_rank_is_not_treated_as_rank_1():
    projects = pd.DataFrame(
        [
            {
                "project_id": "p",
                "status_note": "",
                "application_review_date": "2026-02-01",
                "interview_date": "2026-02-15",
                "district": "Town",
                "school": "Example High School",
                "comments": "",
            }
        ]
    )
    chart = pd.DataFrame(
        [
            {"project_id": "p", "stage": "application", "firm_raw": "Alpha Architects", "rank": "1"},
            {"project_id": "p", "stage": "application", "firm_raw": "Beta Architects", "rank": "2"},
            {"project_id": "p", "stage": "final", "firm_raw": "Alpha Architects", "rank": ""},
            {"project_id": "p", "stage": "final", "firm_raw": "Beta Architects", "rank": "2"},
        ]
    )
    competitors, events = _blank_inputs()
    firms = _firms(("f_a", "Alpha Architects"), ("f_b", "Beta Architects"))
    project_table, applicants = stage_frame(projects, chart, competitors, events, firms)
    assert project_table.iloc[0]["status"] == "interview_unfinished"
    assert set(applicants["rank1"]) == {""}
    assert set(applicants["shortlisted"].astype(int)) == {1}


def test_a_result_on_the_review_day_is_not_earlier_experience():
    projects = pd.DataFrame(
        [
            {
                "project_id": "p",
                "status_note": "",
                "application_review_date": "2025-06-01",
                "interview_date": "2025-06-15",
                "district": "Town",
                "school": "Example Elementary School",
                "comments": "",
            }
        ]
    )
    chart = pd.DataFrame(
        [
            {"project_id": "p", "stage": "application", "firm_raw": "Alpha Architects", "rank": "1"},
            {"project_id": "p", "stage": "application", "firm_raw": "Beta Architects", "rank": "2"},
            {"project_id": "p", "stage": "final", "firm_raw": "Alpha Architects", "rank": "1"},
            {"project_id": "p", "stage": "final", "firm_raw": "Beta Architects", "rank": "2"},
        ]
    )
    competitors = pd.DataFrame(
        [
            {"selection_id": "same", "firm_id": "f_a", "winner": "1", "in_model_sample": "True"},
            {"selection_id": "same", "firm_id": "f_b", "winner": "0", "in_model_sample": "True"},
            {"selection_id": "earlier", "firm_id": "f_a", "winner": "1", "in_model_sample": "True"},
            {"selection_id": "earlier", "firm_id": "f_c", "winner": "0", "in_model_sample": "True"},
        ]
    )
    events = pd.DataFrame(
        [
            {"selection_id": "same", "selection_date": "2025-06-01", "school_name": "Other Elementary School"},
            {"selection_id": "earlier", "selection_date": "2024-06-01", "school_name": "Old Elementary School"},
        ]
    )
    from msba_dsp.processing.names import resolve_firm

    firms = _firms(("f_a", "Alpha Architects"), ("f_b", "Beta Architects"))
    alpha_id = resolve_firm("Alpha Architects").firm_id
    competitors["firm_id"] = competitors["firm_id"].replace({"f_a": alpha_id})
    _, applicants = stage_frame(projects, chart, competitors, events, firms)
    alpha = applicants.loc[applicants["firm_raw"].eq("Alpha Architects")].iloc[0]
    assert int(alpha["prior_wins_review"]) == 1
    assert int(alpha["prior_same_wins_review"]) == 1


def test_no_interview_and_a_sole_applicant_stay_out_of_the_interview_rate():
    projects = pd.DataFrame(
        [
            {
                "project_id": "ranked",
                "status_note": "",
                "application_review_date": "2025-08-12",
                "interview_date": "",
                "district": "Springfield",
                "school": "Gerena Elementary School",
                "comments": "No interview",
            },
            {
                "project_id": "sole",
                "status_note": "",
                "application_review_date": "2026-04-07",
                "interview_date": "",
                "district": "Triton",
                "school": "Triton Regional High School",
                "comments": "No Interview",
            },
            {
                "project_id": "cancelled",
                "status_note": "March 2025 Meetings Cancelled",
                "application_review_date": "",
                "interview_date": "",
                "district": "",
                "school": "",
                "comments": "",
            },
        ]
    )
    chart = pd.DataFrame(
        [
            {"project_id": "ranked", "stage": "application", "firm_raw": "Alpha Architects", "rank": "1"},
            {"project_id": "ranked", "stage": "application", "firm_raw": "Beta Architects", "rank": "2"},
            {"project_id": "sole", "stage": "application", "firm_raw": "Alpha Architects", "rank": "1"},
            {"project_id": "cancelled", "stage": "application", "firm_raw": "Alpha Architects", "rank": "1"},
        ]
    )
    competitors, events = _blank_inputs()
    firms = _firms(("f_a", "Alpha Architects"), ("f_b", "Beta Architects"))
    project_table, applicants = stage_frame(projects, chart, competitors, events, firms)
    assert set(project_table["project_id"]) == {"ranked", "sole"}
    ranked = applicants.loc[applicants["project_id"].eq("ranked")]
    assert ranked["shortlisted"].eq("").all()
    assert int(ranked.loc[ranked["firm_raw"].eq("Alpha Architects"), "rank1"].iloc[0]) == 1
    assert project_table.loc[project_table["project_id"].eq("sole"), "status"].iloc[0] == "sole_applicant_no_interview"
    assert applicants.loc[applicants["project_id"].eq("sole"), "rank1"].eq("").all()


def test_chart_finalists_resolve_inside_the_applicant_list():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    projects = pd.read_csv(root / "data/processed/chart_projects.csv", dtype=str, keep_default_na=False)
    chart = pd.read_csv(root / "data/processed/chart_firms.csv", dtype=str, keep_default_na=False)
    competitors = pd.read_csv(root / "data/processed/competitors.csv", dtype=str, keep_default_na=False)
    events = pd.read_csv(root / "data/processed/selection_events.csv", dtype=str, keep_default_na=False)
    firms = pd.read_csv(root / "data/processed/firms.csv", dtype=str, keep_default_na=False)
    project_table, _ = stage_frame(projects, chart, competitors, events, firms)
    assert int(project_table["finalists_missing_from_applicants"].astype(int).sum()) == 0
    assert set(project_table["status"]) >= {"interview_ranked", "interview_unfinished", "application_ranked_no_interview", "sole_applicant_no_interview"}
