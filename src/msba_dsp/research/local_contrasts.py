"""Three contrasts that stay inside the files already collected.

The district test uses the published result lists. The cost test uses the
2025–2026 chart only. The spelling recount pools pairs already listed in
near_duplicate_firms.csv and does not rewrite firm ids. Rank 1 is the published
order, not a signed contract. The stored winner model is not refit.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

import numpy as np
import pandas as pd

from msba_dsp.evaluation.metrics import wilson_interval
from msba_dsp.processing.names import is_joint_venture, normalize_key
from msba_dsp.research.incumbency import experience_frame

SEED = 20261020
DRAWS = 2000
MIXED_STOP = 15
COST_CUT_MILLIONS = 100.0


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return round(float(value), digits)


def _interval(values: list[float], draws: int = DRAWS, seed: int = SEED) -> tuple[float, float, float]:
    point = float(np.mean(values))
    rng = np.random.default_rng(seed)
    drawn = rng.choice(np.asarray(values, dtype=float), size=(draws, len(values)), replace=True)
    samples = drawn.mean(axis=1)
    return point, float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))


def _name_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _joint_firm_ids(firms: pd.DataFrame) -> set[str]:
    """Firm ids the directory already labels as a joint submission."""
    notes = []
    for column in ("verification_status", "research_note"):
        if column in firms.columns:
            notes.append(firms[column].astype(str))
    labeled = pd.Series(False, index=firms.index) if not notes else notes[0].str.lower().str.contains("joint submission")
    for extra in notes[1:]:
        labeled = labeled | extra.str.lower().str.contains("joint submission")
    flags = firms["joint_venture"] if "joint_venture" in firms.columns else pd.Series("", index=firms.index)
    flagged = flags.astype(str).str.strip().str.lower().isin({"true", "1", "1.0"})
    return set(firms.loc[labeled | flagged, "firm_id"].astype(str))


def _is_joint_line(left: str, right: str, left_id: str, right_id: str, joint_ids: set[str]) -> bool:
    """A team of two practices, not a slash that is part of one firm's name."""
    for name in (left, right):
        if re.search(r"\bw/|in association|joint venture", str(name), flags=re.IGNORECASE) or is_joint_venture(str(name)):
            return True
    return left_id in joint_ids or right_id in joint_ids


def _parse_millions(text: object) -> tuple[float, float, float] | None:
    numbers = re.findall(r"\d+(?:\.\d+)?", str(text))
    if len(numbers) < 2:
        return None
    low, high = float(numbers[0]), float(numbers[1])
    return low, high, (low + high) / 2.0


def _project_rate(projects: list[tuple[int, int]], index: np.ndarray | None = None) -> float:
    chosen = projects if index is None else [projects[int(i)] for i in index]
    numerator = sum(successes for successes, _ in chosen)
    denominator = sum(rows for _, rows in chosen)
    if denominator == 0:
        return float("nan")
    return numerator / denominator


def _rate_interval(frame: pd.DataFrame, success: str, draws: int = DRAWS, seed: int = SEED) -> dict:
    projects = [
        (int(group[success].sum()), int(len(group)))
        for _, group in frame.groupby("project_id", sort=False)
    ]
    point = _project_rate(projects)
    rng = np.random.default_rng(seed)
    samples = [
        _project_rate(projects, rng.integers(0, len(projects), size=len(projects)))
        for _ in range(draws)
    ] if projects else []
    column = np.asarray(samples, dtype=float)
    successes = int(frame[success].sum())
    rows = int(len(frame))
    low, high = wilson_interval(successes, rows) if rows else (None, None)
    return {
        "applicants": rows,
        "interviewed": successes,
        "projects": len(projects),
        "rate": _round(point),
        "rate_low": _round(float(np.quantile(column, 0.025))) if len(column) else None,
        "rate_high": _round(float(np.quantile(column, 0.975))) if len(column) else None,
        "wilson_low": _round(low),
        "wilson_high": _round(high),
    }


def _difference_interval(
    left: pd.DataFrame,
    right: pd.DataFrame,
    success: str,
    draws: int = DRAWS,
    seed: int = SEED,
) -> dict:
    """Right-band rate minus left-band rate. Projects are resampled separately."""
    def packs(frame: pd.DataFrame) -> list[tuple[int, int]]:
        return [
            (int(group[success].sum()), int(len(group)))
            for _, group in frame.groupby("project_id", sort=False)
        ]

    left_projects = packs(left)
    right_projects = packs(right)
    point = _project_rate(right_projects) - _project_rate(left_projects)
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(draws):
        left_draw = _project_rate(left_projects, rng.integers(0, len(left_projects), size=len(left_projects)))
        right_draw = _project_rate(right_projects, rng.integers(0, len(right_projects), size=len(right_projects)))
        samples.append(right_draw - left_draw)
    column = np.asarray(samples, dtype=float)
    return {
        "difference": _round(point),
        "difference_low": _round(float(np.quantile(column, 0.025))),
        "difference_high": _round(float(np.quantile(column, 0.975))),
    }


def district_incumbent_frame(frame: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Mark a finalist who ranked first for the same district on an earlier date.

    Two rankings on the same day do not update each other. District strings are
    used as printed.
    """
    districts = events[["selection_id", "district"]].drop_duplicates("selection_id")
    scored = frame.merge(districts, on="selection_id", how="left")
    scored["selection_date"] = pd.to_datetime(scored["selection_date"])
    scored = scored.sort_values(["selection_date", "selection_id", "firm_id"], kind="mergesort")
    prior: dict[str, set[str]] = defaultdict(set)
    incumbent: list[int] = []
    for _, day in scored.groupby("selection_date", sort=False):
        for _, row in day.iterrows():
            incumbent.append(int(row["firm_id"] in prior[row["district"]]))
        for _, row in day.iterrows():
            if int(row["winner"]) == 1 and str(row["district"]).strip():
                prior[row["district"]].add(row["firm_id"])
    scored["district_incumbent"] = incumbent
    scored["selection_date"] = scored["selection_date"].dt.strftime("%Y-%m-%d")
    return scored


def _competition_rows(scored: pd.DataFrame) -> pd.DataFrame:
    records = []
    late = scored.loc[scored["selection_year"].ge(2012)]
    for selection_id, group in late.groupby("selection_id", sort=False):
        incumbents = group.loc[group["district_incumbent"].eq(1)]
        winner = group.loc[group["winner"].eq(1)].iloc[0]
        records.append(
            {
                "selection_id": selection_id,
                "selection_date": winner["selection_date"],
                "district": winner["district"],
                "school_name": winner["school_name"],
                "n_finalists": int(len(group)),
                "n_incumbents": int(len(incumbents)),
                "incumbent_share": _round(len(incumbents) / len(group)),
                "incumbent_ranked_first": int(int(winner["district_incumbent"]) == 1),
                "winner_firm_id": winner["firm_id"],
                "winner_name": winner["firm_name"],
                "incumbent_names": "; ".join(sorted(incumbents["firm_name"].astype(str))),
                "mixed": int(group["prior_wins"].eq(0).any() and group["prior_wins"].gt(0).any()),
                "winner_prior_wins": int(winner["prior_wins"]),
            }
        )
    return pd.DataFrame(records)


def district_summary(competitions: pd.DataFrame, scored: pd.DataFrame) -> dict:
    late = scored.loc[scored["selection_year"].ge(2012)]
    same_day = late.groupby(["selection_date", "district"])["selection_id"].nunique()
    present = competitions.loc[competitions["n_incumbents"].gt(0)].copy()
    interviewed = present.loc[~present["selection_id"].str.contains("no-interview")]
    gaps = [
        float(row.incumbent_ranked_first - row.incumbent_share)
        for row in present.itertuples(index=False)
    ]
    point, low, high = _interval(gaps) if gaps else (None, None, None)
    wins = [float(row.incumbent_ranked_first) for row in present.itertuples(index=False)]
    win_point, win_low, win_high = _interval(wins) if wins else (None, None, None)
    mixed = competitions.loc[competitions["mixed"].eq(1)]
    mixed_present = mixed.loc[mixed["n_incumbents"].gt(0)]
    summary = {
        "rankings_from_2012": int(late["selection_id"].nunique()),
        "districts_from_2012": int(late["district"].nunique()),
        "repeat_districts": int(late.groupby("district")["selection_id"].nunique().ge(2).sum()),
        "same_day_district_rankings": int(same_day.ge(2).sum()),
        "lists_with_incumbent": int(len(present)),
        "lists_excluding_no_interview": int(len(interviewed)),
        "incumbent_wins": int(present["incumbent_ranked_first"].sum()) if len(present) else 0,
        "win_rate": _round(win_point),
        "win_rate_low": _round(win_low),
        "win_rate_high": _round(win_high),
        "mean_seat_share": _round(float(present["incumbent_share"].mean())) if len(present) else None,
        "excess": _round(point),
        "excess_low": _round(low),
        "excess_high": _round(high),
        "mixed_lists": int(len(mixed)),
        "mixed_with_incumbent": int(len(mixed_present)),
        "mixed_excess": None,
        "mixed_excess_low": None,
        "mixed_excess_high": None,
        "mixed_stopped": True,
        "excess_excluding_no_interview": None,
        "excess_excluding_no_interview_low": None,
        "excess_excluding_no_interview_high": None,
    }
    if len(interviewed) >= 8 and len(interviewed) != len(present):
        held = [float(row.incumbent_ranked_first - row.incumbent_share) for row in interviewed.itertuples(index=False)]
        held_point, held_low, held_high = _interval(held, seed=SEED + 3)
        summary.update(
            {
                "excess_excluding_no_interview": _round(held_point),
                "excess_excluding_no_interview_low": _round(held_low),
                "excess_excluding_no_interview_high": _round(held_high),
            }
        )
    if len(mixed_present) >= MIXED_STOP:
        mixed_gaps = [
            float(row.incumbent_ranked_first - row.incumbent_share)
            for row in mixed_present.itertuples(index=False)
        ]
        mixed_point, mixed_low, mixed_high = _interval(mixed_gaps, seed=SEED + 1)
        summary.update(
            {
                "mixed_excess": _round(mixed_point),
                "mixed_excess_low": _round(mixed_low),
                "mixed_excess_high": _round(mixed_high),
                "mixed_stopped": False,
            }
        )
    return summary


def collapsed_district_spellings(events: pd.DataFrame) -> pd.DataFrame:
    """Printed district strings that collapse to one key. None are merged."""
    names = sorted({str(value).strip() for value in events["district"] if str(value).strip()})
    grouped: dict[str, list[str]] = defaultdict(list)
    for name in names:
        grouped[_name_key(name)].append(name)
    rows = []
    for key, variants in grouped.items():
        if len(variants) < 2:
            continue
        rows.append({"collapsed": key, "printed": " | ".join(variants), "variants": len(variants)})
    return pd.DataFrame(rows, columns=["collapsed", "printed", "variants"]) if rows else pd.DataFrame(columns=["collapsed", "printed", "variants"])


def firm_name_index(firms: pd.DataFrame) -> dict[str, set[str]]:
    """Map the project's own name key to firm ids. A key shared by two ids is left ambiguous."""
    index: dict[str, set[str]] = defaultdict(set)
    for row in firms.itertuples(index=False):
        keys = set()
        stored = str(getattr(row, "canonical_key", "") or "").strip()
        if stored:
            keys.add(stored)
        names = [getattr(row, "canonical_firm_name", "")]
        historical = getattr(row, "historical_names", "")
        if historical:
            names.extend(part.strip() for part in str(historical).split("|"))
        keys.update(normalize_key(str(name)) for name in names if str(name).strip())
        for key in keys:
            if key:
                index[key].add(str(row.firm_id))
    return index


class _Union:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, item: str) -> None:
        self.parent.setdefault(item, item)

    def find(self, item: str) -> str:
        self.add(item)
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: str, right: str) -> None:
        root_left, root_right = self.find(left), self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left


def resolve_near_duplicates(pairs: pd.DataFrame, firms: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str], dict[str, str]]:
    """Resolve each flagged pair to firm ids. Joint-venture lines stay out of the spelling pool."""
    index = firm_name_index(firms)
    joint_ids = _joint_firm_ids(firms)
    spelling = _Union()
    every = _Union()
    for firm_id in firms["firm_id"].astype(str):
        spelling.add(firm_id)
        every.add(firm_id)
    records = []
    for row in pairs.itertuples(index=False):
        left_ids = index.get(normalize_key(str(row.firm_a)), set())
        right_ids = index.get(normalize_key(str(row.firm_b)), set())
        left_id = next(iter(left_ids)) if len(left_ids) == 1 else ""
        right_id = next(iter(right_ids)) if len(right_ids) == 1 else ""
        joint = _is_joint_line(str(row.firm_a), str(row.firm_b), left_id, right_id, joint_ids)
        if len(left_ids) > 1 or len(right_ids) > 1:
            status = "ambiguous"
        elif len(left_ids) != 1 or len(right_ids) != 1:
            status = "unmatched"
        elif left_ids == right_ids:
            status = "already_one_id"
        else:
            status = "resolved"
        if status == "resolved":
            every.union(left_id, right_id)
            if not joint:
                spelling.union(left_id, right_id)
        records.append(
            {
                "firm_a": row.firm_a,
                "firm_b": row.firm_b,
                "firm_a_id": left_id,
                "firm_b_id": right_id,
                "joint_venture_line": int(joint),
                "status": status,
                "in_spelling_pool": int(status == "resolved" and not joint),
            }
        )
    return pd.DataFrame(records), spelling.parent, every.parent


def _root(parent: dict[str, str], firm_id: str) -> str:
    seen = firm_id
    while parent.get(seen, seen) != seen:
        seen = parent[seen]
    return seen


def pooled_win_counts(frame: pd.DataFrame, parent: dict[str, str]) -> pd.Series:
    """Earlier rank-1 results after pooling, still using earlier dates only."""
    wins: dict[str, int] = defaultdict(int)
    counts: list[int] = []
    ordered = frame.sort_values(["selection_date", "selection_id"], kind="mergesort")
    for _, day in ordered.groupby("selection_date", sort=False):
        day_counts = []
        for row in day.itertuples(index=False):
            day_counts.append(wins[_root(parent, str(row.firm_id))])
        counts.extend(day_counts)
        for row, _prior in zip(day.itertuples(index=False), day_counts):
            if int(row.winner) == 1:
                wins[_root(parent, str(row.firm_id))] += 1
    return pd.Series(counts, index=ordered.index)


def spelling_recount(frame: pd.DataFrame, pairs: pd.DataFrame, firms: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    resolved, spelling_parent, every_parent = resolve_near_duplicates(pairs, firms)
    ordered = frame.sort_values(["selection_date", "selection_id"], kind="mergesort")
    spelling_prior = pooled_win_counts(ordered, spelling_parent)
    every_prior = pooled_win_counts(ordered, every_parent)
    attached = ordered.copy()
    attached["spelling_prior_wins"] = spelling_prior.to_numpy()
    attached["all_pairs_prior_wins"] = every_prior.to_numpy()
    firsts = attached.loc[attached["winner"].eq(1) & attached["selection_year"].ge(2012) & attached["prior_wins"].eq(0)].copy()
    firsts = firsts.sort_values(["selection_date", "firm_name"], kind="mergesort")
    table = firsts[
        ["selection_date", "firm_id", "firm_name", "prior_wins", "prior_finals", "spelling_prior_wins", "all_pairs_prior_wins"]
    ].copy()
    summary = {
        "stored_first_rank1": int(len(table)),
        "still_first_after_spelling_pool": int(table["spelling_prior_wins"].eq(0).sum()),
        "still_first_after_all_flagged_pairs": int(table["all_pairs_prior_wins"].eq(0).sum()),
        "spelling_pairs_pooled": int(resolved["in_spelling_pool"].sum()),
        "joint_lines_left_out": int(resolved["joint_venture_line"].sum()),
        "unresolved_pairs": int(resolved["status"].isin(["ambiguous", "unmatched"]).sum()),
    }
    return table, resolved, summary


def cost_bands(projects: pd.DataFrame, applicants: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Interview rates by the midpoint of the chart's printed construction-cost range.

    The primary cut is $100 million. It is a round threshold on the printed
    ranges, chosen without reference to who was interviewed. Historical HTML
    pages have no budget and are not in this table.
    """
    ranges = projects.copy()
    parsed = ranges["est_construction_cost"].map(_parse_millions)
    ranges["cost_low_millions"] = [None if item is None else item[0] for item in parsed]
    ranges["cost_high_millions"] = [None if item is None else item[1] for item in parsed]
    ranges["midpoint_millions"] = [None if item is None else item[2] for item in parsed]
    work = applicants.merge(
        ranges[["project_id", "est_construction_cost", "midpoint_millions", "comments"]],
        on="project_id",
        how="left",
    )
    work = work.loc[work["shortlisted"].astype(str).isin(["0", "1"])].copy()
    work["shortlisted"] = work["shortlisted"].astype(int)
    work["disqualified"] = work["disqualified"].astype(int)
    work["prior_wins_review"] = work["prior_wins_review"].astype(int)
    work["zero_prior"] = work["prior_wins_review"].eq(0).astype(int)
    interviewed_all = {
        project_id
        for project_id, group in work.groupby("project_id", sort=False)
        if int(group["shortlisted"].min()) == 1
    }
    eligible = work.loc[work["disqualified"].eq(0) & work["midpoint_millions"].notna()].copy()
    eligible["band"] = np.where(
        eligible["midpoint_millions"].astype(float).ge(COST_CUT_MILLIONS),
        "midpoint $100 million or more",
        "midpoint under $100 million",
    )
    eligible["detail_band"] = pd.cut(
        eligible["midpoint_millions"].astype(float),
        bins=[-np.inf, 100, 200, np.inf],
        labels=["under $100 million", "$100 million to under $200 million", "$200 million or more"],
        right=False,
    ).astype(str)
    rows = []
    for band, band_rows in eligible.groupby("band", sort=False):
        for label, part in (
            ("no earlier rank-1 result", band_rows.loc[band_rows["zero_prior"].eq(1)]),
            ("one or more earlier rank-1 results", band_rows.loc[band_rows["zero_prior"].eq(0)]),
        ):
            if part.empty:
                continue
            rows.append({"band": band, "experience": label, "cut": "all interview lists", **_rate_interval(part, "shortlisted")})
    detail = []
    for band, band_rows in eligible.groupby("detail_band", sort=False):
        part = band_rows.loc[band_rows["zero_prior"].eq(1)]
        if part.empty:
            continue
        detail.append({"band": band, "experience": "no earlier rank-1 result", "cut": "descriptive", **_rate_interval(part, "shortlisted")})
    low = eligible.loc[eligible["band"].eq("midpoint under $100 million") & eligible["zero_prior"].eq(1)]
    high = eligible.loc[eligible["band"].eq("midpoint $100 million or more") & eligible["zero_prior"].eq(1)]
    primary = _difference_interval(low, high, "shortlisted")
    selective = eligible.loc[~eligible["project_id"].isin(interviewed_all)]
    selective_low = selective.loc[selective["band"].eq("midpoint under $100 million") & selective["zero_prior"].eq(1)]
    selective_high = selective.loc[selective["band"].eq("midpoint $100 million or more") & selective["zero_prior"].eq(1)]
    sensitivity = None
    if not selective_low.empty and not selective_high.empty:
        sensitivity = _difference_interval(selective_low, selective_high, "shortlisted", seed=SEED + 2)
    summary = {
        "primary_cut": "midpoint of the printed range, $100 million",
        "zero_prior_difference_high_minus_low": primary["difference"],
        "difference_low": primary["difference_low"],
        "difference_high": primary["difference_high"],
        "projects_that_interviewed_everyone": len(interviewed_all),
        "selective_difference": None if sensitivity is None else sensitivity["difference"],
        "selective_difference_low": None if sensitivity is None else sensitivity["difference_low"],
        "selective_difference_high": None if sensitivity is None else sensitivity["difference_high"],
        "disqualified_excluded": int(work["disqualified"].sum()),
    }
    project_table = (
        ranges.loc[ranges["project_id"].isin(set(eligible["project_id"])), ["project_id", "district", "school", "est_construction_cost", "midpoint_millions"]]
        .copy()
    )
    return pd.DataFrame(rows), pd.DataFrame(detail), {**summary, "_projects": project_table}


def build_outputs(
    competitors: pd.DataFrame,
    events: pd.DataFrame,
    firms: pd.DataFrame,
    pairs: pd.DataFrame,
    chart_projects: pd.DataFrame,
    applicants: pd.DataFrame,
) -> dict:
    frame = experience_frame(competitors, events, firms)
    scored = district_incumbent_frame(frame, events)
    competitions = _competition_rows(scored)
    present = competitions.loc[competitions["n_incumbents"].gt(0)].copy()
    recount, resolved, spelling = spelling_recount(frame, pairs, firms)
    rates, detail, cost = cost_bands(chart_projects, applicants)
    return {
        "district_lists": present,
        "district_summary": district_summary(competitions, scored),
        "district_spellings": collapsed_district_spellings(events),
        "spelling_recount": recount,
        "pair_resolution": resolved,
        "spelling_summary": spelling,
        "cost_rates": rates,
        "cost_detail": detail,
        "cost_summary": {key: value for key, value in cost.items() if key != "_projects"},
        "cost_projects": cost["_projects"],
    }


def write_outputs(outputs: dict, processed) -> None:
    outputs["district_lists"].to_csv(processed / "district_incumbent_lists.csv", index=False)
    outputs["district_spellings"].to_csv(processed / "district_spelling_audit.csv", index=False)
    outputs["spelling_recount"].to_csv(processed / "spelling_pool_recount.csv", index=False)
    outputs["pair_resolution"].to_csv(processed / "near_duplicate_resolution.csv", index=False)
    outputs["cost_rates"].to_csv(processed / "chart_cost_band_rates.csv", index=False)
    outputs["cost_detail"].to_csv(processed / "chart_cost_band_detail.csv", index=False)
    payload = {
        "district": outputs["district_summary"],
        "spelling": outputs["spelling_summary"],
        "cost": outputs["cost_summary"],
    }
    (processed / "local_contrasts_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
