import subprocess
import json
import csv
import io
import os

def test_mtg_pips_basic():
    """Test basic pip distribution output."""
    cmd = ["python3", "scripts/mtg_pips.py", "testdata/uthros.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "MANA PIP DISTRIBUTION" in result.stdout
    assert "{U}" in result.stdout

def test_mtg_pips_json():
    """Test JSON output for pips."""
    cmd = ["python3", "scripts/mtg_pips.py", "testdata/uthros.json", "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert any(item['symbol'] == 'U' and item['count'] == 1 for item in data)

def test_mtg_pips_csv():
    """Test CSV output for pips."""
    cmd = ["python3", "scripts/mtg_pips.py", "testdata/uthros.json", "--csv"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    reader = csv.DictReader(io.StringIO(result.stdout))
    rows = list(reader)
    assert any(row['Symbol'] == 'U' and row['Count'] == '1' for row in rows)

def test_mtg_pips_include_text():
    """Test that --include-text works (though uthros has no pips in text)."""
    cmd = ["python3", "scripts/mtg_pips.py", "testdata/uthros.json", "--include-text", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "INCLUDES RULES TEXT" in result.stdout

def test_mtg_pips_filtering():
    """Test that filtering works (resulting in 0 cards for a mismatch)."""
    cmd = ["python3", "scripts/mtg_pips.py", "testdata/uthros.json", "--set", "NONE", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "No cards found matching the criteria." in result.stderr
