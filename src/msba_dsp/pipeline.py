"""Run the local research pipeline from verified snapshots."""

from __future__ import annotations

import importlib.util
import logging
import sqlite3
from pathlib import Path

import pandas as pd

from msba_dsp.config import DASHBOARD, MANIFESTS, PROCESSED, REPORTS, ROOT
from msba_dsp.evaluation.metrics import probability_sums
from msba_dsp.ingestion.manifest import build_manifest
from msba_dsp.models.analysis import run_analysis
from msba_dsp.processing.build import (
    add_decision_date_features,
    chart_competitions,
    cost_table,
    enrich_firm_directory,
    firm_directory,
    historical_competitions,
    near_duplicate_report,
    quality_summary,
)
from msba_dsp.reporting.publish import publish

LOGGER = logging.getLogger("msba_dsp")


def run_collector() -> None:
    path = ROOT / "scripts" / "collect_dsp_results.py"
    spec = importlib.util.spec_from_file_location("collect_dsp_results", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load parser from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED / name, dtype=str, keep_default_na=False)


def _write_sqlite(path: Path, tables: dict[str, pd.DataFrame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    try:
        for name, frame in tables.items():
            if frame is None or frame.empty:
                continue
            column_sql = []
            for column in frame.columns:
                kind = "REAL" if pd.api.types.is_numeric_dtype(frame[column]) else "TEXT"
                column_sql.append(f'"{column}" {kind}')
            connection.execute(f'CREATE TABLE "{name}" ({", ".join(column_sql)})')
            placeholders = ", ".join(["?"] * len(frame.columns))
            values = frame.astype(object).where(pd.notna(frame), None)
            connection.executemany(
                f'INSERT INTO "{name}" VALUES ({placeholders})',
                list(values.itertuples(index=False, name=None)),
            )
        connection.commit()
    finally:
        connection.close()


def build_research_tables() -> dict[str, pd.DataFrame]:
    archive = _read("archive_firm_lists.csv")
    chart_projects = _read("chart_projects.csv")
    chart_firms = _read("chart_firms.csv")
    events_h, competitors_h, shortlists = historical_competitions(archive)
    events_c, competitors_c = chart_competitions(chart_projects, chart_firms)
    events = pd.concat([events_h, events_c], ignore_index=True)
    competitors = pd.concat([competitors_h, competitors_c], ignore_index=True)
    firms, aliases = firm_directory(competitors)
    firms = enrich_firm_directory(firms, competitors, events)
    costs = cost_table(events)
    featured = add_decision_date_features(competitors, events)
    return {
        "archive": archive,
        "events": events,
        "competitors": competitors,
        "shortlists": shortlists,
        "firms": firms,
        "aliases": aliases,
        "costs": costs,
        "featured": featured,
        "near_duplicates": near_duplicate_report(firms),
        "quality": quality_summary(archive, events, competitors, featured, firms, costs, aliases),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for path in (PROCESSED, MANIFESTS, REPORTS, DASHBOARD):
        path.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Parsing local MSBA snapshots")
    run_collector()
    manifest = build_manifest()
    manifest.to_csv(MANIFESTS / "sources.csv", index=False)
    tables = build_research_tables()
    featured = tables["featured"]
    if featured.empty:
        raise RuntimeError("No model-ready competitions were built from the public snapshots.")
    LOGGER.info(
        "Model sample: %s competitions, %s finalist rows, %s firms",
        featured["selection_id"].nunique(),
        len(featured),
        tables["firms"]["firm_id"].nunique(),
    )
    analysis = run_analysis(featured, tables["firms"])
    if not probability_sums(analysis["frame"], "p_logit"):
        raise RuntimeError("Conditional-logit probabilities do not sum to one.")
    if not probability_sums(analysis["test"], "p_logit"):
        raise RuntimeError("Out-of-sample probabilities do not sum to one.")
    export_tables = {
        "projects": tables["events"][
            [
                "project_id",
                "district",
                "school_name",
                "school_category",
                "selection_date",
                "source_url",
            ]
        ].drop_duplicates("project_id"),
        "selection_events": tables["events"],
        "competitors": tables["competitors"],
        "firms": tables["firms"],
        "firm_alias_audit": tables["aliases"],
        "project_costs": tables["costs"],
        "model_frame": analysis["frame"].drop(columns=["_linear_score"], errors="ignore"),
        "shortlists": tables["shortlists"],
        "near_duplicate_firms": tables["near_duplicates"],
    }
    for name, frame in export_tables.items():
        frame.to_csv(PROCESSED / f"{name}.csv", index=False)
    _write_sqlite(PROCESSED / "msba_dsp.sqlite", export_tables)
    publish(tables, analysis, manifest)
    for row in analysis["metrics"]:
        LOGGER.info(
            "%s [%s] loss=%.3f accuracy=%.3f n=%s",
            row["model"],
            row["sample"],
            row["log_loss"],
            row["top_choice_accuracy"],
            row["competitions"],
        )
    LOGGER.info("Wrote reports, SQLite, and dashboard/platform.js")


if __name__ == "__main__":
    main()
