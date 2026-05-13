import subprocess

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
        ['python3', 'scripts/mtg_oracle.py', 'testdata/tarkir.json', '--grep', 'Invasion'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert 'Invasion of Tarkir' in result.stdout

def test_oracle_smart_view_summary():
    """Test that multiple matches show summaries by default."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_oracle.py', 'testdata/', '--grep', 'Elf'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    # Summary format: [U] Beast Summoner {2}{G} • Creature — Elf Druid • (2/2)
    assert '[U] Beast Summoner' in result.stdout
    assert '[C] Double Front' in result.stdout
    # Should NOT show full text in summary mode
    assert 'First ability' not in result.stdout

def test_oracle_smart_view_full_force():
    """Test that --full forces full details even for multiple matches."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_oracle.py', 'testdata/', '--grep', 'Elf', '--full'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert 'Beast Summoner' in result.stdout
    assert 'Double Front' in result.stdout
    # Should show full text
    assert 'First ability' in result.stdout

def test_oracle_no_match():
    """Test oracle with no matches."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_oracle.py', 'testdata/uthros.json', 'NonExistentCard'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Card 'NonExistentCard' not found." in result.stdout
