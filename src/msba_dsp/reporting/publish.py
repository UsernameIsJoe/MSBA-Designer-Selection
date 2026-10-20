"""Write the research report and the browser payload from fitted results."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from msba_dsp.config import DASHBOARD, REPORTS
from msba_dsp.evaluation.metrics import wilson_interval


def _edge_effects(rows: list[dict]) -> list[dict]:
    if len(rows) <= 20:
        return rows
    chosen = rows[:10] + rows[-8:]
    seen: set[str] = set()
    unique = []
    for row in chosen:
        if row["firm_id"] in seen:
            continue
        seen.add(row["firm_id"])
        unique.append(row)
    return unique


def _plain(value):
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_plain(item) for item in value.tolist()]
    if isinstance(value, (np.floating, float)):
        if not np.isfinite(value):
            return None
        return float(value)
    if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return value


def _num(value, digits: int = 3) -> str:
    if value is None:
        return "not estimated"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "not estimated"
    if not np.isfinite(number):
        return "not estimated"
    return f"{number:.{digits}f}"


def _firm_rows(frame: pd.DataFrame, ratings: dict[str, float], names: dict[str, str]) -> list[dict]:
    rows = []
    for firm_id, group in frame.groupby("firm_id", sort=False):
        wins = int(group["winner"].sum())
        appearances = int(len(group))
        low, high = wilson_interval(wins, appearances)
        by_grade = {}
        for category, grade_group in group.groupby("school_category"):
            by_grade[str(category)] = {
                "appearances": int(len(grade_group)),
                "wins": int(grade_group["winner"].sum()),
            }
        rows.append(
            {
                "firm_id": firm_id,
                "name": names.get(firm_id, firm_id),
                "appearances": appearances,
                "wins": wins,
                "win_rate": wins / appearances if appearances else None,
                "wilson_low": low,
                "wilson_high": high,
                "rating": ratings.get(firm_id),
                "rating_note": "Full-sample Plackett-Luce selection strength. Not a preselection forecast and not a design score.",
                "first_year": int(group["selection_year"].min()),
                "last_year": int(group["selection_year"].max()),
                "by_grade": by_grade,
                "joint_venture": bool(group["joint_venture"].iloc[0]),
            }
        )
    rows.sort(key=lambda item: (-item["wins"], -item["appearances"], item["name"]))
    return rows


def _project_rows(frame: pd.DataFrame, test: pd.DataFrame, names: dict[str, str]) -> list[dict]:
    oos = test.set_index(["selection_id", "firm_id"])["p_logit"] if len(test) else pd.Series(dtype=float)
    projects = []
    for selection_id, group in frame.groupby("selection_id", sort=False):
        ordered = group.sort_values("published_rank")
        head = ordered.iloc[0]
        finalists = []
        for _, row in ordered.iterrows():
            key = (selection_id, row["firm_id"])
            finalists.append(
                {
                    "firm_id": row["firm_id"],
                    "firm": names.get(row["firm_id"], row["firm_id"]),
                    "rank": int(row["published_rank"]),
                    "winner": int(row["winner"]) == 1,
                    "prior_wins": int(row["prior_wins"]),
                    "prior_finals": int(row["prior_finals"]),
                    "prior_grade_wins": int(row["prior_grade_wins"]),
                    "newcomer": int(row["newcomer"]) == 1,
                    "p_retrospective": float(row["p_logit"]),
                    "p_preperiod": float(oos.loc[key]) if key in oos.index else None,
                }
            )
        projects.append(
            {
                "selection_id": selection_id,
                "project_id": head["project_id"],
                "date": head["selection_date"],
                "year": int(head["selection_year"]),
                "district": head["district"],
                "school": head["school_name"],
                "label": head["project_label"],
                "category": head["school_category"],
                "round": head["selection_round"],
                "n_finalists": int(head["n_finalists"]),
                "budget_mid": head["budget_mid"] or None,
                "source_url": head["source_url"],
                "rank_method": head["rank_method"],
                "finalists": finalists,
            }
        )
    projects.sort(key=lambda item: item["date"], reverse=True)
    return projects


def _overview(frame: pd.DataFrame) -> dict:
    winners = frame.loc[frame["winner"] == 1]
    shares = winners["firm_id"].value_counts(normalize=True)
    by_year = []
    for year, group in frame.groupby("selection_year"):
        winner_rows = group.loc[group["winner"] == 1]
        competitions = int(group["selection_id"].nunique())
        newcomer_wins = int(((winner_rows["newcomer"] == 1)).sum())
        year_shares = winner_rows["firm_id"].value_counts(normalize=True)
        by_year.append(
            {
                "year": int(year),
                "competitions": competitions,
                "finalist_rows": int(len(group)),
                "mean_finalists": float(group.groupby("selection_id").size().mean()),
                "newcomer_wins": newcomer_wins,
                "newcomer_win_share": newcomer_wins / competitions if competitions else None,
                "top5_share": float(year_shares.head(5).sum()) if len(year_shares) else None,
            }
        )
    by_grade = []
    for category, group in winners.groupby("school_category"):
        by_grade.append(
            {
                "category": str(category),
                "wins": int(len(group)),
                "share": float(len(group) / len(winners)) if len(winners) else None,
            }
        )
    return {
        "competitions": int(frame["selection_id"].nunique()),
        "finalist_rows": int(len(frame)),
        "firms": int(frame["firm_id"].nunique()),
        "mean_finalists": float(frame.groupby("selection_id").size().mean()),
        "first_date": str(frame["selection_date"].min()),
        "last_date": str(frame["selection_date"].max()),
        "hhi": float((shares**2).sum()) if len(shares) else None,
        "top5_share": float(shares.head(5).sum()) if len(shares) else None,
        "unique_winners": int(winners["firm_id"].nunique()),
        "by_year": by_year,
        "by_grade": by_grade,
    }


def _markdown_table(rows: list[dict], columns: list[str]) -> str:
    if not rows:
        return "_None._\n"
    header = "| " + " | ".join(columns) + " |"
    rule = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(str(row.get(column, "")) for column in columns) + " |" for row in rows]
    return "\n".join([header, rule, *body]) + "\n"


def write_reports(tables: dict, analysis: dict, manifest: pd.DataFrame, overview: dict) -> None:
    quality = tables["quality"]
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    hypotheses = analysis["hypotheses"]
    metrics = [
        {
            "model": row["model"],
            "sample": row["sample"],
            "competitions": row["competitions"],
            "log_loss": _num(row["log_loss"]),
            "top_choice_accuracy": _num(row["top_choice_accuracy"]),
            "brier": _num(row["brier"]),
        }
        for row in analysis["metrics"]
    ]
    coefficients = [
        {
            "term": row["term"],
            "estimate": _num(row["estimate"]),
            "ci_low": _num(row["ci_low"]),
            "ci_high": _num(row["ci_high"]),
            "draws": row["bootstrap_draws"],
        }
        for row in analysis["primary"]["coefficients"]
    ]
    hypothesis_lines = [
        {
            "id": row["id"],
            "status": row["status"],
            "competitions": row["sample_competitions"],
            "statement": row["statement"],
        }
        for row in hypotheses
    ]
    source_lines = []
    for _, source in manifest.iterrows():
        source_lines.append(
            f"- `{source['source_id']}` — {source['title']}. Present: {source['file_present']}. "
            f"SHA-256: `{source['sha256'] or 'not hashed'}`. URL: {source['url']}"
        )
    h1 = next(row for row in hypotheses if row["id"] == "H1")
    if h1["status"] == "supported":
        practical = (
            "Among published finalists, a larger number of earlier MSBA wins is associated with a higher "
            "selection probability, and the conditional logit improves on an equal-probability baseline in the "
            "2019-forward test. That is consistent with the DSP's published interest in prior similar experience. "
            "It does not measure interview performance, consultant teams, or references, and it does not say that "
            "experience is the only criterion the panel uses."
        )
    elif h1["status"] == "unsupported":
        practical = (
            "In this public sample, prior MSBA wins are not positively associated with selection after the model "
            "controls are included. Experience narratives that treat win counts as a sufficient statistic are not "
            "supported by the fitted model."
        )
    else:
        practical = (
            "Prior MSBA wins do not yet clear the bar this project set for a stable out-of-sample claim. "
            "Firms should treat win counts as a descriptive history, not as a forecast."
        )

    quality_md = f"""# Data quality

Generated {generated}.

## Coverage

{_markdown_table([
    {"measure": key, "value": value} for key, value in quality.items()
], ["measure", "value"])}

## How a competition enters the model

A competition is in the estimation sample only when the public record lists at least two distinct firms, the published order identifies exactly one top-ranked firm, and that firm did not decline the interview. Accelerated-repair pools, informational interviews, and applicant lists without a ranking stay out of the winner model.

Ranks printed as a bulleted "ranking" without numerals use the published order, first listed as rank 1. Those competitions are flagged `published_list_order`.

Experience features for a selection use only competitions with an earlier calendar date. Same-day selections do not update one another.

## What is not in the estimation file

- Individual panelist votes. The procedures describe a 3-2-1 point system. Vote sheets are not published here.
- Firm headquarters, founding years, and marketing language. Those are not used as quality.
- Schematic-design cost performance. The cost chart is linked by MSBA and is not in this snapshot. It would also be a post-selection measurement.
- Square footage, enrollment, and new-versus-renovation scope, except where a future ingest adds them from a parsed public table.
- The full set of firms that applied but were never listed. Historical pages usually publish the ranked or interviewed set. Only the 2025-2026 chart consistently lists applicants who were not shortlisted. Shortlist probability is therefore not estimated for the historical archive.

## Firm names

Legal suffixes, punctuation, and accents are normalized automatically. A short reviewed alias list covers published spelling and name continuity such as SMMA and successive JCJ labels. Joint ventures and "in association with" listings keep separate identifiers. Medium-confidence aliases are counted in the quality summary and listed in `data/processed/firm_alias_audit.csv`. Near-duplicate names that were not merged are in `data/processed/near_duplicate_firms.csv`.

## Left censoring

The archive starts in 2007, and 2007-2008 are thin. A firm with no earlier row is an MSBA-record newcomer, not necessarily a new practice. Tests of newcomer status emphasize selections from 2012 onward.
"""

    source_md = f"""# Source inventory and feasibility

Generated {generated}.

Hashes cover the local snapshot. `local_mtime_utc` in `data/manifests/sources.csv` is the file modification time. It is not a separately logged download timestamp. Publication dates are left blank when the file does not state one.

{chr(10).join(source_lines)}

## Availability

| Question | Status |
| --- | --- |
| Who was ranked, and in what order? | Available from the 2007-2024 HTML results and the 2025-2026 chart. |
| Who applied but was not interviewed? | Available for many 2025-2026 chart projects. Not consistently available before that. |
| Project district and school | Parsed from the result heading or the chart. |
| Grade level | Inferred from the school name. Unspecified when the name does not say. |
| Preselection construction-cost range | Printed on the 2025-2026 chart only. |
| Final or bid cost, cost per square foot | Not in the local snapshot. Not estimated. |
| Panelist-level votes | Not published in these files. Not invented. |
| Firm office location | Not in the DSP result files. Not estimated. |

## Feasibility

The winner-among-finalists question is feasible. Conditional probabilities sum to one inside each published choice set. The probability of being shortlisted from an unknown applicant pool is not feasible for the historical HTML. Cost-performance hypotheses are not feasible until the construction cost chart, or another public cost series, is parsed without treating post-selection costs as preselection information.
"""

    report = f"""# MSBA designer selection: research note

Generated {generated} by `python -m msba_dsp.pipeline`. Figures below are computed from the local public snapshots. They are associations inside published finalist sets.

## Question

After conditioning on the published choice set, which observable firm histories are associated with being ranked first, and do those associations predict later competitions better than simple baselines?

This note does not treat a low predicted probability as evidence of improper conduct.

## Sample

The model sample contains **{overview['competitions']}** competitions and **{overview['finalist_rows']}** finalist rows, from **{overview['first_date']}** to **{overview['last_date']}**. **{overview['firms']}** firms appear. The mean choice set has **{_num(overview['mean_finalists'], 2)}** firms. **{overview['unique_winners']}** firms win at least once. The winner Herfindahl index is **{_num(overview['hhi'], 3)}** and the five most frequent winners account for **{_num(overview['top5_share'], 3)}** of wins.

The in-sample logit is fit on every model competition. Out-of-sample scores for 2019 onward use a model fit only on competitions through 2018 ({analysis['train_competitions']} training competitions, {analysis['test_competitions']} test competitions). Random splits are not used.

## Baselines and models

Choice-set log loss is the mean negative log probability of the firm that was ranked first. Lower is better. An equal-probability model on a three-firm field has a log loss near 1.10. Top-choice accuracy counts a competition only when one firm has a strictly higher probability than the others and that firm was ranked first. An equal-probability model therefore scores zero on accuracy, because it does not name a unique favorite. A baseline that piles probability on a frequent winner can have a high accuracy and a poor log loss when it is confidently wrong.

{_markdown_table(metrics, ["model", "sample", "competitions", "log_loss", "top_choice_accuracy", "brier"])}

The conditional logit is the interpretable model. Its linear score uses prior wins, same-grade wins, prior finalist appearances, a newcomer indicator, and interactions of prior wins with field size, year, and high-school status. Project-only variables are not entered by themselves, because they do not vary among finalists.

Gradient boosting is trained through 2018 and then normalized so probabilities inside each later competition sum to one. Feature importance is not a causal effect. The Plackett-Luce rating is selection strength against other finalists. Penalized firm effects are residuals after the experience covariates, shrunk toward zero.

### Conditional-logit coefficients

Bootstrap percentile intervals, competition resample. A positive prior-wins coefficient means more earlier wins are associated with a higher selection probability inside the choice set.

{_markdown_table(coefficients, ["term", "estimate", "ci_low", "ci_high", "draws"])}

## Hypotheses

{_markdown_table(hypothesis_lines, ["id", "status", "competitions", "statement"])}

"""
    for row in hypotheses:
        report += f"### {row['id']}. {row['status']}\n\n{row['detail']}\n\nLimitation: {row['limitation']}\n\n"

    report += f"""## Unexpected model outcomes

{len(analysis['anomalies'])} competitions are listed in the dashboard where the walk-forward model assigned the eventual top-ranked firm a probability of 0.15 or less and preferred someone else. The model for year Y is fit only on earlier years. These are unexpected model outcomes. They are not findings of bias, favoritism, or misconduct. Missing interview evidence is the first explanation to consider.

## Reading for firms preparing an MSBA submission

{practical}

The DSP's published criteria also include past performance on budget and schedule, current workload, personnel, consultants, and proximity or willingness to attend local meetings. This dataset measures the selection outcome and the firm's earlier MSBA finalist record. It does not measure those other criteria. Architectural design quality is **not directly measured**.

## Updating

Replace or add the HTML and Excel snapshots in `data/raw`, keep the source pages listed in `src/msba_dsp/ingestion/sources.py`, and rerun the pipeline. New result pages should be added as new snapshots rather than overwritten without a hash. If a source disappears, the previous hashed snapshot remains the estimation file and the manifest shows which sources are absent.
"""
    (REPORTS / "data_quality.md").write_text(quality_md, encoding="utf-8")
    (REPORTS / "source_inventory.md").write_text(source_md, encoding="utf-8")
    (REPORTS / "research_report.md").write_text(report, encoding="utf-8")


def publish(tables: dict, analysis: dict, manifest: pd.DataFrame) -> None:
    frame = analysis["frame"]
    names = tables["firms"].set_index("firm_id")["canonical_firm_name"].to_dict()
    overview = _overview(frame)
    write_reports(tables, analysis, manifest, overview)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quality": tables["quality"],
        "overview": overview,
        "firms": _firm_rows(frame, analysis["ratings_full"], names),
        "projects": _project_rows(frame, analysis["test"], names),
        "experience_curve": analysis["experience_curve"],
        "metrics": analysis["metrics"],
        "coefficients": analysis["primary"]["coefficients"],
        "calibration": analysis["calibration"],
        "gbm_importance": analysis["gbm_importance"],
        "firm_effects": _edge_effects(analysis["firm_effects"]),
        "hypotheses": analysis["hypotheses"],
        "anomalies": analysis["anomalies"],
        "early_wins": analysis["early_wins"],
        "late_wins": analysis["late_wins"],
        "lab": {
            "models": analysis["lab_models"],
            "snapshots": analysis["snapshots"],
            "firm_names": [{"firm_id": firm_id, "name": name} for firm_id, name in sorted(names.items(), key=lambda item: item[1])],
        },
        "sources": manifest[["source_id", "title", "url", "file_present", "sha256"]].to_dict("records"),
        "limits": [
            "Probabilities are conditional on appearing in the published finalist or ranked-applicant set.",
            "Full-sample probabilities on a historical project use later competitions and are retrospective descriptions.",
            "Pre-period probabilities for 2019 onward were fit only through 2018.",
            "Architectural design quality is not directly measured.",
            "Cost efficiency is not scored. The construction cost chart was not in the local snapshot.",
            "Unexpected model outcomes are not evidence of misconduct.",
        ],
    }
    text = "window.PLATFORM = " + json.dumps(_plain(payload), ensure_ascii=False) + ";\n"
    (DASHBOARD / "platform.js").write_text(text, encoding="utf-8")
