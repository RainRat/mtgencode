import pytest
from lib import utils

def test_split_types_basic():
    supertypes, types = utils.split_types("Legendary Creature")
    assert supertypes == ["Legendary"]
    assert types == ["Creature"]

def test_split_types_lowercase():
    supertypes, types = utils.split_types("legendary creature")
    assert supertypes == ["legendary"]
    assert types == ["creature"]

def test_split_types_multiple_supertypes():
    supertypes, types = utils.split_types("Legendary Snow Creature")
    assert supertypes == ["Legendary", "Snow"]
    assert types == ["Creature"]

def test_split_types_no_supertypes():
    supertypes, types = utils.split_types("Artifact Creature")
    assert supertypes == []
    assert types == ["Artifact", "Creature"]

def test_split_types_empty():
    supertypes, types = utils.split_types("")
    assert supertypes == []
    assert types == []

def test_parse_type_line_standard():
    s, t, sub = utils.parse_type_line("Creature \u2014 Goblin")
    assert s == []
    assert t == ["Creature"]
    assert sub == ["Goblin"]

def test_parse_type_line_multiple_supertypes():
    s, t, sub = utils.parse_type_line("Legendary Snow Creature \u2014 Spirit")
    assert s == ["Legendary", "Snow"]
    assert t == ["Creature"]
    assert sub == ["Spirit"]

def test_parse_type_line_en_dash():
    s, t, sub = utils.parse_type_line("Creature \u2013 Elf Warrior")
    assert s == []
    assert t == ["Creature"]
    assert sub == ["Elf", "Warrior"]

def test_parse_type_line_hyphen():
    s, t, sub = utils.parse_type_line("Artifact - Equipment")
    assert s == []
    assert t == ["Artifact"]
    assert sub == ["Equipment"]

def test_parse_type_line_no_subtypes():
    s, t, sub = utils.parse_type_line("Instant")
    assert s == []
    assert t == ["Instant"]
    assert sub == []

def test_parse_type_line_legendary_no_subtypes():
    s, t, sub = utils.parse_type_line("Legendary Artifact")
    assert s == ["Legendary"]
    assert t == ["Artifact"]
    assert sub == []

def test_parse_type_line_empty():
    s, t, sub = utils.parse_type_line("")
    assert s == []
    assert t == []
    assert sub == []

def test_parse_type_line_none():
    s, t, sub = utils.parse_type_line(None)
    assert s == []
    assert t == []
    assert sub == []

def test_parse_type_line_multiple_dashes():
    s, t, sub = utils.parse_type_line("Creature \u2014 Goblin \u2014 Warrior")
    assert s == []
    assert t == ["Creature"]
    assert sub == ["Goblin", "Warrior"]

def test_parse_type_line_malformed_dash():
    s, t, sub = utils.parse_type_line("Creature\u2014Goblin")
    assert s == []
    assert t == ["Creature\u2014Goblin"]
    assert sub == []
