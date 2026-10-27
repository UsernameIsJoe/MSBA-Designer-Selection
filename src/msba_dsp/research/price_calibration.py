"""Within-list prices built from earlier rank-1 counts.

A price is a forecast of the published order. It is not a quality score, and
it is not a claim about how the panel should have voted. Rank 1 remains the
published order, not a signed contract. The stored winner model is not refit.

Strength on a list is (earlier rank-1 count + 1/2) raised to an exponent.
Dividing by the sum of those strengths makes the prices on that list add to
one. Exponent 1 is proportional to the count. Exponent 0 is an equal chance.
The half-count is the same additive constant already used in the shrunk win
rate. It is not a fitted prior.

Counts use strictly earlier calendar dates. Two rankings on the same day do
not update each other. Description uses rankings from 2012 on, because the
archive starts in 2007. The exponent is chosen on 2012–2018 and scored on
2019–2026, the same later window as the stored winner model.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from msba_dsp.research.incumbency import experience_frame
from msba_dsp.research.market_structure import model_rows

SEED = 20261020
DRAWS = 2000
BASE = 0.5
EVAL_START = 2012
TEST_START = 2019
ALPHA_STEP = 0.05
ALPHA_MAX = 2.0
SQRT_ALPHA = 0.5
# Right edge sits above 1 so a price of 1 would still fall in the last bin.
RELIABILITY_EDGES = (0.0, 0.20, 0.35, 0.50, 0.65, 1.01)
RELIABILITY_LABELS = (
    "Under 20%",
    "20% to 35%",
    "35% to 50%",
    "50% to 65%",
    "65% or higher",
)


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return round(float(value), digits)


def alpha_grid() -> np.ndarray:
    count = int(round(ALPHA_MAX / ALPHA_STEP)) + 1
    return np.round(np.linspace(0.0, ALPHA_MAX, count), 2)


def history_frame(competitors: pd.DataFrame, events: pd.DataFrame, firms: pd.DataFrame) -> pd.DataFrame:
    """One row per model finalist, with earlier-date counts and the published rank."""
    frame = experience_frame(competitors, events, firms)
    rows = model_rows(competitors, events, firms)
    ranks = rows[["selection_id", "firm_id", "rank_num", "district", "project_label"]].copy()
    merged = frame.merge(ranks, on=["selection_id", "firm_id"], how="left", validate="one_to_one")
    if merged["rank_num"].isna().any():
        raise ValueError("a model finalist is missing a published rank")
    merged["rank_num"] = merged["rank_num"].astype(int)
    merged["winner"] = merged["winner"].astype(int)
    merged["prior_wins"] = merged["prior_wins"].astype(int)
    merged["prior_finals"] = merged["prior_finals"].astype(int)
    merged["selection_year"] = merged["selection_year"].astype(int)
    return merged.sort_values(["selection_date", "selection_id", "rank_num"], kind="mergesort").reset_index(drop=True)


def luce_prices(prior_wins: np.ndarray, alpha: float, base: float = BASE) -> np.ndarray:
    """Strengths raised to ``alpha``, normalized so the list sums to one.

    Alpha 0 returns an equal price for every firm, including a firm with no
    earlier rank-1 result. The base keeps a zero-win firm at a positive strength.
    """
    wins = np.asarray(prior_wins, dtype=float)
    if len(wins) == 0:
        return wins
    strength = np.power(wins + base, float(alpha))
    total = float(strength.sum())
    if not np.isfinite(total) or total <= 0:
        return np.full(len(wins), 1.0 / len(wins))
    return strength / total


def shrunk_rate_prices(prior_wins: np.ndarray, prior_finals: np.ndarray) -> np.ndarray:
    """The stored baseline: prices proportional to (wins + 1/2) / (finals + 1)."""
    wins = np.asarray(prior_wins, dtype=float)
    finals = np.asarray(prior_finals, dtype=float)
    strength = (wins + BASE) / (finals + 1.0)
    total = float(strength.sum())
    return strength / total


def _group_indices(frame: pd.DataFrame) -> list[np.ndarray]:
    indices: list[np.ndarray] = []
    for _, group in frame.groupby("selection_id", sort=True):
        indices.append(group.index.to_numpy())
    return indices


def assign_price(frame: pd.DataFrame, alpha: float, column: str = "p_price") -> pd.DataFrame:
    out = frame.copy()
    out[column] = np.nan
    for idx in _group_indices(out):
        out.loc[idx, column] = luce_prices(out.loc[idx, "prior_wins"].to_numpy(), alpha)
    return out


def competition_scores(frame: pd.DataFrame, prob_col: str) -> pd.DataFrame:
    """One row per ranking: log loss of the winner's price, and the Brier score."""
    records = []
    for selection_id, group in frame.groupby("selection_id", sort=True):
        if int(group["winner"].sum()) != 1:
            raise ValueError(f"{selection_id} does not have one rank-1 firm")
        probs = group[prob_col].to_numpy(dtype=float)
        if not np.allclose(probs.sum(), 1.0, atol=1e-8):
            raise ValueError(f"{selection_id} prices sum to {probs.sum()}")
        winner = group.loc[group["winner"].eq(1), prob_col].iloc[0]
        y = group["winner"].to_numpy(dtype=float)
        records.append(
            {
                "selection_id": selection_id,
                "selection_year": int(group["selection_year"].iloc[0]),
                "log_loss": float(-np.log(np.clip(winner, 1e-12, 1.0))),
                "brier": float(np.mean((probs - y) ** 2)),
            }
        )
    return pd.DataFrame(records)


def _mean_interval(values: np.ndarray, draws: int = DRAWS, seed: int = SEED) -> dict:
    point = float(np.mean(values)) if len(values) else float("nan")
    if len(values) == 0:
        return {"estimate": None, "low": None, "high": None, "n": 0}
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(draws, len(values)), replace=True).mean(axis=1)
    return {
        "estimate": _round(point),
        "low": _round(float(np.quantile(samples, 0.025))),
        "high": _round(float(np.quantile(samples, 0.975))),
        "n": int(len(values)),
    }


def fit_alpha(frame: pd.DataFrame, year_start: int = EVAL_START, year_end: int = TEST_START) -> dict:
    """Smallest grid exponent that minimizes mean log loss on the fit window.

    The window is half-open on the right: 2012 through 2018 when the defaults
    are used. The later years are not read here.
    """
    train = frame.loc[frame["selection_year"].ge(year_start) & frame["selection_year"].lt(year_end)]
    if train["selection_id"].nunique() == 0:
        raise ValueError("the exponent fit window has no rankings")
    rows = []
    best_alpha = None
    best_loss = None
    for alpha in alpha_grid():
        priced = assign_price(train, float(alpha))
        loss = float(competition_scores(priced, "p_price")["log_loss"].mean())
        rows.append({"alpha": float(alpha), "train_log_loss": _round(loss, 6), "competitions": int(priced["selection_id"].nunique())})
        if best_loss is None or loss < best_loss - 1e-12 or (abs(loss - best_loss) <= 1e-12 and float(alpha) < best_alpha):
            best_loss = loss
            best_alpha = float(alpha)
    return {"alpha": best_alpha, "train_log_loss": _round(best_loss, 6), "grid": rows}


def _rule_prices(group: pd.DataFrame, rule: str, alpha: float) -> np.ndarray:
    """Each named rule has its own exponent. ``alpha`` is only the train-set minimum."""
    if rule == "shrunk_rate":
        return shrunk_rate_prices(group["prior_wins"].to_numpy(), group["prior_finals"].to_numpy())
    exponents = {
        "equal": 0.0,
        "proportional": 1.0,
        "square_root": SQRT_ALPHA,
        "train_minimum": float(alpha),
    }
    if rule not in exponents:
        raise ValueError(f"unknown price rule: {rule}")
    return luce_prices(group["prior_wins"].to_numpy(), exponents[rule])


def score_rules(frame: pd.DataFrame, alpha_hat: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Log loss and Brier score for each price, by window, with paired gaps against an equal chance."""
    rules = (
        ("equal", 0.0),
        ("proportional", 1.0),
        ("square_root", SQRT_ALPHA),
        ("train_minimum", alpha_hat),
        ("shrunk_rate", alpha_hat),
    )
    windows = {
        "fit_2012_2018": frame["selection_year"].ge(EVAL_START) & frame["selection_year"].lt(TEST_START),
        "test_2019_2026": frame["selection_year"].ge(TEST_START),
        "describe_2012_2026": frame["selection_year"].ge(EVAL_START),
    }
    score_rows = []
    gap_rows = []
    for window, mask in windows.items():
        part = frame.loc[mask]
        losses: dict[str, np.ndarray] = {}
        briers: dict[str, np.ndarray] = {}
        ids = None
        for rule, alpha in rules:
            records = []
            for selection_id, group in part.groupby("selection_id", sort=True):
                probs = _rule_prices(group, rule, alpha)
                winner = float(probs[group["winner"].to_numpy() == 1][0])
                y = group["winner"].to_numpy(dtype=float)
                records.append((-np.log(np.clip(winner, 1e-12, 1.0)), float(np.mean((probs - y) ** 2)), selection_id))
            losses[rule] = np.array([row[0] for row in records], dtype=float)
            briers[rule] = np.array([row[1] for row in records], dtype=float)
            ids = [row[2] for row in records]
            score_rows.append(
                {
                    "window": window,
                    "rule": rule,
                    "alpha": None if rule == "shrunk_rate" else alpha,
                    "competitions": int(len(records)),
                    "log_loss": _round(float(losses[rule].mean()), 10),
                    "brier": _round(float(briers[rule].mean()), 10),
                }
            )
        for rule, _alpha in rules:
            if rule == "equal":
                continue
            gap = losses["equal"] - losses[rule]
            summary = _mean_interval(gap, seed=SEED + (sum(ord(ch) for ch in rule + window) % 10000))
            brier_gap = briers["equal"] - briers[rule]
            brier_summary = _mean_interval(brier_gap, seed=SEED + 17 + (sum(ord(ch) for ch in rule) % 1000))
            gap_rows.append(
                {
                    "window": window,
                    "rule": rule,
                    "competitions": int(len(gap)),
                    "log_loss_improvement": summary["estimate"],
                    "log_loss_low": summary["low"],
                    "log_loss_high": summary["high"],
                    "brier_improvement": brier_summary["estimate"],
                    "brier_low": brier_summary["low"],
                    "brier_high": brier_summary["high"],
                    "first_selection_id": ids[0] if ids else None,
                    "last_selection_id": ids[-1] if ids else None,
                }
            )
    return pd.DataFrame(score_rows), pd.DataFrame(gap_rows)


def _bin_index(prices: np.ndarray) -> np.ndarray:
    edges = np.asarray(RELIABILITY_EDGES[1:], dtype=float)
    return np.digitize(prices, edges, right=False)


def reliability_table(frame: pd.DataFrame, alpha: float, draws: int = DRAWS, seed: int = SEED) -> pd.DataFrame:
    """Actual rank-1 rate minus the price, inside fixed price bins.

    Lists are the resampled unit. A row can change bins across draws because
    the bin is a property of the price, which does not change, so membership
    is fixed. Resampling lists still changes the mix inside a bin.
    """
    priced = assign_price(frame, alpha)
    groups = []
    for _, group in priced.groupby("selection_id", sort=True):
        groups.append(
            (
                group["p_price"].to_numpy(dtype=float),
                group["winner"].to_numpy(dtype=float),
            )
        )
    n_bins = len(RELIABILITY_LABELS)

    def accumulate(indices: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        won = np.zeros(n_bins)
        price_sum = np.zeros(n_bins)
        count = np.zeros(n_bins)
        for index in indices:
            probs, outcomes = groups[int(index)]
            bins = _bin_index(probs)
            for bin_id in range(n_bins):
                mask = bins == bin_id
                count[bin_id] += mask.sum()
                won[bin_id] += outcomes[mask].sum()
                price_sum[bin_id] += probs[mask].sum()
        return won, price_sum, count

    point_won, point_price, point_count = accumulate(np.arange(len(groups)))
    rng = np.random.default_rng(seed)
    drawn = rng.integers(0, len(groups), size=(draws, len(groups)))
    gaps = np.full((draws, n_bins), np.nan)
    for draw_id, indices in enumerate(drawn):
        won, price_sum, count = accumulate(indices)
        for bin_id in range(n_bins):
            if count[bin_id] == 0:
                continue
            gaps[draw_id, bin_id] = won[bin_id] / count[bin_id] - price_sum[bin_id] / count[bin_id]
    rows = []
    for bin_id, label in enumerate(RELIABILITY_LABELS):
        count = int(point_count[bin_id])
        actual = float(point_won[bin_id] / count) if count else float("nan")
        predicted = float(point_price[bin_id] / count) if count else float("nan")
        column = gaps[:, bin_id]
        column = column[np.isfinite(column)]
        rows.append(
            {
                "alpha": alpha,
                "bin": label,
                "bin_low": RELIABILITY_EDGES[bin_id],
                "bin_high": RELIABILITY_EDGES[bin_id + 1],
                "finalists": count,
                "predicted": _round(predicted),
                "actual": _round(actual),
                "gap": _round(actual - predicted) if count else None,
                "gap_low": _round(float(np.quantile(column, 0.025))) if len(column) else None,
                "gap_high": _round(float(np.quantile(column, 0.975))) if len(column) else None,
            }
        )
    return pd.DataFrame(rows)


def favorite_lists(frame: pd.DataFrame, alpha: float = 1.0) -> pd.DataFrame:
    """Lists with one firm strictly ahead on earlier rank-1 counts, and that count at least 1."""
    priced = assign_price(frame, alpha)
    records = []
    for selection_id, group in priced.groupby("selection_id", sort=True):
        maximum = int(group["prior_wins"].max())
        leaders = group.loc[group["prior_wins"].eq(maximum)]
        if len(leaders) != 1 or maximum < 1:
            continue
        favorite = leaders.iloc[0]
        others = group.loc[group["firm_id"].ne(favorite["firm_id"])]
        field = "; ".join(
            f"{row.firm_name} ({int(row.prior_wins)})" for row in others.sort_values("prior_wins", ascending=False).itertuples()
        )
        records.append(
            {
                "selection_id": selection_id,
                "selection_date": favorite["selection_date"],
                "selection_year": int(favorite["selection_year"]),
                "school_name": favorite["school_name"],
                "district": favorite["district"],
                "firm_id": favorite["firm_id"],
                "firm_name": favorite["firm_name"],
                "prior_wins": int(favorite["prior_wins"]),
                "lead": int(favorite["prior_wins"] - others["prior_wins"].max()),
                "n_finalists": int(favorite["n_finalists"]),
                "seat": _round(1.0 / len(group), 6),
                "winner": int(favorite["winner"]),
                "rank_num": int(favorite["rank_num"]),
                "p_proportional": _round(float(favorite["p_price"]), 6),
                "field": field,
            }
        )
    return pd.DataFrame(records)


def _lead_label(lead: int) -> str:
    if lead <= 1:
        return "1 earlier win"
    if lead == 2:
        return "2 earlier wins"
    if lead <= 4:
        return "3 or 4 earlier wins"
    return "5 or more earlier wins"


def lead_table(favorites: pd.DataFrame) -> pd.DataFrame:
    labeled = favorites.copy()
    labeled["lead_label"] = labeled["lead"].map(_lead_label)
    order = ["1 earlier win", "2 earlier wins", "3 or 4 earlier wins", "5 or more earlier wins"]
    rows = []
    for offset, label in enumerate(order):
        part = labeled.loc[labeled["lead_label"].eq(label)]
        excess = part["winner"].to_numpy(dtype=float) - part["seat"].to_numpy(dtype=float)
        summary = _mean_interval(excess, seed=SEED + 30 + offset)
        rows.append(
            {
                "lead": label,
                "lists": int(len(part)),
                "rank1": int(part["winner"].sum()) if len(part) else 0,
                "rank1_rate": _round(float(part["winner"].mean())) if len(part) else None,
                "mean_seat": _round(float(part["seat"].mean())) if len(part) else None,
                "excess": summary["estimate"],
                "excess_low": summary["low"],
                "excess_high": summary["high"],
            }
        )
    return pd.DataFrame(rows)


def favorite_summary(favorites: pd.DataFrame) -> dict:
    excess = favorites["winner"].to_numpy(dtype=float) - favorites["seat"].to_numpy(dtype=float)
    overall = _mean_interval(excess, seed=SEED + 3)
    slices = {}
    for size in (2, 3, 4):
        part = favorites.loc[favorites["n_finalists"].eq(size)]
        gap = part["winner"].to_numpy(dtype=float) - part["seat"].to_numpy(dtype=float)
        summary = _mean_interval(gap, seed=SEED + size)
        slices[str(size)] = {
            "lists": int(len(part)),
            "rank1": int(part["winner"].sum()) if len(part) else 0,
            "rank1_rate": _round(float(part["winner"].mean())) if len(part) else None,
            "mean_seat": _round(float(part["seat"].mean())) if len(part) else None,
            "excess": summary["estimate"],
            "excess_low": summary["low"],
            "excess_high": summary["high"],
        }
    return {
        "lists": int(len(favorites)),
        "rank1": int(favorites["winner"].sum()),
        "rank1_rate": _round(float(favorites["winner"].mean())),
        "mean_seat": _round(float(favorites["seat"].mean())),
        "excess": overall["estimate"],
        "excess_low": overall["low"],
        "excess_high": overall["high"],
        "by_field_size": slices,
    }


def place_when_not_first(favorites: pd.DataFrame) -> dict:
    """On three-firm lists the favorite lost, how often the favorite is second rather than last.

    Conditional on not placing first, an exchangeable pair of opponents puts
    the favorite second half the time. The resample drops draws with no loss.
    """
    three = favorites.loc[favorites["n_finalists"].eq(3)].copy()
    losses = three.loc[three["winner"].eq(0)]
    point = float((losses["rank_num"] == 2).mean()) if len(losses) else float("nan")
    rng = np.random.default_rng(SEED + 11)
    values = three[["winner", "rank_num"]].to_numpy()
    samples = []
    if len(values):
        drawn = rng.choice(len(values), size=(DRAWS, len(values)), replace=True)
        for indices in drawn:
            sample = values[indices]
            lost = sample[sample[:, 0] == 0]
            if len(lost) == 0:
                continue
            samples.append(float(np.mean(lost[:, 1] == 2)))
    column = np.asarray(samples, dtype=float)
    return {
        "three_firm_favorites": int(len(three)),
        "three_firm_losses": int(len(losses)),
        "favorite_second": int((losses["rank_num"] == 2).sum()) if len(losses) else 0,
        "favorite_last": int((losses["rank_num"] == 3).sum()) if len(losses) else 0,
        "share_second_given_loss": _round(point),
        "share_low": _round(float(np.quantile(column, 0.025))) if len(column) else None,
        "share_high": _round(float(np.quantile(column, 0.975))) if len(column) else None,
        "four_firm_favorites": int(favorites["n_finalists"].eq(4).sum()),
    }


def upset_by_next_count(frame: pd.DataFrame, favorites: pd.DataFrame) -> dict:
    three_ids = set(favorites.loc[favorites["n_finalists"].eq(3) & favorites["winner"].eq(0), "selection_id"])
    outcomes = []
    tied = 0
    for selection_id, group in frame.groupby("selection_id", sort=True):
        if selection_id not in three_ids:
            continue
        maximum = int(group["prior_wins"].max())
        others = group.loc[group["prior_wins"].lt(maximum)]
        next_count = int(others["prior_wins"].max())
        contenders = others.loc[others["prior_wins"].eq(next_count)]
        if len(contenders) != 1:
            tied += 1
            continue
        winner_id = group.loc[group["winner"].eq(1), "firm_id"].iloc[0]
        outcomes.append(int(winner_id == contenders.iloc[0]["firm_id"]))
    summary = _mean_interval(np.asarray(outcomes, dtype=float), seed=SEED + 21)
    return {
        "upset_lists_unique_second": summary["n"],
        "upset_wins_by_second": int(np.sum(outcomes)) if outcomes else 0,
        "upset_rate": summary["estimate"],
        "upset_low": summary["low"],
        "upset_high": summary["high"],
        "upset_lists_tied_second": int(tied),
    }


def high_price_losses(favorites: pd.DataFrame, threshold: float = 0.75, limit: int = 8) -> pd.DataFrame:
    losses = favorites.loc[favorites["winner"].eq(0) & favorites["p_proportional"].ge(threshold)]
    losses = losses.sort_values(["p_proportional", "selection_date"], ascending=[False, True], kind="mergesort")
    return losses.head(limit).reset_index(drop=True)


def _window_losses(frame: pd.DataFrame, rule: str, alpha: float) -> np.ndarray:
    losses = []
    for _, group in frame.groupby("selection_id", sort=True):
        probs = _rule_prices(group, rule, alpha)
        winner = float(probs[group["winner"].to_numpy() == 1][0])
        losses.append(-np.log(np.clip(winner, 1e-12, 1.0)))
    return np.asarray(losses, dtype=float)


def paired_improvement(frame: pd.DataFrame, better_rule: str, baseline_rule: str, alpha: float, seed: int) -> dict:
    """Positive means ``better_rule`` has the lower log loss. Lists are aligned by id."""
    improvement = _window_losses(frame, baseline_rule, alpha) - _window_losses(frame, better_rule, alpha)
    summary = _mean_interval(improvement, seed=seed)
    summary["rule"] = better_rule
    summary["baseline"] = baseline_rule
    return summary


def same_day_firm_lists(frame: pd.DataFrame) -> int:
    """Firm-days on which the same firm is a finalist for two rankings."""
    counts = frame.groupby(["selection_date", "firm_id"], sort=False)["selection_id"].nunique()
    return int((counts >= 2).sum())


def build_outputs(competitors: pd.DataFrame, events: pd.DataFrame, firms: pd.DataFrame) -> dict:
    frame = history_frame(competitors, events, firms)
    described = frame.loc[frame["selection_year"].ge(EVAL_START)].copy()
    fit = fit_alpha(frame)
    scores, gaps = score_rules(frame, fit["alpha"])
    proportional = reliability_table(described, 1.0, seed=SEED + 5)
    damped = reliability_table(
        frame.loc[frame["selection_year"].ge(TEST_START)].copy(),
        fit["alpha"],
        seed=SEED + 6,
    )
    favorites = favorite_lists(described, alpha=1.0)
    standing = favorite_summary(favorites)
    places = place_when_not_first(favorites)
    places.update(upset_by_next_count(described, favorites))
    examples = high_price_losses(favorites)
    summary = {
        "eval_start": EVAL_START,
        "test_start": TEST_START,
        "base": BASE,
        "draws": DRAWS,
        "seed": SEED,
        "described_rankings": int(described["selection_id"].nunique()),
        "described_finalists": int(len(described)),
        "fit_rankings": int(frame.loc[frame["selection_year"].ge(EVAL_START) & frame["selection_year"].lt(TEST_START), "selection_id"].nunique()),
        "test_rankings": int(frame.loc[frame["selection_year"].ge(TEST_START), "selection_id"].nunique()),
        "alpha": fit["alpha"],
        "alpha_train_log_loss": fit["train_log_loss"],
        "favorite": standing,
        "place_when_not_first": places,
        "priced_at_least_60_and_lost": int((favorites["winner"].eq(0) & favorites["p_proportional"].ge(0.60)).sum()),
        "priced_at_least_75": int(favorites["p_proportional"].ge(0.75).sum()),
        "priced_at_least_75_and_lost": int((favorites["winner"].eq(0) & favorites["p_proportional"].ge(0.75)).sum()),
        "no_unique_favorite": int(described["selection_id"].nunique() - len(favorites)),
        "firm_days_on_two_lists": same_day_firm_lists(described),
        "test_versus_shrunk_rate": paired_improvement(
            frame.loc[frame["selection_year"].ge(TEST_START)].copy(),
            "train_minimum",
            "shrunk_rate",
            fit["alpha"],
            SEED + 41,
        ),
        "test_versus_square_root": paired_improvement(
            frame.loc[frame["selection_year"].ge(TEST_START)].copy(),
            "square_root",
            "train_minimum",
            fit["alpha"],
            SEED + 42,
        ),
    }
    return {
        "summary": summary,
        "grid": pd.DataFrame(fit["grid"]),
        "scores": scores,
        "gaps": gaps,
        "reliability_proportional": proportional,
        "reliability_damped_test": damped,
        "favorites": favorites,
        "leads": lead_table(favorites),
        "examples": examples,
    }


def write_outputs(outputs: dict, processed) -> None:
    outputs["grid"].to_csv(processed / "price_train_grid.csv", index=False)
    outputs["scores"].to_csv(processed / "price_forecast_scores.csv", index=False)
    outputs["gaps"].to_csv(processed / "price_forecast_gaps.csv", index=False)
    outputs["reliability_proportional"].to_csv(processed / "price_reliability.csv", index=False)
    outputs["reliability_damped_test"].to_csv(processed / "price_reliability_test.csv", index=False)
    outputs["favorites"].to_csv(processed / "price_favorites.csv", index=False)
    outputs["leads"].to_csv(processed / "price_leads.csv", index=False)
    outputs["examples"].to_csv(processed / "price_high_losses.csv", index=False)
    (processed / "price_summary.json").write_text(json.dumps(outputs["summary"], indent=2), encoding="utf-8")
