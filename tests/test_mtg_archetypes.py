import pytest
import subprocess
import json
import os

def test_archetypes_zero_division_bug(tmp_path):
    # Minimal dataset: only one multicolored card.
    # WU (Azorius) will be populated with "UW" identity.
    # Others like "BU" (Dimir) will be empty.
    data = [
        {
            "name": "WU Card",
            "manaCost": "{W}{U}",
            "types": ["Creature"],
            "power": "1",
            "toughness": "1",
            "rarity": "Common"
        }
    ]
    infile = tmp_path / "test_cards.json"
    with open(infile, 'w') as f:
        json.dump(data, f)

    # Run the script with --min-cards 0
    # After the fix, active_pairs will only include WU, preventing ZeroDivisionError.
    result = subprocess.run(
        ['python3', 'scripts/mtg_archetypes.py', str(infile), '--min-cards', '0'],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "ARCHETYPE PROFILING" in result.stdout
    assert "WU (Azorius)" in result.stdout
    assert "UB (Dimir)" not in result.stdout

def test_archetypes_basic_functionality(tmp_path):
    # Minimal dataset with enough cards to profile one archetype correctly
    data = [
        {"name": "W", "manaCost": "{W}", "types": ["Creature"], "power": "1", "toughness": "1", "rarity": "Common"},
        {"name": "U", "manaCost": "{U}", "types": ["Creature"], "power": "1", "toughness": "1", "rarity": "Common"},
        {"name": "WU", "manaCost": "{W}{U}", "types": ["Creature"], "power": "1", "toughness": "1", "rarity": "Uncommon"},
        {"name": "WU2", "manaCost": "{1}{W}{U}", "types": ["Instant"], "rarity": "Common"},
        {"name": "WU3", "manaCost": "{2}{W}{U}", "types": ["Enchantment"], "rarity": "Common"}
    ]
    infile = tmp_path / "functional_cards.json"
    with open(infile, 'w') as f:
        json.dump(data, f)

    result = subprocess.run(
        ['python3', 'scripts/mtg_archetypes.py', str(infile), '--min-cards', '1'],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "ARCHETYPE PROFILING" in result.stdout
    assert "WU (Azorius)" in result.stdout
