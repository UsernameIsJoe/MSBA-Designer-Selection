"""Collapse printed firm names that are the same office spelled differently.

Joint ventures, ties, and predecessor firms stay separate. The raw names
remain in firm_crosswalk.csv.
"""

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

# Each inner list is one firm. The canonical label is the spelling that
# appears most often.
GROUPS = [
    ["Arrowstreet, Inc.", "Arrowstreet Inc.", "Arrowstreet", "ArrowStreet, Inc.", "Arrowstreet, Inc.."],
    ["Drummey Rosane Anderson, Inc.", "Drummey Rosane Anderson, Inc"],
    ["Kaestle Boos Associates, Inc.", "Kaestle Boos Associates", "Kaestle Boos Associates , Inc."],
    ["Flansburgh Associates, Inc.", "Flansburgh Architects", "Flansburgh Architect", "Flansburgh Associates", "Flansburg Architects"],
    ["Mount Vernon Group Architects, Inc.", "Mount Vernon Group Architects", "Mount Vernon Group, Inc.", "Mount Vernon Group", "Mount Vernon Group Architects, Inc. (as determined at the September 18, 2012 DSP meeting)"],
    ["Raymond Design Associates, Inc.", "Raymond Design Associates", "RDA Architects"],
    ["Dore & Whittier Architects, Inc.", "Dore + Whittier", "Dore + Whittier Architects", "Dore + Whittier Architects, Inc", "Dore & Whittier Associates, Inc.", "Dore and Whittier Architects, Inc."],
    ["JCJ Architecture, PC", "JCJ Architecture, P.C.", "JCJ Architecture PC", "JCJ Architects PC", "JCJ Architects, PC", "JCJ Architecture and Interiors, PC", "JCJ Architecture + Interiors, PC", "JCJ Architecture & Interiors, PC"],
    ["Turowski2 Architecture, Inc.", "Turowski 2", "Turowski 2 Architecture, Inc.", "Turowoski2 Architecture, Inc."],
    ["Symmes Maini & McKee Associates, Inc.", "Symmes Maini & McKee Associates", "SMMA", "Symmes Maini & McKee Associates, Inc. (SMMA)", "Symmes Maini & Mckee Associates", "Symmes Maini McKee Associates, Inc.", "Symmes Maini& McKee Associates, Inc."],
    ["HMFH Architects, Inc.", "HMFH Architects"],
    ["Miller Dyer Spears Inc.", "Miller Dyer Spears, Inc.", "Miller Dyer Spears", "Miller Dyer Spears, Inc", "Miller Dyer Spears Architects, Inc", "Miller Dyer Spears Architects, Inc."],
    ["OMR Architects, Inc.", "The Office of Michael Rosenfeld, Inc."],
    ["Perkins Eastman", "Perkins Eastman|DPC", "Perkins Eastman / DPC", "Perkins Eastman DPC", "Perkins Eastman | DPC", "Perkins Eastman/DPC", "Perkins Eastman | Design Partnership of Cambridge, Inc."],
    ["Lamoureux Pagano & Associates, Inc.", "Lamoureux Pagano Associates, Inc.", "Lamoureux Pagano Associates Architects", "Lamoureux Pagano Associates | Architects, Inc.", "Lamoureux Pagano Associates", "Lamoureux Pagano Associates | Architects", "Lamoureaux Pagano Associates | Architects", "Lamoureaux, Pagano & Associates, Inc.", "Lamoureux Pagano Associates, Architects", "Lamoureux Pagano & Associates, Inc. (as determined at the Feb. 28, 2012 DSP meeting)"],
    ["Ai3 Architects LLC", "Ai3 Architects, LLC", "AI3 Architects, LLC"],
    ["Jonathan Levi Architects, LLC", "Jonathan Levi Architects LLC", "Jonathan Levi Architects", "Jonathan Levi Associates, Inc."],
    ["Tappé Associates, Inc.", "Tappe Architects, Inc.", "Tappe Associates, Inc.", "Tappè Associates, Inc.", "Tappé Architects, Inc.", "Tappe Architects", "Tappè Architects, Inc."],
    ["DiNisco Design, Inc.", "DiNisco Design Partnership, Limited", "DiNisco Design Partnership, Ltd.", "DiNisco Design", "DiNisco Design Inc.", "DiNisco Design Partnership Limited", "DiNisco Design, Inc. (declined to interview)"],
    ["Jones Whitsett Architects, Inc.", "Jones Whitsett Architects", "Jones Whitsett Associates"],
    ["S/L/A/M Collaborative", "The S/L/A/M Collaborative", "The SLAM Collaborative, Inc.", "The S/L/A/M Collaborative, Inc."],
    ["Perkins + Will", "Perkins+Will", "Perkins & Will, Inc.", "Perkins & Will", "Perkins & Will Architects, Inc.", "Perkins & Will Architecture, Inc."],
    ["TSKP Studio", "TSKP Studio, LLC", "TSKP Studios, Inc.", "Tai Soo Kim Partners, LLC", "Tai Soo Kim Partners Architects"],
    ["LaVallee Brensinger Architects", "LaVallee Brensinger", "Lavallee Brensinger Architects", "LaValle Bresinger Architects, Inc", "LaVallee Brensigner", "LaVallee Brensigner Architects"],
    ["Studio G Architects, Inc.", "Studio G. Architects, Inc.", "Studio G Architects", "Studio G Architects, Inc", "Studio G. Architects"],
    ["Finegold Alexander Architects, Inc.", "Finegold Alexander and Associates, Inc.", "Finegold Alexander Architects", "Finegold Alexander and Associates Inc."],
    ["CGKV Architects, Inc.", "CGKV Architects, Inc"],
    ["Caolo & Bieniek Associates, Inc.", "Caolo & Bieniek Associates", "Caolo Bieniek Associates, Inc."],
    ["Knight, Bagge & Anderson, Inc.", "Knight Bagge & Anderson, Inc."],
    ["CSS Architects, Inc.", "CSS Architects Incorporated"],
    ["Habeeb & Associates Architects, Inc.", "Habeeb & Associates, Inc.", "Habeeb & Associates Architects"],
    ["Taylor & Burns, Inc.", "Taylor & Burns Architects", "Taylor & Burns"],
    ["Machado and Silvetti Associates, LLC", "Machado Silvetti Associates, LLC"],
    ["Saam Architecture", "saam architecture LLC", "saam architecture"],
    ["Tighe & Bond, Inc.", "Tighe & Bond"],
    ["CBT/Childs Bertman Tseckares Inc.", "CBT/Childs Bertman Tseckares, Inc.", "CBT/Childs Bertram Tseckares, Inc."],
    ["Russo Barr Associates, Inc."],
    ["Icon Architecture, Inc.", "Icon Architecture", "ICON architecture, inc."],
    ["Dietz & Co. Architects, Inc.", "Dietz & Company Architects, Inc.", "Dietz & Company"],
    ["William Rawn Associates, Architects, Inc.", "William Rawn Associates, Architects Inc.", "William Rawn Associations, Architects, Inc."],
    ["ARC/Architectural Resources Cambridge", "ARC/Architectural Resources Cambridge, Inc."],
    ["Baker/Wohl Architects, Inc.", "Baker | Wohl Architects, Inc.", "Baker Wohl Architects, Inc.", "Baker/Wohl Architects"],
    ["BLW Engineers, Inc.", "BLW Engineering"],
    ["Civitects Architecture", "Civitects", "Civitects PC"],
    ["EDM Architecture & Engineering, PC", "Edm"],
    ["Hesnor Engineering Company", "Hesnor Engineering"],
    ["Shekar & Associates, Inc.", "Shekar & Associates"],
    ["Fletcher Thompson Architecture Engineering, LLC", "Fletcher Thompson Architecture Engineering, LLC."],
    ["DiMarinisi & Wolfe Architects", "DiMarinisi & Wolfe Architects Urban Design"],
    ["Cannon Boston, Inc. dba Cannon Design", "Cannon Boston, Inc. and affiliates d/b/a Cannon Design"],
    ["BVH Integrated Services", "BVH Integrated Services, Inc."],
    ["Consulting Engineering Services", "Consulting Engineering Services LLC"],
    ["HAKS Engineers", "HAKS Engineers, P.C."],
    ["Next Phase Studios", "Next Phase Studios Architects"],
    ["Leers Weinzapfel Associates Architects, Inc.", "Leers Weinsapfel Associates"],
    ["LPBA Architects, Inc.", "LPBA/Architects, Inc."],
]


def spelling_rows() -> list[dict]:
    """One row per printed spelling, counted from the archive and the chart."""
    archive = list(csv.DictReader((PROCESSED / "archive_firm_lists.csv").open(encoding="utf-8")))
    chart = list(csv.DictReader((PROCESSED / "chart_firms.csv").open(encoding="utf-8")))
    projects = {
        row["project_id"]: row
        for row in csv.DictReader((PROCESSED / "chart_projects.csv").open(encoding="utf-8"))
    }
    raw: dict[str, dict] = defaultdict(
        lambda: {
            "appearances": 0,
            "first_place": 0,
            "final_rankings": 0,
            "applicant_lists": 0,
            "repair_pools": 0,
            "informational": 0,
            "other": 0,
            "first_seen": "",
            "last_seen": "",
        }
    )

    def touch(bucket: dict, day: str) -> None:
        if not day:
            return
        if not bucket["first_seen"] or day < bucket["first_seen"]:
            bucket["first_seen"] = day
        if not bucket["last_seen"] or day > bucket["last_seen"]:
            bucket["last_seen"] = day

    for row in archive:
        bucket = raw[row["firm_raw"].strip()]
        bucket["appearances"] += 1
        kind = row["list_kind"]
        if kind == "final_ranking":
            bucket["final_rankings"] += 1
            if row["position"] == "1":
                bucket["first_place"] += 1
        elif kind == "unranked_applicants":
            bucket["applicant_lists"] += 1
        elif kind == "pool_recommendation":
            bucket["repair_pools"] += 1
        elif kind == "informational":
            bucket["informational"] += 1
        else:
            bucket["other"] += 1
        touch(bucket, row["meeting_date"])

    for row in chart:
        bucket = raw[row["firm_raw"].strip()]
        bucket["appearances"] += 1
        project = projects.get(row["project_id"], {})
        if row["stage"] == "final":
            bucket["final_rankings"] += 1
            if str(row["rank"]) == "1":
                bucket["first_place"] += 1
            touch(bucket, project.get("interview_date") or project.get("application_review_date") or "")
        else:
            bucket["applicant_lists"] += 1
            touch(bucket, project.get("application_review_date") or "")

    return [{"firm": name, **counts} for name, counts in raw.items()]


def same_list_collisions(groups: list[list[str]]) -> list[str]:
    with (PROCESSED / "archive_firm_lists.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    lists: dict[tuple, set[str]] = defaultdict(set)
    for row in rows:
        lists[(row["meeting_date"], row["project"], row["list_kind"])].add(row["firm_raw"].strip())
    problems = []
    for group in groups:
        if len(group) < 2:
            continue
        members = set(group)
        for key, names in lists.items():
            found = sorted(members & names)
            if len(found) > 1:
                problems.append(f"{found} on {key[0]} | {key[1][:60]} | {key[2]}")
    return problems


def main() -> None:
    raise SystemExit(
        "Retired. data/processed/firms.csv is the firm directory, and "
        "data/reference/firm_company.csv holds the company profile. "
        "Running this script would replace that directory with the older list-count table."
    )
    firms = spelling_rows()
    known = {row["firm"] for row in firms}
    assigned: dict[str, str] = {}
    collisions = same_list_collisions(GROUPS)
    if collisions:
        print("SAME-LIST COLLISIONS")
        for line in collisions:
            print(" ", line)
        raise SystemExit(1)
    for group in GROUPS:
        missing = [name for name in group if name not in known]
        if missing:
            print("MISSING FROM DATA")
            for name in missing:
                print(" ", name)
            raise SystemExit(1)
        counts = {row["firm"]: int(row["appearances"]) for row in firms if row["firm"] in group}
        canonical = sorted(group, key=lambda name: (-counts[name], len(name), name))[0]
        for name in group:
            assigned[name] = canonical
    for row in firms:
        assigned.setdefault(row["firm"], row["firm"])

    by_firm: dict[str, list[dict]] = defaultdict(list)
    for row in firms:
        by_firm[assigned[row["firm"]]].append(row)

    merged = []
    for canonical, parts in by_firm.items():
        parts.sort(key=lambda row: (-int(row["appearances"]), row["firm"]))
        aliases = [row["firm"] for row in parts if row["firm"] != canonical]
        dates = [row["first_seen"] for row in parts if row["first_seen"]]
        last_dates = [row["last_seen"] for row in parts if row["last_seen"]]
        merged.append(
            {
                "firm": canonical,
                "appearances": sum(int(row["appearances"]) for row in parts),
                "first_place": sum(int(row["first_place"]) for row in parts),
                "final_rankings": sum(int(row["final_rankings"]) for row in parts),
                "applicant_lists": sum(int(row["applicant_lists"]) for row in parts),
                "repair_pools": sum(int(row["repair_pools"]) for row in parts),
                "informational": sum(int(row["informational"]) for row in parts),
                "other": sum(int(row["other"]) for row in parts),
                "first_seen": min(dates) if dates else "",
                "last_seen": max(last_dates) if last_dates else "",
                "spellings": len(parts),
                "aliases": " | ".join(aliases),
            }
        )
    merged.sort(key=lambda row: (-row["appearances"], row["firm"].lower()))

    fieldnames = list(merged[0].keys())
    with (PROCESSED / "firms.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged)

    with (PROCESSED / "firm_crosswalk.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["raw_name", "firm", "raw_appearances"])
        writer.writeheader()
        for row in sorted(firms, key=lambda item: item["firm"].lower()):
            writer.writerow(
                {
                    "raw_name": row["firm"],
                    "firm": assigned[row["firm"]],
                    "raw_appearances": row["appearances"],
                }
            )

    multi = [row for row in merged if row["spellings"] > 1]
    print(f"printed names {len(firms)}")
    print(f"firms after merge {len(merged)}")
    print(f"groups with more than one spelling {len(multi)}")
    for row in multi:
        print(f"{row['spellings']}  {row['firm']}  <-  {row['aliases']}")


if __name__ == "__main__":
    main()
