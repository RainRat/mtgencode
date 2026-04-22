import subprocess
import json
import csv
import io
import os
import pytest

def test_functional_basic(tmp_path):
    """Test basic functional reprint detection."""
    d = tmp_path / "subdir"
    d.mkdir()
    test_file = d / "test_functional.json"

    with open(test_file, "w") as f:
        json.dump([
            {
                "name": "Card A",
                "manaCost": "{1}{W}",
                "types": ["Creature"],
                "subtypes": ["Human"],
                "power": "2",
                "toughness": "2",
                "text": "First strike",
                "rarity": "Common"
            },
            {
                "name": "Card B",
                "manaCost": "{1}{W}",
                "types": ["Creature"],
                "subtypes": ["Human"],
                "power": "2",
                "toughness": "2",
                "text": "First strike",
                "rarity": "Common"
            }
        ], f)

    cmd = ["python3", "scripts/mtg_functional.py", str(test_file), "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "FUNCTIONAL REPRINT GROUPS (1 match)" in result.stdout
    assert "Card A, Card B" in result.stdout
    # Standardized summary in stderr
    assert "Functional check complete" in result.stderr

def test_functional_no_match(tmp_path):
    """Test output when no functional reprints are found."""
    test_file = tmp_path / "test_no_functional.json"
    with open(test_file, "w") as f:
        json.dump([
            {
                "name": "Card A",
                "manaCost": "{1}{W}",
                "types": ["Creature"],
                "subtypes": ["Human"],
                "power": "2",
                "toughness": "2",
                "text": "First strike",
                "rarity": "Common"
            },
            {
                "name": "Card C",
                "manaCost": "{U}",
                "types": ["Instant"],
                "text": "Draw a card.",
                "rarity": "Common"
            }
        ], f)

    cmd = ["python3", "scripts/mtg_functional.py", str(test_file), "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "No functional reprints found." in result.stderr

def test_functional_json_output(tmp_path):
    """Test JSON output format."""
    test_file = tmp_path / "test_functional_json.json"
    with open(test_file, "w") as f:
        json.dump([
            {"name": "A", "manaCost": "{W}", "types": ["Creature"], "power": "1", "toughness": "1"},
            {"name": "B", "manaCost": "{W}", "types": ["Creature"], "power": "1", "toughness": "1"}
        ], f)

    cmd = ["python3", "scripts/mtg_functional.py", str(test_file), "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert "A" in data[0]['names']
    assert "B" in data[0]['names']
