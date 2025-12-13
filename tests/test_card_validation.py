from lib.cardlib import fields_check_valid, field_name, field_types, field_subtypes, field_pt, field_text, field_loyalty

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
