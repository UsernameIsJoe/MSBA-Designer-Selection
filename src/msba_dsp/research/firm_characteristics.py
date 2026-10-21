"""Present-day firm attributes and published DSP rankings.

Staff size and office descriptions are research attributes dated 2026. They are
not treated as facts the panel knew at an earlier selection. Founding year is
used only to compute age at the selection, and only when a year was recorded.
Missing attributes stay missing.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from msba_dsp.research.market_structure import model_rows

BAND_ORDER = ["11-50", "51-200", "201-500", "501-1000", "1001+"]
BAND_RANK = {band: index + 1 for index, band in enumerate(BAND_ORDER)}
COLLAPSED = {"11-50": "11-50", "51-200": "51-200", "201-500": "201+", "501-1000": "201+", "1001+": "201+"}
GEO_PRIMARY = ["boston_hq", "ma_outside_boston", "out_of_state_boston_branch", "out_of_state_no_branch"]
GEO_LABELS = {
    "boston_hq": "Boston headquarters",
    "ma_outside_boston": "Massachusetts headquarters outside Boston",
    "out_of_state_boston_branch": "Out-of-state headquarters, Boston branch open",
    "out_of_state_no_branch": "Out-of-state headquarters, no Boston office",
    "out_of_state_branch_undated": "Out-of-state headquarters, branch timing unknown",
    "unknown": "Unknown",
}


def staff_band(raw: str, drop_point_estimates: bool = False, thousand_with_larger: bool = False) -> str:
    """Map a recorded size to a non-overlapping band. No midpoint is invented."""
    text = str(raw).strip().lower().replace(",", "").replace("~", "").replace(" ", "")
    ranged = {"11-50": "11-50", "51-200": "51-200", "201-500": "201-500", "1001-5000": "1001+"}
    points = {"20": "11-50", "180": "51-200", "230": "201-500", "399": "201-500", "1000": "501-1000", "1800": "1001+"}
    if text in ranged:
        band = ranged[text]
    elif text in points and not drop_point_estimates:
        band = points[text]
    else:
        return ""
    if thousand_with_larger and band == "501-1000":
        return "1001+"
    return band


def geography(hq: str, boston_role: str, year: int, credit_undated_branch: bool = False, inner_core_as_boston: bool = False) -> str:
    """Place a firm in one headquarters group for a given selection year."""
    place = str(hq).strip().lower()
    role = str(boston_role).strip().lower()
    if "if confirmed" in role or "if active" in role:
        return "unknown"
    if inner_core_as_boston and place in {"cambridge ma", "somerville ma"}:
        return "boston_hq"
    if place in {"boston ma", "charlestown ma"} or "neighborhood" in role:
        return "boston_hq"
    if place.endswith(" ma"):
        return "ma_outside_boston"
    if not place:
        return "unknown"
    opened = 2010 if "opened 2010" in role else 2013 if "opened 2013" in role else None
    if opened is not None:
        return "out_of_state_boston_branch" if int(year) >= opened else "out_of_state_no_branch"
    if "boston branch" in role:
        return "out_of_state_boston_branch" if credit_undated_branch else "out_of_state_branch_undated"
    if "no boston" in role:
        return "out_of_state_no_branch"
    return "unknown"


def age_at_selection(year: int, founded: str) -> float | None:
    text = str(founded).strip()
    if not text:
        return None
    try:
        founded_year = int(float(text))
    except ValueError:
        return None
    age = int(year) - founded_year
    if age < 0 or age > 200:
        return None
    return float(age)


def _blank(value: object) -> bool:
    return str(value).strip() == "" or str(value).lower() == "nan"


def attribute_frame(
    rows: pd.DataFrame,
    firms: pd.DataFrame,
    drop_point_estimates: bool = False,
    thousand_with_larger: bool = False,
    credit_undated_branch: bool = False,
    inner_core_as_boston: bool = False,
) -> pd.DataFrame:
    """Attach present-day attributes. Joint ventures are left out of the comparisons."""
    keep = firms[
        [
            "firm_id",
            "canonical_firm_name",
            "staff_size",
            "staff_basis",
            "founded_year",
            "hq_location",
            "boston_role",
            "nationwide_operations",
            "verification_status",
            "joint_venture",
        ]
    ].drop_duplicates("firm_id")
    frame = rows.merge(keep, on="firm_id", how="left", suffixes=("", "_dir"))
    frame = frame.loc[~frame["is_joint_venture"]].copy()
    frame["staff_band"] = [
        staff_band(value, drop_point_estimates, thousand_with_larger) if str(status).startswith("Verified") else ""
        for value, status in zip(frame["staff_size"], frame["verification_status"])
    ]
    frame["staff_rank"] = frame["staff_band"].map(BAND_RANK)
    frame["staff_group"] = frame["staff_band"].map(COLLAPSED).fillna("")
    frame["geo"] = [
        geography(hq, role, int(year), credit_undated_branch, inner_core_as_boston)
        if str(status).startswith("Verified") or str(status).startswith("Partial")
        else "unknown"
        for hq, role, year, status in zip(
            frame["hq_location"], frame["boston_role"], frame["selection_year"], frame["verification_status"]
        )
    ]
    # A partial profile does not confirm a headquarters category.
    frame.loc[~frame["verification_status"].astype(str).str.startswith("Verified"), "geo"] = "unknown"
    frame["age"] = [
        age_at_selection(int(year), founded) if str(status).startswith("Verified") else None
        for year, founded, status in zip(frame["selection_year"], frame["founded_year"], frame["verification_status"])
    ]
    frame["nationwide"] = np.where(
        frame["verification_status"].astype(str).str.startswith("Verified") & frame["nationwide_operations"].eq("Yes"),
        "yes",
        np.where(frame["nationwide_operations"].eq("") | ~frame["verification_status"].astype(str).str.startswith("Verified"), "unknown", "no"),
    )
    return frame


def coverage_table(frame: pd.DataFrame, competitions: int) -> dict:
    firms = frame.drop_duplicates("firm_id")
    return {
        "finalist_rows": int(len(frame)),
        "firms": int(len(firms)),
        "competitions": int(competitions),
        "firms_with_staff_band": int(firms["staff_band"].ne("").sum()),
        "rows_with_staff_band": int(frame["staff_band"].ne("").sum()),
        "firms_with_primary_geography": int(firms["geo"].isin(GEO_PRIMARY).sum()),
        "rows_with_primary_geography": int(frame["geo"].isin(GEO_PRIMARY).sum()),
        "firms_with_age": int(firms["age"].notna().sum()),
        "rows_with_age": int(frame["age"].notna().sum()),
        "firms_nationwide_yes": int(firms["nationwide"].eq("yes").sum()),
    }


def _winner_against_field(frame: pd.DataFrame, value_column: str) -> pd.DataFrame:
    """One row per competition in which the winner and another finalist both have a value."""
    records = []
    for selection_id, group in frame.groupby("selection_id", sort=False):
        known = group.loc[group[value_column].notna()]
        if len(known) < 2:
            continue
        winners = known.loc[known["is_winner"]]
        if len(winners) != 1:
            continue
        winner_value = float(winners[value_column].iloc[0])
        others = known.loc[~known["is_winner"], value_column].astype(float)
        records.append(
            {
                "selection_id": selection_id,
                "selection_year": int(group["selection_year"].iloc[0]),
                "n_known": int(len(known)),
                "winner_value": winner_value,
                "field_max": float(known[value_column].max()),
                "unique_max": int(known[value_column].eq(known[value_column].max()).sum() == 1),
                "winner_is_unique_max": int(winner_value == float(known[value_column].max()) and known[value_column].eq(known[value_column].max()).sum() == 1),
                "winner_strictly_above_other_mean": int(winner_value > float(others.mean())),
            }
        )
    return pd.DataFrame(records)


def contrast_summary(detail: pd.DataFrame, draws: int = 2000, seed: int = 20261020) -> dict:
    if detail.empty:
        return {"competitions": 0}
    unique = detail.loc[detail["unique_max"].eq(1)]
    observed = float(unique["winner_is_unique_max"].mean()) if len(unique) else None
    baseline = float((1 / unique["n_known"]).mean()) if len(unique) else None
    above = float(detail["winner_strictly_above_other_mean"].mean())
    rng = np.random.default_rng(seed)
    index = np.arange(len(detail))
    boot_above = []
    boot_gap = []
    for _ in range(draws):
        take = detail.iloc[rng.choice(index, size=len(detail), replace=True)]
        boot_above.append(float(take["winner_strictly_above_other_mean"].mean()))
        usable = take.loc[take["unique_max"].eq(1)]
        if len(usable):
            boot_gap.append(float(usable["winner_is_unique_max"].mean() - (1 / usable["n_known"]).mean()))
    gap = None if observed is None else observed - baseline
    return {
        "competitions": int(len(detail)),
        "competitions_with_unique_max": int(len(unique)),
        "winner_is_unique_max": _round(observed),
        "random_finalist_baseline": _round(baseline),
        "unique_max_gap": _round(gap),
        "unique_max_gap_low": _round(float(np.quantile(boot_gap, 0.025))) if boot_gap else None,
        "unique_max_gap_high": _round(float(np.quantile(boot_gap, 0.975))) if boot_gap else None,
        "winner_above_other_mean": _round(above),
        "winner_above_other_mean_low": _round(float(np.quantile(boot_above, 0.025))),
        "winner_above_other_mean_high": _round(float(np.quantile(boot_above, 0.975))),
    }


def geography_excess(frame: pd.DataFrame, draws: int = 2000, seed: int = 20261020) -> pd.DataFrame:
    """Winner frequency minus field share, inside competitions with two located firms."""
    records = []
    for selection_id, group in frame.groupby("selection_id", sort=False):
        known = group.loc[group["geo"].isin(GEO_PRIMARY)]
        winners = known.loc[known["is_winner"]]
        if len(known) < 2 or len(winners) != 1:
            continue
        shares = known["geo"].value_counts(normalize=True)
        winner_geo = winners["geo"].iloc[0]
        for category in GEO_PRIMARY:
            records.append(
                {
                    "selection_id": selection_id,
                    "category": category,
                    "excess": float(winner_geo == category) - float(shares.get(category, 0.0)),
                }
            )
    detail = pd.DataFrame(records)
    if detail.empty:
        return detail
    rng = np.random.default_rng(seed)
    ids = detail["selection_id"].drop_duplicates().to_numpy()
    rows = []
    for category in GEO_PRIMARY:
        part = detail.loc[detail["category"].eq(category)]
        point = float(part["excess"].mean())
        samples = []
        for _ in range(draws):
            drawn = rng.choice(ids, size=len(ids), replace=True)
            samples.append(float(part.set_index("selection_id").loc[drawn, "excess"].mean()))
        column = np.asarray(samples)
        rows.append(
            {
                "category": category,
                "label": GEO_LABELS[category],
                "competitions": int(part["selection_id"].nunique()),
                "excess": _round(point),
                "excess_low": _round(float(np.quantile(column, 0.025))),
                "excess_high": _round(float(np.quantile(column, 0.975))),
            }
        )
    return pd.DataFrame(rows)


def _fit_arrays(matrix: np.ndarray, winner: np.ndarray, slices: list[np.ndarray], penalty: float = 1e-4) -> np.ndarray | None:
    if matrix.size == 0 or np.allclose(matrix, 0):
        return None

    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        utility = matrix @ beta
        gradient = penalty * beta
        loss = 0.5 * penalty * float(np.dot(beta, beta))
        for idx in slices:
            scores = utility[idx]
            top = float(np.max(scores))
            weights = np.exp(scores - top)
            total = float(weights.sum())
            probabilities = weights / total
            chosen = winner[idx] == 1
            loss += top + float(np.log(total) - scores[chosen][0])
            gradient += matrix[idx].T @ (probabilities - chosen.astype(float))
        return loss, gradient

    result = minimize(objective, np.zeros(matrix.shape[1]), method="BFGS", jac=True, options={"maxiter": 60})
    if not result.success or not np.all(np.isfinite(result.x)):
        return None
    return np.asarray(result.x, dtype=float)


def _competition_arrays(frame: pd.DataFrame, columns: list[str]) -> list[tuple[np.ndarray, np.ndarray]]:
    pieces = []
    ordered = frame.sort_values(["selection_id", "firm_id"], kind="mergesort")
    for _, group in ordered.groupby("selection_id", sort=False):
        winner = group["is_winner"].to_numpy(dtype=int)
        if int(winner.sum()) != 1:
            continue
        pieces.append((group[columns].to_numpy(dtype=float), winner))
    return pieces


def _fit_logit(frame: pd.DataFrame, columns: list[str], penalty: float = 1e-4) -> dict | None:
    pieces = _competition_arrays(frame, columns)
    if not pieces:
        return None
    matrix = np.vstack([matrix for matrix, _ in pieces])
    winner = np.concatenate([winner for _, winner in pieces])
    slices = []
    start = 0
    for block, _ in pieces:
        slices.append(np.arange(start, start + len(block)))
        start += len(block)
    beta = _fit_arrays(matrix, winner, slices, penalty)
    if beta is None:
        return None
    return {"beta": beta, "names": columns, "competitions": len(pieces), "rows": int(len(winner))}


def _bootstrap_logit(frame: pd.DataFrame, columns: list[str], draws: int = 400, seed: int = 20261020) -> pd.DataFrame:
    pieces = _competition_arrays(frame, columns)
    if not pieces:
        return pd.DataFrame()
    matrix = np.vstack([block for block, _ in pieces])
    winner = np.concatenate([flags for _, flags in pieces])
    slices = []
    start = 0
    for block, _ in pieces:
        slices.append(np.arange(start, start + len(block)))
        start += len(block)
    point = _fit_arrays(matrix, winner, slices)
    if point is None:
        return pd.DataFrame()
    point_beta = point
    point = {"beta": point_beta, "competitions": len(pieces), "rows": int(sum(len(flags) for _, flags in pieces))}
    rng = np.random.default_rng(seed)
    index = np.arange(len(pieces))
    samples = []
    for _ in range(draws):
        drawn = rng.choice(index, size=len(index), replace=True)
        drawn_matrix = np.vstack([pieces[item][0] for item in drawn])
        drawn_winner = np.concatenate([pieces[item][1] for item in drawn])
        drawn_slices = []
        cursor = 0
        for item in drawn:
            length = len(pieces[item][1])
            drawn_slices.append(np.arange(cursor, cursor + length))
            cursor += length
        fitted = _fit_arrays(drawn_matrix, drawn_winner, drawn_slices)
        if fitted is not None:
            samples.append(fitted)
    stack = np.vstack(samples) if samples else np.empty((0, len(columns)))
    rows = []
    for index, name in enumerate(columns):
        column = stack[:, index] if len(stack) else np.array([])
        rows.append(
            {
                "term": name,
                "estimate": _round(float(point["beta"][index]), 3),
                "ci_low": _round(float(np.quantile(column, 0.025)), 3) if len(column) else None,
                "ci_high": _round(float(np.quantile(column, 0.975)), 3) if len(column) else None,
                "draws": int(len(stack)),
                "competitions": point["competitions"],
                "rows": point["rows"],
            }
        )
    return pd.DataFrame(rows)


def size_logit(frame: pd.DataFrame) -> pd.DataFrame:
    known = frame.loc[frame["staff_group"].ne("")].copy()
    varying = []
    for selection_id, group in known.groupby("selection_id", sort=False):
        if group["staff_group"].nunique() >= 2 and int(group["is_winner"].sum()) == 1:
            varying.append(group)
    if not varying:
        return pd.DataFrame()
    sample = pd.concat(varying, ignore_index=True)
    for group in ["51-200", "201+"]:
        sample[f"group_{group}"] = sample["staff_group"].eq(group).astype(float)
    return _bootstrap_logit(sample, ["group_51-200", "group_201+"]).assign(reference="11-50", model="collapsed_staff_band")


def age_logit(frame: pd.DataFrame) -> pd.DataFrame:
    known = frame.loc[frame["age"].notna(), ["selection_id", "firm_id", "is_winner", "age"]].copy()
    parts = []
    for _, group in known.groupby("selection_id", sort=False):
        if len(group) < 2 or group["age"].nunique() < 2 or int(group["is_winner"].sum()) != 1:
            continue
        group = group.copy()
        group["age_within_field"] = (group["age"] - group["age"].mean()) / 10.0
        parts.append(group)
    if not parts:
        return pd.DataFrame()
    sample = pd.concat(parts, ignore_index=True)
    return _bootstrap_logit(sample, ["age_within_field"]).assign(reference="field mean age", model="age_per_10_years")


def band_counts(frame: pd.DataFrame) -> pd.DataFrame:
    known = frame.loc[frame["staff_band"].ne("")]
    rows = []
    for band in BAND_ORDER:
        part = known.loc[known["staff_band"].eq(band)]
        rows.append(
            {
                "staff_band": band,
                "firms": int(part["firm_id"].nunique()),
                "finalist_rows": int(len(part)),
                "rank1_results": int(part["is_winner"].sum()),
            }
        )
    return pd.DataFrame(rows)


def geo_counts(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for category, label in GEO_LABELS.items():
        part = frame.loc[frame["geo"].eq(category)]
        rows.append(
            {
                "category": category,
                "label": label,
                "firms": int(part["firm_id"].nunique()),
                "finalist_rows": int(len(part)),
                "rank1_results": int(part["is_winner"].sum()),
            }
        )
    return pd.DataFrame(rows)


def age_bins(frame: pd.DataFrame) -> pd.DataFrame:
    known = frame.loc[frame["age"].notna()].copy()
    bins = [0, 25, 50, 75, 200]
    labels = ["Under 25", "25-49", "50-74", "75 or older"]
    known["age_bin"] = pd.cut(known["age"], bins=bins, labels=labels, right=False)
    rows = []
    for label in labels:
        part = known.loc[known["age_bin"].astype(str).eq(label)]
        rows.append(
            {
                "age_bin": label,
                "finalist_rows": int(len(part)),
                "rank1_results": int(part["is_winner"].sum()),
                "firms": int(part["firm_id"].nunique()),
            }
        )
    return pd.DataFrame(rows)


def _school_table(frame: pd.DataFrame) -> pd.DataFrame:
    known = frame.loc[frame["staff_group"].ne("") & frame["school_category"].isin(["elementary", "middle", "high", "vocational"])]
    rows = []
    for (category, group), part in known.groupby(["school_category", "staff_group"], sort=False):
        rows.append(
            {
                "school_category": category,
                "staff_group": group,
                "finalist_rows": int(len(part)),
                "rank1_results": int(part["is_winner"].sum()),
            }
        )
    return pd.DataFrame(rows)


def profile_counts(frame: pd.DataFrame) -> pd.DataFrame:
    """Coarse profiles only. A profile needs both a location and a size band."""
    work = frame.loc[frame["staff_group"].ne("") & frame["geo"].isin(GEO_PRIMARY)].copy()
    work["profile"] = np.select(
        [
            work["geo"].eq("boston_hq") & work["staff_group"].eq("11-50"),
            work["geo"].isin(["boston_hq", "ma_outside_boston"]) & work["staff_group"].ne("11-50"),
            work["geo"].eq("ma_outside_boston") & work["staff_group"].eq("11-50"),
            work["geo"].eq("out_of_state_boston_branch"),
            work["geo"].eq("out_of_state_no_branch"),
        ],
        [
            "Boston headquarters, 11-50 staff",
            "Massachusetts headquarters, including Boston, 51 or more staff",
            "Massachusetts outside Boston, 11-50 staff",
            "Out-of-state headquarters with a dated Boston branch",
            "Out-of-state headquarters, no Boston office",
        ],
        default="",
    )
    rows = []
    for profile, part in work.loc[work["profile"].ne("")].groupby("profile", sort=False):
        rows.append(
            {
                "profile": profile,
                "firms": int(part["firm_id"].nunique()),
                "finalist_rows": int(len(part)),
                "rank1_results": int(part["is_winner"].sum()),
            }
        )
    return pd.DataFrame(rows)


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return round(float(value), digits)


def build_outputs(competitors: pd.DataFrame, events: pd.DataFrame, firms: pd.DataFrame) -> dict:
    rows = model_rows(competitors, events, firms)
    base = attribute_frame(rows, firms)
    size_detail = _winner_against_field(base.assign(value=base["staff_rank"]), "value")
    age_detail = _winner_against_field(base.assign(value=base["age"]), "value")
    point_free = attribute_frame(rows, firms, drop_point_estimates=True)
    upper_thousand = attribute_frame(rows, firms, thousand_with_larger=True)
    undated = attribute_frame(rows, firms, credit_undated_branch=True)
    inner = attribute_frame(rows, firms, inner_core_as_boston=True)
    costs = events[["selection_id", "estimated_cost_low", "estimated_cost_high"]].drop_duplicates("selection_id")
    budgeted = base.merge(costs, on="selection_id", how="left")
    budgeted = budgeted.loc[budgeted["estimated_cost_low"].ne("") & budgeted["estimated_cost_high"].ne("")]
    early = base.loc[base["selection_year"].between(2012, 2018)]
    late = base.loc[base["selection_year"] >= 2019]
    numbered = base.loc[base["rank_method"].ne("published_list_order")]
    return {
        "frame": base,
        "coverage": coverage_table(base, rows["selection_id"].nunique()),
        "bands": band_counts(base),
        "geographies": geo_counts(base),
        "ages": age_bins(base),
        "profiles": profile_counts(base),
        "size_contrast": contrast_summary(size_detail),
        "age_contrast": contrast_summary(age_detail),
        "geography_excess": geography_excess(base),
        "size_model": size_logit(base),
        "age_model": age_logit(base),
        "by_school": _school_table(base),
        "budget_contrast": contrast_summary(_winner_against_field(budgeted.assign(value=budgeted["staff_rank"]), "value"), draws=400),
        "sensitivity": pd.DataFrame(
            [
                {"check": "primary_present_day_bands", **contrast_summary(size_detail, draws=400)},
                {"check": "drop_point_estimates", **contrast_summary(_winner_against_field(point_free.assign(value=point_free["staff_rank"]), "value"), draws=400)},
                {"check": "count_about_1000_with_1001_plus", **contrast_summary(_winner_against_field(upper_thousand.assign(value=upper_thousand["staff_rank"]), "value"), draws=400)},
                {"check": "drop_inferred_rank_order", **contrast_summary(_winner_against_field(numbered.assign(value=numbered["staff_rank"]), "value"), draws=400)},
                {"check": "selections_2012_2018", **contrast_summary(_winner_against_field(early.assign(value=early["staff_rank"]), "value"), draws=400)},
                {"check": "selections_2019_2026", **contrast_summary(_winner_against_field(late.assign(value=late["staff_rank"]), "value"), draws=400)},
            ]
        ),
        "geography_undated_branch": geography_excess(undated, draws=400),
        "geography_inner_core": geography_excess(inner, draws=400),
    }


def write_outputs(outputs: dict, processed, reports) -> None:
    processed.mkdir(parents=True, exist_ok=True)
    figures = reports / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    outputs["bands"].to_csv(processed / "firm_staff_bands.csv", index=False)
    outputs["geographies"].to_csv(processed / "firm_geography_counts.csv", index=False)
    outputs["ages"].to_csv(processed / "firm_age_bins.csv", index=False)
    outputs["profiles"].to_csv(processed / "firm_profiles.csv", index=False)
    outputs["geography_excess"].to_csv(processed / "firm_geography_excess.csv", index=False)
    outputs["geography_inner_core"].to_csv(processed / "firm_geography_inner_core.csv", index=False)
    outputs["geography_undated_branch"].to_csv(processed / "firm_geography_undated_branch.csv", index=False)
    outputs["sensitivity"].to_csv(processed / "firm_characteristic_sensitivity.csv", index=False)
    outputs["by_school"].to_csv(processed / "firm_staff_by_school.csv", index=False)
    models = pd.concat([outputs["size_model"], outputs["age_model"]], ignore_index=True)
    models.to_csv(processed / "firm_characteristic_models.csv", index=False)
    summary = {
        "coverage": outputs["coverage"],
        "size_contrast": outputs["size_contrast"],
        "age_contrast": outputs["age_contrast"],
        "budget_contrast": outputs["budget_contrast"],
    }
    (processed / "firm_characteristics_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _figures(outputs, figures)


def _figures(outputs: dict, figures) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "axes.spines.top": False, "axes.spines.right": False, "font.size": 11})
    _coverage_figure(plt, outputs["frame"], figures / "02_attribute_coverage.png")
    _size_figure(plt, outputs["bands"], outputs["size_contrast"], figures / "02_staff_bands.png")
    _geo_figure(plt, outputs["geography_excess"], figures / "02_geography_excess.png")


def _coverage_figure(plt, frame: pd.DataFrame, path) -> None:
    annual = []
    for year, group in frame.groupby("selection_year"):
        annual.append(
            {
                "year": int(year),
                "staff": float(group["staff_band"].ne("").mean()),
                "geography": float(group["geo"].isin(GEO_PRIMARY).mean()),
                "age": float(group["age"].notna().mean()),
            }
        )
    annual = pd.DataFrame(annual)
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.plot(annual["year"], annual["staff"] * 100, marker="o", color="#0072B2", label="Present-day staff band")
    ax.plot(annual["year"], annual["geography"] * 100, marker="o", color="#D55E00", label="Headquarters group")
    ax.plot(annual["year"], annual["age"] * 100, marker="o", color="#009E73", label="Founding year")
    ax.set_ylim(0, 100)
    ax.set_xlabel("Year of the published ranking")
    ax.set_ylabel("Share of finalist rows with the attribute (%)")
    ax.set_title("How much of each year's finalist list has a firm profile")
    ax.legend(frameon=False)
    fig.text(0.01, 0.01, "Staff size and offices are 2026 research attributes. A blank profile stays blank. 2026 is a partial year.", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _size_figure(plt, bands: pd.DataFrame, contrast: dict, path) -> None:
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.bar(bands["staff_band"], bands["finalist_rows"], color="#0072B2", label="Finalist rows")
    ax.bar(bands["staff_band"], bands["rank1_results"], color="#D55E00", width=0.5, label="Rank-1 results")
    ax.set_xlabel("Present-day staff band")
    ax.set_ylabel("Count in the multi-firm rankings")
    ax.set_title("Finalists and rank-1 results by current staff band")
    ax.legend(frameon=False)
    gap = contrast.get("unique_max_gap")
    fig.text(0.01, 0.01, f"Within-competition gap, winner at the unique top band minus chance: {gap}. Bands are not historical headcounts.", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _geo_figure(plt, excess: pd.DataFrame, path) -> None:
    if excess.empty:
        return
    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    y = np.arange(len(excess))
    ax.axvline(0, color="#888888", lw=1)
    ax.errorbar(
        excess["excess"] * 100,
        y,
        xerr=[(excess["excess"] - excess["excess_low"]) * 100, (excess["excess_high"] - excess["excess"]) * 100],
        fmt="o",
        color="#0072B2",
        capsize=3,
    )
    ax.set_yticks(y)
    ax.set_yticklabels(excess["label"])
    ax.set_xlabel("Percentage points")
    ax.set_title("Rank-1 frequency minus the group's share of located finalists")
    fig.text(0.01, 0.01, "Interval is a competition bootstrap. Current offices are not attendance records from the selection year.", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)
