import subprocess
import json
import os

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "../scripts/mtg_query.py")

def test_query_compare_basic():
    """Test basic card comparison."""
    cmd = ["python3", SCRIPT_PATH, "compare", "Uthros", "Invasion of Alara", "testdata/", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "CARD COMPARISON" in result.stdout
    assert "Uthros Research Craft" in result.stdout
    assert "Invasion of Alara" in result.stdout
    assert "CMC" in result.stdout

def test_query_compare_json():
    """Test JSON output for comparison."""
    cmd = ["python3", SCRIPT_PATH, "compare", "Uthros", "Invasion", "testdata/", "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "card1" in data
    assert "card2" in data
    assert data["card1"]["name"] == "Uthros Research Craft"
    assert data["card2"]["name"] == "Invasion of Alara"

def test_query_compare_fuzzy():
    """Test fuzzy matching in comparison."""
    # "Uthros Research" is a fuzzy match for "Uthros Research Craft"
    cmd = ["python3", SCRIPT_PATH, "compare", "Uthros Research", "Alara", "testdata/", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Uthros Research Craft" in result.stdout
    assert "Invasion of Alara" in result.stdout

def test_query_compare_multi_face():
    """Test comparison of multiple card faces."""
    # Compare front and back of the same card
    cmd = ["python3", SCRIPT_PATH, "compare", "Double Front", "Double Back", "testdata/manual.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Double Front // Double Back" in result.stdout
    assert "Double Back" in result.stdout
    # Check that they are identified as different in the table
    # Since Double Front matches the whole card (both faces) and Double Back matches only one face
    assert "(1/1) // (2/2)" in result.stdout
    assert "(2/2)" in result.stdout
