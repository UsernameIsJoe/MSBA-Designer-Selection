from pathlib import Path

import pandas as pd

from msba_dsp.research.panel_history import (
    OFFICIAL_2026,
    assign_era,
    audit_roster,
    era_table,
    person_key,
    seat_group,
)


def test_middle_initials_match_the_october_2026_page():
    assert person_key("Rachel Shanley") == person_key("Rachel E. Shanley")
    assert person_key("John Jumpe Jr.") == person_key("John F. Jumpe Jr.")
    assert person_key("John Ferrante") == person_key("John S. Ferrante")
    assert seat_group("MSBA Staff; alternate to one of three staff seats") == "staff_alternate"
    assert seat_group("MSBA Staff, Registered Architect") == "msba_staff"


def test_october_2026_names_are_the_local_roster_page():
    import re

    html = (Path(__file__).resolve().parents[1] / "data" / "reference" / "panel_members.html").read_text(encoding="utf-8")
    start = html.find("MSBA Designer Selection Panel")
    end = html.find("Mr. Jumpe will serve")
    items = re.findall(r"<li>(.*?)</li>", html[start:end])
    matched = []
    for item in items:
        hits = [name for name, _designation in OFFICIAL_2026 if name in item]
        assert hits == [hits[0]]
        matched.append(hits[0])
    assert matched == [name for name, _designation in OFFICIAL_2026]
    assert "alternate" in html[end : end + 500].lower()


def test_a_2026_designation_is_not_copied_onto_an_earlier_snapshot():
    roster = pd.read_csv(Path(__file__).resolve().parents[1] / "data" / "processed" / "dsp_roster_inferred.csv", dtype=str, keep_default_na=False)
    audited, timeline, overlap = audit_roster(roster)
    brown = audited.loc[audited["person_key"].eq("karl brown")]
    assert set(brown["era"]) == {"2010-2012", "2013-2017", "2018-2024", "2025-2026"}
    assert brown.loc[brown["era"].eq("2010-2012"), "october_2026_designation"].iloc[0] == ""
    assert "Staff" in brown.loc[brown["era"].eq("2025-2026"), "october_2026_designation"].iloc[0]
    assert "vacant" not in set(overlap["retained_names"].str.cat(sep="; ").split("; "))
    first = overlap.iloc[0]
    assert first["retained"] == 9
    assert first["only_earlier"] == 3
    assert first["only_later"] == 3
    eras = era_table(roster)
    assert assign_era(2011, eras) == "2010-2012"
    assert assign_era(2018, eras) == "2018-2024"
    assert assign_era(2006, eras) == ""
    jumpe = timeline.loc[timeline["person_key"].eq("john jumpe")].iloc[0]
    assert "departure" not in jumpe["roles_on_snapshots"].lower()
    assert "2025-2026" in jumpe["eras"]
    assert jumpe["seat_group_2026"] == "staff_alternate"


def test_model_rankings_fall_inside_the_snapshot_years():
    from msba_dsp.research.panel_history import competition_frame

    root = Path(__file__).resolve().parents[1] / "data" / "processed"
    competitors = pd.read_csv(root / "competitors.csv", dtype=str, keep_default_na=False)
    events = pd.read_csv(root / "selection_events.csv", dtype=str, keep_default_na=False)
    firms = pd.read_csv(root / "firms.csv", dtype=str, keep_default_na=False)
    roster = pd.read_csv(root / "dsp_roster_inferred.csv", dtype=str, keep_default_na=False)
    competitions = competition_frame(competitors, events, firms, roster)
    assert len(competitions) == 273
    assert set(competitions["era"]) == {"2007-2009", "2010-2012", "2013-2017", "2018-2024", "2025-2026"}
    assert int(competitions["winner_prior_wins"].ge(0).all()) == 1
