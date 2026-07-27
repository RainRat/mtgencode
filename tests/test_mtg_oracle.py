import subprocess

def test_oracle_basic():
    """Test basic oracle lookup with exact match."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_query.py', 'oracle', 'testdata/uthros.json', 'Uthros'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert 'Uthros Research Craft' in result.stdout
    assert 'Artifact - Spacecraft' in result.stdout

def test_oracle_fuzzy():
    """Test oracle fuzzy matching auto-fulfillment."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_query.py', 'oracle', 'testdata/uthros.json', 'Uthrss'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Card 'Uthrss' not found." in result.stderr
    assert "Showing best match: Uthros Research Craft" in result.stderr
    assert "Uthros Research Craft" in result.stdout

def test_oracle_grep():
    """Test oracle filtering with grep."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_query.py', 'oracle', 'testdata/tarkir.json', '--grep', 'Invasion'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert 'Invasion of Tarkir' in result.stdout

def test_oracle_smart_view_summary():
    """Test that multiple matches show summaries by default."""
    result = subprocess.run(
        ['python3', 'scripts/mtg_query.py', 'oracle', 'testdata/', '--grep', 'Elf'],
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
        ['python3', 'scripts/mtg_query.py', 'oracle', 'testdata/', '--grep', 'Elf', '--full'],
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
        ['python3', 'scripts/mtg_query.py', 'oracle', 'testdata/uthros.json', 'NonExistentCard'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Card 'NonExistentCard' not found." in result.stdout

def test_oracle_interactive_prompt_and_lookup(mocker):
    """Test that oracle subcommand interactively prompts the user in a TTY."""
    import sys
    from argparse import Namespace
    from scripts.mtg_query import handle_oracle

    # Mock interactive TTY and user inputs a card name
    mocker.patch('sys.stdin.isatty', return_value=True)
    mocker.patch('builtins.input', return_value='Uthros')

    mock_execute = mocker.patch('scripts.mtg_query._execute_oracle', return_value=[])

    args = Namespace(
        query=None,
        infile='testdata/uthros.json',
        quiet=False,
        fields='name,cost,type,stats,rarity,text'
    )
    # Set potential default flags
    for key in ['grep', 'grep_name', 'grep_type', 'grep_text', 'grep_cost', 'grep_pt', 'grep_loyalty',
                'vgrep', 'exclude_name', 'exclude_type', 'exclude_text', 'exclude_cost', 'exclude_pt', 'exclude_loyalty',
                'set', 'rarity', 'colors', 'identity', 'produces', 'id_count', 'cmc', 'pow', 'tou', 'loy',
                'complexity', 'rating', 'fair_mv', 'mechanic', 'action', 'legal', 'color_pie_break', 'deck',
                'seed']:
        setattr(args, key, None)
    for key in ['booster', 'box', 'limit', 'sample']:
        setattr(args, key, 0)
    args.shuffle = False

    handle_oracle(args)

    assert args.query == 'Uthros'
    assert mock_execute.call_count == 1

def test_oracle_interactive_prompt_empty(mocker, capsys):
    """Test that oracle subcommand gracefully cancels on empty input in interactive TTY."""
    import sys
    from argparse import Namespace
    from scripts.mtg_query import handle_oracle

    # Mock interactive TTY and user presses Enter (empty input)
    mocker.patch('sys.stdin.isatty', return_value=True)
    mocker.patch('builtins.input', return_value='')

    mock_execute = mocker.patch('scripts.mtg_query._execute_oracle', return_value=[])

    args = Namespace(
        query=None,
        infile='testdata/uthros.json',
        quiet=False,
        fields='name,cost,type,stats,rarity,text'
    )
    # Set potential default flags
    for key in ['grep', 'grep_name', 'grep_type', 'grep_text', 'grep_cost', 'grep_pt', 'grep_loyalty',
                'vgrep', 'exclude_name', 'exclude_type', 'exclude_text', 'exclude_cost', 'exclude_pt', 'exclude_loyalty',
                'set', 'rarity', 'colors', 'identity', 'produces', 'id_count', 'cmc', 'pow', 'tou', 'loy',
                'complexity', 'rating', 'fair_mv', 'mechanic', 'action', 'legal', 'color_pie_break', 'deck',
                'seed']:
        setattr(args, key, None)
    for key in ['booster', 'box', 'limit', 'sample']:
        setattr(args, key, 0)
    args.shuffle = False

    res = handle_oracle(args)

    assert res == []
    assert args.query is None
    assert mock_execute.call_count == 0
    captured = capsys.readouterr()
    assert "Lookup cancelled." in captured.err
