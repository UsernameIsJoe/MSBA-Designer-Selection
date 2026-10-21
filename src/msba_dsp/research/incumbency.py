"""Prior MSBA results and school-type experience, using earlier dates only.

The existing winner model is not refit. School labels used here correct two
classification problems in the stored categories: "Middleborough" is not the
word "middle," and a vocational technical high school is not a combined-grade
school. Names that do not state a grade stay unclassified.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

import numpy as np
import pandas as pd

from msba_dsp.evaluation.metrics import wilson_interval
from msba_dsp.research.firm_characteristics import _fit_arrays, attribute_frame
from msba_dsp.research.market_structure import model_rows

TRACKED = ("elementary", "middle", "high", "vocational", "combined")


def classify_school(school_name: str) -> str:
    """Grade group supported by the school name. Uncertain names stay blank of a grade."""
    text = str(school_name).lower().replace("–", " ").replace("—", " ")
    text = text.replace("/", " / ")
    if re.search(r"\bk\s*[-–]\s*8\b|\bpk\s*[-–]\s*8\b|\bpre-?k\s*[-–]\s*8\b", text):
        return "combined"
    if re.search(r"\bmiddle\s*/\s*high\b|\bmiddle\s*-\s*senior\b", text):
        return "combined"
    if re.search(r"vocational|\btechnical high\b", text):
        return "vocational"
    if re.search(r"elementary|\bprimary\b|\bes\b", text):
        return "elementary"
    if re.search(r"\bmiddle\b|\bintermediate\b|\bms\b", text):
        return "middle"
    if re.search(r"high school|\bsenior high\b|\bhs\b|\bhigh\b", text):
        return "high"
    if "school" in text:
        return "unspecified"
    return "unknown"


def _years_between(earlier: pd.Timestamp, later: pd.Timestamp) -> float:
    return round((later - earlier).days / 365.25, 3)


def experience_frame(competitors: pd.DataFrame, events: pd.DataFrame, firms: pd.DataFrame) -> pd.DataFrame:
    """One row per model-sample finalist. Counts use strictly earlier calendar dates."""
    rows = model_rows(competitors, events, firms)
    if "canonical_firm_name" not in rows.columns:
        rows["canonical_firm_name"] = rows["firm_id"]
    rows["category"] = rows["school_name"].map(classify_school)
    rows["selection_date"] = pd.to_datetime(rows["selection_date"])
    rows = rows.sort_values(["selection_date", "selection_id", "rank_num"], kind="mergesort")

    wins: dict[str, int] = defaultdict(int)
    finals: dict[str, int] = defaultdict(int)
    category_wins: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    category_finals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    win_dates: dict[str, list[pd.Timestamp]] = defaultdict(list)
    last_appearance: dict[str, pd.Timestamp] = {}
    last_win: dict[str, pd.Timestamp] = {}
    records: list[dict] = []

    for selection_date, day in rows.groupby("selection_date", sort=False):
        as_of = pd.Timestamp(selection_date)
        start_3 = as_of - pd.DateOffset(years=3)
        start_5 = as_of - pd.DateOffset(years=5)
        day_records: list[dict] = []
        for _, row in day.iterrows():
            firm_id = row["firm_id"]
            category = row["category"]
            prior_wins = wins[firm_id]
            prior_finals = finals[firm_id]
            same_wins = category_wins[firm_id][category] if category in TRACKED else 0
            same_finals = category_finals[firm_id][category] if category in TRACKED else 0
            previous_appearance = last_appearance.get(firm_id)
            previous_win = last_win.get(firm_id)
            day_records.append(
                {
                    "selection_id": row["selection_id"],
                    "selection_date": as_of.strftime("%Y-%m-%d"),
                    "selection_year": int(row["selection_year"]),
                    "firm_id": firm_id,
                    "firm_name": row.get("canonical_firm_name", ""),
                    "winner": int(row["is_winner"]),
                    "n_finalists": int(day.loc[day["selection_id"].eq(row["selection_id"])].shape[0]),
                    "school_name": row["school_name"],
                    "stored_category": row["school_category"],
                    "category": category,
                    "category_known": int(category in TRACKED),
                    "rank_method": row["rank_method"],
                    "prior_wins": prior_wins,
                    "prior_finals": prior_finals,
                    "shrunk_win_rate": (prior_wins + 0.5) / (prior_finals + 1.0),
                    "wins_previous_3y": sum(1 for when in win_dates[firm_id] if start_3 <= when < as_of),
                    "wins_previous_5y": sum(1 for when in win_dates[firm_id] if start_5 <= when < as_of),
                    "years_since_appearance": "" if previous_appearance is None else _years_between(previous_appearance, as_of),
                    "years_since_win": "" if previous_win is None else _years_between(previous_win, as_of),
                    "prior_same_wins": same_wins,
                    "prior_same_finals": same_finals,
                    "after_first_observed_win": int(prior_wins > 0),
                }
            )
        records.extend(day_records)
        for record in day_records:
            firm_id = record["firm_id"]
            finals[firm_id] += 1
            last_appearance[firm_id] = as_of
            category = record["category"]
            if category in TRACKED:
                category_finals[firm_id][category] += 1
            if record["winner"] == 1:
                wins[firm_id] += 1
                last_win[firm_id] = as_of
                win_dates[firm_id].append(as_of)
                if category in TRACKED:
                    category_wins[firm_id][category] += 1
    return pd.DataFrame(records)


def category_audit(frame: pd.DataFrame) -> pd.DataFrame:
    changed = frame.drop_duplicates("selection_id")
    rows = []
    for stored, group in changed.groupby("stored_category"):
        for corrected, part in group.groupby("category"):
            rows.append(
                {
                    "stored_category": stored,
                    "corrected_category": corrected,
                    "competitions": int(len(part)),
                }
            )
    return pd.DataFrame(rows).sort_values(["stored_category", "corrected_category"])


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return round(float(value), digits)


def outcome_by_prior_wins(frame: pd.DataFrame, minimum_year: int = 2012) -> pd.DataFrame:
    """Win rate on this appearance, by how many earlier rank-1 results the firm had."""
    sample = frame.loc[frame["selection_year"] >= minimum_year]
    rows = []
    for label, part in (
        ("0", sample.loc[sample["prior_wins"].eq(0)]),
        ("1", sample.loc[sample["prior_wins"].eq(1)]),
        ("2", sample.loc[sample["prior_wins"].eq(2)]),
        ("3 or more", sample.loc[sample["prior_wins"].ge(3)]),
    ):
        wins = int(part["winner"].sum())
        trials = int(len(part))
        low, high = wilson_interval(wins, trials)
        rows.append(
            {
                "prior_rank1_results": label,
                "finalist_rows": trials,
                "rank1_results": wins,
                "win_rate": _round(wins / trials) if trials else None,
                "win_rate_low": _round(low),
                "win_rate_high": _round(high),
                "minimum_year": minimum_year,
            }
        )
    return pd.DataFrame(rows)


def incumbency_excess(frame: pd.DataFrame, minimum_year: int = 2012, draws: int = 2000, seed: int = 20261020) -> dict:
    """Rank-1 frequency of firms that already have a rank-1 result, minus their field share."""
    records = []
    sample = frame.loc[frame["selection_year"] >= minimum_year]
    for selection_id, group in sample.groupby("selection_id", sort=False):
        experienced = group["after_first_observed_win"].astype(bool)
        if experienced.sum() == 0 or (~experienced).sum() == 0:
            continue
        winner = group.loc[group["winner"].eq(1)]
        if len(winner) != 1:
            continue
        records.append(
            {
                "selection_id": selection_id,
                "excess": float(int(winner["after_first_observed_win"].iloc[0]) == 1) - float(experienced.mean()),
            }
        )
    detail = pd.DataFrame(records)
    if detail.empty:
        return {"competitions": 0}
    rng = np.random.default_rng(seed)
    index = np.arange(len(detail))
    samples = [float(detail.iloc[rng.choice(index, size=len(detail), replace=True)]["excess"].mean()) for _ in range(draws)]
    point = float(detail["excess"].mean())
    column = np.asarray(samples)
    return {
        "competitions": int(len(detail)),
        "minimum_year": minimum_year,
        "excess": _round(point),
        "excess_low": _round(float(np.quantile(column, 0.025))),
        "excess_high": _round(float(np.quantile(column, 0.975))),
    }


def _pieces(frame: pd.DataFrame, columns: list[str], require_variation: bool) -> list[tuple[str, np.ndarray, np.ndarray]]:
    pieces = []
    for selection_id, group in frame.groupby("selection_id", sort=False):
        if int(group["winner"].sum()) != 1:
            continue
        varies = any(int(group[column].nunique()) >= 2 for column in columns)
        if require_variation and not varies:
            continue
        pieces.append((str(selection_id), group[columns].to_numpy(dtype=float), group["winner"].to_numpy(dtype=int)))
    return pieces


def _probabilities(beta: np.ndarray, matrix: np.ndarray, slices: list[np.ndarray]) -> np.ndarray:
    probabilities = np.zeros(len(matrix))
    utility = matrix @ beta
    for idx in slices:
        scores = utility[idx]
        top = float(np.max(scores))
        weights = np.exp(scores - top)
        probabilities[idx] = weights / weights.sum()
    return probabilities


def _loss_from_probs(winner: np.ndarray, probabilities: np.ndarray, slices: list[np.ndarray]) -> float:
    losses = []
    for idx in slices:
        chosen = idx[winner[idx] == 1]
        losses.append(-np.log(max(float(probabilities[chosen][0]), 1e-12)))
    return float(np.mean(losses))


def fit_comparison(train: pd.DataFrame, test: pd.DataFrame, columns: list[str], bootstrap: bool = True, seed: int = 20261020) -> dict:
    train_pieces = _pieces(train, columns, require_variation=True)
    test_pieces = _pieces(test, columns, require_variation=False)
    if len(train_pieces) < 20 or not test_pieces:
        return {"term_set": ",".join(columns), "competitions_train": len(train_pieces), "competitions_test": len(test_pieces)}
    matrix = np.vstack([block for _, block, _ in train_pieces])
    winner = np.concatenate([flags for _, _, flags in train_pieces])
    slices = []
    start = 0
    for _, block, _ in train_pieces:
        slices.append(np.arange(start, start + len(block)))
        start += len(block)
    beta = _fit_arrays(matrix, winner, slices, penalty=1e-4)
    test_matrix = np.vstack([block for _, block, _ in test_pieces])
    test_winner = np.concatenate([flags for _, _, flags in test_pieces])
    test_slices = []
    start = 0
    for _, block, _ in test_pieces:
        test_slices.append(np.arange(start, start + len(block)))
        start += len(block)
    if beta is None:
        return {"term_set": ",".join(columns), "competitions_train": len(slices), "competitions_test": len(test_slices)}
    probabilities = _probabilities(beta, test_matrix, test_slices)
    loss = _loss_from_probs(test_winner, probabilities, test_slices)
    winner_probability = {}
    for (selection_id, _, flags), idx in zip(test_pieces, test_slices):
        winner_probability[selection_id] = float(probabilities[idx][flags == 1][0])
    column = np.array([])
    if bootstrap:
        rng = np.random.default_rng(seed)
        index = np.arange(len(test_slices))
        losses = []
        for _ in range(2000):
            drawn = rng.choice(index, size=len(index), replace=True)
            chosen = [float(probabilities[test_slices[item]][test_winner[test_slices[item]] == 1][0]) for item in drawn]
            losses.append(float(-np.log(np.clip(chosen, 1e-12, 1)).mean()))
        column = np.asarray(losses)
    coefficients = {name: _round(float(value), 3) for name, value in zip(columns, beta)}
    return {
        "term_set": ",".join(columns),
        "competitions_train": len(slices),
        "competitions_test": len(test_slices),
        "log_loss": _round(loss),
        "log_loss_low": _round(float(np.quantile(column, 0.025))) if len(column) else None,
        "log_loss_high": _round(float(np.quantile(column, 0.975))) if len(column) else None,
        "coefficients": coefficients,
        "winner_probability": winner_probability,
    }


def equal_loss(frame: pd.DataFrame) -> dict:
    losses = []
    probabilities = {}
    for selection_id, group in frame.groupby("selection_id", sort=False):
        if int(group["winner"].sum()) != 1:
            continue
        probability = 1.0 / len(group)
        probabilities[str(selection_id)] = probability
        losses.append(-np.log(probability))
    point = float(np.mean(losses))
    rng = np.random.default_rng(20261020)
    samples = [float(np.mean(rng.choice(losses, size=len(losses), replace=True))) for _ in range(2000)]
    column = np.asarray(samples)
    return {
        "term_set": "equal_probability",
        "competitions_test": len(losses),
        "log_loss": _round(point),
        "log_loss_low": _round(float(np.quantile(column, 0.025))),
        "log_loss_high": _round(float(np.quantile(column, 0.975))),
        "winner_probability": probabilities,
    }


def loss_gap(left: dict, right: dict, seed: int = 20261020) -> dict:
    """Difference left minus right on shared test competitions. Positive means left is worse."""
    if "winner_probability" not in left or "winner_probability" not in right:
        return {}
    shared = [key for key in left["winner_probability"] if key in right["winner_probability"]]
    if len(shared) < 20:
        return {}
    rng = np.random.default_rng(seed)
    index = np.arange(len(shared))
    gaps = []
    for _ in range(2000):
        drawn = [shared[item] for item in rng.choice(index, size=len(index), replace=True)]
        left_loss = -np.log(np.clip([left["winner_probability"][key] for key in drawn], 1e-12, 1)).mean()
        right_loss = -np.log(np.clip([right["winner_probability"][key] for key in drawn], 1e-12, 1)).mean()
        gaps.append(float(left_loss - right_loss))
    column = np.asarray(gaps)
    return {
        "comparison": f"{left['term_set']} minus {right['term_set']}",
        "difference": _round(float(left["log_loss"] - right["log_loss"])),
        "difference_low": _round(float(np.quantile(column, 0.025))),
        "difference_high": _round(float(np.quantile(column, 0.975))),
    }


def walk_forward(frame: pd.DataFrame) -> pd.DataFrame:
    """Score each year from a model fit on all earlier years."""
    rows = []
    years = sorted(int(year) for year in frame["selection_year"].unique() if int(year) >= 2014)
    specs = {
        "prior_wins": ["prior_wins"],
        "wins_plus_same_type": ["prior_wins", "prior_same_wins"],
        "shrunk_win_rate": ["shrunk_win_rate"],
    }
    for year in years:
        train = frame.loc[(frame["selection_year"] < year) & (frame["category_known"].eq(1))]
        test = frame.loc[(frame["selection_year"].eq(year)) & (frame["category_known"].eq(1))]
        if test["selection_id"].nunique() < 8 or train["selection_id"].nunique() < 30:
            continue
        equal = equal_loss(test)
        rows.append({"year": year, "model": "equal_probability", "log_loss": equal["log_loss"], "competitions": equal["competitions_test"]})
        for name, columns in specs.items():
            fitted = fit_comparison(train, test, columns, bootstrap=False)
            rows.append({"year": year, "model": name, "log_loss": fitted.get("log_loss"), "competitions": fitted.get("competitions_test")})
    return pd.DataFrame(rows)


def _attribute_model(competitors_frame: pd.DataFrame, firms: pd.DataFrame, train_end: int) -> dict:
    """Present-day staff and headquarters entered only as a competing description."""
    work = competitors_frame.copy()
    work["is_joint_venture"] = False
    work["is_winner"] = work["winner"].astype(bool)
    attached = attribute_frame(work, firms)
    attached["staff_51_200"] = attached["staff_group"].eq("51-200").astype(float)
    attached["staff_201_plus"] = attached["staff_group"].eq("201+").astype(float)
    attached["boston_hq"] = attached["geo"].eq("boston_hq").astype(float)
    attached["ma_outside"] = attached["geo"].eq("ma_outside_boston").astype(float)
    columns = ["prior_wins", "prior_same_wins", "staff_51_200", "staff_201_plus", "boston_hq", "ma_outside"]
    train = attached.loc[attached["selection_year"] <= train_end]
    test = attached.loc[attached["selection_year"] > train_end]
    return fit_comparison(train, test, columns)


def timing_summary(frame: pd.DataFrame) -> dict:
    known = frame.loc[frame["years_since_win"].ne("")]
    winners = known.loc[known["winner"].eq(1), "years_since_win"].astype(float)
    others = known.loc[known["winner"].eq(0), "years_since_win"].astype(float)
    return {
        "rows_with_a_prior_win": int(len(known)),
        "median_years_since_win_if_rank1": _round(float(winners.median())) if len(winners) else None,
        "median_years_since_win_if_not": _round(float(others.median())) if len(others) else None,
    }


def build_outputs(competitors: pd.DataFrame, events: pd.DataFrame, firms: pd.DataFrame) -> dict:
    frame = experience_frame(competitors, events, firms)
    known = frame.loc[frame["category_known"].eq(1)].copy()
    train = known.loc[known["selection_year"] <= 2018]
    test = known.loc[known["selection_year"] >= 2019]
    train_late = known.loc[known["selection_year"].between(2012, 2018)]
    specs = [
        ["prior_wins"],
        ["prior_finals"],
        ["shrunk_win_rate"],
        ["prior_wins", "prior_finals"],
        ["prior_wins", "prior_same_wins"],
        ["prior_wins", "prior_same_finals"],
        ["prior_wins", "prior_same_wins", "wins_previous_3y"],
        ["prior_wins", "wins_previous_5y"],
    ]
    fitted = [fit_comparison(train, test, columns) for columns in specs]
    late_grade = fit_comparison(train_late, test, ["prior_wins", "prior_same_wins"])
    late_wins = fit_comparison(train_late, test, ["prior_wins"])
    by_name = {item["term_set"]: item for item in fitted}
    attributes = _attribute_model(competitors_frame=known, firms=firms, train_end=2018)
    if attributes:
        fitted.append(attributes)
        by_name[attributes["term_set"]] = attributes
    base_equal = equal_loss(test)
    gaps = [
        loss_gap(by_name["prior_wins"], base_equal),
        loss_gap(by_name["prior_wins"], by_name["prior_wins,prior_same_wins"]),
        loss_gap(by_name["prior_wins,prior_same_wins"], by_name["shrunk_win_rate"]),
        loss_gap(by_name["prior_wins"], by_name["prior_wins,wins_previous_5y"]),
        loss_gap(by_name["shrunk_win_rate"], base_equal),
        loss_gap(by_name["prior_wins,prior_same_wins"], by_name["prior_wins,prior_same_wins,staff_51_200,staff_201_plus,boston_hq,ma_outside"]),
    ]
    public = []
    for item in fitted:
        public.append({key: value for key, value in item.items() if key != "winner_probability"})
    return {
        "frame": frame,
        "audit": category_audit(frame),
        "by_prior_wins": outcome_by_prior_wins(frame),
        "by_prior_wins_full": outcome_by_prior_wins(frame, minimum_year=2007),
        "excess": incumbency_excess(frame),
        "excess_full": incumbency_excess(frame, minimum_year=2007),
        "models": pd.DataFrame(public),
        "equal": {key: value for key, value in base_equal.items() if key != "winner_probability"},
        "gaps": gaps,
        "late_start": {
            "wins": {key: value for key, value in late_wins.items() if key != "winner_probability"},
            "wins_plus_same_type": {key: value for key, value in late_grade.items() if key != "winner_probability"},
        },
        "walk": walk_forward(known),
        "timing": timing_summary(frame),
        "correlation": _round(float(known[["prior_wins", "prior_same_wins"]].corr().iloc[0, 1]), 3),
    }


def write_outputs(outputs: dict, processed, reports) -> None:
    processed.mkdir(parents=True, exist_ok=True)
    figures = reports / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    outputs["audit"].to_csv(processed / "school_category_audit.csv", index=False)
    outputs["by_prior_wins"].to_csv(processed / "incumbency_by_prior_wins.csv", index=False)
    outputs["models"].to_csv(processed / "incumbency_models.csv", index=False)
    outputs["walk"].to_csv(processed / "incumbency_walk_forward.csv", index=False)
    pd.DataFrame(outputs["gaps"]).to_csv(processed / "incumbency_loss_gaps.csv", index=False)
    summary = {
        "excess_from_2012": outputs["excess"],
        "excess_full_archive": outputs["excess_full"],
        "equal_2019_forward": outputs["equal"],
        "timing": outputs["timing"],
        "correlation_prior_wins_same_type": outputs["correlation"],
        "late_start": outputs["late_start"],
    }
    (processed / "incumbency_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _figures(outputs, figures)


def _figures(outputs: dict, figures) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "axes.spines.top": False, "axes.spines.right": False, "font.size": 11})
    rates = outputs["by_prior_wins"]
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    x = np.arange(len(rates))
    ax.bar(x, rates["win_rate"] * 100, color="#0072B2", width=0.7)
    ax.errorbar(
        x,
        rates["win_rate"] * 100,
        yerr=[(rates["win_rate"] - rates["win_rate_low"]) * 100, (rates["win_rate_high"] - rates["win_rate"]) * 100],
        fmt="none",
        ecolor="#222222",
        capsize=3,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(rates["prior_rank1_results"])
    ax.set_ylim(0, 80)
    ax.set_xlabel("Earlier rank-1 results, counted only from this archive")
    ax.set_ylabel("Rank-1 rate on this appearance (%)")
    ax.set_title("Later finalist appearances after earlier rank-1 results, 2012–2026")
    fig.text(0.01, 0.01, "Wilson intervals. A firm with zero earlier rank-1 results includes archive newcomers. 2026 is partial.", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(figures / "03_win_rate_by_prior_wins.png", dpi=150)
    plt.close(fig)

    walk = outputs["walk"]
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    for model, color in (
        ("equal_probability", "#888888"),
        ("prior_wins", "#0072B2"),
        ("wins_plus_same_type", "#D55E00"),
        ("shrunk_win_rate", "#009E73"),
    ):
        part = walk.loc[walk["model"].eq(model)]
        ax.plot(part["year"], part["log_loss"], marker="o", color=color, label=model.replace("_", " "))
    ax.set_xlabel("Year being predicted")
    ax.set_ylabel("Log loss")
    ax.set_title("Walk-forward log loss on known school types")
    ax.legend(frameon=False)
    fig.text(0.01, 0.01, "Each point is fit only on earlier years. Lower is better. 2026 is a partial year.", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(figures / "03_walk_forward_log_loss.png", dpi=150)
    plt.close(fig)
