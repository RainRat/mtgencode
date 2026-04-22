import subprocess
import pytest

def test_curve_basic():
    """Test basic mana curve analysis."""
    cmd = ["python3", "scripts/mtg_curve.py", "testdata/uthros.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "MANA CURVE ANALYSIS (1 match)" in result.stdout
    assert "Global Average CMC: 3.00" in result.stdout
    assert "Average CMC by Color:" in result.stdout
    assert "U         3.00      1      100.0%" in result.stdout

def test_curve_filtering():
    """Test filtering in mana curve analysis."""
    # Filter for creatures. Uthros is an artifact, not a creature (unless stated otherwise in rules text which it isn't by default types)
    # Wait, Uthros is "Artifact - Spacecraft". Card.is_creature checks for 'creature' in types or 'vehicle' in subtypes.
    # Uthros is not a creature.
    cmd = ["python3", "scripts/mtg_curve.py", "testdata/uthros.json", "--grep-type", "Creature", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "No cards found matching the criteria" in result.stderr

def test_curve_multi_color():
    """Test curve with multiple colors (if test data allows)."""
    # Using invasion_of_tarkir.json which is Red
    cmd = ["python3", "scripts/mtg_curve.py", "testdata/invasion_of_tarkir.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Global Average CMC: 2.00" in result.stdout
    assert "R         2.00      1      100.0%" in result.stdout

def test_curve_legend():
    """Test that legend is present."""
    cmd = ["python3", "scripts/mtg_curve.py", "testdata/uthros.json", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "Legend: # Creature  = Non-creature" in result.stdout

def test_curve_empty():
    """Test behavior on empty result."""
    cmd = ["python3", "scripts/mtg_curve.py", "testdata/uthros.json", "--cmc", ">10", "--no-color"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "No cards found matching the criteria" in result.stderr
