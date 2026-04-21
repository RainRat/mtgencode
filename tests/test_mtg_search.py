import subprocess
import json
import csv
import io
import os
import pytest

def test_search_basic():
    """Test basic searching with grep."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--grep", "Uthros", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Uthros Research Craft" in result.stdout
    assert "Artifact - Spacecraft" in result.stdout

def test_search_json_output():
    """Test JSON output format."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['name'] == 'Uthros Research Craft'

def test_search_csv_output():
    """Test CSV output format."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--csv"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    reader = csv.DictReader(io.StringIO(result.stdout))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]['Name'] == 'Uthros Research Craft'

def test_search_table_output():
    """Test Table output format."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--table", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "SEARCH RESULTS (1 match)" in result.stdout
    assert "Name" in result.stdout
    assert "Uthros Research Craft" in result.stdout

def test_search_markdown_table():
    """Test Markdown table output format."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--md-table"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "| Name | Cost |" in result.stdout
    assert "| :--- | :--- |" in result.stdout
    assert "| Uthros Research Craft |" in result.stdout

def test_search_summary_output():
    """Test summary output format."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--summary", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Uthros Research Craft" in result.stdout
    assert "[R]" in result.stdout

def test_search_filtering_cmc():
    """Test filtering by CMC."""
    # Uthros has CMC 3
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--cmc", "3", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "Uthros Research Craft" in result.stdout

    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--cmc", ">4", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "No cards found matching the criteria" in result.stderr

def test_search_filtering_rarity():
    """Test filtering by rarity."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--rarity", "rare", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "Uthros Research Craft" in result.stdout

    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--rarity", "common", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "No cards found matching the criteria" in result.stderr

def test_search_fields_selection():
    """Test custom fields selection."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--fields", "name,rarity", "--csv"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    reader = csv.DictReader(io.StringIO(result.stdout))
    rows = list(reader)
    assert 'Name' in rows[0]
    assert 'Rarity' in rows[0]
    assert 'Cost' not in rows[0]

def test_search_fuzzy_suggestions():
    """Test fuzzy suggestions on zero matches."""
    # 'Uthrrs' is close to 'Uthros'
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--grep-name", "Uthrrs"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "No cards found matching the criteria" in result.stderr
    assert "Did you mean:" in result.stderr
    assert "- Uthros" in result.stderr

def test_search_sorting():
    """Test sorting output."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--sort", "name", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0

def test_search_limit_and_shuffle():
    """Test limit and shuffle flags."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--limit", "1", "--shuffle", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Uthros Research Craft" in result.stdout

def test_search_invalid_fields_warning():
    """Test warning for unrecognized fields."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--fields", "name,invalid_field"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "Warning: Unrecognized fields: invalid_field" in result.stderr

def test_search_simulation():
    """Test that simulation flags run."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/uthros.json", "--booster", "1", "--fields", "name,pack", "--csv"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Pack" in result.stdout

def test_search_tarkir_fix():
    """Verify that Battle cards from tarkir.json are now correctly identified as valid."""
    cmd = ["python3", "scripts/mtg_search.py", "testdata/tarkir.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Invasion of Tarkir" in result.stdout
    assert "5" in result.stdout
