"""Arrowstreet's own lists, against the seat it held and against firms with a similar number of lists.

The three team submissions stay on their own ids. Rank 1 is the published order,
not a signed contract. The stored winner model is not refit.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from msba_dsp.research.incumbency import experience_frame

ARROWSTREET_ID = "f_e546323383"
TEAM_IDS = ("f_3cb2cf250d", "f_e24437a0c5", "f_dbf5f944ac")
PEER_LOW = 15
PEER_HIGH = 25
SEED = 20261020
DRAWS = 2000


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return round(float(value), digits)


def _mean_interval(values: np.ndarray, draws: int = DRAWS, seed: int = SEED) -> tuple[float, float, float]:
    point = float(np.mean(values))
    rng = np.random.default_rng(seed)
    drawn = rng.choice(values, size=(draws, len(values)), replace=True)
    samples = drawn.mean(axis=1)
    return point, float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))


def list_gaps(rows: pd.DataFrame) -> pd.DataFrame:
    """One firm's lists. Gap is 1 if that firm ranked first, minus one seat's share."""
    scored = rows.copy()
    scored["seat_share"] = 1.0 / scored["n_finalists"].astype(float)
    scored["gap"] = scored["winner"].astype(float) - scored["seat_share"]
    return scored


def firm_excess(frame: pd.DataFrame, firm_id: str, seed: int = SEED) -> dict:
    rows = list_gaps(frame.loc[frame["firm_id"].eq(firm_id)])
    if rows.empty:
        return {"firm_id": firm_id, "lists": 0}
    gaps = rows["gap"].to_numpy(dtype=float)
    point, low, high = _mean_interval(gaps, seed=seed)
    name = str(rows["firm_name"].iloc[-1])
    return {
        "firm_id": firm_id,
        "firm_name": name,
        "lists": int(len(rows)),
        "rank1": int(rows["winner"].sum()),
        "expected_rank1": _round(float(rows["seat_share"].sum()), 2),
        "excess_wins": _round(float(rows["gap"].sum()), 2),
        "excess_per_list": _round(point),
        "excess_low": _round(low),
        "excess_high": _round(high),
    }


def peer_excesses(frame: pd.DataFrame) -> pd.DataFrame:
    counts = frame.groupby("firm_id").size()
    peers = counts.loc[counts.ge(PEER_LOW) & counts.le(PEER_HIGH)].index
    rows = [firm_excess(frame, firm_id, seed=SEED + index) for index, firm_id in enumerate(sorted(peers))]
    return pd.DataFrame(rows).sort_values(["excess_per_list", "firm_name"], ascending=[False, True], kind="mergesort")


def arrowstreet_cases(frame: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """One row per Arrowstreet list. Experience uses the counts already stored on the frame."""
    districts = events[["selection_id", "district"]].drop_duplicates("selection_id")
    records = []
    own_ids = set(frame.loc[frame["firm_id"].eq(ARROWSTREET_ID), "selection_id"])
    for selection_id, group in frame.groupby("selection_id", sort=False):
        if selection_id not in own_ids:
            continue
        arrow = group.loc[group["firm_id"].eq(ARROWSTREET_ID)].iloc[0]
        others = group.loc[group["firm_id"].ne(ARROWSTREET_ID)]
        more = others.loc[others["prior_wins"].gt(arrow["prior_wins"])]
        winner = group.loc[group["winner"].eq(1)].iloc[0]
        records.append(
            {
                "selection_date": arrow["selection_date"],
                "district": districts.set_index("selection_id")["district"].get(selection_id, ""),
                "school_name": arrow["school_name"],
                "category": arrow["category"],
                "n_finalists": int(arrow["n_finalists"]),
                "arrowstreet_prior_wins": int(arrow["prior_wins"]),
                "arrowstreet_ranked_first": int(arrow["winner"]),
                "firms_with_more_prior_wins": int(len(more)),
                "more_experienced_names": "; ".join(sorted(more["firm_name"].astype(str))),
                "winner_name": winner["firm_name"],
                "winner_had_more_prior_wins": int(winner["firm_id"] != ARROWSTREET_ID and int(winner["prior_wins"]) > int(arrow["prior_wins"])),
                "arrowstreet_unique_leader": int(len(others) > 0 and int(arrow["prior_wins"]) > int(others["prior_wins"].max())),
                "other_firms": "; ".join(sorted(others["firm_name"].astype(str))),
            }
        )
    return pd.DataFrame(records).sort_values(["selection_date", "school_name"], kind="mergesort")


def experience_summary(cases: pd.DataFrame) -> dict:
    more = cases.loc[cases["firms_with_more_prior_wins"].gt(0)]
    leader = cases.loc[cases["arrowstreet_unique_leader"].eq(1)]
    more_rate = None
    more_low = None
    more_high = None
    if len(more) >= 8:
        values = more["winner_had_more_prior_wins"].to_numpy(dtype=float)
        point, low, high = _mean_interval(values, seed=SEED + 50)
        more_rate, more_low, more_high = _round(point), _round(low), _round(high)
    leader_rate = None
    leader_low = None
    leader_high = None
    if len(leader) >= 8:
        values = leader["arrowstreet_ranked_first"].to_numpy(dtype=float)
        point, low, high = _mean_interval(values, seed=SEED + 51)
        leader_rate, leader_low, leader_high = _round(point), _round(low), _round(high)
    return {
        "lists": int(len(cases)),
        "lists_with_a_more_experienced_firm": int(len(more)),
        "those_won_by_a_more_experienced_firm": int(more["winner_had_more_prior_wins"].sum()) if len(more) else 0,
        "those_won_by_arrowstreet": int(more["arrowstreet_ranked_first"].sum()) if len(more) else 0,
        "more_experienced_win_rate": more_rate,
        "more_experienced_win_rate_low": more_low,
        "more_experienced_win_rate_high": more_high,
        "lists_where_arrowstreet_had_the_most_wins": int(len(leader)),
        "arrowstreet_wins_when_leader": int(leader["arrowstreet_ranked_first"].sum()) if len(leader) else 0,
        "leader_win_rate": leader_rate,
        "leader_win_rate_low": leader_low,
        "leader_win_rate_high": leader_high,
    }


def team_rows(frame: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    districts = events[["selection_id", "district"]].drop_duplicates("selection_id")
    rows = frame.loc[frame["firm_id"].isin(TEAM_IDS)].merge(districts, on="selection_id", how="left")
    keep = ["selection_date", "district", "school_name", "firm_name", "winner", "n_finalists", "prior_wins"]
    return rows[keep].sort_values(["selection_date", "firm_name"], kind="mergesort")


def build_outputs(competitors: pd.DataFrame, events: pd.DataFrame, firms: pd.DataFrame) -> dict:
    frame = experience_frame(competitors, events, firms)
    cases = arrowstreet_cases(frame, events)
    peers = peer_excesses(frame)
    own = peers.loc[peers["firm_id"].eq(ARROWSTREET_ID)]
    if own.empty:
        own_row = firm_excess(frame, ARROWSTREET_ID)
    else:
        own_row = own.iloc[0].to_dict()
    higher = int(peers.loc[peers["firm_id"].ne(ARROWSTREET_ID), "excess_per_list"].gt(own_row["excess_per_list"]).sum()) if len(peers) else 0
    return {
        "cases": cases,
        "peers": peers,
        "teams": team_rows(frame, events),
        "summary": {
            "arrowstreet": {key: (None if pd.isna(value) else value) for key, value in own_row.items()},
            "peer_firms": int(len(peers)),
            "peer_window": f"{PEER_LOW}-{PEER_HIGH} lists",
            "peers_with_higher_excess": higher,
            "experience": experience_summary(cases),
            "team_rows": int(frame["firm_id"].isin(TEAM_IDS).sum()),
            "team_rank1": int(frame.loc[frame["firm_id"].isin(TEAM_IDS), "winner"].sum()),
        },
    }


def write_outputs(outputs: dict, processed) -> None:
    outputs["cases"].to_csv(processed / "arrowstreet_lists.csv", index=False)
    outputs["peers"].to_csv(processed / "arrowstreet_peer_excess.csv", index=False)
    outputs["teams"].to_csv(processed / "arrowstreet_team_rows.csv", index=False)
    (processed / "arrowstreet_summary.json").write_text(json.dumps(outputs["summary"], indent=2, default=str), encoding="utf-8")
