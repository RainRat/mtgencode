import pytest
import subprocess
import json
import os

def test_mtg_complexity_basic():
    """Test basic execution of mtg_complexity.py."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_complexity.py', 'testdata/uthros.json', '--no-color'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "MOST COMPLEX CARDS" in result.stdout
    assert "Uthros Research Craft" in result.stdout
    assert "42.5" in result.stdout

def test_mtg_complexity_json():
    """Test JSON output of mtg_complexity.py."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_complexity.py', 'testdata/uthros.json', '--json'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert 'cards' in data
    assert data['cards'][0]['name'] == "Uthros Research Craft"
    assert data['cards'][0]['score'] == 42.46666666666667
    assert 'rare' in data['rarity_averages']

def test_mtg_complexity_nwo():
    """Test NWO violation flagging."""
    # Using a directory that contains commons
    result = subprocess.run(
        ['python3', 'scripts/mtg_complexity.py', 'testdata/', '--nwo-threshold', '5', '--no-color'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "NWO COMPLIANCE WARNINGS" in result.stdout
    assert "Food Factory" in result.stdout

def test_mtg_complexity_empty():
    """Test execution with no matching cards."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_complexity.py', 'testdata/uthros.json', '--rarity', 'common'],
        capture_output=True, text=True
    )
    # It should not crash but report no cards found
    assert "No cards found matching the criteria." in result.stderr
