from lib.utils import parse_type_line

def test_parse_type_line_empty():
    assert parse_type_line(None) == ([], [], [])
    assert parse_type_line("") == ([], [], [])

def test_parse_type_line_no_subtypes():
    assert parse_type_line("Creature") == ([], ["Creature"], [])
    assert parse_type_line("Legendary Artifact") == (["Legendary"], ["Artifact"], [])

def test_parse_type_line_em_dash():
    # Standard em-dash separator (\u2014)
    assert parse_type_line("Creature \u2014 Elf Archer") == ([], ["Creature"], ["Elf", "Archer"])

def test_parse_type_line_en_dash():
    # En-dash separator (\u2013)
    assert parse_type_line("Creature \u2013 Elf Archer") == ([], ["Creature"], ["Elf", "Archer"])

def test_parse_type_line_hyphen():
    # Hyphen separator (-)
    assert parse_type_line("Creature - Elf Archer") == ([], ["Creature"], ["Elf", "Archer"])

def test_parse_type_line_multiple_subtypes():
    assert parse_type_line("Artifact Creature \u2014 Construct") == ([], ["Artifact", "Creature"], ["Construct"])

def test_parse_type_line_complex_supertypes():
    assert parse_type_line("Legendary Snow Enchantment Creature \u2014 Shrine Spirit") == (
        ["Legendary", "Snow"], ["Enchantment", "Creature"], ["Shrine", "Spirit"]
    )

def test_parse_type_line_multiple_dash_parts():
    # The current implementation handles multiple dashes by extending subtypes
    assert parse_type_line("Type - Sub1 - Sub2") == ([], ["Type"], ["Sub1", "Sub2"])
