"""Applicant, interview, and rank-1 stages on the 2025–2026 result chart.

Historical pages usually publish the interviewed firms and omit the rest of the
applicant pool. This phase does not turn those pages into an application rate.
Rank 1 is the published order, not a signed contract. Present-day staff size
and office location stay descriptive.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from msba_dsp.evaluation.metrics import wilson_interval
from msba_dsp.processing.names import resolve_firm
from msba_dsp.research.firm_characteristics import COLLAPSED, geography, staff_band
from msba_dsp.research.incumbency import TRACKED, classify_school
from msba_dsp.research.market_structure import _truthy

SEED = 20261020
DRAWS = 2000
# Stored firm ids that a chart spelling does not share. Used only as a
# sensitivity. The primary rates keep the published firm ids separate.
LOOKALIKE_KEYS = {
    "flansburg architects": "flansburgh associates",
    "turowski2": "turowski2 architecture",
    "lavallee brensinger": "lavallee brensinger architects",
    "machado silvetti associates": "machado and silvetti associates",
}


def _blank(value: object) -> bool:
    return str(value).strip() == "" or str(value).lower() == "nan"


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return round(float(value), digits)


def _numeric_rank(value: object) -> int | None:
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    return None


def _win_bucket(count: int) -> str:
    if count <= 0:
        return "0"
    if count <= 2:
        return "1-2"
    return "3 or more"


def _same_type_bucket(category: str, same_wins: int) -> str:
    if category not in TRACKED:
        return "school type not stated"
    if same_wins <= 0:
        return "no earlier same-type rank-1"
    return "one or more earlier same-type rank-1"


def history_index(competitors: pd.DataFrame, events: pd.DataFrame) -> dict[str, list[tuple[str, int, str]]]:
    """Model-sample results keyed by firm. Dates are ISO strings."""
    model = competitors.loc[_truthy(competitors["in_model_sample"]), ["selection_id", "firm_id", "winner"]].copy()
    meta = events[["selection_id", "selection_date", "school_name"]].drop_duplicates("selection_id")
    model = model.merge(meta, on="selection_id", how="left")
    model["won"] = _truthy(model["winner"]).astype(int)
    model["category"] = model["school_name"].map(classify_school)
    grouped: dict[str, list[tuple[str, int, str]]] = {}
    for firm_id, group in model.groupby("firm_id", sort=False):
        grouped[str(firm_id)] = [
            (str(date), int(won), str(category))
            for date, won, category in zip(group["selection_date"], group["won"], group["category"])
        ]
    return grouped


def _prior(history: dict[str, list[tuple[str, int, str]]], firm_id: str, as_of: str, category: str) -> tuple[int, int, int]:
    wins = finals = same = 0
    for date, won, earlier_category in history.get(firm_id, []):
        if date >= as_of:
            continue
        finals += 1
        wins += won
        if category in TRACKED and earlier_category == category and won:
            same += won
    return wins, finals, same


def _project_status(applicant_count: int, final_ranks: list[int | None], comments: str) -> str:
    no_interview = "no interview" in comments.lower()
    if not final_ranks and no_interview and applicant_count == 1:
        return "sole_applicant_no_interview"
    if not final_ranks and no_interview and applicant_count >= 2:
        return "application_ranked_no_interview"
    if not final_ranks:
        return "no_final_list"
    if any(rank is None for rank in final_ranks):
        return "interview_unfinished"
    best = min(rank for rank in final_ranks if rank is not None)
    if sum(rank == best for rank in final_ranks) != 1:
        return "interview_unfinished"
    return "interview_ranked"


def stage_frame(
    projects: pd.DataFrame,
    chart_firms: pd.DataFrame,
    competitors: pd.DataFrame,
    events: pd.DataFrame,
    firms: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per resolved applicant, plus one row per live chart project."""
    history = history_index(competitors, events)
    id_by_key = {}
    for firm_id, name in zip(firms["firm_id"], firms["canonical_firm_name"]):
        if _blank(name):
            continue
        id_by_key[resolve_firm(str(name)).canonical_key] = str(firm_id)
    profile = firms.drop_duplicates("firm_id").set_index("firm_id")
    project_rows = []
    applicant_rows = []
    live = projects.loc[projects["status_note"].astype(str).str.strip().eq("")]
    for _, project in live.iterrows():
        block = chart_firms.loc[chart_firms["project_id"].eq(project["project_id"])]
        applications = block.loc[block["stage"].eq("application")]
        finals = block.loc[block["stage"].eq("final")]
        by_firm: dict[str, dict] = {}
        for _, firm in applications.iterrows():
            resolved = resolve_firm(str(firm["firm_raw"]))
            slot = by_firm.setdefault(
                resolved.firm_id,
                {"firm_raw": str(firm["firm_raw"]), "canonical_key": resolved.canonical_key, "joint_venture": resolved.joint_venture, "ranks": [], "disqualified": False},
            )
            rank_text = str(firm["rank"]).strip().lower()
            if "disqualif" in rank_text:
                slot["disqualified"] = True
            number = _numeric_rank(firm["rank"])
            if number is not None:
                slot["ranks"].append(number)
        final_ids = {}
        final_ranks = []
        for _, firm in finals.iterrows():
            resolved = resolve_firm(str(firm["firm_raw"]))
            number = _numeric_rank(firm["rank"])
            final_ids[resolved.firm_id] = number
            final_ranks.append(number)
        status = _project_status(len(by_firm), final_ranks, str(project["comments"]))
        category = classify_school(str(project["school"]))
        review = str(project["application_review_date"]).strip()
        interview = str(project["interview_date"]).strip() or review
        winner_id = ""
        if status == "interview_ranked":
            best = min(rank for rank in final_ranks if rank is not None)
            winner_id = next(firm_id for firm_id, rank in final_ids.items() if rank == best)
        elif status == "application_ranked_no_interview":
            numbered = [(firm_id, min(slot["ranks"])) for firm_id, slot in by_firm.items() if slot["ranks"]]
            if numbered:
                best = min(rank for _, rank in numbered)
                leaders = [firm_id for firm_id, rank in numbered if rank == best]
                if len(leaders) == 1:
                    winner_id = leaders[0]
                    status = "application_ranked_no_interview"
                else:
                    status = "application_rank_unresolved"
        raw_final = {str(name) for name in finals["firm_raw"]}
        raw_application = {str(name) for name in applications["firm_raw"]}
        project_rows.append(
            {
                "project_id": project["project_id"],
                "district": project["district"],
                "school": project["school"],
                "category": category,
                "application_review_date": review,
                "interview_date": interview,
                "comments": project["comments"],
                "status": status,
                "applicants": len(by_firm),
                "shortlist_size": len(final_ids),
                "rank1_firm_id": winner_id,
                "raw_spelling_mismatches": len(raw_final - raw_application),
                "finalists_missing_from_applicants": len(set(final_ids) - set(by_firm)),
            }
        )
        has_shortlist = status in {"interview_ranked", "interview_unfinished"}
        has_rank = status in {"interview_ranked", "application_ranked_no_interview"} and bool(winner_id)
        for firm_id, slot in by_firm.items():
            wins_review, finals_review, same_review = _prior(history, firm_id, review, category)
            wins_interview, finals_interview, same_interview = _prior(history, firm_id, interview, category)
            paired = id_by_key.get(LOOKALIKE_KEYS.get(slot["canonical_key"], ""), "")
            paired_wins = _prior(history, paired, review, category)[0] if paired and paired != firm_id else 0
            record = profile.loc[firm_id] if firm_id in profile.index else None
            verified = False if record is None else str(record["verification_status"]).startswith("Verified")
            staff = staff_band(record["staff_size"]) if verified else ""
            year = int(review[:4]) if len(review) >= 4 else 2026
            geo = geography(record["hq_location"], record["boston_role"], year) if verified else "unknown"
            if record is not None and str(record.get("joint_venture", "")).strip().lower() in {"true", "1"}:
                slot["joint_venture"] = True
            applicant_rows.append(
                {
                    "project_id": project["project_id"],
                    "firm_id": firm_id,
                    "firm_raw": slot["firm_raw"],
                    "canonical_key": slot["canonical_key"],
                    "joint_venture": int(bool(slot["joint_venture"])),
                    "disqualified": int(slot["disqualified"]),
                    "application_rank": min(slot["ranks"]) if slot["ranks"] else "",
                    "category": category,
                    "status": status,
                    "shortlisted": int(firm_id in final_ids) if has_shortlist else "",
                    "rank1": int(firm_id == winner_id) if has_rank else "",
                    "prior_wins_review": wins_review,
                    "prior_finals_review": finals_review,
                    "prior_same_wins_review": same_review,
                    "prior_wins_interview": wins_interview,
                    "prior_finals_interview": finals_interview,
                    "prior_same_wins_interview": same_interview,
                    "lookalike_extra_wins": paired_wins,
                    "staff_group": COLLAPSED.get(staff, ""),
                    "geo": geo,
                }
            )
    return pd.DataFrame(project_rows), pd.DataFrame(applicant_rows)


def _bootstrap_rate(frame: pd.DataFrame, success: str, draws: int = DRAWS, seed: int = SEED) -> tuple[float | None, float | None]:
    if frame.empty:
        return None, None
    pieces = [group[success].astype(int).to_numpy() for _, group in frame.groupby("project_id", sort=False)]
    point = float(np.sum([piece.sum() for piece in pieces]) / np.sum([len(piece) for piece in pieces]))
    rng = np.random.default_rng(seed)
    rates = []
    index = np.arange(len(pieces))
    for _ in range(draws):
        chosen = rng.choice(index, size=len(index), replace=True)
        numerator = sum(int(pieces[item].sum()) for item in chosen)
        denominator = sum(len(pieces[item]) for item in chosen)
        rates.append(numerator / denominator)
    column = np.asarray(rates)
    return point, (float(np.quantile(column, 0.025)), float(np.quantile(column, 0.975)))


def _rate_row(frame: pd.DataFrame, stage: str, family: str, group: str, success: str) -> dict:
    point, interval = _bootstrap_rate(frame, success)
    successes = int(frame[success].astype(int).sum())
    trials = int(len(frame))
    low, high = wilson_interval(successes, trials)
    return {
        "stage": stage,
        "group_family": family,
        "group": group,
        "rows": trials,
        "successes": successes,
        "projects": int(frame["project_id"].nunique()),
        "rate": _round(point),
        "rate_low": _round(interval[0]) if interval else None,
        "rate_high": _round(interval[1]) if interval else None,
        "wilson_low": _round(low),
        "wilson_high": _round(high),
    }


def conversion_rates(applicants: pd.DataFrame) -> pd.DataFrame:
    """Rates with a project bootstrap. Each stage has its own denominator."""
    shortlist = applicants.loc[applicants["shortlisted"].astype(str).isin(["0", "1"])].copy()
    shortlist["shortlisted"] = shortlist["shortlisted"].astype(int)
    ranked = applicants.loc[applicants["status"].eq("interview_ranked") & applicants["rank1"].astype(str).isin(["0", "1"])].copy()
    ranked["rank1"] = ranked["rank1"].astype(int)
    finalists = ranked.loc[ranked["shortlisted"].astype(str).isin(["0", "1"]) & ranked["shortlisted"].astype(int).eq(1)].copy()
    rows = []
    stages = [
        ("application_to_shortlist", shortlist, "shortlisted", "prior_wins_review", "prior_same_wins_review"),
        ("shortlist_to_rank1", finalists, "rank1", "prior_wins_interview", "prior_same_wins_interview"),
        ("application_to_rank1", ranked, "rank1", "prior_wins_interview", "prior_same_wins_interview"),
    ]
    for stage, frame, success, win_column, same_column in stages:
        if frame.empty:
            continue
        rows.append(_rate_row(frame, stage, "overall", "all applicants" if stage != "shortlist_to_rank1" else "all interviewed firms", success))
        work = frame.copy()
        work["win_bucket"] = work[win_column].astype(int).map(_win_bucket)
        work["same_bucket"] = [_same_type_bucket(category, int(same)) for category, same in zip(work["category"], work[same_column])]
        for group, part in work.groupby("win_bucket", sort=False):
            rows.append(_rate_row(part, stage, "earlier_rank1_results", str(group), success))
        for group, part in work.groupby("same_bucket", sort=False):
            rows.append(_rate_row(part, stage, "same_type_experience", str(group), success))
        attributes = work.loc[work["joint_venture"].astype(int).eq(0)]
        for group, part in attributes.groupby(attributes["staff_group"].replace("", "missing"), sort=False):
            rows.append(_rate_row(part, stage, "staff_band_2026", str(group), success))
        for group, part in attributes.groupby(attributes["geo"].replace("", "unknown"), sort=False):
            rows.append(_rate_row(part, stage, "headquarters_2026", str(group), success))
    return pd.DataFrame(rows)


def seat_excess(applicants: pd.DataFrame, outcome: str, experience: str, draws: int = DRAWS, seed: int = SEED) -> dict:
    """Share of successes going to firms with an earlier rank-1 result, minus their share of the rows."""
    frame = applicants.loc[applicants[outcome].astype(str).isin(["0", "1"])].copy()
    frame[outcome] = frame[outcome].astype(int)
    frame["experienced"] = frame[experience].astype(int).gt(0).astype(int)
    gaps = []
    for _, group in frame.groupby("project_id", sort=False):
        if group["experienced"].nunique() < 2 or int(group[outcome].sum()) == 0:
            continue
        gaps.append(float(group.loc[group[outcome].eq(1), "experienced"].mean() - group["experienced"].mean()))
    if len(gaps) < 8:
        return {"projects": len(gaps), "excess": None}
    point = float(np.mean(gaps))
    rng = np.random.default_rng(seed)
    samples = [float(np.mean(rng.choice(gaps, size=len(gaps), replace=True))) for _ in range(draws)]
    column = np.asarray(samples)
    return {
        "projects": len(gaps),
        "excess": _round(point),
        "excess_low": _round(float(np.quantile(column, 0.025))),
        "excess_high": _round(float(np.quantile(column, 0.975))),
    }


def application_rank_table(applicants: pd.DataFrame) -> pd.DataFrame:
    """Pre-interview numbers on the chart, among projects that published an interview list."""
    frame = applicants.loc[applicants["shortlisted"].astype(str).isin(["0", "1"])].copy()
    frame["shortlisted"] = frame["shortlisted"].astype(int)
    frame["rank_group"] = frame["application_rank"].map(lambda value: str(value) if str(value) in {"1", "2", "3"} else ("4 or lower" if str(value).isdigit() else "no number"))
    frame.loc[frame["disqualified"].astype(int).eq(1), "rank_group"] = "disqualified"
    rows = [_rate_row(part, "application_rank_to_shortlist", "preinterview_rank", str(group), "shortlisted") for group, part in frame.groupby("rank_group", sort=False)]
    completed = applicants.loc[applicants["status"].eq("interview_ranked")].copy()
    unique_first = []
    for project_id, group in completed.groupby("project_id", sort=False):
        numbered = group.loc[group["application_rank"].astype(str).str.isdigit()]
        if numbered.empty:
            continue
        best = numbered["application_rank"].astype(int).min()
        leaders = numbered.loc[numbered["application_rank"].astype(int).eq(best)]
        if len(leaders) != 1:
            continue
        unique_first.append({"project_id": project_id, "held": int(leaders["rank1"].astype(int).iloc[0])})
    if unique_first:
        held = pd.DataFrame(unique_first)
        rows.append(_rate_row(held, "preinterview_first_to_rank1", "preinterview_rank", "unique pre-interview first", "held"))
    return pd.DataFrame(rows)


def experience_cross(applicants: pd.DataFrame) -> pd.DataFrame:
    """Earlier rank-1 results against same-type results. Counts, not a model."""
    frame = applicants.loc[applicants["shortlisted"].astype(str).isin(["0", "1"])].copy()
    frame["shortlisted"] = frame["shortlisted"].astype(int)
    frame["bucket"] = frame["prior_wins_review"].astype(int).map(_win_bucket)
    frame["same_type"] = [
        _same_type_bucket(category, int(same)) for category, same in zip(frame["category"], frame["prior_same_wins_review"])
    ]
    rows = []
    for (bucket, same_type), part in frame.groupby(["bucket", "same_type"], sort=False):
        rows.append(
            {
                "stage": "application_to_shortlist",
                "earlier_rank1_results": bucket,
                "same_type": same_type,
                "rows": int(len(part)),
                "interviewed": int(part["shortlisted"].sum()),
                "rate": _round(float(part["shortlisted"].mean())),
            }
        )
    return pd.DataFrame(rows)


def geography_boundary(applicants: pd.DataFrame, firms: pd.DataFrame) -> pd.DataFrame:
    """City line, and the same rates with Cambridge and Somerville grouped with Boston."""
    profile = firms.drop_duplicates("firm_id").set_index("firm_id")
    rows = []
    stages = [
        ("application_to_shortlist", applicants.loc[applicants["shortlisted"].astype(str).isin(["0", "1"])].copy(), "shortlisted"),
        ("shortlist_to_rank1", applicants.loc[applicants["status"].eq("interview_ranked") & applicants["shortlisted"].astype(str).eq("1")].copy(), "rank1"),
    ]
    for boundary, inner in (("city_line", False), ("cambridge_and_somerville_with_boston", True)):
        for stage, frame, success in stages:
            if frame.empty:
                continue
            work = frame.copy()
            work[success] = work[success].astype(int)
            geos = []
            for firm_id, review in zip(work["firm_id"], work["project_id"]):
                record = profile.loc[firm_id] if firm_id in profile.index else None
                verified = record is not None and str(record["verification_status"]).startswith("Verified")
                year = 2026
                geos.append(geography(record["hq_location"], record["boston_role"], year, inner_core_as_boston=inner) if verified else "unknown")
            work["geo_boundary"] = geos
            work = work.loc[work["joint_venture"].astype(int).eq(0)]
            for group in ("boston_hq", "ma_outside_boston"):
                part = work.loc[work["geo_boundary"].eq(group)]
                if part.empty:
                    continue
                row = _rate_row(part, stage, "headquarters_2026", group, success)
                row["boundary"] = boundary
                rows.append(row)
    return pd.DataFrame(rows)


def field_summary(projects: pd.DataFrame) -> dict:
    interviewed = projects.loc[projects["status"].isin(["interview_ranked", "interview_unfinished"])]
    if interviewed.empty:
        return {}
    applicants = interviewed["applicants"].astype(int)
    shortlist = interviewed["shortlist_size"].astype(int)
    return {
        "projects_with_an_interview_list": int(len(interviewed)),
        "completed_rankings": int(projects["status"].eq("interview_ranked").sum()),
        "unfinished_rankings": int(projects["status"].eq("interview_unfinished").sum()),
        "no_interview_rankings": int(projects["status"].eq("application_ranked_no_interview").sum()),
        "sole_applicant_projects": int(projects["status"].eq("sole_applicant_no_interview").sum()),
        "median_applicants": _round(float(applicants.median()), 1),
        "mean_applicants": _round(float(applicants.mean()), 2),
        "min_applicants": int(applicants.min()),
        "max_applicants": int(applicants.max()),
        "median_interview_list": _round(float(shortlist.median()), 1),
        "two_firm_interview_lists": int(shortlist.eq(2).sum()),
        "three_firm_interview_lists": int(shortlist.eq(3).sum()),
        "four_firm_interview_lists": int(shortlist.eq(4).sum()),
        "projects_that_interviewed_every_applicant": int((shortlist == applicants).sum()),
        "raw_spelling_mismatches": int(projects["raw_spelling_mismatches"].astype(int).sum()),
        "finalists_missing_from_applicants": int(projects["finalists_missing_from_applicants"].astype(int).sum()),
    }


def historical_coverage(shortlists: pd.DataFrame) -> dict:
    """Posted unranked lists. These are not an applicant pool."""
    if shortlists.empty:
        return {"lists": 0}
    keys = shortlists.groupby(["meeting_date", "project_label"], sort=False)
    return {
        "firm_rows": int(len(shortlists)),
        "posted_lists": int(keys.ngroups),
        "list_kinds": {str(kind): int(count) for kind, count in shortlists["list_kind"].value_counts().items()},
    }


def build_outputs(
    projects: pd.DataFrame,
    chart_firms: pd.DataFrame,
    competitors: pd.DataFrame,
    events: pd.DataFrame,
    firms: pd.DataFrame,
    shortlists: pd.DataFrame,
) -> dict:
    project_table, applicants = stage_frame(projects, chart_firms, competitors, events, firms)
    rates = conversion_rates(applicants)
    shortlist = applicants.loc[applicants["shortlisted"].astype(str).isin(["0", "1"])].copy()
    ranked = applicants.loc[applicants["status"].eq("interview_ranked")].copy()
    cut = project_table.loc[project_table["shortlist_size"].astype(int).lt(project_table["applicants"].astype(int)), "project_id"]
    selective = shortlist.loc[shortlist["project_id"].isin(set(cut))]
    zero = shortlist.loc[shortlist["prior_wins_review"].astype(int).eq(0)]
    credited = shortlist.copy()
    credited["prior_wins_review"] = credited["prior_wins_review"].astype(int) + credited["lookalike_extra_wins"].astype(int)
    credited_zero = credited.loc[credited["prior_wins_review"].eq(0)]
    return {
        "projects": project_table,
        "applicants": applicants,
        "rates": rates,
        "application_ranks": application_rank_table(applicants),
        "field": field_summary(project_table),
        "historical": historical_coverage(shortlists),
        "shortlist_excess": seat_excess(shortlist, "shortlisted", "prior_wins_review"),
        "rank_excess": seat_excess(ranked, "rank1", "prior_wins_interview"),
        "selective_shortlist_rate": _rate_row(selective, "application_to_shortlist", "overall", "projects that did not interview everyone", "shortlisted") if len(selective) else {},
        "zero_prior_shortlist": _rate_row(zero, "application_to_shortlist", "sensitivity", "stored id, no earlier rank-1", "shortlisted") if len(zero) else {},
        "zero_prior_shortlist_if_lookalikes_credited": _rate_row(credited_zero, "application_to_shortlist", "sensitivity", "lookalike history credited, no earlier rank-1", "shortlisted") if len(credited_zero) else {},
        "rows_whose_prior_wins_change_if_lookalikes_are_credited": int(((applicants["prior_wins_review"].astype(int) == 0) & applicants["lookalike_extra_wins"].astype(int).gt(0)).sum()),
        "selective_shortlist_excess": seat_excess(selective, "shortlisted", "prior_wins_review"),
        "shortlist_without_disqualified": _rate_row(shortlist.loc[shortlist["disqualified"].astype(int).eq(0)], "application_to_shortlist", "sensitivity", "disqualified applicants removed", "shortlisted") if len(shortlist) else {},
        "experience_cross": experience_cross(applicants),
        "geography_boundary": geography_boundary(applicants, firms),
    }


def write_outputs(outputs: dict, processed, reports) -> None:
    processed.mkdir(parents=True, exist_ok=True)
    figures = reports / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    outputs["projects"].to_csv(processed / "selection_stage_projects.csv", index=False)
    outputs["applicants"].to_csv(processed / "selection_stage_applicants.csv", index=False)
    outputs["rates"].to_csv(processed / "selection_stage_rates.csv", index=False)
    outputs["application_ranks"].to_csv(processed / "selection_stage_application_ranks.csv", index=False)
    outputs["experience_cross"].to_csv(processed / "selection_stage_experience_cross.csv", index=False)
    outputs["geography_boundary"].to_csv(processed / "selection_stage_geography_boundary.csv", index=False)
    summary = {
        "field": outputs["field"],
        "historical_unranked_lists": outputs["historical"],
        "shortlist_excess": outputs["shortlist_excess"],
        "rank_excess": outputs["rank_excess"],
        "selective_shortlist_rate": outputs["selective_shortlist_rate"],
        "zero_prior_shortlist": outputs["zero_prior_shortlist"],
        "zero_prior_shortlist_if_lookalikes_credited": outputs["zero_prior_shortlist_if_lookalikes_credited"],
        "rows_whose_prior_wins_change_if_lookalikes_are_credited": outputs["rows_whose_prior_wins_change_if_lookalikes_are_credited"],
        "selective_shortlist_excess": outputs["selective_shortlist_excess"],
        "shortlist_without_disqualified": outputs["shortlist_without_disqualified"],
    }
    (processed / "selection_stage_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _figures(outputs, figures)


def _figures(outputs: dict, figures) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "axes.spines.top": False, "axes.spines.right": False, "font.size": 11})
    projects = outputs["projects"]
    interviewed = projects.loc[projects["status"].isin(["interview_ranked", "interview_unfinished"])].copy()
    interviewed["applicants"] = interviewed["applicants"].astype(int)
    interviewed["shortlist_size"] = interviewed["shortlist_size"].astype(int)
    counts = interviewed.groupby(["applicants", "shortlist_size"]).size().reset_index(name="projects")
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    ax.scatter(counts["applicants"], counts["shortlist_size"], s=50 + counts["projects"] * 28, color="#0072B2", zorder=3)
    for _, point in counts.iterrows():
        if int(point["projects"]) > 1:
            ax.text(point["applicants"] + 0.18, point["shortlist_size"] + 0.12, str(int(point["projects"])), fontsize=9, color="#222222")
    limit = int(max(interviewed["applicants"].max(), interviewed["shortlist_size"].max()) + 1)
    ax.plot([0, limit], [0, limit], color="#888888", lw=1)
    ax.set_xlim(0, limit)
    ax.set_ylim(0, limit)
    ax.set_xlabel("Applicants")
    ax.set_ylabel("Firms on the interview list")
    ax.set_title("Applicants and the interview list, 2025–2026")
    fig.text(0.01, 0.01, "Marker size and the printed count are the number of projects at that point. The line is equal counts. 2026 is partial.", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(figures / "04_applicants_and_interviews.png", dpi=150)
    plt.close(fig)

    rates = outputs["rates"]
    order = ["0", "1-2", "3 or more"]
    stages = [
        ("application_to_shortlist", "Interviewed", "#0072B2"),
        ("shortlist_to_rank1", "Rank 1, if interviewed", "#D55E00"),
    ]
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    width = 0.36
    x = np.arange(len(order))
    for offset, (stage, label, color) in zip((-width / 2, width / 2), stages):
        part = rates.loc[rates["stage"].eq(stage) & rates["group_family"].eq("earlier_rank1_results")].set_index("group").reindex(order)
        ax.bar(x + offset, part["rate"] * 100, width=width, color=color, label=label)
        ax.errorbar(
            x + offset,
            part["rate"] * 100,
            yerr=[(part["rate"] - part["rate_low"]) * 100, (part["rate_high"] - part["rate"]) * 100],
            fmt="none",
            ecolor="#222222",
            capsize=3,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(["None", "1–2", "3 or more"])
    ax.set_ylim(0, 100)
    ax.set_xlabel("Earlier rank-1 results in this archive")
    ax.set_ylabel("Rate (%)")
    ax.set_title("Chart stages by earlier rank-1 results")
    ax.legend(frameon=False)
    fig.text(0.01, 0.01, "Intervals resample projects. Rank 1 uses completed interview lists. 2026 is partial.", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(figures / "04_stages_by_prior_wins.png", dpi=150)
    plt.close(fig)
