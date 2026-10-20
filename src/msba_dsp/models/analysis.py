"""Baselines, conditional logit, partial-pooling firm effects, ratings, and checks."""

from __future__ import annotations

import logging
import math
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.ensemble import GradientBoostingClassifier

from msba_dsp.config import FIRM_EFFECT_PENALTY, LOGIT_PENALTY, N_BOOTSTRAP, RATING_PENALTY, SEED, WALK_FORWARD_START
from msba_dsp.evaluation.metrics import (
    attach_probabilities,
    brier_score,
    choice_log_loss,
    top_choice_accuracy,
    wilson_interval,
)

LOGGER = logging.getLogger("msba_dsp")

PRIMARY_FEATURES = [
    "prior_wins",
    "prior_grade_wins",
    "prior_finals",
    "newcomer",
    "prior_wins_x_field",
    "prior_wins_x_time",
    "prior_wins_x_high",
]


def _rng() -> np.random.Generator:
    return np.random.default_rng(SEED)


def design_matrix(frame: pd.DataFrame, columns: list[str] | None = None) -> tuple[np.ndarray, list[str]]:
    names = list(columns or PRIMARY_FEATURES)
    year = frame["selection_year"].to_numpy(dtype=float)
    wins = frame["prior_wins"].to_numpy(dtype=float)
    values = {
        "prior_wins": wins,
        "prior_grade_wins": frame["prior_grade_wins"].to_numpy(dtype=float),
        "prior_finals": frame["prior_finals"].to_numpy(dtype=float),
        "newcomer": frame["newcomer"].to_numpy(dtype=float),
        "prior_wins_x_field": wins * (frame["n_finalists"].to_numpy(dtype=float) - 3.0),
        "prior_wins_x_time": wins * ((year - 2016.0) / 10.0),
        "prior_wins_x_high": wins * (frame["school_category"].eq("high").to_numpy(dtype=float)),
        "rating_asof": frame["rating_asof"].to_numpy(dtype=float) if "rating_asof" in frame else np.zeros(len(frame)),
        "wins_previous_3y": frame["wins_previous_3y"].to_numpy(dtype=float),
        "log_budget": np.log(frame["budget_mid"].replace("", np.nan).astype(float).to_numpy()),
    }
    if "prior_wins_x_log_budget" in names:
        values["prior_wins_x_log_budget"] = wins * values["log_budget"]
    matrix = np.column_stack([values[name] for name in names])
    return matrix, names


def _slices(frame: pd.DataFrame) -> list[np.ndarray]:
    grouped: list[np.ndarray] = []
    start = 0
    for size in frame.groupby("selection_id", sort=False).size():
        grouped.append(np.arange(start, start + int(size)))
        start += int(size)
    return grouped


def _nll(beta: np.ndarray, matrix: np.ndarray, winner: np.ndarray, slices: list[np.ndarray], penalty: float) -> float:
    loss, _ = _logit_objective(beta, matrix, winner, slices, penalty)
    return loss


def _logit_objective(
    beta: np.ndarray,
    matrix: np.ndarray,
    winner: np.ndarray,
    slices: list[np.ndarray],
    penalty: float,
) -> tuple[float, np.ndarray]:
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
        loss += top + math.log(total) - float(scores[chosen][0])
        gradient += matrix[idx].T @ (probabilities - chosen.astype(float))
    return loss, gradient


def fit_logit(
    frame: pd.DataFrame,
    columns: list[str] | None = None,
    penalty: float = LOGIT_PENALTY,
) -> dict:
    ordered = frame.sort_values(["selection_id", "published_rank"], kind="mergesort")
    matrix, names = design_matrix(ordered, columns)
    winner = ordered["winner"].to_numpy(dtype=int)
    slices = _slices(ordered)

    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        return _logit_objective(beta, matrix, winner, slices, penalty)

    result = minimize(objective, np.zeros(matrix.shape[1]), method="BFGS", jac=True, options={"maxiter": 80})
    beta = np.asarray(result.x, dtype=float)
    pure = _nll(beta, matrix, winner, slices, penalty=0.0)
    return {
        "beta": beta,
        "names": names,
        "success": bool(result.success),
        "log_likelihood": float(-pure),
        "n_competitions": int(ordered["selection_id"].nunique()),
        "n_rows": int(len(ordered)),
    }


def predict_logit(frame: pd.DataFrame, beta: np.ndarray, columns: list[str], prob_col: str) -> pd.DataFrame:
    matrix, _ = design_matrix(frame, columns)
    scored = frame.copy()
    scored["_linear_score"] = matrix @ beta
    return attach_probabilities(scored, "_linear_score", prob_col)


def _resample_frame(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    ids = frame["selection_id"].drop_duplicates().to_numpy()
    drawn = rng.choice(ids, size=len(ids), replace=True)
    parts = []
    for draw_index, selection_id in enumerate(drawn):
        part = frame.loc[frame["selection_id"] == selection_id].copy()
        part["selection_id"] = f"{selection_id}__{draw_index}"
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def bootstrap_logit(
    frame: pd.DataFrame,
    columns: list[str] | None = None,
    draws: int | None = None,
) -> dict:
    point = fit_logit(frame, columns)
    rng = _rng()
    samples = []
    n_draws = N_BOOTSTRAP if draws is None else draws
    for _ in range(n_draws):
        try:
            fitted = fit_logit(_resample_frame(frame, rng), columns)
        except (ValueError, IndexError):
            continue
        if fitted["success"] and np.all(np.isfinite(fitted["beta"])):
            samples.append(fitted["beta"])
    stack = np.vstack(samples) if samples else np.empty((0, len(point["beta"])))
    rows = []
    for index, name in enumerate(point["names"]):
        column = stack[:, index] if len(stack) else np.array([])
        lo, hi = (float(np.quantile(column, 0.025)), float(np.quantile(column, 0.975))) if len(column) else (None, None)
        rows.append(
            {
                "term": name,
                "estimate": float(point["beta"][index]),
                "ci_low": lo,
                "ci_high": hi,
                "bootstrap_draws": int(len(stack)),
            }
        )
    point["coefficients"] = rows
    point["bootstrap"] = stack
    return point


def add_baseline_scores(frame: pd.DataFrame) -> pd.DataFrame:
    scored = frame.copy()
    finals = scored["prior_finals"].to_numpy(dtype=float)
    wins = scored["prior_wins"].to_numpy(dtype=float)
    scored["score_equal"] = 0.0
    scored["score_wins"] = wins
    scored["score_grade"] = scored["prior_grade_wins"].to_numpy(dtype=float)
    scored["score_rate"] = np.log((wins + 0.5) / (finals + 1.0))
    scored = attach_probabilities(scored, "score_equal", "p_equal")
    scored = attach_probabilities(scored, "score_wins", "p_wins")
    scored = attach_probabilities(scored, "score_grade", "p_grade")
    scored = attach_probabilities(scored, "score_rate", "p_rate")
    return scored


def metric_row(name: str, sample: str, frame: pd.DataFrame, prob_col: str) -> dict:
    return {
        "model": name,
        "sample": sample,
        "competitions": int(frame["selection_id"].nunique()),
        "log_loss": choice_log_loss(frame, prob_col),
        "top_choice_accuracy": top_choice_accuracy(frame, prob_col),
        "brier": brier_score(frame, prob_col),
    }


def _rankings(frame: pd.DataFrame) -> list[list[str]]:
    rankings: list[list[str]] = []
    for _, group in frame.groupby("selection_id", sort=False):
        ordered = group.sort_values("published_rank", kind="mergesort")
        rankings.append(ordered["firm_id"].tolist())
    return rankings


def fit_plackett_luce(frame: pd.DataFrame, penalty: float = RATING_PENALTY) -> dict[str, float]:
    rankings = _rankings(frame)
    if len(rankings) < 10:
        return {}
    firms = sorted({firm for ranking in rankings for firm in ranking})
    index = {firm: position for position, firm in enumerate(firms)}
    encoded = [[index[firm] for firm in ranking] for ranking in rankings]

    def objective(theta: np.ndarray) -> tuple[float, np.ndarray]:
        gradient = penalty * theta.copy()
        loss = 0.5 * penalty * float(np.dot(theta, theta))
        for ranking in encoded:
            for cut in range(len(ranking) - 1):
                rest = ranking[cut:]
                scores = theta[rest]
                top = float(np.max(scores))
                weights = np.exp(scores - top)
                total = float(weights.sum())
                probabilities = weights / total
                loss += top + math.log(total) - float(scores[0])
                np.add.at(gradient, rest, probabilities)
                gradient[rest[0]] -= 1.0
        return loss, gradient

    result = minimize(objective, np.zeros(len(firms)), method="BFGS", jac=True, options={"maxiter": 80})
    return {firm: float(value) for firm, value in zip(firms, result.x)}


def assign_walk_forward_ratings(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, dict[str, float]]]:
    """Rating for a competition in year Y is fit only on earlier years."""
    scored = frame.copy()
    scored["rating_asof"] = 0.0
    stored: dict[int, dict[str, float]] = {}
    for year in sorted(scored["selection_year"].unique()):
        history = scored.loc[scored["selection_year"] < int(year)]
        ratings = fit_plackett_luce(history) if history["selection_id"].nunique() >= 15 else {}
        stored[int(year)] = ratings
        mask = scored["selection_year"] == int(year)
        scored.loc[mask, "rating_asof"] = scored.loc[mask, "firm_id"].map(lambda firm: ratings.get(firm, 0.0))
    return scored, stored


def fit_firm_effects(frame: pd.DataFrame, penalty: float = FIRM_EFFECT_PENALTY) -> dict:
    ordered = frame.sort_values(["selection_id", "published_rank"], kind="mergesort")
    covariate_names = ["prior_wins", "prior_grade_wins", "prior_finals", "newcomer"]
    matrix, _ = design_matrix(ordered, covariate_names)
    firms = ordered["firm_id"].drop_duplicates().tolist()
    firm_index = {firm: index for index, firm in enumerate(firms)}
    firm_codes = ordered["firm_id"].map(firm_index).to_numpy(dtype=int)
    winner = ordered["winner"].to_numpy(dtype=int)
    slices = _slices(ordered)
    n_covariates = matrix.shape[1]
    n_firms = len(firms)

    def objective(theta: np.ndarray) -> tuple[float, np.ndarray]:
        beta = theta[:n_covariates]
        effects = theta[n_covariates:]
        utility = matrix @ beta + effects[firm_codes]
        loss = 0.5 * penalty * float(np.dot(effects, effects))
        beta_gradient = np.zeros(n_covariates)
        effect_gradient = penalty * effects
        for idx in slices:
            scores = utility[idx]
            top = float(np.max(scores))
            weights = np.exp(scores - top)
            total = float(weights.sum())
            probabilities = weights / total
            chosen = winner[idx] == 1
            loss += top + math.log(total) - float(scores[chosen][0])
            residual = probabilities - chosen.astype(float)
            beta_gradient += matrix[idx].T @ residual
            np.add.at(effect_gradient, firm_codes[idx], residual)
        return loss, np.concatenate([beta_gradient, effect_gradient])

    result = minimize(
        objective,
        np.zeros(n_covariates + n_firms),
        method="BFGS",
        jac=True,
        options={"maxiter": 80},
    )
    theta = np.asarray(result.x, dtype=float)
    counts = ordered.groupby("firm_id").size().to_dict()
    effects = [
        {
            "firm_id": firm,
            "effect": float(theta[n_covariates + index]),
            "appearances": int(counts.get(firm, 0)),
        }
        for index, firm in enumerate(firms)
    ]
    return {
        "success": bool(result.success),
        "beta": theta[:n_covariates],
        "names": covariate_names,
        "firm_effects": effects,
        "penalty": penalty,
        "theta": theta,
        "firms": firms,
    }


def predict_firm_effects(frame: pd.DataFrame, fitted: dict, prob_col: str = "p_firm") -> pd.DataFrame:
    matrix, _ = design_matrix(frame, fitted["names"])
    effect_map = {row["firm_id"]: row["effect"] for row in fitted["firm_effects"]}
    scored = frame.copy()
    effects = scored["firm_id"].map(lambda firm: effect_map.get(firm, 0.0)).to_numpy(dtype=float)
    scored["_linear_score"] = matrix @ fitted["beta"] + effects
    return attach_probabilities(scored, "_linear_score", prob_col)


def _gbm_probabilities(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    columns = ["prior_wins", "prior_grade_wins", "prior_finals", "newcomer", "prior_wins_x_field", "rating_asof"]
    model = GradientBoostingClassifier(
        n_estimators=60,
        max_depth=2,
        learning_rate=0.05,
        subsample=0.9,
        random_state=SEED,
    )
    x_train, _ = design_matrix(train, columns)
    model.fit(x_train, train["winner"].to_numpy(dtype=int))
    scored = test.copy()
    x_test, _ = design_matrix(scored, columns)
    raw = model.predict_proba(x_test)[:, 1]
    scored["_gbm_score"] = np.log(np.clip(raw, 1e-6, 1 - 1e-6))
    scored = attach_probabilities(scored, "_gbm_score", "p_gbm")
    importance = [
        {"term": name, "importance": float(value)}
        for name, value in zip(columns, model.feature_importances_)
    ]
    scored.attrs["importance"] = importance
    return scored


def calibration_table(frame: pd.DataFrame, prob_col: str) -> list[dict]:
    working = frame.copy()
    try:
        working["bin"] = pd.qcut(working[prob_col], 5, duplicates="drop")
    except ValueError:
        return []
    rows = []
    for interval, group in working.groupby("bin", observed=True):
        wins = int(group["winner"].sum())
        trials = int(len(group))
        lo, hi = wilson_interval(wins, trials)
        rows.append(
            {
                "bin": str(interval),
                "mean_predicted": float(group[prob_col].mean()),
                "observed_win_rate": wins / trials if trials else None,
                "finalist_rows": trials,
                "wins": wins,
                "wilson_low": lo,
                "wilson_high": hi,
            }
        )
    return rows


def experience_curve(frame: pd.DataFrame) -> list[dict]:
    bins = [-0.1, 0, 1, 2, 4, 9, 10_000]
    labels = ["0", "1", "2", "3-4", "5-9", "10+"]
    working = frame.copy()
    working["bin"] = pd.cut(working["prior_wins"], bins=bins, labels=labels)
    rows = []
    for label, group in working.groupby("bin", observed=True):
        wins = int(group["winner"].sum())
        trials = int(len(group))
        lo, hi = wilson_interval(wins, trials)
        rows.append(
            {
                "prior_wins": str(label),
                "wins": wins,
                "finalist_appearances": trials,
                "win_rate": wins / trials if trials else None,
                "wilson_low": lo,
                "wilson_high": hi,
            }
        )
    return rows


def _loss_difference(frame: pd.DataFrame, left: str, right: str, draws: int = 400) -> dict:
    """Bootstrap competitions to compare two choice log losses. Positive means left is better."""
    per_id = []
    for selection_id, group in frame.groupby("selection_id", sort=False):
        winner = group.loc[group["winner"] == 1]
        if len(winner) != 1:
            continue
        per_id.append(
            (
                -math.log(max(float(winner[left].iloc[0]), 1e-12)),
                -math.log(max(float(winner[right].iloc[0]), 1e-12)),
            )
        )
    if not per_id:
        return {"difference": None, "ci_low": None, "ci_high": None}
    losses = np.array(per_id)
    rng = _rng()
    diffs = []
    for _ in range(draws):
        sample = losses[rng.integers(0, len(losses), len(losses))]
        diffs.append(float(sample[:, 1].mean() - sample[:, 0].mean()))
    diffs_arr = np.array(diffs)
    return {
        "difference": float(losses[:, 1].mean() - losses[:, 0].mean()),
        "ci_low": float(np.quantile(diffs_arr, 0.025)),
        "ci_high": float(np.quantile(diffs_arr, 0.975)),
        "competitions": int(len(losses)),
    }


def _ci_excludes_zero(row: dict, positive: bool | None = None) -> bool:
    lo, hi = row.get("ci_low"), row.get("ci_high")
    if lo is None or hi is None:
        return False
    if positive is True:
        return lo > 0
    if positive is False:
        return hi < 0
    return hi < 0 or lo > 0


def _coef(fitted: dict, term: str) -> dict:
    for row in fitted.get("coefficients", []):
        if row["term"] == term:
            return row
    return {"term": term, "estimate": None, "ci_low": None, "ci_high": None, "bootstrap_draws": 0}


def _num(value: object) -> str:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "not estimated"
    if not math.isfinite(number):
        return "not estimated"
    return f"{number:.3f}"


def build_hypotheses(results: dict) -> list[dict]:
    primary = results["primary"]
    oos = results["oos_metrics"]
    equal_oos = next(row["log_loss"] for row in oos if row["model"] == "equal_probability")
    logit_oos = next(row["log_loss"] for row in oos if row["model"] == "conditional_logit")
    shrunk_oos = next(row["log_loss"] for row in oos if row["model"] == "shrunk_win_rate")
    rating_oos = next(row["log_loss"] for row in oos if row["model"] == "logit_plus_rating")
    firm_oos = next(row["log_loss"] for row in oos if row["model"] == "penalized_firm_effects")
    wins_row = _coef(primary, "prior_wins")
    grade_row = _coef(primary, "prior_grade_wins")
    newcomer_row = _coef(primary, "newcomer")
    field_row = _coef(primary, "prior_wins_x_field")
    time_row = _coef(primary, "prior_wins_x_time")
    h4_refit = results["newcomer_refit"]
    h4_row = _coef(h4_refit, "newcomer")
    workload = results["workload"]
    workload_row = _coef(workload, "wins_previous_3y")
    budget = results["budget"]
    rating_cmp = results["rating_comparison"]
    firm_cmp = results["firm_effect_comparison"]

    def pack(identifier, statement, status, sample, detail, limitation):
        return {
            "id": identifier,
            "statement": statement,
            "status": status,
            "sample_competitions": sample,
            "detail": detail,
            "limitation": limitation,
        }

    h1_status = "inconclusive"
    if _ci_excludes_zero(wins_row, True) and logit_oos < equal_oos:
        h1_status = "supported"
    elif _ci_excludes_zero(wins_row, False):
        h1_status = "unsupported"

    budget_status = "inconclusive"
    budget_detail = "Preselection construction-cost ranges are not in the historical HTML results."
    if budget["n_competitions"] >= 20 and budget.get("coefficients"):
        budget_row = _coef(budget, "prior_wins_x_log_budget")
        budget_detail = (
            f"On the {budget['n_competitions']} competitions with a published range, "
            f"the experience × log budget coefficient is {budget_row['estimate']:.3f} "
            f"(interval {budget_row['ci_low']:.3f} to {budget_row['ci_high']:.3f})."
        )
        if _ci_excludes_zero(budget_row, True):
            budget_status = "supported"
        elif _ci_excludes_zero(budget_row, False):
            budget_status = "unsupported"
    else:
        budget_detail += f" The chart subset has {budget['n_competitions']} usable competitions."

    grade_status = "inconclusive"
    if results["experience_correlation"] >= 0.9:
        grade_detail = (
            f"Prior grade-level wins and total wins correlate at {results['experience_correlation']:.2f}, "
            "so the extra grade coefficient is not separately informative."
        )
    else:
        grade_detail = (
            f"Grade-specific win coefficient {grade_row['estimate']:.3f} "
            f"(interval {grade_row['ci_low']:.3f} to {grade_row['ci_high']:.3f}) "
            f"after controlling for total wins. Correlation with total wins is {results['experience_correlation']:.2f}."
        )
        if _ci_excludes_zero(grade_row, True) and results["grade_oos_improves"]:
            grade_status = "supported"
        elif _ci_excludes_zero(grade_row, False):
            grade_status = "unsupported"

    h4_same_direction = (
        newcomer_row["estimate"] is not None
        and h4_row["estimate"] is not None
        and np.sign(newcomer_row["estimate"]) == np.sign(h4_row["estimate"])
        and _ci_excludes_zero(newcomer_row)
        and _ci_excludes_zero(h4_row)
    )
    h4_status = "supported" if h4_same_direction else "inconclusive"
    if (
        newcomer_row["estimate"] is not None
        and h4_row["estimate"] is not None
        and _ci_excludes_zero(newcomer_row)
        and _ci_excludes_zero(h4_row)
        and np.sign(newcomer_row["estimate"]) != np.sign(h4_row["estimate"])
    ):
        h4_status = "inconclusive"

    h5_status = "supported" if _ci_excludes_zero(field_row) else "inconclusive"
    h7_status = "supported" if _ci_excludes_zero(time_row) or results["era_intervals_disjoint"] else "inconclusive"
    h8_beats_simple = rating_oos < shrunk_oos and rating_oos < equal_oos
    h8_status = "inconclusive"
    if rating_cmp["ci_high"] is not None and rating_cmp["ci_high"] < 0:
        h8_status = "unsupported"
    elif rating_cmp["ci_low"] is not None and rating_cmp["ci_low"] > 0 and h8_beats_simple:
        h8_status = "supported"
    h6_status = "inconclusive"
    if firm_cmp["ci_high"] is not None and firm_cmp["ci_high"] < 0:
        h6_status = "unsupported"
    elif (
        firm_cmp["ci_low"] is not None
        and firm_cmp["ci_low"] > 0
        and results["firms_with_residual_signal"]
        and firm_oos < shrunk_oos
    ):
        h6_status = "supported"
    h10_status = "supported" if _ci_excludes_zero(workload_row) else "inconclusive"

    return [
        pack(
            "H1",
            "Prior MSBA wins predict selection among finalists.",
            h1_status,
            primary["n_competitions"],
            (
                f"Conditional-logit coefficient on prior wins is {wins_row['estimate']:.3f} "
                f"(bootstrap interval {wins_row['ci_low']:.3f} to {wins_row['ci_high']:.3f}). "
                f"Out-of-sample log loss is {logit_oos:.3f} versus {equal_oos:.3f} for equal probabilities."
            ),
            "The archive begins in 2007, so earlier careers are unobserved. The estimate is an association inside published finalist sets.",
        ),
        pack(
            "H2",
            "The association between experience and selection is stronger on larger projects.",
            budget_status,
            budget["n_competitions"],
            budget_detail,
            "Historical result pages do not publish construction budgets. A high-school indicator is not treated as a cost measure.",
        ),
        pack(
            "H3",
            "Same-grade experience predicts selection beyond total MSBA wins.",
            grade_status,
            primary["n_competitions"],
            grade_detail,
            "Grade is parsed from the school name. Unspecified names are excluded from the grade count. This is not an independent specialty certification.",
        ),
        pack(
            "H4",
            "Firms with no observed MSBA finalist history have a different selection probability after experience counts.",
            h4_status,
            h4_refit["n_competitions"],
            (
                f"Full-sample newcomer coefficient {newcomer_row['estimate']:.3f} "
                f"(interval {newcomer_row['ci_low']:.3f} to {newcomer_row['ci_high']:.3f}). "
                f"Refit on selections from 2012 onward: {h4_row['estimate']:.3f} "
                f"(interval {h4_row['ci_low']:.3f} to {h4_row['ci_high']:.3f})."
            ),
            "Newcomer means no earlier finalist appearance in this public archive. It does not mean the firm is a new architecture practice. Pre-2007 MSBA work is invisible, so the 2012 refit is required before calling the result supported.",
        ),
        pack(
            "H5",
            "The number of finalists changes the association between experience and selection.",
            h5_status,
            primary["n_competitions"],
            (
                f"Coefficient on prior wins × (finalists − 3) is {field_row['estimate']:.3f} "
                f"(interval {field_row['ci_low']:.3f} to {field_row['ci_high']:.3f})."
            ),
            "Finalist count is a property of the published choice set. It does not say what would happen if a firm were added or removed.",
        ),
        pack(
            "H6",
            "Some firms win more often than experience, grade history, and newcomer status predict.",
            h6_status,
            firm_cmp.get("competitions"),
            (
                f"Out-of-sample log loss is {_num(firm_oos)} with penalized firm effects, {_num(logit_oos)} for the "
                f"experience logit, and {_num(shrunk_oos)} for the shrunk win-rate baseline. "
                f"The improvement over the experience logit is {_num(firm_cmp['difference'])} "
                f"(interval {_num(firm_cmp['ci_low'])} to {_num(firm_cmp['ci_high'])}). "
                f"Firms with a residual interval excluding zero and at least eight appearances: {results['firms_with_residual_signal']}."
            ),
            "Firm effects are procurement-selection residuals. They are not a design-quality score. Partial pooling pulls infrequent firms toward zero.",
        ),
        pack(
            "H7",
            "The experience association changes across time.",
            h7_status,
            primary["n_competitions"],
            (
                f"Coefficient on prior wins × (year − 2016) / 10 is {time_row['estimate']:.3f} "
                f"(interval {time_row['ci_low']:.3f} to {time_row['ci_high']:.3f}). "
                f"Early and late intervals disjoint: {results['era_intervals_disjoint']}."
            ),
            "A change in a coefficient is a change in statistical association. It is not, by itself, a change in a written policy.",
        ),
        pack(
            "H8",
            "A walk-forward competitive rating predicts later selections beyond raw experience counts.",
            h8_status,
            rating_cmp.get("competitions"),
            (
                f"Adding the pre-period rating changes test log loss by {_num(rating_cmp['difference'])} "
                f"relative to the experience logit (interval {_num(rating_cmp['ci_low'])} to {_num(rating_cmp['ci_high'])}). "
                f"The rating model’s own test log loss is {_num(rating_oos)}, compared with {_num(shrunk_oos)} for the "
                "shrunk win-rate baseline. Support requires an improvement on that simple baseline, not only on the logit."
            ),
            "The rating measures historical success against other finalists. It is not an architectural quality rating. Future results are not used to build the rating for a test year.",
        ),
        pack(
            "H9",
            "Selection outcomes correlate with publicly measurable cost performance.",
            "inconclusive",
            0,
            "The designer construction cost chart is linked by MSBA but is not in the local snapshot, and schematic-design budgets would be post-selection outcomes.",
            "No bid, schematic, or final-cost comparison is estimated. Cost efficiency is not scored.",
        ),
        pack(
            "H10",
            "Recent firm award workload is associated with selection after total experience is included.",
            h10_status,
            workload["n_competitions"],
            (
                f"Coefficient on wins in the previous three years, controlling for total prior wins, "
                f"is {workload_row['estimate']:.3f} "
                f"(interval {workload_row['ci_low']:.3f} to {workload_row['ci_high']:.3f})."
            ),
            "Recent wins are a public-award workload proxy, not a count of all active contracts. Institutional concentration is reported descriptively and is not given a causal interpretation.",
        ),
    ]


def run_analysis(featured: pd.DataFrame, firms: pd.DataFrame) -> dict:
    frame = add_baseline_scores(featured)
    LOGGER.info("Fitting walk-forward selection ratings")
    frame, ratings_by_year = assign_walk_forward_ratings(frame)
    LOGGER.info("Bootstrapping the conditional logit")
    frame = frame.sort_values(["selection_date", "selection_id", "published_rank"], kind="mergesort").reset_index(drop=True)

    primary = bootstrap_logit(frame, PRIMARY_FEATURES, draws=N_BOOTSTRAP)
    full_pred = predict_logit(frame, primary["beta"], PRIMARY_FEATURES, "p_logit")
    # Preserve walk-forward columns from `frame`.
    full_pred["rating_asof"] = frame["rating_asof"].to_numpy()
    full_pred["p_equal"] = frame["p_equal"].to_numpy()
    full_pred["p_wins"] = frame["p_wins"].to_numpy()
    full_pred["p_grade"] = frame["p_grade"].to_numpy()
    full_pred["p_rate"] = frame["p_rate"].to_numpy()

    train = frame.loc[frame["selection_year"] <= 2018].copy()
    oos_fit = fit_logit(train, PRIMARY_FEATURES)
    test = predict_logit(frame.loc[frame["selection_year"] >= 2019].copy(), oos_fit["beta"], PRIMARY_FEATURES, "p_logit")

    rating_cols = PRIMARY_FEATURES + ["rating_asof"]
    rating_fit = fit_logit(train, rating_cols)
    test = predict_logit(test, rating_fit["beta"], rating_cols, "p_rating")

    gbm = _gbm_probabilities(train, test)
    test["p_gbm"] = gbm["p_gbm"].to_numpy()

    firm_train = fit_firm_effects(train)
    test = predict_firm_effects(test, firm_train, "p_firm")

    no_grade_cols = [name for name in PRIMARY_FEATURES if name != "prior_grade_wins"]
    no_grade_fit = fit_logit(train, no_grade_cols)
    test = predict_logit(test, no_grade_fit["beta"], no_grade_cols, "p_no_grade")
    grade_cmp = _loss_difference(test, "p_logit", "p_no_grade")

    metrics = [
        metric_row("equal_probability", "in_sample", full_pred, "p_equal"),
        metric_row("prior_wins", "in_sample", full_pred, "p_wins"),
        metric_row("grade_wins", "in_sample", full_pred, "p_grade"),
        metric_row("shrunk_win_rate", "in_sample", full_pred, "p_rate"),
        metric_row("conditional_logit", "in_sample", full_pred, "p_logit"),
        metric_row("equal_probability", "2019_forward", test, "p_equal"),
        metric_row("prior_wins", "2019_forward", test, "p_wins"),
        metric_row("grade_wins", "2019_forward", test, "p_grade"),
        metric_row("shrunk_win_rate", "2019_forward", test, "p_rate"),
        metric_row("conditional_logit", "2019_forward", test, "p_logit"),
        metric_row("logit_plus_rating", "2019_forward", test, "p_rating"),
        metric_row("choice_normalized_gbm", "2019_forward", test, "p_gbm"),
        metric_row("penalized_firm_effects", "2019_forward", test, "p_firm"),
    ]

    early = bootstrap_logit(frame.loc[frame["selection_year"] <= 2016], ["prior_wins", "prior_finals", "newcomer"], draws=max(40, N_BOOTSTRAP // 2))
    late = bootstrap_logit(frame.loc[frame["selection_year"] >= 2017], ["prior_wins", "prior_finals", "newcomer"], draws=max(40, N_BOOTSTRAP // 2))
    early_row = _coef(early, "prior_wins")
    late_row = _coef(late, "prior_wins")
    era_disjoint = bool(
        early_row["ci_high"] is not None
        and late_row["ci_low"] is not None
        and (early_row["ci_high"] < late_row["ci_low"] or late_row["ci_high"] < early_row["ci_low"])
    )

    newcomer_refit = bootstrap_logit(
        frame.loc[frame["selection_year"] >= 2012],
        PRIMARY_FEATURES,
        draws=max(40, N_BOOTSTRAP // 2),
    )
    workload = bootstrap_logit(
        frame,
        ["prior_wins", "prior_finals", "newcomer", "wins_previous_3y"],
        draws=max(40, N_BOOTSTRAP // 2),
    )
    budget_frame = frame.loc[frame["budget_mid"].astype(str).str.len() > 0].copy()
    if budget_frame["selection_id"].nunique() >= 12:
        budget_fit = bootstrap_logit(
            budget_frame,
            ["prior_wins", "prior_finals", "newcomer", "prior_wins_x_log_budget"],
            draws=max(30, N_BOOTSTRAP // 2),
        )
    else:
        budget_fit = {"n_competitions": int(budget_frame["selection_id"].nunique()), "coefficients": [], "beta": np.array([]), "names": []}

    LOGGER.info("Estimating penalized firm effects")
    full_effects = fit_firm_effects(frame)
    effect_draws = []
    rng = _rng()
    for _ in range(max(25, N_BOOTSTRAP // 3)):
        try:
            fitted = fit_firm_effects(_resample_frame(frame, rng))
        except (ValueError, IndexError):
            continue
        if fitted["success"]:
            effect_draws.append({row["firm_id"]: row["effect"] for row in fitted["firm_effects"]})
    name_map = firms.set_index("firm_id")["canonical_firm_name"].to_dict()
    residual_rows = []
    signal_count = 0
    for row in full_effects["firm_effects"]:
        if row["appearances"] < 8:
            continue
        samples = [draw[row["firm_id"]] for draw in effect_draws if row["firm_id"] in draw]
        lo = float(np.quantile(samples, 0.025)) if samples else None
        hi = float(np.quantile(samples, 0.975)) if samples else None
        excludes = lo is not None and hi is not None and (hi < 0 or lo > 0)
        signal_count += int(excludes)
        residual_rows.append(
            {
                "firm_id": row["firm_id"],
                "firm": name_map.get(row["firm_id"], row["firm_id"]),
                "effect": row["effect"],
                "appearances": row["appearances"],
                "ci_low": lo,
                "ci_high": hi,
                "interval_excludes_zero": excludes,
            }
        )
    residual_rows.sort(key=lambda item: item["effect"], reverse=True)

    LOGGER.info("Scoring walk-forward anomalies and laboratory cutoffs")
    anomalies = _anomalies(frame, name_map)
    descriptive_ratings = fit_plackett_luce(frame)
    correlation_value = frame[["prior_wins", "prior_grade_wins"]].corr().iloc[0, 1]
    correlation = float(correlation_value) if pd.notna(correlation_value) else 0.0

    results = {
        "frame": full_pred,
        "test": test,
        "primary": primary,
        "oos_fit": oos_fit,
        "metrics": metrics,
        "oos_metrics": [row for row in metrics if row["sample"] == "2019_forward"],
        "calibration": calibration_table(test, "p_logit"),
        "experience_curve": experience_curve(frame),
        "gbm_importance": gbm.attrs.get("importance", []),
        "ratings_full": descriptive_ratings,
        "ratings_by_year": ratings_by_year,
        "firm_effects": residual_rows,
        "firms_with_residual_signal": signal_count,
        "anomalies": anomalies,
        "experience_correlation": correlation,
        "grade_oos_improves": bool(grade_cmp["ci_low"] is not None and grade_cmp["ci_low"] > 0),
        "grade_comparison": grade_cmp,
        "rating_comparison": _loss_difference(test, "p_rating", "p_logit"),
        "firm_effect_comparison": _loss_difference(test, "p_firm", "p_logit"),
        "era_intervals_disjoint": era_disjoint,
        "early_wins": early_row,
        "late_wins": late_row,
        "newcomer_refit": newcomer_refit,
        "workload": workload,
        "budget": budget_fit,
        "train_competitions": int(train["selection_id"].nunique()),
        "test_competitions": int(test["selection_id"].nunique()),
    }
    results["hypotheses"] = build_hypotheses(results)
    results["snapshots"] = _snapshots(frame, descriptive_ratings)
    results["lab_models"] = _lab_models(frame)
    return results


def _anomalies(frame: pd.DataFrame, name_map: dict[str, str]) -> list[dict]:
    rows: list[dict] = []
    years = [int(year) for year in sorted(frame["selection_year"].unique()) if int(year) >= WALK_FORWARD_START]
    for year in years:
        history = frame.loc[frame["selection_year"] < year]
        current = frame.loc[frame["selection_year"] == year].copy()
        if history["selection_id"].nunique() < 30 or current.empty:
            continue
        fitted = fit_logit(history, PRIMARY_FEATURES)
        if not fitted["success"]:
            continue
        current = predict_logit(current, fitted["beta"], PRIMARY_FEATURES, "p_walk")
        for selection_id, group in current.groupby("selection_id", sort=False):
            winner = group.loc[group["winner"] == 1].iloc[0]
            favorite = group.loc[group["p_walk"].idxmax()]
            probability = float(winner["p_walk"])
            if favorite["firm_id"] == winner["firm_id"]:
                continue
            if probability > 0.15:
                continue
            rows.append(
                {
                    "selection_id": selection_id,
                    "selection_date": winner["selection_date"],
                    "selection_year": int(winner["selection_year"]),
                    "project": winner["project_label"],
                    "district": winner["district"],
                    "school_name": winner["school_name"],
                    "school_category": winner["school_category"],
                    "winner": name_map.get(winner["firm_id"], winner["firm_id"]),
                    "winner_probability": probability,
                    "favorite": name_map.get(favorite["firm_id"], favorite["firm_id"]),
                    "favorite_probability": float(favorite["p_walk"]),
                    "n_finalists": int(winner["n_finalists"]),
                    "winner_prior_wins": int(winner["prior_wins"]),
                    "favorite_prior_wins": int(favorite["prior_wins"]),
                    "source_url": winner["source_url"],
                    "training_competitions": int(history["selection_id"].nunique()),
                    "label": "unexpected_model_outcome",
                    "finalists": [
                        {
                            "firm": name_map.get(row.firm_id, row.firm_id),
                            "rank": int(row.published_rank),
                            "prior_wins": int(row.prior_wins),
                            "prior_finals": int(row.prior_finals),
                            "probability": float(row.p_walk),
                            "winner": int(row.winner) == 1,
                        }
                        for row in group.sort_values("published_rank").itertuples()
                    ],
                }
            )
    rows.sort(key=lambda item: item["winner_probability"])
    return rows[:25]


def _snapshots(frame: pd.DataFrame, full_ratings: dict[str, float]) -> list[dict]:
    """State after each calendar year, for hypothetical contests that use only that history."""
    wins = defaultdict(int)
    finals = defaultdict(int)
    grades: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    snapshots: list[dict] = []
    last_year = None
    firms_seen: set[str] = set()

    def emit(year: int) -> None:
        for firm in sorted(firms_seen):
            snapshots.append(
                {
                    "firm_id": firm,
                    "through_year": year,
                    "prior_wins": wins[firm],
                    "prior_finals": finals[firm],
                    "elementary_wins": grades[firm]["elementary"],
                    "middle_wins": grades[firm]["middle"],
                    "high_wins": grades[firm]["high"],
                    "rating": full_ratings.get(firm, 0.0) if year == int(frame["selection_year"].max()) else None,
                }
            )

    ordered = frame.sort_values(["selection_date", "selection_id"], kind="mergesort")
    for _, row in ordered.iterrows():
        year = int(row["selection_year"])
        if last_year is not None and year != last_year:
            emit(last_year)
        last_year = year
        firm = row["firm_id"]
        firms_seen.add(firm)
        finals[firm] += 1
        if int(row["winner"]) == 1:
            wins[firm] += 1
            category = row["school_category"]
            if category in grades[firm] or category in {"elementary", "middle", "high"}:
                grades[firm][category] += 1
    if last_year is not None:
        emit(last_year)
    # Attach walk-forward-through-year ratings: a snapshot at Y can only use ratings
    # known from competitions through Y. The descriptive full-sample rating stays blank
    # except at the last year, where it is separately labeled in the dashboard.
    return snapshots


def _lab_models(frame: pd.DataFrame) -> list[dict]:
    models = []
    years = [year for year in (2014, 2016, 2018, 2020, 2022, 2024) if (frame["selection_year"] <= year).any()]
    max_year = int(frame["selection_year"].max())
    if max_year not in years:
        years.append(max_year)
    for year in years:
        sample = frame.loc[frame["selection_year"] <= year]
        if sample["selection_id"].nunique() < 40:
            continue
        fitted = bootstrap_logit(sample, PRIMARY_FEATURES, draws=max(30, N_BOOTSTRAP // 2))
        draws = fitted["bootstrap"].tolist() if len(fitted["bootstrap"]) else []
        models.append(
            {
                "through_year": int(year),
                "competitions": fitted["n_competitions"],
                "coefficients": fitted["coefficients"],
                "bootstrap": draws,
                "feature_names": PRIMARY_FEATURES,
            }
        )
    return models
