from msba_dsp.processing.build import clean_project_label, school_category, split_project_label
from msba_dsp.processing.names import resolve_firm


def test_scheduling_sentence_does_not_become_the_school_name():
    label = (
        "Finalist interviews will be conducted at the June 21, 2016 meeting. "
        "Attleboro High School, Attleboro, MA"
    )
    district, school = split_project_label(label)
    assert school == "Attleboro High School"
    assert district == "Attleboro"
    assert school_category(school) == "high"
    assert "interview" not in clean_project_label(label).lower()


def test_legal_suffix_and_punctuation_collapse():
    left = resolve_firm("HMFH Architects, Inc.")
    right = resolve_firm("HMFH Architects")
    assert left.firm_id == right.firm_id
    assert left.joint_venture is False


def test_reviewed_alias_smma_and_dore():
    smma = resolve_firm("SMMA")
    long_name = resolve_firm("Symmes Maini & McKee Associates, Inc.")
    assert smma.firm_id == long_name.firm_id
    dore = resolve_firm("Dore + Whittier")
    dore_long = resolve_firm("Dore & Whittier Architects, Inc.")
    assert dore.firm_id == dore_long.firm_id


def test_similar_names_stay_apart():
    perkins_will = resolve_firm("Perkins & Will, Inc.")
    perkins_eastman = resolve_firm("Perkins Eastman")
    partnership = resolve_firm("Design Partnership of Cambridge, Inc.")
    assert len({perkins_will.firm_id, perkins_eastman.firm_id, partnership.firm_id}) == 3


def test_joint_venture_is_not_the_parent():
    parent = resolve_firm("Mount Vernon Group Architects, Inc.")
    joint = resolve_firm("Mount Vernon Group Architects in association with Moody Nolan")
    assert joint.joint_venture is True
    assert joint.firm_id != parent.firm_id


def test_tie_notation_is_flagged():
    resolved = resolve_firm("Tie: Perkins Eastman | Design Partnership of Cambridge, Inc. AND Tappe Associates, Inc.")
    assert resolved.tie_record is True
