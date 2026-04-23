import json
import io
import sys
from unittest.mock import patch, MagicMock
import pytest
from scripts import mtg_diff

def run_diff(args, input_data1, input_data2, isatty=False):
    """Helper to run mtg_diff.main with mocked files and capture output."""
    mock_stdout = MagicMock(spec=io.TextIOBase)
    mock_stdout.getvalue = MagicMock()
    # We'll use a real StringIO for capturing but wrap it in a mock that supports isatty
    real_stdout = io.StringIO()
    mock_stdout.write.side_effect = real_stdout.write
    mock_stdout.getvalue.side_effect = real_stdout.getvalue
    mock_stdout.isatty.return_value = isatty

    mock_stderr = MagicMock(spec=io.TextIOBase)
    mock_stderr.getvalue = MagicMock()
    real_stderr = io.StringIO()
    mock_stderr.write.side_effect = real_stderr.write
    mock_stderr.getvalue.side_effect = real_stderr.getvalue
    mock_stderr.isatty.return_value = isatty

    with patch('sys.stdout', mock_stdout), \
         patch('sys.stderr', mock_stderr), \
         patch('scripts.mtg_diff.jdecode.mtg_open_file') as mock_open:

        # Mock mtg_open_file to return our test data
        def mock_open_side_effect(infile, **kwargs):
            # Very basic implementation of filtering for our tests
            from lib import cardlib
            cards = [cardlib.Card(c) for c in (input_data1 if infile == 'file1.json' else input_data2)]

            # Apply some basic filtering if requested to satisfy tests
            if 'rarities' in kwargs and kwargs['rarities']:
                target_rarities = [r.lower() for r in kwargs['rarities']]
                cards = [c for c in cards if c.rarity_name.lower() in target_rarities]

            return cards

        mock_open.side_effect = mock_open_side_effect

        with patch('sys.argv', ['mtg_diff.py', 'file1.json', 'file2.json'] + args):
            try:
                mtg_diff.main()
            except SystemExit:
                pass

        return mock_stdout.getvalue(), mock_stderr.getvalue()

def test_diff_basic_addition():
    data1 = []
    data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    stdout, stderr = run_diff([], data1, data2)
    assert "ADDED CARDS (1 match)" in stdout
    # The script output names in lowercase for additions/removals
    assert "new card" in stdout
    assert "Added" in stdout
    assert "1" in stdout

def test_diff_basic_removal():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    data2 = []
    stdout, stderr = run_diff([], data1, data2)
    assert "REMOVED CARDS (1 match)" in stdout
    assert "old card" in stdout
    assert "Removed" in stdout

def test_diff_basic_modification():
    data1 = [{"name": "Mod Card", "manaCost": "{W}", "types": ["Creature"], "pt": "1/1", "rarity": "common", "text": "Old text."}]
    data2 = [{"name": "Mod Card", "manaCost": "{U}", "types": ["Instant"], "rarity": "rare", "text": "New text."}]
    stdout, stderr = run_diff([], data1, data2)
    assert "MODIFIED CARDS (1 match)" in stdout
    assert "mod card" in stdout
    assert "Cost:" in stdout
    assert "Type:" in stdout
    assert "Rarity:" in stdout
    assert "Text:" in stdout
    assert "{W}" in stdout
    assert "{U}" in stdout

def test_diff_loyalty_modification():
    data1 = [{"name": "PW", "types": ["Planeswalker"], "loyalty": "3", "rarity": "mythic"}]
    data2 = [{"name": "PW", "types": ["Planeswalker"], "loyalty": "4", "rarity": "mythic"}]
    stdout, stderr = run_diff([], data1, data2)
    assert "Loyalty/Defense:" in stdout
    assert "3" in stdout
    assert "4" in stdout

def test_diff_bside():
    data1 = [{
        "name": "Split",
        "manaCost": "{R}",
        "types": ["Sorcery"],
        "bside": {"name": "Back", "manaCost": "{G}", "types": ["Instant"]}
    }]
    data2 = [{
        "name": "Split",
        "manaCost": "{R}",
        "types": ["Sorcery"],
        "bside": {"name": "Back", "manaCost": "{B}", "types": ["Instant"]}
    }]
    stdout, stderr = run_diff([], data1, data2)
    assert "B-Side Cost:" in stdout
    assert "{G}" in stdout
    assert "{B}" in stdout

def test_diff_bside_presence():
    data1 = [{"name": "Normal", "types": ["Creature"], "pt": "1/1"}]
    data2 = [{"name": "Normal", "types": ["Creature"], "pt": "1/1", "bside": {"name": "Back", "types": ["Land"]}}]
    stdout, stderr = run_diff([], data1, data2)
    assert "B-Side:" in stdout
    assert "Missing" in stdout
    assert "Present" in stdout

    # Other way around
    stdout2, stderr2 = run_diff([], data2, data1)
    assert "B-Side:" in stdout2
    assert "Present" in stdout2
    assert "Missing" in stdout2

def test_diff_summary_only():
    data1 = [{"name": "A", "types": ["Land"]}]
    data2 = [{"name": "B", "types": ["Land"]}]
    stdout, stderr = run_diff(["--summary-only"], data1, data2)
    assert "SUMMARY" in stdout
    assert "ADDED CARDS" not in stdout
    assert "REMOVED CARDS" not in stdout

def test_diff_filtering():
    data1 = [{"name": "A", "types": ["Land"], "rarity": "common"}]
    data2 = [{"name": "A", "types": ["Land"], "rarity": "rare"}]
    stdout, stderr = run_diff(["--rarity", "rare"], data1, data2)
    assert "ADDED CARDS (1 match)" in stdout
    assert "a" in stdout

def test_diff_no_changes():
    data = [{"name": "A", "types": ["Land"]}]
    stdout, stderr = run_diff([], data, data)
    assert "Unchanged" in stdout
    assert "1" in stdout
    assert "MODIFIED CARDS" not in stdout

def test_diff_color():
    data1 = [{"name": "A", "types": ["Land"]}]
    data2 = [{"name": "B", "types": ["Land"]}]
    stdout, stderr = run_diff(["--color"], data1, data2)
    assert "\033[" in stdout

def test_diff_color_auto():
    data1 = [{"name": "A", "types": ["Land"]}]
    data2 = [{"name": "B", "types": ["Land"]}]
    stdout, stderr = run_diff([], data1, data2, isatty=True)
    assert "\033[" in stdout

def test_diff_color_modification():
    data1 = [{"name": "Mod", "types": ["Land"], "manaCost": "{1}"}]
    data2 = [{"name": "Mod", "types": ["Land"], "manaCost": "{2}"}]
    stdout, stderr = run_diff(["--color"], data1, data2)
    assert "\033[" in stdout
    assert "mod" in stdout
    assert "Cost:" in stdout

def test_diff_verbose():
    data1 = [{"name": "A", "types": ["Land"]}]
    data2 = [{"name": "A", "types": ["Land"]}]
    stdout, stderr = run_diff(["--verbose"], data1, data2)
    assert "Loading" in stderr

def test_diff_quiet():
    data1 = [{"name": f"Card{i}", "types": ["Land"]} for i in range(10)]
    data2 = data1
    stdout, stderr = run_diff([], data1, data2, isatty=True)
    assert "Comparison complete" in stderr

    # Test quiet flag
    stdout_q, stderr_q = run_diff(["-q"], data1, data2, isatty=True)
    assert "Comparison complete" not in stderr_q

def test_diff_progress_bar_threshold():
    # We can't easily check if tqdm was called but we can ensure it runs with >5 cards
    data1 = [{"name": f"Card{i}", "types": ["Land"]} for i in range(6)]
    data2 = data1
    stdout, stderr = run_diff([], data1, data2)
    assert "Unchanged" in stdout
