"""Metrics for competitions in which probabilities sum to one."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if trials <= 0:
        return None, None
    p = successes / trials
    z2 = z * z
    den = 1.0 + z2 / trials
    center = (p + z2 / (2.0 * trials)) / den
    half = z * math.sqrt((p * (1.0 - p) / trials) + z2 / (4.0 * trials * trials)) / den
    return max(0.0, center - half), min(1.0, center + half)


def softmax(scores: np.ndarray) -> np.ndarray:
    shifted = scores - np.max(scores)
    weights = np.exp(shifted)
    total = weights.sum()
    if not np.isfinite(total) or total <= 0:
        return np.full(scores.shape, 1.0 / len(scores))
    return weights / total


def attach_probabilities(frame: pd.DataFrame, score_col: str, prob_col: str) -> pd.DataFrame:
    """Softmax a score inside each selection. Ties in the score share probability."""
    out = frame.copy()
    out[prob_col] = np.nan
    for _, idx in out.groupby("selection_id", sort=False).groups.items():
        scores = out.loc[idx, score_col].to_numpy(dtype=float)
        out.loc[idx, prob_col] = softmax(scores)
    return out


def _winner_probs(frame: pd.DataFrame, prob_col: str) -> np.ndarray:
    winners = frame.loc[frame["winner"] == 1, ["selection_id", prob_col]]
    return winners[prob_col].to_numpy(dtype=float)


def choice_log_loss(frame: pd.DataFrame, prob_col: str) -> float:
    probs = np.clip(_winner_probs(frame, prob_col), 1e-12, 1.0)
    if len(probs) == 0:
        return float("nan")
    return float(-np.log(probs).mean())


def top_choice_accuracy(frame: pd.DataFrame, prob_col: str) -> float:
    """Share of competitions whose unique highest probability is the winner.

    Equal probabilities are not credited. Otherwise a stable sort that lists
    the winner first would make a tied baseline look perfect.
    """
    correct = 0
    total = 0
    for _, group in frame.groupby("selection_id", sort=False):
        if int(group["winner"].sum()) != 1:
            continue
        total += 1
        top = group[prob_col].max()
        leaders = group.loc[np.isclose(group[prob_col], top), "firm_id"]
        actual = group.loc[group["winner"] == 1, "firm_id"].iloc[0]
        correct += int(len(leaders) == 1 and leaders.iloc[0] == actual)
    return float(correct / total) if total else float("nan")


def brier_score(frame: pd.DataFrame, prob_col: str) -> float:
    """Mean squared error of the choice probabilities, averaged over competitions."""
    scores: list[float] = []
    for _, group in frame.groupby("selection_id", sort=False):
        if int(group["winner"].sum()) != 1:
            continue
        y = group["winner"].to_numpy(dtype=float)
        p = group[prob_col].to_numpy(dtype=float)
        scores.append(float(np.mean((p - y) ** 2)))
    return float(np.mean(scores)) if scores else float("nan")


def probability_sums(frame: pd.DataFrame, prob_col: str, tol: float = 1e-8) -> bool:
    totals = frame.groupby("selection_id", sort=False)[prob_col].sum()
    return bool(np.allclose(totals.to_numpy(dtype=float), 1.0, atol=tol))
