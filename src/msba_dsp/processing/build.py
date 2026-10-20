"""Build the relational research tables from parsed public snapshots."""

from __future__ import annotations

import re
from collections import defaultdict

import numpy as np
import pandas as pd

from msba_dsp.config import BASE_URL, PROCESSED, REFERENCE
from msba_dsp.processing.names import clean_display, resolve_firm

PERIOD_URLS = {
    "2007-2009": f"{BASE_URL}/building/team/dsp/meeting_results/2007-2009",
    "2010-2014": f"{BASE_URL}/building/team/dsp/meeting_results/2010-2014",
    "2015-2018": f"{BASE_URL}/building/team/dsp/meeting_results/2015-2018",
    "2019-2024": f"{BASE_URL}/building/team/dsp/meeting_results/2019-2024",
}
CHART_URL = (
    f"{BASE_URL}/sites/default/files/edit-contentfiles/DSP/"
    "DSP_Meeting_Results_Chart_October9.xlsx"
)

GRADE_RULES: list[tuple[str, str]] = [
    ("elementary", r"elementary|\bprimary\b|\bes\b"),
    ("middle", r"middle|\bintermediate\b|\bms\b"),
    ("high", r"high school|\bsenior high\b|\bhs\b"),
    ("vocational", r"vocational|\btechnical high\b"),
]


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED / name, dtype=str, keep_default_na=False)


def school_category(school_name: str) -> str:
    text = school_name.lower().replace("–", " ").replace("—", " ")
    found = [label for label, pattern in GRADE_RULES if re.search(pattern, text)]
    if re.search(r"\bk\s*[-–]\s*8\b|\bpk\s*[-–]\s*8\b|\bpre-?k\s*[-–]\s*8\b", text):
        found.append("mixed")
    unique = list(dict.fromkeys(found))
    if len(unique) > 1:
        return "mixed"
    if len(unique) == 1:
        return unique[0]
    if "school" in text:
        return "unspecified"
    return "unknown"


def clean_project_label(label: str) -> str:
    """Drop a scheduling sentence when the school name is published after it."""
    text = re.sub(r"\s+", " ", label).strip()
    if re.search(r"interview|will be held|will be conducted", text, re.IGNORECASE) and ". " in text:
        tail = text.split(". ")[-1].strip()
        if re.search(r"school|elementary|middle|\bhigh\b", tail, re.IGNORECASE) and len(tail) < 180:
            return tail
    return text


def split_project_label(label: str) -> tuple[str, str]:
    text = clean_project_label(label)
    text = re.sub(r"\s+", " ", text.replace("–", "-").replace("—", "-")).strip()
    if not text:
        return "", ""
    if "," in text:
        parts = [part.strip() for part in text.split(",") if part.strip()]
        if len(parts) >= 2 and parts[-1].upper() in {"MA", "MASS", "MASSACHUSETTS"}:
            parts = parts[:-1]
        if len(parts) >= 2:
            return parts[1], parts[0]
    if " - " in text:
        left, right = [part.strip() for part in text.split(" - ", 1)]
        return left, right
    return "", text


def parse_cost_range(text: str) -> tuple[float | None, float | None]:
    if not text or not re.search(r"\d", text):
        return None, None
    amounts: list[float] = []
    for match in re.finditer(
        r"([0-9]+(?:\.[0-9]+)?)\s*(billion|million|m)?",
        text.lower().replace(",", ""),
    ):
        value = float(match.group(1))
        unit = match.group(2) or ""
        if unit in {"million", "m"}:
            value *= 1_000_000
        elif unit == "billion":
            value *= 1_000_000_000
        elif value < 10_000:
            # The chart writes school budgets in millions. A bare small number
            # without a unit is not treated as dollars.
            continue
        amounts.append(value)
    if not amounts:
        return None, None
    return min(amounts), max(amounts)


def _project_id(school: str, district: str, year: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", f"{district} {school} {year}".lower()).strip("-")
    return f"p_{slug[:80]}"


def _selection_id(date: str, project_id: str, round_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", f"{date} {project_id} {round_name}".lower()).strip("-")
    return f"s_{slug[:100]}"


def _hhi(firm_ids: list[str]) -> str:
    if not firm_ids:
        return ""
    counts = pd.Series(firm_ids).value_counts()
    shares = counts / float(counts.sum())
    return f"{float((shares**2).sum()):.6f}"


def _rank_value(value: str) -> float | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _prepare_competitors(raw_rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(raw_rows)
    if frame.empty:
        return frame
    resolved = frame["firm_raw"].map(resolve_firm)
    frame["firm_id"] = resolved.map(lambda item: item.firm_id)
    frame["canonical_key"] = resolved.map(lambda item: item.canonical_key)
    frame["joint_venture"] = resolved.map(lambda item: item.joint_venture)
    frame["declined"] = resolved.map(lambda item: item.declined)
    frame["tie_record"] = resolved.map(lambda item: item.tie_record)
    frame["match_method"] = resolved.map(lambda item: item.method)
    frame["match_confidence"] = resolved.map(lambda item: item.confidence)
    frame["firm_display_raw"] = frame["firm_raw"].map(clean_display)
    return frame


def _finalize_choice_sets(competitors: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate firms and mark which competitions have one winner."""
    if competitors.empty:
        return competitors
    competitors = competitors.loc[~competitors["tie_record"]].copy()
    competitors = competitors.loc[competitors["canonical_key"] != ""].copy()
    competitors["rank_num"] = competitors["published_rank"].map(_rank_value)
    competitors = competitors.sort_values(
        ["selection_id", "rank_num", "source_order"],
        kind="mergesort",
        na_position="last",
    )
    competitors = competitors.drop_duplicates(["selection_id", "firm_id"], keep="first")

    flags: list[str] = []
    winners: list[int] = []
    keep_ids: set[str] = set()
    for selection_id, group in competitors.groupby("selection_id", sort=False):
        ranks = group["rank_num"].tolist()
        if any(rank is None or (isinstance(rank, float) and np.isnan(rank)) for rank in ranks):
            flags.extend(["incomplete_rank"] * len(group))
            winners.extend([0] * len(group))
            continue
        if len(group) < 2:
            flags.extend(["single_firm"] * len(group))
            winners.extend([0] * len(group))
            continue
        best = min(ranks)
        n_best = sum(rank == best for rank in ranks)
        if n_best != 1:
            flags.extend(["tied_winner"] * len(group))
            winners.extend([0] * len(group))
            continue
        if bool(group.loc[group["rank_num"] == best, "declined"].iloc[0]):
            flags.extend(["winner_declined"] * len(group))
            winners.extend([0] * len(group))
            continue
        keep_ids.add(selection_id)
        for _, row in group.iterrows():
            flags.append("model_sample")
            winners.append(int(row["rank_num"] == best))
    competitors["choice_status"] = flags
    competitors["winner"] = winners
    competitors["in_model_sample"] = competitors["selection_id"].isin(keep_ids)
    return competitors


def historical_competitions(archive: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    finals = archive.loc[archive["list_kind"].isin(["final_ranking", "award"])].copy()
    finals["_order"] = np.arange(len(finals))
    competitor_rows: list[dict] = []
    event_rows: list[dict] = []
    project_rows: list[dict] = []
    seen_events: set[str] = set()

    for (meeting_date, project), group in finals.groupby(["meeting_date", "project"], sort=False):
        group = group.sort_values("_order", kind="mergesort")
        label = str(project).strip()
        if not label or not meeting_date:
            continue
        district, school = split_project_label(label)
        year = meeting_date[:4]
        category = school_category(school or label)
        project_id = _project_id(school or label, district, year)
        selection_id = _selection_id(meeting_date, project_id, "final")
        positions = [_rank_value(value) for value in group["position"]]
        explicit = all(position is not None for position in positions)
        if explicit:
            rank_method = "explicit_number"
        elif all(position is None for position in positions):
            rank_method = "published_list_order"
            positions = [float(i) for i in range(1, len(group) + 1)]
        else:
            rank_method = "partial_numbers"
        period = str(group["source_period"].iloc[0])
        source_url = PERIOD_URLS.get(period, "")
        if selection_id not in seen_events:
            event_rows.append(
                {
                    "selection_id": selection_id,
                    "project_id": project_id,
                    "selection_date": meeting_date,
                    "selection_year": year,
                    "selection_round": "final_ranking",
                    "rank_method": rank_method,
                    "source_url": source_url,
                    "source_name": f"DSP results {period}",
                    "district": district,
                    "school_name": school or label,
                    "project_label": f"{district} - {school or label}".strip(" -"),
                    "school_category": category,
                    "estimated_cost_low": "",
                    "estimated_cost_high": "",
                    "comments": "",
                }
            )
            project_rows.append(
                {
                    "project_id": project_id,
                    "district": district,
                    "school_name": school or label,
                    "municipality": district,
                    "grade_configuration": "",
                    "school_category": category,
                    "project_type": "",
                    "construction_scope": "",
                    "estimated_construction_cost": "",
                    "project_square_footage": "",
                    "planned_student_capacity": "",
                    "project_status": "designer_selection_published",
                    "source_url": source_url,
                }
            )
            seen_events.add(selection_id)
        for offset, (_, row) in enumerate(group.iterrows()):
            competitor_rows.append(
                {
                    "selection_id": selection_id,
                    "project_id": project_id,
                    "firm_raw": row["firm_raw"],
                    "published_rank": "" if positions[offset] is None else str(int(positions[offset])),
                    "finalist_status": "finalist",
                    "source_order": int(row["_order"]),
                    "stage": "final_ranking",
                }
            )

    shortlist = archive.loc[
        archive["list_kind"].isin(["unranked_applicants", "interview_list", "qualified_applicant"])
    ].copy()
    short_rows: list[dict] = []
    for _, row in shortlist.iterrows():
        if not row["project"] or not row["meeting_date"]:
            continue
        district, school = split_project_label(row["project"])
        short_rows.append(
            {
                "meeting_date": row["meeting_date"],
                "project_label": row["project"],
                "district": district,
                "school_name": school or row["project"],
                "list_kind": row["list_kind"],
                "firm_raw": row["firm_raw"],
                "source_url": PERIOD_URLS.get(row["source_period"], ""),
            }
        )
    competitors = _finalize_choice_sets(_prepare_competitors(competitor_rows))
    return pd.DataFrame(event_rows), competitors, pd.DataFrame(short_rows)


def chart_competitions(projects: pd.DataFrame, firms: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    event_rows: list[dict] = []
    competitor_rows: list[dict] = []
    order = 0
    for _, project in projects.iterrows():
        if project["status_note"].strip():
            continue
        project_firms = firms.loc[firms["project_id"] == project["project_id"]]
        finals = project_firms.loc[project_firms["stage"] == "final"]
        applicants = project_firms.loc[project_firms["stage"] == "application"]
        comments = project["comments"]
        no_interview = "no interview" in comments.lower()
        if len(finals):
            use = finals
            round_name = "chart_final_ranking"
            date = project["interview_date"] or project["application_review_date"]
        elif no_interview and len(applicants):
            use = applicants
            round_name = "application_ranking_no_interview"
            date = project["application_review_date"]
        else:
            continue
        if not date:
            continue
        low, high = parse_cost_range(project["est_construction_cost"])
        district = project["district"]
        school = project["school"]
        year = date[:4]
        project_id = _project_id(school, district, year)
        selection_id = _selection_id(date, project_id, round_name)
        category = school_category(school)
        cost_text = project["est_construction_cost"]
        event_rows.append(
            {
                "selection_id": selection_id,
                "project_id": project_id,
                "selection_date": date,
                "selection_year": year,
                "selection_round": round_name,
                "rank_method": "chart_rank",
                "source_url": CHART_URL,
                "source_name": "DSP meeting result chart 2025-2026",
                "district": district,
                "school_name": school,
                "project_label": f"{district} - {school}".strip(" -"),
                "school_category": category,
                "estimated_cost_low": "" if low is None else f"{low:.0f}",
                "estimated_cost_high": "" if high is None else f"{high:.0f}",
                "comments": comments,
            }
        )
        for _, firm in use.iterrows():
            order += 1
            competitor_rows.append(
                {
                    "selection_id": selection_id,
                    "project_id": project_id,
                    "firm_raw": firm["firm_raw"],
                    "published_rank": firm["rank"],
                    "finalist_status": "finalist" if round_name != "application_ranking_no_interview" else "applicant_ranked_without_interview",
                    "source_order": order,
                    "stage": round_name,
                }
            )
        # Applicants who were not on the final list are retained as non-finalists
        # for the 2025-2026 chart only. They are not in the winner model.
        if len(finals):
            final_names = set(finals["firm_raw"])
            for _, firm in applicants.iterrows():
                if firm["firm_raw"] in final_names:
                    continue
                order += 1
                competitor_rows.append(
                    {
                        "selection_id": selection_id + "_applicants",
                        "project_id": project_id,
                        "firm_raw": firm["firm_raw"],
                        "published_rank": firm["rank"],
                        "finalist_status": "applicant_not_shortlisted",
                        "source_order": order,
                        "stage": "application",
                    }
                )
    competitors = _prepare_competitors(competitor_rows)
    if competitors.empty:
        return pd.DataFrame(event_rows), competitors
    model_mask = competitors["finalist_status"] != "applicant_not_shortlisted"
    finalized = _finalize_choice_sets(competitors.loc[model_mask].copy())
    others = competitors.loc[~model_mask].copy()
    if not others.empty:
        others["rank_num"] = others["published_rank"].map(_rank_value)
        others["choice_status"] = "applicant_pool_only"
        others["winner"] = 0
        others["in_model_sample"] = False
        finalized = pd.concat([finalized, others], ignore_index=True)
    return pd.DataFrame(event_rows), finalized


def _mode_name(values: pd.Series) -> str:
    cleaned = [value for value in values if value]
    if not cleaned:
        return ""
    return pd.Series(cleaned).value_counts().index[0]


def firm_directory(competitors: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict] = []
    audits: list[dict] = []
    if competitors.empty:
        return pd.DataFrame(), pd.DataFrame()
    for firm_id, group in competitors.groupby("firm_id", sort=False):
        raw_names = sorted(set(group["firm_raw"]))
        rows.append(
            {
                "firm_id": firm_id,
                "canonical_firm_name": _mode_name(group["firm_display_raw"]),
                "canonical_key": group["canonical_key"].iloc[0],
                "historical_names": " | ".join(raw_names),
                "documented_mergers": "",
                "public_headquarters_location": "",
                "verified_founding_year": "",
                "published_specializations": "",
                "joint_venture": str(bool(group["joint_venture"].iloc[0])),
                "match_method": group["match_method"].iloc[0],
                "match_confidence": group["match_confidence"].iloc[0],
                "source_url": "",
                "name_count": len(raw_names),
            }
        )
        for raw_name in raw_names:
            audits.append(
                {
                    "firm_raw": raw_name,
                    "firm_id": firm_id,
                    "canonical_key": group["canonical_key"].iloc[0],
                    "match_method": group["match_method"].iloc[0],
                    "match_confidence": group["match_confidence"].iloc[0],
                    "joint_venture": str(bool(group["joint_venture"].iloc[0])),
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(audits)


COMPANY_COLUMNS = [
    "staff_size",
    "staff_basis",
    "staff_asof",
    "founded_year",
    "age_at_first_seen_years",
    "age_as_of_2026",
    "geographic_scope",
    "nationwide_operations",
    "hq_location",
    "boston_role",
    "company_source_url",
    "company_source_url_2",
    "verification_status",
    "research_note",
]
WIN_COLUMNS = [
    "ranked_selections",
    "wins",
    "win_rate",
    "avg_win_interval_years",
    "tries_before_first_win",
    "first_ranked",
    "last_ranked",
]


def _blank(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none"} else text


def _whole_number(value: object) -> str:
    text = _blank(value)
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return str(int(number))
    return text


def firm_ranking_record(competitors: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """One completed ranking per firm per project. Rank 1 is a win."""
    empty = pd.DataFrame(columns=["firm_id", *WIN_COLUMNS])
    if competitors.empty or events.empty:
        return empty
    counted = competitors.loc[competitors["choice_status"].isin(["model_sample", "single_firm"])].copy()
    if counted.empty:
        return empty
    counted = counted.drop_duplicates(["project_id", "firm_id"], keep="first")
    dates = events.set_index("selection_id")["selection_date"]
    counted["selection_date"] = counted["selection_id"].map(dates)
    counted = counted.loc[counted["selection_date"].fillna("") != ""].copy()
    counted["selection_date"] = pd.to_datetime(counted["selection_date"])
    rank_text = counted["rank_num"].map(_blank)
    counted["won"] = (counted["winner"].map(_blank) == "1") | (
        (counted["choice_status"] == "single_firm") & rank_text.isin(["1", "1.0"])
    )
    records: list[dict] = []
    for firm_id, group in counted.groupby("firm_id", sort=False):
        ordered = group.sort_values(["selection_date", "selection_id"], kind="mergesort")
        wins = ordered.loc[ordered["won"]]
        gaps = []
        win_dates = wins["selection_date"].tolist()
        for earlier, later in zip(win_dates, win_dates[1:]):
            gaps.append((later - earlier).days / 365.25)
        if len(wins):
            first = wins.iloc[0]
            first_key = (first["selection_date"], first["selection_id"])
            tries_before = int(
                sum(
                    (date, selection_id) < first_key
                    for date, selection_id in zip(ordered["selection_date"], ordered["selection_id"])
                )
            )
        else:
            tries_before = ""
        records.append(
            {
                "firm_id": firm_id,
                "ranked_selections": int(len(ordered)),
                "wins": int(len(wins)),
                "win_rate": f"{len(wins) / len(ordered):.4f}",
                "avg_win_interval_years": f"{sum(gaps) / len(gaps):.2f}" if gaps else "",
                "tries_before_first_win": tries_before,
                "first_ranked": ordered["selection_date"].iloc[0].date().isoformat(),
                "last_ranked": ordered["selection_date"].iloc[-1].date().isoformat(),
            }
        )
    return pd.DataFrame(records)


def _profile_score(row: pd.Series, canonical_name: str) -> tuple:
    verified = _blank(row.get("verification_status")).startswith("Verified")
    exact = _blank(row.get("source_firm_name")).casefold() == canonical_name.casefold()
    filled = sum(bool(_blank(row.get(column))) for column in ("staff_size", "hq_location", "founded_year"))
    return (exact, verified, filled)


def enrich_firm_directory(
    firms: pd.DataFrame,
    competitors: pd.DataFrame,
    events: pd.DataFrame,
) -> pd.DataFrame:
    """Add company profile and completed-ranking record onto the firm directory."""
    directory = firms.copy()
    directory = directory.drop(columns=[column for column in [*COMPANY_COLUMNS, *WIN_COLUMNS] if column in directory.columns])
    company_path = REFERENCE / "firm_company.csv"
    if company_path.exists() and len(directory):
        company = pd.read_csv(company_path, dtype=str, keep_default_na=False)
        chosen_rows: list[dict] = []
        for firm_id, group in company.groupby("firm_id", sort=False):
            if _blank(firm_id):
                canonical = ""
                match = directory.loc[directory["firm_id"] == firm_id, "canonical_firm_name"]
                if len(match):
                    canonical = match.iloc[0]
                ordered = sorted(group.to_dict("records"), key=lambda row: _profile_score(pd.Series(row), canonical), reverse=True)
                chosen = dict(ordered[0])
                notes = [_blank(chosen.get("research_note"))]
                for other in ordered[1:]:
                    different = [
                        column
                        for column in ("staff_size", "hq_location", "founded_year")
                        if _blank(other.get(column)) and _blank(other.get(column)) != _blank(chosen.get(column))
                    ]
                    if different:
                        notes.append(
                            f"Also recorded as {_blank(other.get('source_firm_name'))}: "
                            + ", ".join(f"{column} {_blank(other.get(column))}" for column in different)
                            + "."
                        )
                chosen["research_note"] = " ".join(note for note in notes if note)
                chosen_rows.append(chosen)
        if chosen_rows:
            chosen_frame = pd.DataFrame(chosen_rows)
            keep = ["firm_id", *COMPANY_COLUMNS]
            directory = directory.merge(chosen_frame[keep], on="firm_id", how="left")
            missing_hq = directory["public_headquarters_location"].map(_blank) == ""
            directory.loc[missing_hq, "public_headquarters_location"] = directory.loc[missing_hq, "hq_location"].map(_blank)
            missing_year = directory["verified_founding_year"].map(_blank) == ""
            directory.loc[missing_year, "verified_founding_year"] = directory.loc[missing_year, "founded_year"].map(_whole_number)
    else:
        for column in COMPANY_COLUMNS:
            directory[column] = ""
    for column in COMPANY_COLUMNS:
        if column not in directory.columns:
            directory[column] = ""
        directory[column] = directory[column].map(_blank if column not in {"founded_year", "age_at_first_seen_years", "age_as_of_2026"} else _whole_number)

    record = firm_ranking_record(competitors, events)
    directory = directory.drop(columns=[column for column in WIN_COLUMNS if column in directory.columns])
    directory = directory.merge(record, on="firm_id", how="left")
    for column in ("ranked_selections", "wins", "tries_before_first_win"):
        directory[column] = directory[column].map(_whole_number)
    for column in ("win_rate", "avg_win_interval_years", "first_ranked", "last_ranked"):
        directory[column] = directory[column].map(_blank)
    return directory


def cost_table(events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for _, event in events.iterrows():
        if not event["estimated_cost_low"]:
            continue
        low = float(event["estimated_cost_low"])
        high = float(event["estimated_cost_high"])
        rows.append(
            {
                "project_id": event["project_id"],
                "cost_type": "published_preselection_range_midpoint",
                "cost_amount": f"{(low + high) / 2:.0f}",
                "cost_low": f"{low:.0f}",
                "cost_high": f"{high:.0f}",
                "project_phase": "preselection",
                "observation_date": event["selection_date"],
                "construction_cost_per_square_foot": "",
                "source_url": event["source_url"],
                "notes": "Midpoint of the range printed on the DSP chart. Not a bid, a schematic budget, or a final cost.",
            }
        )
    return pd.DataFrame(rows)


def add_decision_date_features(competitors: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Experience features use only selections on earlier calendar dates."""
    model = competitors.loc[competitors["in_model_sample"]].copy()
    meta = events.set_index("selection_id")
    model = model.join(
        meta[
            [
                "selection_date",
                "selection_year",
                "school_category",
                "district",
                "school_name",
                "source_url",
                "rank_method",
                "selection_round",
                "estimated_cost_low",
                "estimated_cost_high",
                "project_label",
            ]
        ],
        on="selection_id",
    )
    model["selection_year"] = model["selection_year"].astype(int)
    model = model.sort_values(["selection_date", "selection_id", "rank_num"], kind="mergesort")

    wins: dict[str, int] = defaultdict(int)
    finals: dict[str, int] = defaultdict(int)
    grade_wins: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    last_win: dict[str, str] = {}
    win_dates: dict[str, list[pd.Timestamp]] = defaultdict(list)
    recent_winners: list[tuple[pd.Timestamp, str]] = []
    feature_rows: list[dict] = []

    for selection_date, day in model.groupby("selection_date", sort=False):
        day_records: list[dict] = []
        for selection_id, group in day.groupby("selection_id", sort=False):
            category = str(group["school_category"].iloc[0])
            n_finalists = int(len(group))
            as_of = pd.Timestamp(selection_date)
            window_start = as_of - pd.DateOffset(years=3)
            recent = [(when, firm_id) for when, firm_id in recent_winners if window_start <= when < as_of]
            recent_hhi = _hhi([firm_id for _, firm_id in recent])
            for _, row in group.iterrows():
                firm_id = row["firm_id"]
                prior_w = wins[firm_id]
                prior_f = finals[firm_id]
                grade_w = grade_wins[firm_id][category] if category in {"elementary", "middle", "high", "vocational"} else 0
                wins_previous_3y = sum(1 for when in win_dates[firm_id] if window_start <= when < as_of)
                previous = last_win.get(firm_id, "")
                years_since = ""
                if previous:
                    years_since = f"{(pd.Timestamp(selection_date) - pd.Timestamp(previous)).days / 365.25:.3f}"
                low = row["estimated_cost_low"]
                high = row["estimated_cost_high"]
                midpoint = ""
                if low and high:
                    midpoint = f"{(float(low) + float(high)) / 2:.0f}"
                day_records.append(
                    {
                        "selection_id": selection_id,
                        "project_id": row["project_id"],
                        "selection_date": selection_date,
                        "selection_year": int(row["selection_year"]),
                        "firm_id": firm_id,
                        "firm_raw": row["firm_raw"],
                        "canonical_key": row["canonical_key"],
                        "published_rank": int(row["rank_num"]),
                        "winner": int(row["winner"]),
                        "n_finalists": n_finalists,
                        "school_category": category,
                        "district": row["district"],
                        "school_name": row["school_name"],
                        "project_label": row["project_label"],
                        "prior_wins": prior_w,
                        "prior_finals": prior_f,
                        "prior_grade_wins": grade_w,
                        "wins_previous_3y": wins_previous_3y,
                        "recent_award_hhi": recent_hhi,
                        "years_since_previous_win": years_since,
                        "newcomer": int(prior_f == 0),
                        "joint_venture": bool(row["joint_venture"]),
                        "budget_mid": midpoint,
                        "source_url": row["source_url"],
                        "rank_method": row["rank_method"],
                        "selection_round": row["selection_round"],
                        "match_confidence": row["match_confidence"],
                    }
                )
        feature_rows.extend(day_records)
        for record in day_records:
            firm_id = record["firm_id"]
            finals[firm_id] += 1
            if record["winner"] == 1:
                wins[firm_id] += 1
                last_win[firm_id] = str(selection_date)
                win_dates[firm_id].append(pd.Timestamp(selection_date))
                recent_winners.append((pd.Timestamp(selection_date), firm_id))
                category = record["school_category"]
                if category in {"elementary", "middle", "high", "vocational"}:
                    grade_wins[firm_id][category] += 1

    featured = pd.DataFrame(feature_rows)
    if featured.empty:
        return featured
    first_date = pd.Timestamp(featured["selection_date"].min())
    featured["history_depth_years"] = (
        (pd.to_datetime(featured["selection_date"]) - first_date).dt.days / 365.25
    ).round(3)
    return featured


def near_duplicate_report(firms: pd.DataFrame) -> pd.DataFrame:
    """Token-overlap pairs that were deliberately left unmerged."""
    singles = firms.loc[firms["joint_venture"] == "False", ["firm_id", "canonical_firm_name", "canonical_key"]]
    records = singles.to_dict("records")
    rows: list[dict] = []
    for i, left in enumerate(records):
        left_tokens = set(str(left["canonical_key"]).split())
        if len(left_tokens) < 2:
            continue
        for right in records[i + 1 :]:
            right_tokens = set(str(right["canonical_key"]).split())
            union = left_tokens | right_tokens
            if not union:
                continue
            score = len(left_tokens & right_tokens) / len(union)
            if score >= 0.6:
                rows.append(
                    {
                        "firm_a": left["canonical_firm_name"],
                        "firm_b": right["canonical_firm_name"],
                        "token_jaccard": round(score, 3),
                        "action": "not_merged",
                    }
                )
    return pd.DataFrame(rows)


def quality_summary(
    archive: pd.DataFrame,
    events: pd.DataFrame,
    competitors: pd.DataFrame,
    featured: pd.DataFrame,
    firms: pd.DataFrame,
    costs: pd.DataFrame,
    aliases: pd.DataFrame,
) -> dict[str, int | float]:
    model_events = featured["selection_id"].nunique() if len(featured) else 0
    return {
        "archive_firm_rows": int(len(archive)),
        "projects_identified": int(events["project_id"].nunique()) if len(events) else 0,
        "selection_events_identified": int(len(events)),
        "finalist_rows": int((competitors["finalist_status"] != "applicant_not_shortlisted").sum())
        if len(competitors)
        else 0,
        "firms_identified": int(len(firms)),
        "model_competitions": int(model_events),
        "model_finalist_rows": int(len(featured)),
        "competitions_explicit_rank": int((events["rank_method"] == "explicit_number").sum()) if len(events) else 0,
        "competitions_rank_inferred": int((events["rank_method"] == "published_list_order").sum())
        if len(events)
        else 0,
        "records_with_budget": int(costs["project_id"].nunique()) if len(costs) else 0,
        "records_with_grade": int(featured["school_category"].isin(["elementary", "middle", "high", "vocational"]).sum())
        if len(featured)
        else 0,
        "ambiguous_medium_confidence_firms": int((firms["match_confidence"] == "medium").sum()) if len(firms) else 0,
        "joint_ventures_kept_separate": int((firms["joint_venture"] == "True").sum()) if len(firms) else 0,
        "alias_rows": int(len(aliases)),
        "share_model_rows_with_grade": float(
            featured["school_category"].isin(["elementary", "middle", "high", "vocational"]).mean()
        )
        if len(featured)
        else 0.0,
        "share_model_rows_with_budget": float(featured["budget_mid"].ne("").mean()) if len(featured) else 0.0,
    }
