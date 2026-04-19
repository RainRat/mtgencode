import subprocess
import json
import csv
import io
import pytest
import os
import sys
from unittest.mock import MagicMock

# Import the script for direct function testing and coverage
import importlib.util
scripts_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../scripts')
spec = importlib.util.spec_from_file_location("mtg_search", os.path.join(scripts_dir, 'mtg_search.py'))
mtg_search = importlib.util.module_from_spec(spec)
sys.modules["mtg_search"] = mtg_search
spec.loader.exec_module(mtg_search)

from lib.cardlib import Card
from unittest.mock import patch

def test_get_field_canonical_name():
    assert mtg_search.get_field_canonical_name("mana") == "cost"
    assert mtg_search.get_field_canonical_name("mv") == "cmc"
    assert mtg_search.get_field_canonical_name("nonexistent") == "nonexistent"

def test_get_field_value():
    card = Card({
        "name": "Test Card",
        "manaCost": "{1}{W}",
        "types": ["Creature"],
        "rarity": "Common",
        "power": "1",
        "toughness": "1",
        "text": "Hello world."
    })
    assert mtg_search.get_field_value(card, "name") == "Test Card"
    assert mtg_search.get_field_value(card, "cost") == "{1}{W}"
    assert mtg_search.get_field_value(card, "cmc") == "2"
    assert mtg_search.get_field_value(card, "rarity") == "common"
    assert mtg_search.get_field_value(card, "power") == "1"
    assert mtg_search.get_field_value(card, "toughness") == "1"
    assert mtg_search.get_field_value(card, "text") == "Hello world."

def test_get_field_value_comprehensive():
    """Test get_field_value for many fields to increase coverage."""
    card = Card({
        "name": "Comprehensive Card",
        "manaCost": "{2}{U}{R}",
        "supertypes": ["Legendary"],
        "types": ["Creature"],
        "subtypes": ["Dragon"],
        "rarity": "Mythic",
        "power": "4",
        "toughness": "4",
        "text": "Flying\n{T}: Add {C}.",
        "colorIdentity": ["U", "R"],
        "setCode": "TEST",
        "number": "123"
    })

    assert mtg_search.get_field_value(card, "name") == "Comprehensive Card"
    assert mtg_search.get_field_value(card, "cost") == "{2}{U}{R}"
    assert mtg_search.get_field_value(card, "cmc") == "4"
    assert set(mtg_search.get_field_value(card, "colors")) == set("UR")
    assert mtg_search.get_field_value(card, "supertypes") == "Legendary"
    assert mtg_search.get_field_value(card, "types") == "Creature"
    assert mtg_search.get_field_value(card, "subtypes") == "Dragon"
    assert mtg_search.get_field_value(card, "type") == "Legendary Creature - Dragon"
    assert mtg_search.get_field_value(card, "pt") == "4/4"
    assert mtg_search.get_field_value(card, "stats") == "4/4"
    assert mtg_search.get_field_value(card, "power") == "4"
    assert mtg_search.get_field_value(card, "toughness") == "4"
    assert "Flying" in mtg_search.get_field_value(card, "text")
    assert mtg_search.get_field_value(card, "rarity") == "mythic"
    assert "Flying" in mtg_search.get_field_value(card, "mechanics")
    assert set(mtg_search.get_field_value(card, "identity")) == set("UR")
    assert mtg_search.get_field_value(card, "id_count") == "2"
    assert mtg_search.get_field_value(card, "set") == "TEST"
    assert mtg_search.get_field_value(card, "number") == "123"
    assert mtg_search.get_field_value(card, "encoded") != ""
    assert mtg_search.get_field_value(card, "summary") != ""

def test_get_field_value_planeswalker():
    card = Card({
        "name": "Jace",
        "types": ["Planeswalker"],
        "rarity": "Rare",
        "loyalty": "3"
    })
    assert mtg_search.get_field_value(card, "loyalty") == "3"
    assert mtg_search.get_field_value(card, "stats") == "3"

def test_mtg_search_main_basic():
    """Test main() function directly for coverage."""
    with patch('sys.argv', ['mtg_search.py', 'testdata/uthros.json', '--quiet', '--no-color']):
        mtg_search.main()

def test_mtg_search_main_json():
    """Test main() with JSON output."""
    with patch('sys.argv', ['mtg_search.py', 'testdata/uthros.json', '--json', '--quiet']):
        # We need to capture stdout to avoid cluttering test output and to verify
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            mtg_search.main()
            data = json.loads(fake_out.getvalue())
            assert data[0]["name"] == "Uthros Research Craft"

def test_mtg_search_main_table():
    """Test main() with Table output."""
    with patch('sys.argv', ['mtg_search.py', 'testdata/uthros.json', '--table', '--quiet', '--no-color']):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            mtg_search.main()
            assert "SEARCH RESULTS" in fake_out.getvalue()

def test_mtg_search_main_csv():
    """Test main() with CSV output."""
    with patch('sys.argv', ['mtg_search.py', 'testdata/uthros.json', '--csv', '--quiet']):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            mtg_search.main()
            assert "Name,Cost,CMC" in fake_out.getvalue()

def test_mtg_search_main_jsonl():
    """Test main() with JSONL output."""
    with patch('sys.argv', ['mtg_search.py', 'testdata/uthros.json', '--jsonl', '--quiet']):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            mtg_search.main()
            data = json.loads(fake_out.getvalue())
            assert data["name"] == "Uthros Research Craft"

def test_mtg_search_main_md_table():
    """Test main() with Markdown table output."""
    with patch('sys.argv', ['mtg_search.py', 'testdata/uthros.json', '--md-table', '--quiet']):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            mtg_search.main()
            output = fake_out.getvalue()
            assert "| Name | Cost |" in output
            assert "| :--- | :--- |" in output

def test_mtg_search_main_summary():
    """Test main() with summary output."""
    with patch('sys.argv', ['mtg_search.py', 'testdata/uthros.json', '--summary', '--quiet', '--no-color']):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            mtg_search.main()
            assert "Uthros Research Craft" in fake_out.getvalue()

def test_mtg_search_main_text_delimiter():
    """Test main() with plain text output and custom delimiter."""
    with patch('sys.argv', ['mtg_search.py', 'testdata/uthros.json', '--text', '--delimiter', ' ### ', '--quiet', '--no-color']):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            mtg_search.main()
            assert "Uthros Research Craft ### {2}{U}" in fake_out.getvalue()

def test_mtg_search_main_fuzzy_word():
    """Test fuzzy matching suggesting from significant words."""
    # Search for "Research" which is a word in the name
    with patch('sys.argv', ['mtg_search.py', 'testdata/uthros.json', '--grep', 'Reserch', '--no-color']):
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            mtg_search.main()
            assert "Did you mean:" in fake_err.getvalue()
            assert "- Uthros Research Craft" in fake_err.getvalue()

def test_get_field_value_color():
    """Test ANSI colorization in get_field_value."""
    card = Card({
        "name": "Red Card",
        "manaCost": "{R}",
        "rarity": "Rare"
    })
    # name color
    val = mtg_search.get_field_value(card, "name", ansi_color=True)
    assert "\033[" in val
    # rarity color
    val = mtg_search.get_field_value(card, "rarity", ansi_color=True)
    assert "\033[" in val
    # colors color
    val = mtg_search.get_field_value(card, "colors", ansi_color=True)
    assert "\033[" in val

def test_mtg_search_main_simulation():
    """Test simulation flags and automatic field inclusion."""
    with patch('sys.argv', ['mtg_search.py', 'testdata/uthros.json', '--booster', '1', '--json', '--quiet']):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            mtg_search.main()
            data = json.loads(fake_out.getvalue())
            # booster adds 'pack' field
            assert "pack" in data[0]

def test_mtg_search_main_sort():
    """Test sorting in main."""
    with patch('sys.argv', ['mtg_search.py', 'testdata/uthros.json', '--sort', 'name', '--quiet', '--no-color']):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            mtg_search.main()
            assert "Uthros Research Craft" in fake_out.getvalue()

def test_mtg_search_main_invalid_field():
    """Test warning for invalid fields."""
    with patch('sys.argv', ['mtg_search.py', 'testdata/uthros.json', '--fields', 'name,invalidfield']):
        with patch('sys.stderr', new=io.StringIO()) as fake_err:
            with patch('sys.stdout', new=io.StringIO()):
                mtg_search.main()
                assert "Warning: Unrecognized fields: invalidfield" in fake_err.getvalue()

def test_mtg_search_basic():
    """Test basic search functionality."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Uthros Research Craft" in result.stdout
    assert "{2}{U}" in result.stdout

def test_mtg_search_table():
    """Test table output format."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--table", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "SEARCH RESULTS (1 match)" in result.stdout
    assert "Name" in result.stdout
    assert "Uthros Research Craft" in result.stdout

def test_mtg_search_json():
    """Test JSON output format."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert data[0]["name"] == "Uthros Research Craft"

def test_mtg_search_jsonl():
    """Test JSONL output format."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--jsonl"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["name"] == "Uthros Research Craft"

def test_mtg_search_csv():
    """Test CSV output format."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--csv"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    reader = csv.DictReader(io.StringIO(result.stdout))
    rows = list(reader)
    assert rows[0]["Name"] == "Uthros Research Craft"

def test_mtg_search_md_table():
    """Test Markdown table output format."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--md-table"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "| Name |" in result.stdout
    assert "| ---" in result.stdout
    assert "| Uthros Research Craft |" in result.stdout

def test_mtg_search_summary():
    """Test summary output format."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--summary", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    # Card.summary() output
    assert "Uthros Research Craft" in result.stdout
    assert "{2}{U}" in result.stdout

def test_mtg_search_aliases():
    """Test field aliases."""
    # mana -> cost, mv -> cmc, oracle -> text, ci -> identity, num -> number
    fields = "name,mana,mv,oracle,ci,num"
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--fields", fields, "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    # The output JSON uses the literal field name from --fields
    assert data[0]["mana"] == "{2}{U}"
    assert data[0]["mv"] == "3"
    assert "Whenever you cast an artifact spell, draw a card" in data[0]["oracle"]
    assert data[0]["ci"] == "U"

def test_mtg_search_multi_face():
    """Test recursive field joining for multi-faced cards."""
    # Invasion of Tarkir // Defiant Thundermaw
    # Note: search tool might have its own casing rules or preserved original casing
    cmd = ["python3", "scripts/mtg_search.py", "testdata/invasion_of_tarkir.json", "--fields", "name,type,cost", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    # Invasion of Tarkir has name preserved, but it might be titlecased by the tool
    assert "Invasion of Tarkir // Defiant Thundermaw" in result.stdout
    # Type line: "Battle - Siege" is what the tool produces from get_type_line
    assert "Battle - Siege" in result.stdout
    assert "{1}{R}" in result.stdout

def test_mtg_search_fuzzy():
    """Test fuzzy matching suggestions for zero-match results."""
    # Search for "Uthrss" should suggest "Uthros Research Craft"
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--grep", "Uthrss", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "No cards found matching the criteria." in result.stderr
    assert "Did you mean:" in result.stderr
    assert "- Uthros Research Craft" in result.stderr

def test_mtg_search_filters():
    """Test advanced filtering flags."""
    # Filter by rarity
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--rarity", "rare", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "Uthros Research Craft" in result.stdout

    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--rarity", "common", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "No cards found matching the criteria." in result.stderr

    # Filter by CMC
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--cmc", "3", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "Uthros Research Craft" in result.stdout

    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--cmc", ">4", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "No cards found matching the criteria." in result.stderr

    # Filter by Power
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--pow", "0", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "Uthros Research Craft" in result.stdout

    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--pow", ">=1", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "No cards found matching the criteria." in result.stderr
