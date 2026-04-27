import subprocess
import os

def test_oracle_basic():
    """Test basic oracle lookup with exact match."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_oracle.py', 'testdata/uthros.json', 'Uthros'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert 'Uthros Research Craft' in result.stdout
    assert 'Artifact - Spacecraft' in result.stdout

def test_oracle_fuzzy():
    """Test oracle fuzzy matching suggestions."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_oracle.py', 'testdata/uthros.json', 'Uthrss'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Card 'Uthrss' not found." in result.stdout
    assert "Did you mean:" in result.stdout
    assert "- Uthros" in result.stdout

def test_oracle_grep():
    """Test oracle filtering with grep."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_oracle.py', 'testdata/tarkir_encoded.txt', '--grep', 'Invasion'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert 'Invasion of Tarkir' in result.stdout

def test_oracle_no_match():
    """Test oracle with no matches."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_oracle.py', 'testdata/uthros.json', 'NonExistentCard'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Card 'NonExistentCard' not found." in result.stdout
