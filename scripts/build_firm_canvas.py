"""Build firm win stats and the participating-firms canvas.

A try is one firm on one completed ranking. The applicant list and the later
ranking for the same school count once. Repair pools, informational interviews,
and rankings that still have a blank place are left out. A win is published
rank 1, including a list that published only that firm.
"""

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
CANVAS = Path(
    r"C:\Users\tu\.cursor\projects\c-Users-tu-Desktop-MSBA\canvases\participating-firms.canvas.tsx"
)
COUNTED = {"model_sample", "single_firm"}


def load_attempts():
    competitors = list(csv.DictReader((PROCESSED / "competitors.csv").open(encoding="utf-8")))
    events = {
        row["selection_id"]: row
        for row in csv.DictReader((PROCESSED / "selection_events.csv").open(encoding="utf-8"))
    }
    grouped = defaultdict(list)
    for row in competitors:
        if row["choice_status"] not in COUNTED:
            continue
        grouped[(row["project_id"], row["firm_id"])].append(row)

    attempts = []
    for (project_id, firm_id), rows in grouped.items():
        chosen = rows[0]
        event = events.get(chosen["selection_id"])
        if event is None:
            continue
        won = chosen["winner"] == "1" or (
            chosen["choice_status"] == "single_firm" and chosen["rank_num"] in {"1", "1.0"}
        )
        attempts.append(
            {
                "firm_id": firm_id,
                "project_id": project_id,
                "selection_id": chosen["selection_id"],
                "date": datetime.strptime(event["selection_date"], "%Y-%m-%d"),
                "won": won,
            }
        )
    return attempts


def firm_stats(attempts, firms):
    by_firm = defaultdict(list)
    for attempt in attempts:
        by_firm[attempt["firm_id"]].append(attempt)

    stats = {}
    for firm in firms:
        rows = sorted(
            by_firm.get(firm["firm_id"], []),
            key=lambda item: (item["date"], item["selection_id"]),
        )
        if not rows:
            stats[firm["firm_id"]] = None
            continue
        wins = [row for row in rows if row["won"]]
        gaps = [
            (later["date"] - earlier["date"]).days / 365.25
            for earlier, later in zip(wins, wins[1:])
        ]
        if wins:
            first_win = wins[0]
            tries_before = sum(1 for row in rows if (row["date"], row["selection_id"]) < (first_win["date"], first_win["selection_id"]))
        else:
            tries_before = None
        stats[firm["firm_id"]] = {
            "ranked_selections": len(rows),
            "wins": len(wins),
            "win_rate": len(wins) / len(rows),
            "avg_win_interval_years": round(sum(gaps) / len(gaps), 2) if gaps else None,
            "tries_before_first_win": tries_before,
            "first_ranked": rows[0]["date"].date().isoformat(),
            "last_ranked": rows[-1]["date"].date().isoformat(),
        }
    return stats


def write_stats(firms, stats):
    path = PROCESSED / "firms.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    fields = list(rows[0].keys()) if rows else []
    extra = [
        "ranked_selections",
        "wins",
        "win_rate",
        "avg_win_interval_years",
        "tries_before_first_win",
        "first_ranked",
        "last_ranked",
    ]
    for name in extra:
        if name not in fields:
            fields.append(name)
    by_id = {row["firm_id"]: row for row in rows}
    for firm in firms:
        row = by_id.get(firm["firm_id"])
        item = stats[firm["firm_id"]]
        if row is None or item is None:
            continue
        row["ranked_selections"] = item["ranked_selections"]
        row["wins"] = item["wins"]
        row["win_rate"] = f"{item['win_rate']:.4f}"
        row["avg_win_interval_years"] = (
            "" if item["avg_win_interval_years"] is None else f"{item['avg_win_interval_years']:.2f}"
        )
        row["tries_before_first_win"] = (
            "" if item["tries_before_first_win"] is None else item["tries_before_first_win"]
        )
        row["first_ranked"] = item["first_ranked"]
        row["last_ranked"] = item["last_ranked"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_canvas(firms, stats, attempts):
    ranked = [firm for firm in firms if stats[firm["firm_id"]]]
    ranked.sort(key=lambda firm: (-stats[firm["firm_id"]]["ranked_selections"], firm["canonical_firm_name"]))
    lines = []
    for firm in ranked:
        item = stats[firm["firm_id"]]
        interval = "null" if item["avg_win_interval_years"] is None else f"{item['avg_win_interval_years']:.2f}"
        tries = "null" if item["tries_before_first_win"] is None else str(item["tries_before_first_win"])
        lines.append(
            "  ["
            + ", ".join(
                [
                    json.dumps(firm["canonical_firm_name"], ensure_ascii=False),
                    str(item["ranked_selections"]),
                    str(item["wins"]),
                    interval,
                    tries,
                    json.dumps(item["first_ranked"]),
                    json.dumps(item["last_ranked"]),
                    json.dumps(firm["historical_names"], ensure_ascii=False),
                ]
            )
            + "],"
        )

    n_firms = len(ranked)
    n_winners = sum(1 for firm in ranked if stats[firm["firm_id"]]["wins"] > 0)
    n_rankings = len({row["selection_id"] for row in attempts})
    first_date = min(row["date"] for row in attempts).date().isoformat()
    last_date = max(row["date"] for row in attempts).date().isoformat()

    source = f"""import {{ H1, H2, Pill, Row, Stack, Stat, Table, Text, TextInput, useCanvasState, useMemo }} from "cursor/canvas";

type Firm = {{
  firm: string;
  ranked: number;
  wins: number;
  intervalYears: number | null;
  triesBeforeWin: number | null;
  firstRanked: string;
  lastRanked: string;
  aliases: string;
}};

const RAW: Array<[string, number, number, number | null, number | null, string, string, string]> = [
{chr(10).join(lines)}
];

const FIRMS: Firm[] = RAW.map(
  ([firm, ranked, wins, intervalYears, triesBeforeWin, firstRanked, lastRanked, aliases]) => ({{
    firm,
    ranked,
    wins,
    intervalYears,
    triesBeforeWin,
    firstRanked,
    lastRanked,
    aliases,
  }}),
);

const FILTERS = [
  {{ id: "all", label: "All ranked firms" }},
  {{ id: "won", label: "Has a win" }},
  {{ id: "none", label: "No win yet" }},
] as const;

type FilterId = (typeof FILTERS)[number]["id"];
type SortId = "ranked" | "rate" | "name";

function matches(firm: Firm, filter: FilterId): boolean {{
  if (filter === "won") return firm.wins > 0;
  if (filter === "none") return firm.wins === 0;
  return true;
}}

function formatRate(firm: Firm): string {{
  const pct = Math.round((firm.wins / firm.ranked) * 1000) / 10;
  return Number.isInteger(pct) ? `${{pct.toFixed(0)}}%` : `${{pct.toFixed(1)}}%`;
}}

function formatInterval(value: number | null): string {{
  return value === null ? "\\u2014" : value.toFixed(1);
}}

function formatTries(value: number | null): string {{
  return value === null ? "\\u2014" : String(value);
}}

export default function ParticipatingFirms() {{
  const [query, setQuery] = useCanvasState("firmRankQuery", "");
  const [filter, setFilter] = useCanvasState<FilterId>("firmRankFilter", "all");
  const [sort, setSort] = useCanvasState<SortId>("firmRankSort", "ranked");

  const shown = useMemo(() => {{
    const needle = query.trim().toLowerCase();
    const next = FIRMS.filter((firm) => {{
      const haystack = (firm.firm + " " + firm.aliases).toLowerCase();
      return matches(firm, filter) && (needle === "" || haystack.includes(needle));
    }});
    next.sort((a, b) => {{
      if (sort === "name") return a.firm.localeCompare(b.firm);
      if (sort === "rate") {{
        const rate = b.wins / b.ranked - a.wins / a.ranked;
        if (rate !== 0) return rate;
        if (b.ranked !== a.ranked) return b.ranked - a.ranked;
      }} else if (b.ranked !== a.ranked) {{
        return b.ranked - a.ranked;
      }}
      return a.firm.localeCompare(b.firm);
    }});
    return next;
  }}, [query, filter, sort]);

  return (
    <Stack gap={{20}}>
      <Stack gap={{8}}>
        <H1>Win rate on completed designer rankings</H1>
        <Text tone="secondary">
          Each row is one firm. A ranked selection is one completed final ranking, counted once even when the firm also appeared on that school's applicant list. {first_date} through {last_date}.
        </Text>
      </Stack>
      <Row gap={{28}}>
        <Stat value="{n_firms}" label="Firms with a completed ranking" />
        <Stat value="{n_winners}" label="Firms with a first-place rank" />
        <Stat value="{n_rankings}" label="Completed rankings" />
      </Row>
      <Stack gap={{10}}>
        <H2>Firm ranking record</H2>
        <Text size="small" tone="tertiary">
          Win rate is wins divided by ranked selections. A win is published rank 1, including a list that named only one firm. Years between wins is the average gap between consecutive wins, and is blank with fewer than two wins. Tries before first win counts earlier rankings, and is blank when the firm has no win. Repair pools, informational interviews, and unfinished rankings are excluded. Alternate spellings stay in the firm file and still match search. Source: MSBA Designer Selection Panel results, downloaded October 20, 2026.
        </Text>
        <Row gap={{8}} wrap align="center">
          <TextInput value={{query}} onChange={{setQuery}} placeholder="Search a firm or a spelling" type="search" style={{{{ minWidth: 240 }}}} />
          {{FILTERS.map((item) => (
            <Pill key={{item.id}} active={{filter === item.id}} onClick={{() => setFilter(item.id)}}>
              {{item.label}}
            </Pill>
          ))}}
          <Pill active={{sort === "ranked"}} onClick={{() => setSort("ranked")}}>Most ranked</Pill>
          <Pill active={{sort === "rate"}} onClick={{() => setSort("rate")}}>Win rate</Pill>
          <Pill active={{sort === "name"}} onClick={{() => setSort("name")}}>A to Z</Pill>
        </Row>
        <Text size="small" tone="secondary">{{shown.length}} of {n_firms} firms</Text>
        <Table
          headers={{["Firm", "Ranked selections", "Wins", "Win rate", "Years between wins", "Tries before first win", "First ranked", "Last ranked"]}}
          columnAlign={{["left", "right", "right", "right", "right", "right", "left", "left"]}}
          rows={{shown.map((firm) => [
            firm.firm,
            String(firm.ranked),
            String(firm.wins),
            formatRate(firm),
            formatInterval(firm.intervalYears),
            formatTries(firm.triesBeforeWin),
            firm.firstRanked,
            firm.lastRanked,
          ])}}
          striped
          stickyHeader
          emptyMessage="No firms match."
        />
      </Stack>
    </Stack>
  );
}}
"""
    CANVAS.parent.mkdir(parents=True, exist_ok=True)
    CANVAS.write_text(source, encoding="utf-8")
    return n_firms, n_winners, n_rankings, first_date, last_date


def main():
    firms = list(csv.DictReader((PROCESSED / "firms.csv").open(encoding="utf-8")))
    attempts = load_attempts()
    stats = firm_stats(attempts, firms)
    path = write_stats(firms, stats)
    summary = write_canvas(firms, stats, attempts)
    ranked = [firm for firm in firms if stats[firm["firm_id"]]]
    ranked.sort(key=lambda firm: -stats[firm["firm_id"]]["wins"])
    print("stats", path)
    print("canvas", summary)
    print("attempts", len(attempts), "wins", sum(row["won"] for row in attempts))
    for firm in ranked[:8]:
        item = stats[firm["firm_id"]]
        print(
            firm["canonical_firm_name"],
            item["ranked_selections"],
            item["wins"],
            f"{item['win_rate']:.1%}",
            item["avg_win_interval_years"],
            item["tries_before_first_win"],
        )


if __name__ == "__main__":
    main()
