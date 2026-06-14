import subprocess
import json
import csv
import io
import os

# Find the script path relative to this test file
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "../scripts/mtg_query.py")

def test_query_search_basic():
    """Test basic searching with grep."""
    cmd = ["python3", SCRIPT_PATH, "search", "testdata/uthros.json", "--grep", "Uthros", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Uthros Research Craft" in result.stdout
    # Test for em dash or hyphen
    assert "Artifact" in result.stdout
    assert "Spacecraft" in result.stdout

def test_query_oracle_basic():
    """Test basic oracle lookup."""
    cmd = ["python3", SCRIPT_PATH, "oracle", "Uthros", "testdata/uthros.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Uthros Research Craft" in result.stdout
    # The output uses em dash \u2014, but we normalized it to hyphen in oracle output for tests
    assert "Artifact - Spacecraft" in result.stdout
    assert "Flying" in result.stdout

def test_query_sets_basic():
    """Test basic sets listing."""
    # Use tarkir.json which has a standard MTGJSON data structure
    cmd = ["python3", SCRIPT_PATH, "sets", "testdata/tarkir.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "CUS" in result.stdout
    assert "custom" in result.stdout
    
def test_query_functional_basic():
    """Test basic functional reprint identification."""
    # We need a file with functional reprints to test this properly
    pass

def test_query_extract_basic():
    """Test basic card extraction."""
    # Use tarkir.json which has a standard MTGJSON data structure
    cmd = ["python3", SCRIPT_PATH, "extract", "testdata/tarkir.json", "ANY", "invasion", "-o", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "invasion of tarkir" in data['name'].lower()

def test_query_random_basic():
    """Test basic random card picking."""
    cmd = ["python3", SCRIPT_PATH, "random", "testdata/uthros.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Uthros Research Craft" in result.stdout
    assert "COMPLEXITY:" in result.stdout

def test_query_random_table():
    """Test random card picking in table format."""
    cmd = ["python3", SCRIPT_PATH, "random", "testdata/uthros.json", "--table", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Uthros Research Craft" in result.stdout
    assert "CMC" in result.stdout
