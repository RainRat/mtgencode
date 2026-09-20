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
    """Test comparison of multiple card faces with cleaner primary face headers."""
    # Compare front and back of the same card
    cmd = ["python3", SCRIPT_PATH, "compare", "Double Front", "Double Back", "testdata/manual.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Double Front" in result.stdout
    assert "Double Back" in result.stdout
    # Check that they are identified as different in the table
    # Since Double Front matches the whole card (both faces) and Double Back matches only one face
    assert "(1/1) // (2/2)" in result.stdout
    assert "(2/2)" in result.stdout

def test_query_compare_multiple_names_without_file():
    """Test comparing 3+ card names when no file positional argument is passed."""
    # When passing 3 names and a directory or file, all 3 names should be recognized as card names
    cmd = ["python3", SCRIPT_PATH, "compare", "Double Front", "Double Back", "Invasion of Tarkir", "testdata/", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "CARD COMPARISON" in result.stdout
    assert "Double Front" in result.stdout
    assert "Double Back" in result.stdout
    assert "Invasion of Tarkir" in result.stdout

def test_query_compare_diff_only():
    """Test --diff-only flag in card comparison."""
    # Uthros and Invasion of Alara both have rarity "rare"
    cmd = ["python3", SCRIPT_PATH, "compare", "Uthros", "Invasion of Alara", "testdata/", "--no-color", "--diff-only"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "CARD COMPARISON" in result.stdout
    assert "Cost" in result.stdout
    assert "CMC" in result.stdout
    # Rarity is identical ("rare" for both) and should be hidden
    assert "Rarity" not in result.stdout

def test_query_compare_diff_only_short_flag():
    """Test -d short flag in card comparison."""
    cmd = ["python3", SCRIPT_PATH, "compare", "Double Front", "Double Back", "testdata/manual.json", "--no-color", "-d"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "CARD COMPARISON" in result.stdout
    # Rarity differs ("common" vs "uncommon"), so it should be included
    assert "Rarity" in result.stdout
    # Color Pie is "Valid" for both, so it should be omitted
    assert "Color Pie" not in result.stdout

def test_query_compare_multiple_file_paths():
    """Test comparing cards when multiple file paths are passed among positional arguments."""
    cmd = ["python3", SCRIPT_PATH, "compare", "Invasion of Tarkir", "Uthros", "testdata/tarkir.json", "testdata/uthros.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "CARD COMPARISON" in result.stdout
    assert "Invasion of Tarkir" in result.stdout
    assert "Uthros Research Craft" in result.stdout
    assert "Could not find card 'testdata/tarkir.json'" not in result.stderr

def test_query_compare_diff_only_no_differences():
    """Test --diff-only flag when comparing identical cards."""
    cmd = ["python3", SCRIPT_PATH, "compare", "Invasion of Tarkir", "Invasion of Tarkir", "testdata/invasion_of_tarkir.json", "--no-color", "-d"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "CARD COMPARISON" in result.stdout
    assert "No differences found between the compared cards." in result.stdout

def test_query_compare_single_card_notice():
    """Test notice output when only a single card is provided for comparison."""
    cmd = ["python3", SCRIPT_PATH, "compare", "Invasion of Tarkir", "testdata/tarkir.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Notice: Only one card provided. Comparing Invasion of Tarkir with most mechanically similar match: Defiant Thundermaw" in result.stderr
