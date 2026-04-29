import subprocess
import pytest
import json

def test_stats_basic():
    """Test basic combat stat analysis."""
    cmd = ["python3", "scripts/mtg_stats.py", "testdata/uthros.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "COMBAT STAT ANALYSIS (1 match)" in result.stdout
    assert "Combat Stat Curve (Avg P/T per CMC):" in result.stdout
    assert "3       0.00       8.00      1   0.00" in result.stdout
    assert "Average Stats by Color:" in result.stdout
    assert "U           0.00       8.00      1" in result.stdout
    assert "Popular P/T Combinations:" in result.stdout
    assert "0/8      1   100.0%" in result.stdout

def test_stats_json():
    """Test JSON output of combat stat analysis."""
    cmd = ["python3", "scripts/mtg_stats.py", "testdata/uthros.json", "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data['total_cards'] == 1
    assert data['creatures_analyzed'] == 1
    assert data['cmc_curve'][0]['cmc'] == "3"
    assert data['cmc_curve'][0]['avg_pow'] == 0.0
    assert data['cmc_curve'][0]['avg_tou'] == 8.0
    assert data['color_breakdown'][0]['color'] == "U"
    assert data['pt_distribution'][0]['pt'] == "0/8"

def test_stats_loyalty():
    """Test loyalty analysis for non-creatures."""
    # Invasion of Tarkir is a Battle with defense 5
    cmd = ["python3", "scripts/mtg_stats.py", "testdata/invasion_of_tarkir.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "No creatures found for combat stat analysis." in result.stdout
    assert "Loyalty Stats (Planeswalkers/Battles):" in result.stdout
    assert "Average Loyalty: 5.00" in result.stdout
    assert "Range:           5 - 5" in result.stdout
    assert "Count:           1" in result.stdout

def test_stats_filtering():
    """Test filtering in combat stat analysis."""
    # Uthros is rare
    cmd = ["python3", "scripts/mtg_stats.py", "testdata/uthros.json", "--rarity", "common", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "No cards found matching the criteria" in result.stderr

def test_stats_empty():
    """Test behavior on empty input."""
    # Use a non-existent file or filter that returns nothing
    cmd = ["python3", "scripts/mtg_stats.py", "testdata/uthros.json", "--grep", "NonExistent", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "No cards found matching the criteria" in result.stderr
