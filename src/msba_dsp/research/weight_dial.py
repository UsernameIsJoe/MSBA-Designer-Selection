"""How far to turn history weights up from an equal chance.

The stored conditional logit estimates a weight for each history item and
then uses those weights at full strength. Full strength is one point on a
dial. Dial 0 gives every firm on the list the same chance. This note fits
the weights on rankings through 2015, picks the dial on 2016–2018, and
scores 2019–2026 once. The later window is not used to choose the dial.

Rank 1 is the published order, not a signed contract. The stored winner
model is not refit and its report is not rewritten.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from msba_dsp.config import LOGIT_PENALTY, SEED
from msba_dsp.evaluation.metrics import choice_log_loss
from msba_dsp.models.analysis import PRIMARY_FEATURES, design_matrix, fit_logit, predict_logit

DRAWS = 2000
FIT_END = 2015
VALIDATION_END = 2018
TEST_START = 2019
# Coarse on purpose. Fifty-four validation rankings cannot support a finer dial.
DIAL_GRID = tuple(np.round(np.arange(0.0, 1.51, 0.25), 2))
LEVEL_TERMS = ("prior_wins", "prior_grade_wins", "prior_finals", "newcomer")
TERM_LABELS = {
    "prior_wins": "Earlier rank-1 results",
    "prior_grade_wins": "Earlier rank-1 results on the same grade",
    "prior_finals": "Earlier finalist appearances",
    "newcomer": "No earlier appearance in this archive",
}


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return round(float(value), digits)


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    """Model-frame rows with the columns the stored logit expects."""
    out = frame.copy()
    out["winner"] = pd.to_numeric(out["winner"]).astype(int)
    out["selection_year"] = pd.to_numeric(out["selection_year"]).astype(int)
    out["prior_wins"] = pd.to_numeric(out["prior_wins"]).astype(float)
    out["prior_grade_wins"] = pd.to_numeric(out["prior_grade_wins"]).astype(float)
    out["prior_finals"] = pd.to_numeric(out["prior_finals"]).astype(float)
    out["newcomer"] = pd.to_numeric(out["newcomer"]).astype(float)
    out["n_finalists"] = pd.to_numeric(out["n_finalists"]).astype(float)
    if "published_rank" not in out.columns and "rank_num" in out.columns:
        out["published_rank"] = out["rank_num"]
    out["published_rank"] = pd.to_numeric(out["published_rank"])
    return out


def window(frame: pd.DataFrame, start: int | None, end: int | None) -> pd.DataFrame:
    years = frame["selection_year"]
    mask = pd.Series(True, index=frame.index)
    if start is not None:
        mask &= years.ge(start)
    if end is not None:
        mask &= years.le(end)
    return frame.loc[mask].copy()


def dial_grid() -> tuple[float, ...]:
    return DIAL_GRID


def fit_weights(frame: pd.DataFrame, columns: list[str]) -> dict:
    fitted = fit_logit(frame, columns, penalty=LOGIT_PENALTY)
    if not fitted["success"] or not np.all(np.isfinite(fitted["beta"])):
        raise RuntimeError(f"weight fit failed for {columns}")
    return fitted


def score_frame(frame: pd.DataFrame, beta: np.ndarray, columns: list[str], dial: float) -> pd.DataFrame:
    """One row per ranking: log loss of the firm that was placed first."""
    scored = predict_logit(frame, np.asarray(beta, dtype=float) * float(dial), columns, "p_dial")
    rows = []
    for selection_id, group in scored.groupby("selection_id", sort=True):
        if int(group["winner"].sum()) != 1:
            raise ValueError(f"{selection_id} does not have one rank-1 firm")
        if not np.allclose(group["p_dial"].sum(), 1.0, atol=1e-8):
            raise ValueError(f"{selection_id} probabilities sum to {group['p_dial'].sum()}")
        probability = float(group.loc[group["winner"].eq(1), "p_dial"].iloc[0])
        top = float(group["p_dial"].max())
        leaders = group.loc[np.isclose(group["p_dial"], top)]
        named = int(len(leaders) == 1 and int(leaders["winner"].iloc[0]) == 1)
        rows.append(
            {
                "selection_id": selection_id,
                "log_loss": float(-np.log(np.clip(probability, 1e-12, 1.0))),
                "winner_probability": probability,
                "named_the_winner": named,
                "unique_pick": int(len(leaders) == 1),
            }
        )
    return pd.DataFrame(rows)


def choose_dial(validation: pd.DataFrame, beta: np.ndarray, columns: list[str]) -> tuple[float, pd.DataFrame]:
    """Smallest dial on the grid whose validation log loss is the minimum.

    A tie goes to the dial closer to an equal chance.
    """
    rows = []
    best_dial = None
    best_loss = None
    for dial in DIAL_GRID:
        losses = score_frame(validation, beta, columns, dial)
        loss = float(losses["log_loss"].mean())
        rows.append({"dial": float(dial), "validation_log_loss": _round(loss, 6), "competitions": int(len(losses))})
        if best_loss is None or loss < best_loss - 1e-8 or (abs(loss - best_loss) <= 1e-8 and float(dial) < best_dial):
            best_loss = loss
            best_dial = float(dial)
    return best_dial, pd.DataFrame(rows)


def _gap(left: np.ndarray, right: np.ndarray, seed: int) -> dict:
    """Mean of right minus left. Positive means left has the lower log loss."""
    gap = right - left
    rng = np.random.default_rng(seed)
    samples = rng.choice(gap, size=(DRAWS, len(gap)), replace=True).mean(axis=1)
    return {
        "estimate": _round(float(gap.mean())),
        "low": _round(float(np.quantile(samples, 0.025))),
        "high": _round(float(np.quantile(samples, 0.975))),
        "n": int(len(gap)),
    }


def _typical_steps(fit_rows: pd.DataFrame, columns: list[str], beta: np.ndarray) -> list[float | None]:
    """Change in the linear score for a one-standard-deviation difference on the fit window."""
    matrix, _names = design_matrix(fit_rows, columns)
    steps = []
    for index in range(len(columns)):
        scale = float(np.std(matrix[:, index], ddof=0))
        steps.append(None if scale == 0 else _round(float(beta[index]) * scale, 4))
    return steps


def evaluate_spec(frame: pd.DataFrame, columns: list[str], label: str) -> dict:
    fit_rows = window(frame, None, FIT_END)
    validation = window(frame, FIT_END + 1, VALIDATION_END)
    test = window(frame, TEST_START, None)
    if fit_rows["selection_year"].max() > FIT_END:
        raise ValueError("the weight fit saw a year after 2015")
    if validation["selection_year"].max() >= TEST_START or validation["selection_year"].min() <= FIT_END:
        raise ValueError("the dial window is not 2016–2018")
    fitted = fit_weights(fit_rows, columns)
    beta = fitted["beta"]
    chosen, curve = choose_dial(validation, beta, columns)
    equal = score_frame(test, beta, columns, 0.0)
    full = score_frame(test, beta, columns, 1.0)
    used = score_frame(test, beta, columns, chosen)
    if not equal["selection_id"].eq(full["selection_id"]).all() or not equal["selection_id"].eq(used["selection_id"]).all():
        raise ValueError("test rankings are not aligned")
    steps = _typical_steps(fit_rows, columns, beta)
    weights = []
    for name, value, step in zip(columns, beta, steps):
        weights.append(
            {
                "term": name,
                "label": TERM_LABELS.get(name, name),
                "weight": _round(float(value), 4),
                "weight_at_chosen_dial": _round(float(value) * chosen, 4),
                "typical_step": step,
            }
        )
    return {
        "label": label,
        "terms": list(columns),
        "fit_competitions": int(fit_rows["selection_id"].nunique()),
        "validation_competitions": int(validation["selection_id"].nunique()),
        "test_competitions": int(test["selection_id"].nunique()),
        "fit_success": True,
        "chosen_dial": chosen,
        "weights": weights,
        "curve": curve.assign(label=label),
        "test": {
            "equal_log_loss": _round(float(equal["log_loss"].mean()), 6),
            "full_log_loss": _round(float(full["log_loss"].mean()), 6),
            "chosen_log_loss": _round(float(used["log_loss"].mean()), 6),
            "chosen_versus_equal": _gap(used["log_loss"].to_numpy(), equal["log_loss"].to_numpy(), SEED + 51 + len(label)),
            "full_versus_equal": _gap(full["log_loss"].to_numpy(), equal["log_loss"].to_numpy(), SEED + 71 + len(label)),
            "chosen_named_the_winner": _round(float(used["named_the_winner"].mean())),
            "full_named_the_winner": _round(float(full["named_the_winner"].mean())),
            "lists_with_a_unique_pick": int(used["unique_pick"].sum()),
        },
    }


def build_outputs(frame: pd.DataFrame) -> dict:
    prepared = prepare(frame)
    specs = [(label, [term]) for term, label in TERM_LABELS.items()]
    specs.append(("Four history items together", list(LEVEL_TERMS)))
    specs.append(("Stored seven-term specification", list(PRIMARY_FEATURES)))
    results = [evaluate_spec(prepared, columns, label) for label, columns in specs]
    curves = pd.concat([item["curve"] for item in results], ignore_index=True)
    weight_rows = []
    score_rows = []
    for item in results:
        for weight in item["weights"]:
            weight_rows.append({"label": item["label"], "chosen_dial": item["chosen_dial"], **weight})
        test = item["test"]
        score_rows.append(
            {
                "label": item["label"],
                "chosen_dial": item["chosen_dial"],
                "fit_competitions": item["fit_competitions"],
                "validation_competitions": item["validation_competitions"],
                "test_competitions": item["test_competitions"],
                "equal_log_loss": test["equal_log_loss"],
                "full_log_loss": test["full_log_loss"],
                "chosen_log_loss": test["chosen_log_loss"],
                "chosen_gain": test["chosen_versus_equal"]["estimate"],
                "chosen_gain_low": test["chosen_versus_equal"]["low"],
                "chosen_gain_high": test["chosen_versus_equal"]["high"],
                "full_gain": test["full_versus_equal"]["estimate"],
                "full_gain_low": test["full_versus_equal"]["low"],
                "full_gain_high": test["full_versus_equal"]["high"],
                "chosen_named_the_winner": test["chosen_named_the_winner"],
                "full_named_the_winner": test["full_named_the_winner"],
            }
        )
    summary = {
        "fit_end": FIT_END,
        "validation_end": VALIDATION_END,
        "test_start": TEST_START,
        "dial_grid": list(DIAL_GRID),
        "draws": DRAWS,
        "seed": SEED,
        "penalty": LOGIT_PENALTY,
        "specs": [
            {
                "label": item["label"],
                "terms": item["terms"],
                "chosen_dial": item["chosen_dial"],
                "weights": item["weights"],
                "test": item["test"],
            }
            for item in results
        ],
    }
    return {
        "summary": summary,
        "curves": curves,
        "weights": pd.DataFrame(weight_rows),
        "scores": pd.DataFrame(score_rows),
    }


def write_outputs(outputs: dict, processed) -> None:
    outputs["curves"].to_csv(processed / "weight_dial_curve.csv", index=False)
    outputs["weights"].to_csv(processed / "weight_dial_weights.csv", index=False)
    outputs["scores"].to_csv(processed / "weight_dial_scores.csv", index=False)
    (processed / "weight_dial_summary.json").write_text(json.dumps(outputs["summary"], indent=2), encoding="utf-8")


def stored_full_strength_loss(frame: pd.DataFrame) -> float:
    """Log loss of the stored seven-term logit fit through 2018 and scored from 2019.

    The published research note reports this comparison. It is a check that
    this dial uses the same score, not a second estimate of that note.
    """
    prepared = prepare(frame)
    train = window(prepared, None, VALIDATION_END)
    test = window(prepared, TEST_START, None)
    fitted = fit_weights(train, list(PRIMARY_FEATURES))
    losses = score_frame(test, fitted["beta"], list(PRIMARY_FEATURES), 1.0)
    return float(losses["log_loss"].mean())
