"""Snapshot audit of the inferred Designer Selection Panel roster.

The inferred file carries one roster across the other years in each era. A name
on that file is not attendance, not a ballot, and not the three local members
on a project. Rank 1 remains the published order, not a signed contract.
"""

from __future__ import annotations

import json
import re
from collections import Counter

import numpy as np
import pandas as pd

from msba_dsp.research.firm_characteristics import attribute_frame
from msba_dsp.research.incumbency import TRACKED, experience_frame
from msba_dsp.research.market_structure import concentration, model_rows

SEED = 20261020
DRAWS = 2000

# Transcribed from data/reference/panel_members.html, saved 2026-10-20.
# The public page listed the same eighteen names on 2026-10-21.
OFFICIAL_2026 = (
    ("Beth McDougal", "MSBA Designee, Registered Architect, Chair"),
    ("Rachel E. Shanley", "MSBA Designee, Professional Engineer, Vice-Chair"),
    ("Jess Baccari", "AGC-MA Designee, Registered Architect"),
    ("Russell Bartash", "MA Building Trades Council Designee"),
    ("Ruth Bennett", "MSBA Designee, Registered Architect"),
    ("Eric Bernardin", "ACEC Designee, Professional Engineer"),
    ("Karl Brown", "MSBA Staff, Registered Architect"),
    ("John S. Ferrante", "Associated General Contractors of Massachusetts Designee"),
    ("Jennifer Gonzalez", "MSBA Executive Director Designee"),
    ("Eric LeBeau", "Public Member"),
    ("Joseph McDonough", "Public Member"),
    ("Alan Slater", "MSBA Designee, Professional Engineer"),
    ("Robert Zverina", "MA AIA Designee, Registered Architect"),
    ("Neil Cronin", "MSBA Staff"),
    ("Utsavi Gadani", "MSBA Staff"),
    ("Arlin Medina", "MSBA Staff"),
    ("Diane Sullivan", "MSBA Staff"),
    ("John F. Jumpe Jr.", "MSBA Staff; alternate to one of three staff seats"),
)
PROCESS_PAGE_APPOINTED = 13
PROCESS_PAGE_LOCAL = 3


def person_key(name: str) -> str:
    """First and last token, so a middle initial does not split one person."""
    text = str(name).lower().replace(".", " ")
    text = re.sub(r"[^a-z\s]", " ", text)
    parts = [part for part in text.split() if part not in {"jr", "sr", "ii", "iii"} and len(part) > 1]
    if len(parts) < 2:
        return " ".join(parts)
    return f"{parts[0]} {parts[-1]}"


def _named(name: str) -> bool:
    return person_key(name) not in {"", "vacant"}


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return round(float(value), digits)


def seat_group(designation: str) -> str:
    text = designation.lower()
    if "alternate" in text:
        return "staff_alternate"
    if "staff" in text:
        return "msba_staff"
    if "public member" in text:
        return "public_member"
    if "designee" in text:
        return "designee"
    return "unspecified"


def official_crosswalk() -> pd.DataFrame:
    rows = []
    for name, designation in OFFICIAL_2026:
        rows.append(
            {
                "october_2026_name": name,
                "person_key": person_key(name),
                "october_2026_designation": designation,
                "seat_group": seat_group(designation),
            }
        )
    return pd.DataFrame(rows)


def era_table(roster: pd.DataFrame) -> pd.DataFrame:
    eras = (
        roster.groupby("era", sort=False)
        .agg(year_start=("year_start", "min"), year_end=("year_end", "max"), confidence=("confidence", "first"), how_inferred=("how_inferred", "first"))
        .reset_index()
    )
    eras["year_start"] = eras["year_start"].astype(int)
    eras["year_end"] = eras["year_end"].astype(int)
    return eras.sort_values("year_start", kind="mergesort").reset_index(drop=True)


def assign_era(year: int, eras: pd.DataFrame) -> str:
    for row in eras.itertuples(index=False):
        if int(row.year_start) <= int(year) <= int(row.year_end):
            return str(row.era)
    return ""


def audit_roster(roster: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Confidence labels stay on the snapshot. The 2026 designation is not copied backward."""
    official = official_crosswalk().set_index("person_key")
    eras = era_table(roster)
    latest = str(eras.iloc[-1]["era"])
    long_rows = []
    for row in roster.itertuples(index=False):
        key = person_key(row.member_name)
        named = _named(row.member_name)
        on_page = named and key in official.index
        designation = official.loc[key, "october_2026_designation"] if on_page else ""
        page_name = official.loc[key, "october_2026_name"] if on_page else ""
        long_rows.append(
            {
                "era": row.era,
                "year_start": int(row.year_start),
                "year_end": int(row.year_end),
                "member_name": row.member_name,
                "person_key": key,
                "role_on_snapshot": row.role,
                "how_inferred": row.how_inferred,
                "confidence": row.confidence,
                "named_person": int(named),
                "on_october_2026_page": int(on_page),
                "october_2026_name": page_name,
                "october_2026_designation": designation if row.era == latest else "",
                "attendance_recorded": "no",
                "ballot_recorded": "no",
                "local_members_named": "no",
                "notes": row.notes,
            }
        )
    audited = pd.DataFrame(long_rows)
    people = []
    for key, group in audited.loc[audited["named_person"].eq(1)].groupby("person_key", sort=False):
        ordered = group.sort_values("year_start", kind="mergesort")
        first = ordered.iloc[0]
        last = ordered.iloc[-1]
        on_page = int(first["on_october_2026_page"]) == 1
        people.append(
            {
                "member_name": first["member_name"],
                "person_key": key,
                "eras": " | ".join(ordered["era"]),
                "roles_on_snapshots": " | ".join(f"{era}: {role}" for era, role in zip(ordered["era"], ordered["role_on_snapshot"])),
                "confidence_by_era": " | ".join(f"{era}: {confidence}" for era, confidence in zip(ordered["era"], ordered["confidence"])),
                "snapshot_count": int(len(ordered)),
                "first_snapshot": first["era"],
                "last_snapshot": last["era"],
                "on_october_2026_page": int(on_page),
                "october_2026_name": first["october_2026_name"],
                "october_2026_designation": official.loc[key, "october_2026_designation"] if on_page else "",
                "seat_group_2026": official.loc[key, "seat_group"] if on_page else "",
            }
        )
    timeline = pd.DataFrame(people)
    overlap_rows = []
    for earlier, later in zip(eras.itertuples(index=False), eras.iloc[1:].itertuples(index=False)):
        left = set(audited.loc[audited["era"].eq(earlier.era) & audited["named_person"].eq(1), "person_key"])
        right = set(audited.loc[audited["era"].eq(later.era) & audited["named_person"].eq(1), "person_key"])
        retained = left & right
        only_earlier = left - right
        only_later = right - left
        union = left | right
        overlap_rows.append(
            {
                "earlier_era": earlier.era,
                "later_era": later.era,
                "earlier_confidence": earlier.confidence,
                "later_confidence": later.confidence,
                "earlier_named": len(left),
                "later_named": len(right),
                "retained": len(retained),
                "only_earlier": len(only_earlier),
                "only_later": len(only_later),
                "jaccard": _round(len(retained) / len(union) if union else None),
                "retained_names": "; ".join(sorted(retained)),
                "only_earlier_names": "; ".join(sorted(only_earlier)),
                "only_later_names": "; ".join(sorted(only_later)),
            }
        )
    return audited, timeline, pd.DataFrame(overlap_rows)


def _interval(values: np.ndarray, draws: int, seed: int) -> tuple[float | None, float | None, float | None]:
    if len(values) == 0:
        return None, None, None
    rng = np.random.default_rng(seed)
    picked = rng.integers(0, len(values), size=(draws, len(values)))
    means = values[picked].mean(axis=1)
    return float(values.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def _rate_interval(numer: np.ndarray, denom: np.ndarray, draws: int, seed: int) -> tuple[float | None, float | None, float | None]:
    if len(numer) == 0 or int(denom.sum()) == 0:
        return None, None, None
    point = float(numer.sum() / denom.sum())
    rng = np.random.default_rng(seed)
    picked = rng.integers(0, len(numer), size=(draws, len(numer)))
    rates = numer[picked].sum(axis=1) / np.maximum(denom[picked].sum(axis=1), 1)
    return point, float(np.quantile(rates, 0.025)), float(np.quantile(rates, 0.975))


def competition_frame(competitors: pd.DataFrame, events: pd.DataFrame, firms: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    """One row per model-sample ranking. Experience uses earlier dates only."""
    history = experience_frame(competitors, events, firms)
    rows = model_rows(competitors, events, firms)
    merged = rows.merge(
        history[["selection_id", "firm_id", "prior_wins", "category"]],
        on=["selection_id", "firm_id"],
        how="left",
        validate="one_to_one",
    )
    attributes = attribute_frame(rows, firms)
    merged = merged.merge(
        attributes[["selection_id", "firm_id", "geo", "staff_group"]],
        on=["selection_id", "firm_id"],
        how="left",
    )
    eras = era_table(roster)
    records = []
    for selection_id, group in merged.groupby("selection_id", sort=False):
        winner = group.loc[group["is_winner"]].iloc[0]
        prior = group["prior_wins"].astype(int)
        geo = str(winner["geo"]) if pd.notna(winner["geo"]) else "unknown"
        staff = str(winner["staff_group"]) if pd.notna(winner["staff_group"]) else ""
        year = int(winner["selection_year"])
        records.append(
            {
                "selection_id": selection_id,
                "selection_date": winner["selection_date"],
                "selection_year": year,
                "era": assign_era(year, eras),
                "n_finalists": int(len(group)),
                "two_firm": int(len(group) == 2),
                "winner_firm_id": winner["firm_id"],
                "winner_prior_wins": int(winner["prior_wins"]),
                "winner_has_prior_rank1": int(int(winner["prior_wins"]) >= 1),
                "mixed_prior": int(prior.ge(1).any() and prior.eq(0).any()),
                "field_prior_share": float(prior.ge(1).mean()),
                "category": winner["category"],
                "category_known": int(winner["category"] in TRACKED),
                "winner_geo": geo if geo else "unknown",
                "winner_staff": staff,
                "zero_prior_rows": int(prior.eq(0).sum()),
                "zero_prior_wins": int(((prior.eq(0)) & group["is_winner"]).sum()),
                "any_prior_rows": int(prior.ge(1).sum()),
                "any_prior_wins": int(((prior.ge(1)) & group["is_winner"]).sum()),
                "finalist_rows": int(len(group)),
                "ma_hq_finalists": int(group["geo"].isin(["boston_hq", "ma_outside_boston"]).sum()),
                "out_of_state_finalists": int(group["geo"].isin(["out_of_state_boston_branch", "out_of_state_no_branch", "out_of_state_branch_undated"]).sum()),
                "known_geo_finalists": int(group["geo"].isin(["boston_hq", "ma_outside_boston", "out_of_state_boston_branch", "out_of_state_no_branch", "out_of_state_branch_undated"]).sum()),
                "banded_finalists": int(group["staff_group"].isin(["11-50", "51-200", "201+"]).sum()),
                "large_finalists": int(group["staff_group"].eq("201+").sum()),
            }
        )
    return pd.DataFrame(records)


def _metric(era: str, name: str, estimate, low, high, numerator, denominator, competitions: int, note: str) -> dict:
    return {
        "era": era,
        "metric": name,
        "estimate": _round(estimate),
        "low": _round(low),
        "high": _round(high),
        "numerator": numerator,
        "denominator": denominator,
        "competitions": competitions,
        "note": note,
    }


def era_metrics(competitions: pd.DataFrame, draws: int = DRAWS, seed: int = SEED) -> pd.DataFrame:
    rows = []
    for era, part in competitions.groupby("era", sort=False):
        if era == "":
            continue
        n = int(len(part))
        winners = part["winner_firm_id"].tolist()
        hhi = concentration(winners)["hhi"]
        top5 = concentration(winners)["top5_share"]
        two, two_low, two_high = _interval(part["two_firm"].to_numpy(dtype=float), draws, seed)
        field, field_low, field_high = _interval(part["n_finalists"].to_numpy(dtype=float), draws, seed)
        mixed = part.loc[part["mixed_prior"].eq(1)]
        excess_values = (mixed["winner_has_prior_rank1"] - mixed["field_prior_share"]).to_numpy(dtype=float)
        excess, excess_low, excess_high = _interval(excess_values, draws, seed + 1)
        zero_rate, zero_low, zero_high = _rate_interval(
            part["zero_prior_wins"].to_numpy(dtype=float),
            part["zero_prior_rows"].to_numpy(dtype=float),
            draws,
            seed + 2,
        )
        prior_rate, prior_low, prior_high = _rate_interval(
            part["any_prior_wins"].to_numpy(dtype=float),
            part["any_prior_rows"].to_numpy(dtype=float),
            draws,
            seed + 3,
        )
        located = part.loc[part["winner_geo"].ne("unknown")]
        ma_rate, ma_low, ma_high = _rate_interval(
            located["winner_geo"].isin(["boston_hq", "ma_outside_boston"]).to_numpy(dtype=float),
            np.ones(len(located)),
            draws,
            seed + 4,
        )
        banded = part.loc[part["winner_staff"].isin(["11-50", "51-200", "201+"])]
        large_rate, large_low, large_high = _rate_interval(
            banded["winner_staff"].eq("201+").to_numpy(dtype=float),
            np.ones(len(banded)),
            draws,
            seed + 5,
        )
        known_type = part.loc[part["category_known"].eq(1)]
        counts = Counter(known_type["category"])
        top_count = counts.most_common(1)[0][1] if counts else 0
        tied = sorted(name for name, count in counts.items() if count == top_count)
        dominant = " and ".join(tied)
        dominant_n = top_count
        ma_finalists, ma_finalists_low, ma_finalists_high = _rate_interval(
            part["ma_hq_finalists"].to_numpy(dtype=float),
            part["known_geo_finalists"].to_numpy(dtype=float),
            draws,
            seed + 6,
        )
        large_finalists, large_finalists_low, large_finalists_high = _rate_interval(
            part["large_finalists"].to_numpy(dtype=float),
            part["banded_finalists"].to_numpy(dtype=float),
            draws,
            seed + 7,
        )
        rows.extend(
            [
                _metric(era, "competitions", n, None, None, n, n, n, "Model sample. 2026 is partial through 2026-09-22."),
                _metric(era, "unique_winners", concentration(winners)["unique_winners"], None, None, concentration(winners)["unique_winners"], n, n, "Distinct rank-1 firm ids."),
                _metric(era, "hhi", hhi, None, None, None, n, n, "Rank-1 Herfindahl index. A resampled percentile interval sits above this estimate, because drawing the same ranking twice shrinks the winner set, so no interval is reported."),
                _metric(era, "top5_share", top5, None, None, None, n, n, "Share of rankings held by the five most frequent rank-1 firms inside that snapshot window. The same resampling problem applies, so no interval is reported."),
                _metric(era, "two_firm_share", two, two_low, two_high, int(part["two_firm"].sum()), n, n, "Rankings with exactly two firms."),
                _metric(era, "mean_field", field, field_low, field_high, int(part["finalist_rows"].sum()), n, n, "Mean firms on the published list."),
                _metric(era, "mixed_competitions", int(len(mixed)), None, None, int(len(mixed)), n, n, "Lists that include both a firm with an earlier rank-1 result and a firm with none."),
                _metric(
                    era,
                    "incumbent_excess",
                    excess,
                    excess_low,
                    excess_high,
                    None,
                    int(len(mixed)),
                    int(len(mixed)),
                    "On mixed lists, rank-1 frequency of firms with an earlier rank-1 result, minus their share of the list.",
                ),
                _metric(era, "zero_prior_rank1_rate", zero_rate, zero_low, zero_high, int(part["zero_prior_wins"].sum()), int(part["zero_prior_rows"].sum()), n, "Appearances with no earlier rank-1 result in this archive. Early years are left-censored."),
                _metric(era, "any_prior_rank1_rate", prior_rate, prior_low, prior_high, int(part["any_prior_wins"].sum()), int(part["any_prior_rows"].sum()), n, "Appearances with at least one earlier rank-1 result."),
                _metric(
                    era,
                    "ma_hq_share_of_located_rank1",
                    ma_rate,
                    ma_low,
                    ma_high,
                    int(located["winner_geo"].isin(["boston_hq", "ma_outside_boston"]).sum()),
                    int(len(located)),
                    n,
                    "2026 headquarters among rank-1 firms with a verified location. Unknown locations are out of this denominator.",
                ),
                _metric(era, "rank1_location_unknown", int((part["winner_geo"].eq("unknown")).sum()) / n if n else None, None, None, int(part["winner_geo"].eq("unknown").sum()), n, n, "Share of rank-1 results with no verified 2026 headquarters."),
                _metric(
                    era,
                    "staff_201_share_of_banded_rank1",
                    large_rate,
                    large_low,
                    large_high,
                    int(banded["winner_staff"].eq("201+").sum()) if len(banded) else 0,
                    int(len(banded)),
                    n,
                    "2026 staff band among rank-1 firms with a verified band. A band is not the firm's size at the selection.",
                ),
                _metric(era, "rank1_staff_unknown", int((~part["winner_staff"].isin(["11-50", "51-200", "201+"])).sum()) / n if n else None, None, None, int((~part["winner_staff"].isin(["11-50", "51-200", "201+"])).sum()), n, n, "Share of rank-1 results with no verified 2026 staff band."),
                _metric(
                    era,
                    "dominant_known_school_type",
                    dominant_n / len(known_type) if len(known_type) else None,
                    None,
                    None,
                    dominant_n,
                    int(len(known_type)),
                    n,
                    f"Most common corrected school type among competitions with a stated grade: {dominant or 'none'}.",
                ),
                _metric(
                    era,
                    "ma_hq_share_of_located_finalists",
                    ma_finalists,
                    ma_finalists_low,
                    ma_finalists_high,
                    int(part["ma_hq_finalists"].sum()),
                    int(part["known_geo_finalists"].sum()),
                    n,
                    "2026 Massachusetts headquarters among finalist slots with a verified location.",
                ),
                _metric(
                    era,
                    "staff_201_share_of_banded_finalists",
                    large_finalists,
                    large_finalists_low,
                    large_finalists_high,
                    int(part["large_finalists"].sum()),
                    int(part["banded_finalists"].sum()),
                    n,
                    "2026 staff band of 201 or more among finalist slots with a verified band.",
                ),
            ]
        )
    return pd.DataFrame(rows)


def school_mix(competitions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for era, part in competitions.groupby("era", sort=False):
        if era == "":
            continue
        total = int(len(part))
        for category, count in part["category"].value_counts().items():
            rows.append(
                {
                    "era": era,
                    "category": category,
                    "competitions": int(count),
                    "share_of_era": _round(count / total),
                    "era_competitions": total,
                }
            )
    return pd.DataFrame(rows)


def snapshot_contrasts(competitions: pd.DataFrame, overlap: pd.DataFrame, draws: int = DRAWS, seed: int = SEED) -> pd.DataFrame:
    """Differences across a snapshot boundary. A difference is not a membership effect."""
    rows = []
    for boundary in overlap.itertuples(index=False):
        left = competitions.loc[competitions["era"].eq(boundary.earlier_era)]
        right = competitions.loc[competitions["era"].eq(boundary.later_era)]
        for metric, column in (("two_firm_share", "two_firm"),):
            change, low, high = _difference(left[column].to_numpy(dtype=float), right[column].to_numpy(dtype=float), draws, seed)
            rows.append(
                {
                    "earlier_era": boundary.earlier_era,
                    "later_era": boundary.later_era,
                    "metric": metric,
                    "later_minus_earlier": _round(change),
                    "low": _round(low),
                    "high": _round(high),
                    "earlier_competitions": int(len(left)),
                    "later_competitions": int(len(right)),
                }
            )
        left_mixed = left.loc[left["mixed_prior"].eq(1)]
        right_mixed = right.loc[right["mixed_prior"].eq(1)]
        left_excess = (left_mixed["winner_has_prior_rank1"] - left_mixed["field_prior_share"]).to_numpy(dtype=float)
        right_excess = (right_mixed["winner_has_prior_rank1"] - right_mixed["field_prior_share"]).to_numpy(dtype=float)
        change, low, high = _difference(left_excess, right_excess, draws, seed + 1)
        rows.append(
            {
                "earlier_era": boundary.earlier_era,
                "later_era": boundary.later_era,
                "metric": "incumbent_excess",
                "later_minus_earlier": _round(change),
                "low": _round(low),
                "high": _round(high),
                "earlier_competitions": int(len(left_mixed)),
                "later_competitions": int(len(right_mixed)),
            }
        )
    return pd.DataFrame(rows)


def _difference(left: np.ndarray, right: np.ndarray, draws: int, seed: int) -> tuple[float | None, float | None, float | None]:
    if len(left) == 0 or len(right) == 0:
        return None, None, None
    point = float(right.mean() - left.mean())
    rng = np.random.default_rng(seed)
    left_pick = rng.integers(0, len(left), size=(draws, len(left)))
    right_pick = rng.integers(0, len(right), size=(draws, len(right)))
    samples = right[right_pick].mean(axis=1) - left[left_pick].mean(axis=1)
    return point, float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))


def page_audit_summary() -> dict:
    groups = Counter(seat_group(designation) for _, designation in OFFICIAL_2026)
    return {
        "october_2026_names": len(OFFICIAL_2026),
        "process_page_appointed_members": PROCESS_PAGE_APPOINTED,
        "process_page_local_members": PROCESS_PAGE_LOCAL,
        "seat_groups": dict(groups),
        "names_not_labeled_staff": groups["designee"] + groups["public_member"],
        "names_labeled_staff": groups["msba_staff"],
        "staff_alternates": groups["staff_alternate"],
    }


def build_outputs(competitors: pd.DataFrame, events: pd.DataFrame, firms: pd.DataFrame, roster: pd.DataFrame) -> dict:
    audited, timeline, overlap = audit_roster(roster)
    competitions = competition_frame(competitors, events, firms, roster)
    metrics = era_metrics(competitions)
    contrasts = snapshot_contrasts(competitions, overlap)
    return {
        "audited": audited,
        "timeline": timeline,
        "overlap": overlap,
        "competitions": competitions,
        "metrics": metrics,
        "schools": school_mix(competitions),
        "contrasts": contrasts,
        "page": page_audit_summary(),
        "eras": era_table(roster),
    }


def write_outputs(outputs: dict, processed, reports) -> None:
    processed.mkdir(parents=True, exist_ok=True)
    figures = reports / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    outputs["audited"].to_csv(processed / "panel_roster_audit.csv", index=False)
    outputs["timeline"].to_csv(processed / "panel_member_timeline.csv", index=False)
    outputs["overlap"].to_csv(processed / "panel_snapshot_overlap.csv", index=False)
    outputs["competitions"].to_csv(processed / "panel_era_competitions.csv", index=False)
    outputs["metrics"].to_csv(processed / "panel_era_outcomes.csv", index=False)
    outputs["schools"].to_csv(processed / "panel_era_school_types.csv", index=False)
    outputs["contrasts"].to_csv(processed / "panel_snapshot_contrasts.csv", index=False)
    summary = {
        "page": outputs["page"],
        "eras": outputs["eras"].to_dict(orient="records"),
        "overlap": outputs["overlap"].drop(columns=["retained_names", "only_earlier_names", "only_later_names"]).to_dict(orient="records"),
        "contrasts": outputs["contrasts"].to_dict(orient="records"),
        "competitions": int(len(outputs["competitions"])),
        "unassigned": int(outputs["competitions"]["era"].eq("").sum()),
    }
    (processed / "panel_history_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _figures(outputs, figures)


def _figures(outputs: dict, figures) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 10,
        }
    )
    overlap = outputs["overlap"]
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    x = np.arange(len(overlap))
    ax.bar(x, overlap["retained"], color="#0072B2", label="On both snapshots")
    ax.bar(x, overlap["only_earlier"] + overlap["only_later"], bottom=overlap["retained"], color="#D55E00", label="On only one snapshot")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{a}\nto {b}" for a, b in zip(overlap["earlier_era"], overlap["later_era"])])
    ax.set_ylabel("Named people")
    ax.set_title("Named people across consecutive roster snapshots")
    ax.legend(frameon=False)
    fig.text(0.01, 0.01, "A vacant seat is not a person. Missing from the next snapshot is not a dated departure. Carried years are not attendance.", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(figures / "05_snapshot_turnover.png", dpi=150)
    plt.close(fig)

    metrics = outputs["metrics"]
    eras = list(outputs["eras"]["era"])
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.8))
    _bar_metric(axes[0], metrics, eras, "two_firm_share", "Two-firm rankings (%)", "competitions", "Two-firm share")
    _bar_metric(axes[1], metrics, eras, "incumbent_excess", "Incumbent excess (points)", "mixed_competitions", "Excess on mixed lists")
    fig.text(0.01, 0.01, "Intervals resample competitions, seed 20261020. Snapshot windows are not confirmed membership. 2026 is partial.", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(figures / "05_outcomes_by_snapshot.png", dpi=150)
    plt.close(fig)


def _bar_metric(ax, metrics: pd.DataFrame, eras: list[str], metric: str, ylabel: str, count_metric: str, title: str) -> None:
    short = {
        "2007-2009": "2007–09",
        "2010-2012": "2010–12",
        "2013-2017": "2013–17",
        "2018-2024": "2018–24",
        "2025-2026": "2025–26",
    }
    part = metrics.loc[metrics["metric"].eq(metric)].set_index("era").reindex(eras)
    x = np.arange(len(eras))
    estimate = part["estimate"].astype(float) * 100
    low = part["low"].astype(float) * 100
    high = part["high"].astype(float) * 100
    ax.bar(x, estimate, color="#0072B2", width=0.72)
    ax.errorbar(x, estimate, yerr=[estimate - low, high - estimate], fmt="none", ecolor="#222222", capsize=3)
    ax.axhline(0, color="#888888", lw=1)
    ax.set_xticks(x)
    labels = []
    for era in eras:
        counts = metrics.loc[metrics["era"].eq(era) & metrics["metric"].eq(count_metric), "numerator"]
        count = int(counts.iloc[0]) if len(counts) else 0
        labels.append(f"{short.get(era, era)}\nn={count}")
    ax.set_xticklabels(labels)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
