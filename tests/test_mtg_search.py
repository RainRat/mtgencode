import pytest
import sys
import os
import json
import io
import tempfile
from unittest.mock import patch
from scripts import mtg_search

def run_mtg_search(args, input_data=None):
    """Helper to run mtg_search.main with mocked argv and capture stdout/stderr."""
    # Add dummy first arg for script name
    test_args = ["mtg_search.py"] + args

    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = 0
    with patch.object(sys, 'argv', test_args):
        with patch.object(sys, 'stdout', stdout):
            with patch.object(sys, 'stderr', stderr):
                # Mock isatty to false for predictable output unless we want to test color
                with patch.object(sys.stdout, 'isatty', return_value=False):
                    try:
                        mtg_search.main()
                    except SystemExit as e:
                        exit_code = e.code if e.code is not None else 0

    return stdout.getvalue(), stderr.getvalue(), exit_code

def test_mtg_search_basic():
    """Test basic search functionality."""
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--no-color"])
    assert code == 0
    assert "Uthros Research Craft" in stdout
    assert " 3 " in stdout # CMC is 3 (with spaces in table/delimited)

def test_mtg_search_filtering():
    """Test various filtering flags."""
    # Filter by name
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--grep-name", "Uthros", "--no-color"])
    assert "Uthros" in stdout

    # Filter by CMC
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--cmc", "3", "--no-color"])
    assert "Uthros" in stdout

    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--cmc", ">5", "--no-color"])
    assert "Uthros" not in stdout

def test_mtg_search_json_output():
    """Test JSON output format."""
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--json"])
    assert code == 0
    data = json.loads(stdout)
    assert isinstance(data, list)
    assert data[0]["name"] == "Uthros Research Craft"

def test_mtg_search_csv_output():
    """Test CSV output format."""
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--csv"])
    assert code == 0
    assert "Name,Cost,CMC,Type,Stats,Rarity,Mechanics" in stdout
    assert "Uthros Research Craft" in stdout

def test_mtg_search_md_table_output():
    """Test Markdown table output format."""
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--md-table"])
    assert code == 0
    assert "| Name | Cost | CMC | Type | Stats | Rarity | Mechanics |" in stdout
    assert "| :--- | :--- | ---: | :--- | ---: | :--- | :--- |" in stdout
    assert "Uthros Research Craft" in stdout

def test_mtg_search_summary_output():
    """Test summary output format."""
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--summary"])
    assert code == 0
    assert "Uthros Research Craft" in stdout
    assert "{2}{U}" in stdout

def test_mtg_search_fields():
    """Test custom field selection."""
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--fields", "name,rarity", "--json"])
    assert code == 0
    data = json.loads(stdout)
    assert "name" in data[0]
    assert "rarity" in data[0]
    assert "cmc" not in data[0]

def test_mtg_search_aliases():
    """Test field aliases."""
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--fields", "mana,mv,oracle", "--json"])
    assert code == 0
    data = json.loads(stdout)
    assert "mana" in data[0] # Alias for cost
    assert "mv" in data[0]   # Alias for cmc
    assert "oracle" in data[0] # Alias for text

def test_mtg_search_fuzzy_matching():
    """Test fuzzy matching suggestions for zero results."""
    # We need a file to trigger fuzzy matching
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--grep-name", "UthrosX"])
    assert "No cards found matching the criteria." in stderr
    assert "Did you mean:" in stderr
    assert "Uthros Research Craft" in stderr

def test_mtg_search_multi_face():
    """Test multi-faced card search and display."""
    stdout, stderr, code = run_mtg_search(["testdata/invasion_of_tarkir.json", "--fields", "name,type,text", "--no-color"])
    assert code == 0
    assert "Invasion of Tarkir" in stdout
    assert "Defiant Thundermaw" in stdout
    assert "Battle - Siege" in stdout

def test_mtg_search_invalid_field_warning():
    """Test warning for unrecognized fields."""
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--fields", "nonexistent_field"])
    assert "Warning: Unrecognized fields: nonexistent_field" in stderr

def test_mtg_search_sorting():
    """Test sorting cards."""
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--sort", "name", "--no-color"])
    assert code == 0
    assert "Uthros Research Craft" in stdout

def test_mtg_search_limit():
    """Test limit flag."""
    # Create a temp file with two cards
    cards = [
        {"name": "Card A", "types": ["Instant"], "rarity": "Common"},
        {"name": "Card B", "types": ["Sorcery"], "rarity": "Common"}
    ]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(cards, f)
        temp_path = f.name

    try:
        stdout, stderr, code = run_mtg_search([temp_path, "--limit", "1", "--no-color"])
        assert code == 0
        assert "Card A" in stdout
        assert "Card B" not in stdout
    finally:
        os.remove(temp_path)

def test_mtg_search_sample():
    """Test sample flag."""
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--sample", "1", "--no-color"])
    assert code == 0
    assert "Uthros Research Craft" in stdout

def test_mtg_search_jsonl_output():
    """Test JSONL output format."""
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--jsonl"])
    assert code == 0
    # JSONL parsing: one JSON object per line
    lines = [line for line in stdout.splitlines() if line.strip()]
    data = json.loads(lines[0])
    assert data["name"] == "Uthros Research Craft"

def test_mtg_search_table_output_empty():
    """Test table output with zero matches."""
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--grep", "nomatch", "--table"])
    assert "SEARCH RESULTS" not in stdout
    assert "No cards found matching the criteria." in stderr

def test_mtg_search_extra_fields():
    """Test more fields for coverage."""
    fields = "colors,supertypes,types,subtypes,power,toughness,loyalty,identity,id_count,set,number,encoded"
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--fields", fields, "--json"])
    assert code == 0
    data = json.loads(stdout)
    card = data[0]
    assert card["colors"] == "U"
    assert card["types"] == "Artifact"
    assert card["subtypes"] == "Spacecraft"
    assert card["power"] == "0"
    assert card["toughness"] == "8"
    assert card["identity"] == "U"
    assert card["id_count"] == "1"
    assert card["set"] == "EOC"
    assert card["number"] == "7"
    assert "encoded" in card

def test_mtg_search_stats_field():
    """Test the smart 'stats' field."""
    # Power/Toughness
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--fields", "stats", "--json"])
    assert code == 0
    data = json.loads(stdout)
    assert data[0]["stats"] == "0/8"

    # Loyalty
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump([{"name": "Jace", "types": ["Planeswalker"], "rarity": "Rare", "loyalty": "3"}], f)
        temp_path = f.name
    try:
        stdout, stderr, code = run_mtg_search([temp_path, "--fields", "stats", "--json"])
        assert code == 0
        data = json.loads(stdout)
        assert data[0]["stats"] == "3"
    finally:
        os.remove(temp_path)

def test_mtg_search_auto_format():
    """Test automatic format detection from extension."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        pass
    try:
        # Should detect CSV from .csv extension
        stdout, stderr, code = run_mtg_search(["testdata/uthros.json", f.name])
        assert code == 0
        with open(f.name, 'r') as csv_f:
            content = csv_f.read()
            assert "Name,Cost,CMC,Type,Stats,Rarity,Mechanics" in content
    finally:
        os.remove(f.name)

def test_mtg_search_markdown_escaping():
    """Test markdown escaping for pipes and newlines."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump([{"name": "Piped | Card", "types": ["Instant"], "rarity": "Common", "text": "Line 1\nLine 2"}], f)
        temp_path = f.name
    try:
        stdout, stderr, code = run_mtg_search([temp_path, "--md-table", "--fields", "name,text"])
        assert code == 0
        assert "Piped \\| Card" in stdout
        assert "Line 1 Line 2" in stdout
    finally:
        os.remove(temp_path)

def test_mtg_search_simulation_fields():
    """Test auto-inclusion of simulation fields."""
    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--booster", "1", "--json"])
    assert code == 0
    data = json.loads(stdout)
    assert "pack" in data[0]

    stdout, stderr, code = run_mtg_search(["testdata/uthros.json", "--box", "1", "--json"])
    assert code == 0
    data = json.loads(stdout)
    assert "box" in data[0]
    assert "pack" in data[0]
