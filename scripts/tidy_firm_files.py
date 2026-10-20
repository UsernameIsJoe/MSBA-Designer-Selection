"""Fold company research into the firm directory and archive the older firm tables."""

import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from msba_dsp.processing.build import COMPANY_COLUMNS, enrich_firm_directory
from msba_dsp.processing.names import resolve_firm

PROCESSED = ROOT / "data" / "processed"
REFERENCE = ROOT / "data" / "reference"
ARCHIVE = ROOT / "data" / "archive"
INFO_CANDIDATES = [PROCESSED / "firm info.csv", ARCHIVE / "firm_info.csv"]


def blank(value) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.lower() in {"nan", "none"} else text


def match_firm_id(name: str, by_name: dict[str, str], known_ids: set[str]) -> str:
    cleaned = blank(name)
    if not cleaned:
        return ""
    direct = by_name.get(cleaned.casefold())
    if direct:
        return direct
    resolved = resolve_firm(cleaned)
    if resolved.tie_record or not resolved.canonical_key:
        return ""
    if resolved.firm_id in known_ids:
        return resolved.firm_id
    return ""


def main() -> None:
    firms = pd.read_csv(PROCESSED / "firms.csv", dtype=str, keep_default_na=False)
    competitors = pd.read_csv(PROCESSED / "competitors.csv", dtype=str, keep_default_na=False)
    events = pd.read_csv(PROCESSED / "selection_events.csv", dtype=str, keep_default_na=False)
    info_path = next(path for path in INFO_CANDIDATES if path.exists())
    info = pd.read_csv(info_path, dtype=str, keep_default_na=False)

    canonical_names = {
        blank(row.canonical_firm_name).casefold(): row.firm_id for row in firms.itertuples(index=False)
    }
    by_name = dict(canonical_names)
    for row in firms.itertuples(index=False):
        for alias in blank(row.historical_names).split("|"):
            key = alias.strip().casefold()
            if key and key not in canonical_names:
                by_name.setdefault(key, row.firm_id)
    known_ids = set(firms["firm_id"])

    company_rows = []
    for row in info.to_dict("records"):
        firm_id = match_firm_id(row.get("firm", ""), by_name, known_ids) or match_firm_id(
            row.get("matched_firm", ""), by_name, known_ids
        )
        company_rows.append(
            {
                "firm_id": firm_id,
                "source_firm_name": blank(row.get("firm")),
                "matched_firm": blank(row.get("matched_firm")),
                "aliases": blank(row.get("aliases")),
                "staff_size": blank(row.get("staff_size")),
                "staff_basis": blank(row.get("staff_basis")),
                "staff_asof": blank(row.get("staff_asof")),
                "founded_year": blank(row.get("founded_year")),
                "age_at_first_seen_years": blank(row.get("age_at_first_seen_years")),
                "age_as_of_2026": blank(row.get("age_as_of_2026")),
                "geographic_scope": blank(row.get("geographic_scope")),
                "nationwide_operations": blank(row.get("nationwide_operations")),
                "hq_location": blank(row.get("hq_location")),
                "boston_role": blank(row.get("boston_role")),
                "company_source_url": blank(row.get("source_url")),
                "company_source_url_2": blank(row.get("source_url_2")),
                "verification_status": blank(row.get("verification_status")),
                "research_note": blank(row.get("research_note")),
            }
        )

    REFERENCE.mkdir(parents=True, exist_ok=True)
    company = pd.DataFrame(company_rows)
    company.to_csv(REFERENCE / "firm_company.csv", index=False)

    # Drop a previous enrichment so the join does not duplicate columns.
    firms = firms.drop(columns=[column for column in [*COMPANY_COLUMNS, "ranked_selections", "wins", "win_rate", "avg_win_interval_years", "tries_before_first_win", "first_ranked", "last_ranked"] if column in firms.columns])
    enriched = enrich_firm_directory(firms, competitors, events)
    enriched.to_csv(PROCESSED / "firms.csv", index=False)

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    moves = [
        (PROCESSED / "firm info.csv", ARCHIVE / "firm_info.csv"),
        (PROCESSED / "firm_win_stats.csv", ARCHIVE / "firm_win_stats.csv"),
        (PROCESSED / "firm_crosswalk.csv", ARCHIVE / "firm_crosswalk.csv"),
        (PROCESSED / "source_manifest.csv", ARCHIVE / "source_manifest.csv"),
    ]
    for source, destination in moves:
        if source.exists():
            if destination.exists():
                destination.unlink()
            shutil.move(str(source), str(destination))

    matched = company.loc[company["firm_id"] != "", "firm_id"].nunique()
    verified = int(enriched["verification_status"].str.startswith("Verified").sum()) if "verification_status" in enriched else 0
    with_hq = int((enriched["hq_location"] != "").sum()) if "hq_location" in enriched else 0
    print(f"company rows {len(company)}")
    print(f"matched firm ids {matched}")
    print(f"unmatched company rows {int((company['firm_id'] == '').sum())}")
    print(f"directory firms {len(enriched)} with headquarters {with_hq} verified {verified}")
    print(f"arrowstreet wins {enriched.loc[enriched['canonical_firm_name'] == 'Arrowstreet, Inc.', ['ranked_selections', 'wins', 'hq_location', 'staff_size', 'founded_year']].to_dict('records')}")


if __name__ == "__main__":
    main()
