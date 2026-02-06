from lib.cardlib import fields_check_valid, field_name, field_types, field_subtypes, field_pt, field_text, field_loyalty

class MockText:
    def __init__(self, text):
        self.text = text

def test_fields_check_valid_creature():
    fields = {
        field_name: [(-1, "ornithopter")],
        field_types: [(-1, ["artifact", "creature"])],
        field_pt: [(-1, "0/2")]
    }
    assert fields_check_valid(fields)

def test_fields_check_valid_creature_missing_pt():
    fields = {
        field_name: [(-1, "bad creature")],
        field_types: [(-1, ["creature"])],
    }
    assert not fields_check_valid(fields)

def test_fields_check_valid_vehicle():
    fields = {
        field_name: [(-1, "smuggler's copter")],
        field_types: [(-1, ["artifact"])],
        field_subtypes: [(-1, ["vehicle"])],
        field_pt: [(-1, "3/3")]
    }
    assert fields_check_valid(fields)

def test_fields_check_valid_vehicle_no_pt():
    fields = {
        field_name: [(-1, "bad vehicle")],
        field_types: [(-1, ["artifact"])],
        field_subtypes: [(-1, ["vehicle"])],
    }
    # Vehicles are considered creatures by the logic, so they need PT
    assert not fields_check_valid(fields)

def test_fields_check_valid_non_creature():
    fields = {
        field_name: [(-1, "counterspell")],
        field_types: [(-1, ["instant"])],
    }
    # Non-creature without PT should be valid
    assert fields_check_valid(fields)

def test_fields_check_valid_non_creature_with_pt():
    fields = {
        field_name: [(-1, "weird spell")],
        field_types: [(-1, ["instant"])],
        field_pt: [(-1, "1/1")]
    }
    # Non-creature with PT should be invalid
    assert not fields_check_valid(fields)

def test_fields_check_valid_multiple_type_entries():
    # This simulates the condition where the nested loop behavior matters
    fields = {
        field_name: [(-1, "weird vehicle")],
        field_types: [(-1, ["artifact"]), (-1, ["enchantment"])], # Two entries for types
        field_subtypes: [(-1, ["vehicle"])],
        field_pt: [(-1, "3/3")]
    }
    # Artifact + Vehicle -> iscreature=True. Needs PT. Has PT. Valid.
    assert fields_check_valid(fields)

def test_fields_check_valid_station_artifact():
    # Station artifact logic: isartifact + 'station' in text -> valid even without PT
    fields = {
        field_name: [(-1, "summoning station")],
        field_types: [(-1, ["artifact"])],
        field_text: [(-1, MockText("tap: create a 2/2 colorless pincher creature token. station"))],
    }
    assert fields_check_valid(fields)

def test_fields_check_valid_station_artifact_no_keyword():
    fields = {
        field_name: [(-1, "sol ring")],
        field_types: [(-1, ["artifact"])],
        field_text: [(-1, MockText("add {c}{c}."))],
    }
    assert fields_check_valid(fields)

def test_fields_check_valid_planeswalker():
    fields = {
        field_name: [(-1, "jace")],
        field_types: [(-1, ["planeswalker", "jace"])],
        field_loyalty: [(-1, "4")]
    }
    assert fields_check_valid(fields)

def test_fields_check_valid_battle():
    fields = {
        field_name: [(-1, "invasion of zendikar")],
        field_types: [(-1, ["battle", "siege"])],
        field_loyalty: [(-1, "3")]
    }
    assert fields_check_valid(fields)

def test_fields_check_valid_battle_missing_loyalty():
    fields = {
        field_name: [(-1, "bad battle")],
        field_types: [(-1, ["battle"])],
    }
    assert not fields_check_valid(fields)

def test_fields_check_valid_missing_name():
    fields = {
        field_types: [(-1, ["creature"])],
        field_pt: [(-1, "1/1")]
    }
    assert not fields_check_valid(fields)

def test_fields_check_valid_missing_types():
    fields = {
        field_name: [(-1, "mystery card")],
        field_pt: [(-1, "1/1")]
    }
    assert not fields_check_valid(fields)

def test_fields_check_valid_planeswalker_brittle_check():
    # Investigating the potential bug where types are split across entries
    # and "planeswalker" is not in the first one.
    fields = {
        field_name: [(-1, "weird walker")],
        field_types: [(-1, ["legendary"]), (-1, ["planeswalker"])],
        field_loyalty: [(-1, "5")]
    }
    assert fields_check_valid(fields)

def test_fields_check_valid_battle_brittle_check_no_loyalty():
    # If a battle is defined in second type entry and missing loyalty
    fields = {
        field_name: [(-1, "weird battle")],
        field_types: [(-1, ["siege"]), (-1, ["battle"])],
        # No loyalty
    }
    # Should be invalid because battles need loyalty
    assert not fields_check_valid(fields)

def test_fields_check_valid_planeswalker_missing_loyalty():
    fields = {
        field_name: [(-1, "jace")],
        field_types: [(-1, ["planeswalker"])],
        # No loyalty
    }
    # Should be invalid because planeswalkers need loyalty
    assert not fields_check_valid(fields)

def test_fields_check_valid_battle_creature_missing_loyalty():
    fields = {
        field_name: [(-1, "battle creature")],
        field_types: [(-1, ["battle", "creature"])],
        field_pt: [(-1, "1/1")],
        # No loyalty
    }
    # Should be invalid because battles need loyalty even if they are creatures
    assert not fields_check_valid(fields)

def test_fields_check_valid_instant_with_loyalty():
    fields = {
        field_name: [(-1, "instant with loyalty")],
        field_types: [(-1, ["instant"])],
        field_loyalty: [(-1, "3")]
    }
    # Should be invalid because instants don't have loyalty
    assert not fields_check_valid(fields)
