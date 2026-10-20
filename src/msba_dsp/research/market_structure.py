"""Market structure of published MSBA designer rankings.

The primary sample is the existing winner-model sample: a published ranking with
at least two firms and exactly one top-ranked firm. Rank 1 is the panel's order,
not a signed contract. Applicant lists, repair pools, and unfinished rankings
stay out of these counts.
"""

from __future__ import annotations

import json
from collections import Counter

import numpy as np
import pandas as pd

PARTIAL_YEAR = 2026
PERIODS: list[tuple[int, int, str]] = [
    (2007, 2011, "2007-2011"),
    (2012, 2016, "2012-2016"),
    (2017, 2021, "2017-2021"),
    (2022, 2026, "2022-2026"),
]
LEFT_CENSOR_END = 2011


def _truthy(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "1.0"})


def _blank(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return str(value).strip()


def concentration(winner_ids: list[str]) -> dict[str, float | int | None]:
    """Shares, HHI, and effective number of winners for one set of rank-1 outcomes."""
    winners = [firm_id for firm_id in winner_ids if firm_id]
    n = len(winners)
    if n == 0:
        return {
            "competitions": 0,
            "unique_winners": 0,
            "hhi": None,
            "effective_winners": None,
            "normalized_hhi": None,
            "top1_share": None,
            "top3_share": None,
            "top5_share": None,
            "top10_share": None,
        }
    counts = Counter(winners)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    shares = [count / n for _, count in ordered]
    hhi = float(sum(share * share for share in shares))
    n_winners = len(ordered)

    def top(k: int) -> float:
        return float(sum(count for _, count in ordered[:k]) / n)

    normalized = None
    if n_winners > 1:
        normalized = (hhi - 1.0 / n_winners) / (1.0 - 1.0 / n_winners)
    return {
        "competitions": n,
        "unique_winners": n_winners,
        "hhi": hhi,
        "effective_winners": 1.0 / hhi,
        "normalized_hhi": normalized,
        "top1_share": top(1),
        "top3_share": top(3),
        "top5_share": top(5),
        "top10_share": top(10),
    }


def participation_concentration(firm_ids: list[str]) -> dict[str, float | int | None]:
    """Concentration of finalist slots, counting each appearance once."""
    stats = concentration(firm_ids)
    return {
        "finalist_slots": stats["competitions"],
        "unique_finalists": stats["unique_winners"],
        "participation_hhi": stats["hhi"],
        "effective_finalists": stats["effective_winners"],
        "participation_normalized_hhi": stats["normalized_hhi"],
        "participation_top1_share": stats["top1_share"],
        "participation_top5_share": stats["top5_share"],
        "participation_top10_share": stats["top10_share"],
    }


def model_rows(competitors: pd.DataFrame, events: pd.DataFrame, firms: pd.DataFrame) -> pd.DataFrame:
    """One row per finalist in the existing multi-firm winner sample."""
    model = competitors.loc[_truthy(competitors["in_model_sample"])].copy()
    meta_columns = [
        "selection_date",
        "selection_year",
        "selection_round",
        "rank_method",
        "district",
        "school_name",
        "school_category",
        "project_label",
    ]
    meta = events[["selection_id", *meta_columns]].drop_duplicates("selection_id")
    model = model.merge(meta, on="selection_id", how="left")
    names = firms[["firm_id", "canonical_firm_name"]].drop_duplicates("firm_id")
    model = model.merge(names, on="firm_id", how="left")
    model["selection_year"] = model["selection_year"].astype(int)
    model["rank_num"] = pd.to_numeric(model["rank_num"], errors="coerce")
    model["is_winner"] = _truthy(model["winner"])
    model["is_joint_venture"] = _truthy(model["joint_venture"])
    return model.sort_values(["selection_date", "selection_id", "rank_num"], kind="mergesort")


def competition_table(rows: pd.DataFrame) -> pd.DataFrame:
    """One row per ranking, with the rank-1 firm and the size of the field."""
    records: list[dict] = []
    for selection_id, group in rows.groupby("selection_id", sort=False):
        winners = group.loc[group["is_winner"]]
        if len(winners) != 1:
            raise ValueError(f"{selection_id} has {len(winners)} winners in the model sample")
        winner = winners.iloc[0]
        records.append(
            {
                "selection_id": selection_id,
                "project_id": winner["project_id"],
                "selection_date": winner["selection_date"],
                "selection_year": int(winner["selection_year"]),
                "partial_year": int(winner["selection_year"]) == PARTIAL_YEAR,
                "n_finalists": int(len(group)),
                "winner_firm_id": winner["firm_id"],
                "winner_name": winner["canonical_firm_name"],
                "winner_is_joint_venture": bool(winner["is_joint_venture"]),
                "rank_method": winner["rank_method"],
                "selection_round": winner["selection_round"],
                "school_category": winner["school_category"],
                "district": winner["district"],
                "school_name": winner["school_name"],
            }
        )
    return pd.DataFrame(records)


def _window_row(label: str, competitions: pd.DataFrame, slots: pd.DataFrame, extra: dict | None = None) -> dict:
    winner_stats = concentration(competitions["winner_firm_id"].tolist())
    slot_stats = participation_concentration(slots["firm_id"].tolist()) if len(slots) else participation_concentration([])
    row = {
        "window": label,
        "competitions": winner_stats["competitions"],
        "unique_finalists": int(slots["firm_id"].nunique()) if len(slots) else 0,
        "unique_winners": winner_stats["unique_winners"],
        "hhi": _round(winner_stats["hhi"]),
        "effective_winners": _round(winner_stats["effective_winners"]),
        "normalized_hhi": _round(winner_stats["normalized_hhi"]),
        "top1_share": _round(winner_stats["top1_share"]),
        "top3_share": _round(winner_stats["top3_share"]),
        "top5_share": _round(winner_stats["top5_share"]),
        "top10_share": _round(winner_stats["top10_share"]),
        "participation_hhi": _round(slot_stats["participation_hhi"]),
        "effective_finalists": _round(slot_stats["effective_finalists"]),
        "participation_top5_share": _round(slot_stats["participation_top5_share"]),
        "participation_top10_share": _round(slot_stats["participation_top10_share"]),
        "mean_finalists": _round(float(competitions["n_finalists"].mean())) if len(competitions) else None,
    }
    if extra:
        row.update(extra)
    return row


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return round(float(value), digits)


def annual_table(competitions: pd.DataFrame, rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for year, group in competitions.groupby("selection_year"):
        slots = rows.loc[rows["selection_year"] == year]
        records.append(
            _window_row(
                str(int(year)),
                group,
                slots,
                {
                    "year": int(year),
                    "partial_year": bool(int(year) == PARTIAL_YEAR),
                    "first_date": group["selection_date"].min(),
                    "last_date": group["selection_date"].max(),
                },
            )
        )
    return pd.DataFrame(records)


def rolling_table(competitions: pd.DataFrame, rows: pd.DataFrame, width: int = 5) -> pd.DataFrame:
    years = sorted(int(year) for year in competitions["selection_year"].unique())
    if not years:
        return pd.DataFrame()
    records = []
    for start in range(min(years), max(years) - width + 2):
        end = start + width - 1
        group = competitions.loc[competitions["selection_year"].between(start, end)]
        if group.empty:
            continue
        slots = rows.loc[rows["selection_year"].between(start, end)]
        records.append(
            _window_row(
                f"{start}-{end}",
                group,
                slots,
                {
                    "year_start": start,
                    "year_end": end,
                    "contains_partial_year": bool(end >= PARTIAL_YEAR and start <= PARTIAL_YEAR),
                },
            )
        )
    return pd.DataFrame(records)


def _resample_stat(values: list, stat, draws: int, rng: np.random.Generator) -> np.ndarray:
    index = np.arange(len(values))
    samples = np.empty(draws, dtype=float)
    for draw in range(draws):
        take = rng.choice(index, size=len(values), replace=True)
        samples[draw] = stat([values[i] for i in take])
    return samples


def period_contrasts(competitions: pd.DataFrame, draws: int = 2000, seed: int = 20261020) -> dict:
    """Resample two complete periods separately and compare their statistics.

    The concentration contrast uses 2007-2011 against 2017-2021. The field-size
    contrast uses 2009-2016 against 2018-2025 so the partial 2026 year is not
    in either group.
    """
    rng = np.random.default_rng(seed)
    early = competitions.loc[competitions["selection_year"].between(2007, 2011), "winner_firm_id"].tolist()
    late = competitions.loc[competitions["selection_year"].between(2017, 2021), "winner_firm_id"].tolist()
    early_top = _resample_stat(early, lambda sample: concentration(sample)["top5_share"], draws, rng)
    late_top = _resample_stat(late, lambda sample: concentration(sample)["top5_share"], draws, rng)
    early_hhi = _resample_stat(early, lambda sample: concentration(sample)["hhi"], draws, rng)
    late_hhi = _resample_stat(late, lambda sample: concentration(sample)["hhi"], draws, rng)
    top_diff = early_top - late_top
    hhi_diff = early_hhi - late_hhi
    early_fields = competitions.loc[competitions["selection_year"].between(2009, 2016)]
    late_fields = competitions.loc[competitions["selection_year"].between(2018, 2025)]
    early_two = early_fields["n_finalists"].eq(2).astype(float).tolist()
    late_two = late_fields["n_finalists"].eq(2).astype(float).tolist()
    two_diff = _resample_stat(late_two, np.mean, draws, rng) - _resample_stat(early_two, np.mean, draws, rng)
    point_top = concentration(early)["top5_share"] - concentration(late)["top5_share"]
    point_hhi = concentration(early)["hhi"] - concentration(late)["hhi"]
    point_two = float(np.mean(late_two) - np.mean(early_two))
    return {
        "draws": draws,
        "top5_early_window": "2007-2011",
        "top5_late_window": "2017-2021",
        "top5_early": _round(concentration(early)["top5_share"]),
        "top5_late": _round(concentration(late)["top5_share"]),
        "top5_difference": _round(point_top),
        "top5_difference_low": _round(float(np.quantile(top_diff, 0.025))),
        "top5_difference_high": _round(float(np.quantile(top_diff, 0.975))),
        "hhi_difference": _round(point_hhi),
        "hhi_difference_low": _round(float(np.quantile(hhi_diff, 0.025))),
        "hhi_difference_high": _round(float(np.quantile(hhi_diff, 0.975))),
        "two_firm_early_window": "2009-2016",
        "two_firm_late_window": "2018-2025",
        "two_firm_early_competitions": int(len(early_two)),
        "two_firm_late_competitions": int(len(late_two)),
        "two_firm_early_share": _round(float(np.mean(early_two))),
        "two_firm_late_share": _round(float(np.mean(late_two))),
        "two_firm_difference": _round(point_two),
        "two_firm_difference_low": _round(float(np.quantile(two_diff, 0.025))),
        "two_firm_difference_high": _round(float(np.quantile(two_diff, 0.975))),
    }


def bootstrap_concentration(
    competitions: pd.DataFrame,
    draws: int = 1000,
    seed: int = 20261020,
) -> dict[str, float | int | None]:
    """Competition-resampled percentile intervals for full-sample concentration."""
    winners = competitions["winner_firm_id"].tolist()
    point = concentration(winners)
    if len(winners) == 0:
        return {}
    rng = np.random.default_rng(seed)
    index = np.arange(len(winners))
    samples = {key: [] for key in ("hhi", "effective_winners", "top1_share", "top5_share", "top10_share")}
    for _ in range(draws):
        take = rng.choice(index, size=len(winners), replace=True)
        stats = concentration([winners[i] for i in take])
        for key in samples:
            samples[key].append(stats[key])
    out: dict[str, float | int | None] = {"draws": draws, "competitions": len(winners)}
    for key, values in samples.items():
        column = np.asarray(values, dtype=float)
        out[key] = _round(point[key])
        out[f"{key}_low"] = _round(float(np.quantile(column, 0.025)))
        out[f"{key}_high"] = _round(float(np.quantile(column, 0.975)))
    return out


def winner_distribution(competitions: pd.DataFrame) -> pd.DataFrame:
    counts = competitions.groupby(["winner_firm_id", "winner_name"], sort=False).size()
    frame = counts.reset_index(name="rank1_count")
    total = int(frame["rank1_count"].sum())
    frame = frame.sort_values(["rank1_count", "winner_name"], ascending=[False, True], kind="mergesort")
    frame["share"] = frame["rank1_count"] / total
    frame["cumulative_share"] = frame["share"].cumsum()
    frame["rank_among_winners"] = np.arange(1, len(frame) + 1)
    return frame.reset_index(drop=True)


def firm_persistence(rows: pd.DataFrame, archive_end: str) -> pd.DataFrame:
    """Finalist activity inside the archive. Entry before 2012 is left-censored."""
    end = pd.Timestamp(archive_end)
    records = []
    for firm_id, group in rows.groupby("firm_id", sort=False):
        ordered = group.sort_values(["selection_date", "selection_id"], kind="mergesort")
        first = pd.Timestamp(ordered["selection_date"].iloc[0])
        last = pd.Timestamp(ordered["selection_date"].iloc[-1])
        wins = int(ordered["is_winner"].sum())
        years = sorted(set(int(year) for year in ordered["selection_year"]))
        periods = [label for start, stop, label in PERIODS if any(start <= year <= stop for year in years)]
        records.append(
            {
                "firm_id": firm_id,
                "firm_name": ordered["canonical_firm_name"].iloc[0],
                "finalist_appearances": int(len(ordered)),
                "rank1_count": wins,
                "rank1_rate": round(wins / len(ordered), 4),
                "first_date": first.strftime("%Y-%m-%d"),
                "last_date": last.strftime("%Y-%m-%d"),
                "entry_year": int(first.year),
                "last_year": int(last.year),
                "left_censored_entry": int(first.year) <= LEFT_CENSOR_END,
                "active_years": len(years),
                "span_years": round((last - first).days / 365.25, 2),
                "years_since_last_observed": round((end - last).days / 365.25, 2),
                "periods_present": len(periods),
                "period_list": "; ".join(periods),
                "seen_in_2024_or_later": int(last.year) >= 2024,
            }
        )
    frame = pd.DataFrame(records)
    return frame.sort_values(["rank1_count", "finalist_appearances", "firm_name"], ascending=[False, False, True], kind="mergesort")


def period_turnover(rows: pd.DataFrame, competitions: pd.DataFrame) -> pd.DataFrame:
    """Entry, absence, and winner continuity across calendar periods.

    A firm is an archive newcomer in the period of its first finalist row.
    That is not the founding of a practice. Firms whose first row falls in
    2007-2011 are left-censored. A firm is counted as not seen again only when
    a later period exists and the firm has no row in it.
    """
    presence: dict[str, set[str]] = {}
    wins: dict[str, set[str]] = {}
    for start, stop, label in PERIODS:
        period_rows = rows.loc[rows["selection_year"].between(start, stop)]
        presence[label] = set(period_rows["firm_id"])
        period_wins = competitions.loc[competitions["selection_year"].between(start, stop)]
        wins[label] = set(period_wins["winner_firm_id"])
    first_period = {}
    for firm_id, group in rows.groupby("firm_id"):
        year = int(group["selection_year"].min())
        for start, stop, label in PERIODS:
            if start <= year <= stop:
                first_period[firm_id] = label
                break
    records = []
    labels = [label for _, _, label in PERIODS]
    for index, label in enumerate(labels):
        start, stop, _ = PERIODS[index]
        later = set()
        for later_label in labels[index + 1 :]:
            later |= presence[later_label]
        firms_now = presence[label]
        newcomers = {firm_id for firm_id, period in first_period.items() if period == label}
        not_seen_again = firms_now - later if index < len(labels) - 1 else set()
        period_wins = competitions.loc[competitions["selection_year"].between(start, stop)]
        n_wins = len(period_wins)
        incumbent_win_ids = set()
        if index:
            incumbent_win_ids = set.union(*(wins[earlier] for earlier in labels[:index]))
        incumbent_wins = int(period_wins["winner_firm_id"].isin(incumbent_win_ids).sum()) if n_wins else 0
        previous_winners = wins[labels[index - 1]] if index else set()
        repeat_previous = int(period_wins["winner_firm_id"].isin(previous_winners).sum()) if n_wins and index else 0
        records.append(
            {
                "period": label,
                "year_start": start,
                "year_end": stop,
                "left_censored": index == 0,
                "contains_partial_year": stop >= PARTIAL_YEAR,
                "right_censored": index == len(labels) - 1,
                "competitions": n_wins,
                "unique_finalists": len(firms_now),
                "unique_winners": len(wins[label]),
                "archive_newcomers": len(newcomers & firms_now),
                "finalists_not_seen_in_a_later_period": len(not_seen_again),
                "wins_by_firms_that_won_in_an_earlier_period": incumbent_wins,
                "share_wins_by_earlier_winners": _round(incumbent_wins / n_wins) if n_wins and index else None,
                "wins_by_previous_period_winners": repeat_previous if index else None,
                "share_wins_by_previous_period_winners": _round(repeat_previous / n_wins) if n_wins and index else None,
            }
        )
    return pd.DataFrame(records)


def competition_size_table(competitions: pd.DataFrame) -> pd.DataFrame:
    records = []
    for size, group in competitions.groupby("n_finalists"):
        stats = concentration(group["winner_firm_id"].tolist())
        records.append(
            {
                "n_finalists": int(size),
                "competitions": int(len(group)),
                "share_of_competitions": round(len(group) / len(competitions), 4),
                "unique_winners": stats["unique_winners"],
                "hhi": _round(stats["hhi"]),
                "top5_share": _round(stats["top5_share"]),
            }
        )
    return pd.DataFrame(records).sort_values("n_finalists")


def size_by_year(competitions: pd.DataFrame) -> pd.DataFrame:
    records = []
    for year, group in competitions.groupby("selection_year"):
        records.append(
            {
                "year": int(year),
                "partial_year": int(year) == PARTIAL_YEAR,
                "competitions": int(len(group)),
                "mean_finalists": round(float(group["n_finalists"].mean()), 3),
                "median_finalists": float(group["n_finalists"].median()),
                "min_finalists": int(group["n_finalists"].min()),
                "max_finalists": int(group["n_finalists"].max()),
                "share_two_firm": round(float((group["n_finalists"] == 2).mean()), 4),
                "share_four_or_more": round(float((group["n_finalists"] >= 4).mean()), 4),
            }
        )
    return pd.DataFrame(records)


def head_to_head(rows: pd.DataFrame, minimum: int = 5) -> pd.DataFrame:
    """Pairs that share a multi-firm ranking. A lower published rank placed higher."""
    names = rows.drop_duplicates("firm_id").set_index("firm_id")["canonical_firm_name"]
    pair_counts: dict[tuple[str, str], dict[str, int]] = {}
    for _, group in rows.groupby("selection_id", sort=False):
        members = list(zip(group["firm_id"], group["rank_num"], group["is_winner"]))
        for i, (left_id, left_rank, left_win) in enumerate(members):
            for right_id, right_rank, right_win in members[i + 1 :]:
                key = tuple(sorted((left_id, right_id)))
                bucket = pair_counts.setdefault(
                    key,
                    {
                        "shared": 0,
                        "a_ahead": 0,
                        "b_ahead": 0,
                        "tied_rank": 0,
                        "a_rank1": 0,
                        "b_rank1": 0,
                        "other_rank1": 0,
                    },
                )
                first, second = key
                bucket["shared"] += 1
                if left_rank < right_rank:
                    ahead = left_id
                elif right_rank < left_rank:
                    ahead = right_id
                else:
                    ahead = ""
                    bucket["tied_rank"] += 1
                if ahead == first:
                    bucket["a_ahead"] += 1
                elif ahead == second:
                    bucket["b_ahead"] += 1
                if left_win:
                    winner = left_id
                elif right_win:
                    winner = right_id
                else:
                    winner = ""
                if winner == first:
                    bucket["a_rank1"] += 1
                elif winner == second:
                    bucket["b_rank1"] += 1
                else:
                    bucket["other_rank1"] += 1
    records = []
    for (first, second), bucket in pair_counts.items():
        if bucket["shared"] < minimum:
            continue
        leader = max(bucket["a_ahead"], bucket["b_ahead"])
        trailer = min(bucket["a_ahead"], bucket["b_ahead"])
        records.append(
            {
                "firm_a_id": first,
                "firm_b_id": second,
                "firm_a": names.get(first, first),
                "firm_b": names.get(second, second),
                "shared_rankings": bucket["shared"],
                "a_finished_ahead": bucket["a_ahead"],
                "b_finished_ahead": bucket["b_ahead"],
                "tied_rank": bucket["tied_rank"],
                "a_ranked_first": bucket["a_rank1"],
                "b_ranked_first": bucket["b_rank1"],
                "someone_else_ranked_first": bucket["other_rank1"],
                "in_report": int(bucket["shared"] >= 8 or leader >= 6),
                "one_sided": int(leader >= 6 and leader >= 2 * trailer),
            }
        )
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    return frame.sort_values(["shared_rankings", "firm_a", "firm_b"], ascending=[False, True, True], kind="mergesort")


def sensitivity(competitions: pd.DataFrame, rows: pd.DataFrame, competitors: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """The same concentration statistics under stated sample changes."""
    specs = {
        "primary_multifirm": competitions,
        "drop_inferred_list_order": competitions.loc[competitions["rank_method"] != "published_list_order"],
        "drop_joint_venture_winners": competitions.loc[~competitions["winner_is_joint_venture"]],
    }
    single = _single_firm_wins(competitors, events)
    if len(single):
        added = pd.concat([competitions, single], ignore_index=True)
        specs["add_sole_published_firm"] = added
    records = []
    for name, group in specs.items():
        stats = concentration(group["winner_firm_id"].tolist())
        records.append(
            {
                "sample": name,
                "competitions": stats["competitions"],
                "unique_winners": stats["unique_winners"],
                "hhi": _round(stats["hhi"]),
                "effective_winners": _round(stats["effective_winners"]),
                "top5_share": _round(stats["top5_share"]),
                "top10_share": _round(stats["top10_share"]),
            }
        )
    return pd.DataFrame(records)


def _single_firm_wins(competitors: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    single = competitors.loc[competitors["choice_status"] == "single_firm"].copy()
    if single.empty:
        return single
    single["rank_num"] = pd.to_numeric(single["rank_num"], errors="coerce")
    single = single.loc[single["rank_num"] == 1]
    meta = events[["selection_id", "selection_date", "selection_year"]].drop_duplicates("selection_id")
    single = single.merge(meta, on="selection_id", how="left")
    return pd.DataFrame(
        {
            "selection_id": single["selection_id"],
            "winner_firm_id": single["firm_id"],
            "winner_is_joint_venture": _truthy(single["joint_venture"]).to_numpy(),
            "rank_method": "",
            "selection_year": single["selection_year"].astype(int),
            "n_finalists": 1,
        }
    )


def sample_audit(competitors: pd.DataFrame, events: pd.DataFrame, firms: pd.DataFrame) -> dict:
    """Counts a reader needs before trusting a concentration figure."""
    choice = competitors["choice_status"].value_counts().to_dict()
    rounds = events["selection_round"].value_counts().to_dict()
    methods = events["rank_method"].value_counts().to_dict()
    model = competitors.loc[_truthy(competitors["in_model_sample"])]
    duplicate_projects = int(events["project_id"].duplicated().sum())
    company_filled = {
        "directory_firms": int(len(firms)),
        "with_verification_status": int(firms["verification_status"].map(_blank).ne("").sum())
        if "verification_status" in firms
        else 0,
        "with_staff_size": int(firms["staff_size"].map(_blank).ne("").sum()) if "staff_size" in firms else 0,
        "with_headquarters": int(firms["hq_location"].map(_blank).ne("").sum()) if "hq_location" in firms else 0,
        "with_founded_year": int(firms["founded_year"].map(_blank).ne("").sum()) if "founded_year" in firms else 0,
    }
    return {
        "selection_events": int(len(events)),
        "projects": int(events["project_id"].nunique()),
        "duplicate_project_rows": duplicate_projects,
        "competitor_rows": int(len(competitors)),
        "choice_status": {str(key): int(value) for key, value in choice.items()},
        "selection_rounds": {str(key): int(value) for key, value in rounds.items()},
        "rank_methods_on_events": {str(key): int(value) for key, value in methods.items()},
        "model_competitions": int(model["selection_id"].nunique()),
        "model_finalist_rows": int(len(model)),
        "model_firms": int(model["firm_id"].nunique()),
        "directory_firms": int(firms["firm_id"].nunique()),
        "event_date_min": str(events["selection_date"].min()),
        "event_date_max": str(events["selection_date"].max()),
        "company": company_filled,
    }


def build_outputs(competitors: pd.DataFrame, events: pd.DataFrame, firms: pd.DataFrame) -> dict[str, pd.DataFrame | dict]:
    rows = model_rows(competitors, events, firms)
    competitions = competition_table(rows)
    archive_end = str(competitions["selection_date"].max())
    return {
        "rows": rows,
        "competitions": competitions,
        "annual": annual_table(competitions, rows),
        "rolling": rolling_table(competitions, rows),
        "distribution": winner_distribution(competitions),
        "persistence": firm_persistence(rows, archive_end),
        "periods": period_turnover(rows, competitions),
        "sizes": competition_size_table(competitions),
        "size_by_year": size_by_year(competitions),
        "matchups": head_to_head(rows),
        "sensitivity": sensitivity(competitions, rows, competitors, events),
        "bootstrap": bootstrap_concentration(competitions),
        "contrasts": period_contrasts(competitions),
        "audit": sample_audit(competitors, events, firms),
        "archive_end": archive_end,
    }


def write_outputs(outputs: dict, processed, reports) -> None:
    processed.mkdir(parents=True, exist_ok=True)
    figures = reports / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    tables = {
        "market_annual.csv": outputs["annual"],
        "market_rolling.csv": outputs["rolling"],
        "market_winner_distribution.csv": outputs["distribution"],
        "market_firm_persistence.csv": outputs["persistence"],
        "market_periods.csv": outputs["periods"],
        "market_competition_size.csv": outputs["sizes"],
        "market_competition_size_by_year.csv": outputs["size_by_year"],
        "market_head_to_head.csv": outputs["matchups"],
        "market_sensitivity.csv": outputs["sensitivity"],
    }
    for name, frame in tables.items():
        frame.to_csv(processed / name, index=False)
    summary = {
        "archive_end": outputs["archive_end"],
        "audit": outputs["audit"],
        "bootstrap": outputs["bootstrap"],
        "contrasts": outputs["contrasts"],
        "full_sample": _window_row("full", outputs["competitions"], outputs["rows"]),
    }
    (processed / "market_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_figures(outputs, figures)


def write_figures(outputs: dict, figures) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    annual = outputs["annual"]
    rolling = outputs["rolling"]
    distribution = outputs["distribution"]
    sizes = outputs["sizes"]
    size_year = outputs["size_by_year"]
    periods = outputs["periods"]

    _style(plt)
    _winner_curve(plt, distribution, figures / "01_winner_concentration_curve.png")
    _rolling(plt, rolling, figures / "01_rolling_concentration.png")
    _participation(plt, annual, figures / "01_market_participation.png")
    _sizes(plt, sizes, size_year, figures / "01_competition_size.png")
    _turnover(plt, periods, figures / "01_period_turnover.png")


def _style(plt) -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.titleweight": "regular",
        }
    )


def _winner_curve(plt, distribution: pd.DataFrame, path) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    x = distribution["rank_among_winners"].to_numpy()
    y = distribution["cumulative_share"].to_numpy() * 100
    ax.plot(x, y, color="#0072B2", lw=2.0)
    ax.axhline(100 * distribution["share"].iloc[:5].sum() if len(distribution) >= 5 else y[-1], color="#D55E00", ls="--", lw=1, label="Top 5 firms")
    if len(distribution) >= 5:
        ax.scatter([5], [y[4]], color="#D55E00", zorder=3)
        ax.annotate(
            f"Top 5: {y[4]:.0f}%",
            (5, y[4]),
            textcoords="offset points",
            xytext=(8, -12),
            color="#D55E00",
        )
    if len(distribution) >= 10:
        ax.scatter([10], [y[9]], color="#009E73", zorder=3)
        ax.annotate(
            f"Top 10: {y[9]:.0f}%",
            (10, y[9]),
            textcoords="offset points",
            xytext=(8, 6),
            color="#009E73",
        )
    ax.set_xlabel("Firms ordered by number of rank-1 results")
    ax.set_ylabel("Cumulative share of rank-1 results (%)")
    ax.set_title("How concentrated are first-place rankings?")
    ax.set_ylim(0, 105)
    ax.set_xlim(1, max(int(x[-1]), 2))
    fig.text(
        0.01,
        0.01,
        "Multi-firm published rankings, August 2007–September 2026. Rank 1 is not a signed contract.",
        fontsize=8,
        color="#444444",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _rolling(plt, rolling: pd.DataFrame, path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(8.6, 6.4), sharex=True)
    labels = rolling["window"].tolist()
    x = np.arange(len(labels))
    partial = rolling["contains_partial_year"].astype(bool).to_numpy()
    series = (
        (rolling["top5_share"] * 100, "Top-5 share of rank-1 results (%)", "Top-5 share of rank-1 results", "#D55E00"),
        (rolling["hhi"], "Herfindahl-Hirschman index", "HHI of rank-1 results", "#0072B2"),
    )
    for ax, (values, ylabel, title, color) in zip(axes, series):
        if partial.any():
            ax.axvspan(x[partial][0] - 0.5, x[partial][-1] + 0.5, color="#F3F3F3", zorder=0)
        ax.plot(x, values, color=color, lw=2.0, marker="o", ms=3.5)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.set_ylim(0, 60 if "Top-5" in title else 0.10)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=45, ha="right")
    axes[1].set_xlabel("Five-year window")
    fig.text(
        0.01,
        0.01,
        "Shaded windows include the partial 2026 year. Effective winners = 1 / HHI. Source: model-sample rankings.",
        fontsize=8,
        color="#444444",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _participation(plt, annual: pd.DataFrame, path) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    years = annual["year"].to_numpy()
    ax.bar(years, annual["competitions"], color="#CFCFCF", label="Rankings", width=0.8)
    ax.plot(years, annual["unique_finalists"], color="#0072B2", marker="o", lw=1.6, label="Unique finalist firms")
    ax.plot(years, annual["unique_winners"], color="#D55E00", marker="o", lw=1.6, label="Unique rank-1 firms")
    if (annual["year"] == PARTIAL_YEAR).any():
        ax.annotate("2026 partial", (PARTIAL_YEAR, annual.loc[annual["year"] == PARTIAL_YEAR, "competitions"].iloc[0]), textcoords="offset points", xytext=(-28, 8), fontsize=8)
    ax.set_xlabel("Year of the published ranking")
    ax.set_ylabel("Count")
    ax.set_title("Competitions, finalists, and rank-1 firms by year")
    ax.legend(frameon=False)
    fig.text(
        0.01,
        0.01,
        "A finalist is a firm on a completed multi-firm ranking. 2026 runs through the last stored ranking.",
        fontsize=8,
        color="#444444",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _sizes(plt, sizes: pd.DataFrame, size_year: pd.DataFrame, path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.6))
    axes[0].bar(sizes["n_finalists"].astype(str), sizes["competitions"], color="#0072B2")
    axes[0].set_xlabel("Finalists on the published ranking")
    axes[0].set_ylabel("Rankings")
    axes[0].set_title("Size of the choice set")
    axes[1].plot(size_year["year"], size_year["mean_finalists"], color="#0072B2", marker="o")
    axes[1].set_xlabel("Year")
    axes[1].set_ylabel("Mean finalists per ranking")
    axes[1].set_title("Field size over time")
    axes[1].set_ylim(0, max(4.5, float(size_year["mean_finalists"].max()) + 0.4))
    fig.text(
        0.01,
        0.01,
        "Multi-firm rankings only. Sole-firm lists and unfinished rankings are excluded.",
        fontsize=8,
        color="#444444",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _turnover(plt, periods: pd.DataFrame, path) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    x = np.arange(len(periods))
    width = 0.36
    absence = periods["finalists_not_seen_in_a_later_period"].astype(float)
    absence.iloc[-1] = np.nan
    ax.bar(x - width / 2, periods["archive_newcomers"], width=width, color="#0072B2", label="First observed as a finalist in this period")
    ax.bar(
        x + width / 2,
        absence,
        width=width,
        color="#D55E00",
        label="Not on a later ranking in this archive",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(periods["period"])
    ax.set_ylabel("Firms")
    ax.set_title("Finalist entry and later absence, by period")
    ax.legend(frameon=False, loc="upper right")
    fig.text(
        0.01,
        0.01,
        "2007–2011 entry is left-censored. The last period cannot show later absence. Not a count of new practices.",
        fontsize=8,
        color="#444444",
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)
