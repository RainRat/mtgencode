import io
import json
import csv
import os
import sys
from unittest.mock import patch, MagicMock
from scripts import mtg_query

def run_query_diff(args, input_data1, input_data2, isatty=False):
    """Helper to run mtg_query.py diff with mocked datasets and capture output."""
    mock_stdout = MagicMock(spec=io.TextIOBase)
    mock_stdout.getvalue = MagicMock()
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
         patch('scripts.mtg_query.cli_utils.load_and_filter_cards') as mock_load:

        def mock_load_side_effect(ns):
            from lib import cardlib
            infile = getattr(ns, 'infile', '-')
            cards_data = input_data1 if infile == 'file1.json' else input_data2
            return [cardlib.Card(c) for c in cards_data]

        mock_load.side_effect = mock_load_side_effect

        with patch('sys.argv', ['mtg_query.py', 'diff', 'file1.json', 'file2.json'] + args):
            try:
                mtg_query.main()
            except SystemExit:
                pass

        return mock_stdout.getvalue(), mock_stderr.getvalue()

def test_query_diff_basic_addition():
    data1 = []
    data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    stdout, stderr = run_query_diff([], data1, data2)
    assert "ADDED CARDS (1 match)" in stdout
    assert "new card" in stdout
    assert "Added" in stdout
    assert "1" in stdout

def test_query_diff_basic_removal():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    data2 = []
    stdout, stderr = run_query_diff([], data1, data2)
    assert "REMOVED CARDS (1 match)" in stdout
    assert "old card" in stdout
    assert "Removed" in stdout

def test_query_diff_basic_modification():
    data1 = [{"name": "Mod Card", "manaCost": "{W}", "types": ["Creature"], "pt": "1/1", "rarity": "common", "text": "Old text."}]
    data2 = [{"name": "Mod Card", "manaCost": "{U}", "types": ["Instant"], "rarity": "rare", "text": "New text."}]
    stdout, stderr = run_query_diff([], data1, data2)
    assert "MODIFIED CARDS (1 match)" in stdout
    assert "mod card" in stdout
    assert "Cost:" in stdout
    assert "Type:" in stdout
    assert "Rarity:" in stdout

def test_query_diff_summary_only():
    data1 = [{"name": "A", "types": ["Land"]}]
    data2 = [{"name": "B", "types": ["Land"]}]
    stdout, stderr = run_query_diff(["--summary-only"], data1, data2)
    assert "SUMMARY" in stdout
    assert "ADDED CARDS" not in stdout
    assert "REMOVED CARDS" not in stdout

def test_query_diff_dry_run():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    stdout, stderr = run_query_diff(["--dry-run"], data1, data2)
    assert "Dry Run Summary: 2 total card(s) evaluated across datasets." in stdout
    assert "Comparison Breakdown:" in stdout
    assert "Added: 1 card(s)" in stdout
    assert "Removed: 1 card(s)" in stdout

def test_query_diff_json_format():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    stdout, stderr = run_query_diff(["--json"], data1, data2)
    parsed = json.loads(stdout)
    assert parsed["summary"]["added"] == 1
    assert parsed["summary"]["removed"] == 1
    assert parsed["added"][0]["name"] == "New Card"

def test_query_diff_csv_format():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    stdout, stderr = run_query_diff(["--csv"], data1, data2)
    lines = list(csv.reader(io.StringIO(stdout)))
    assert lines[0] == ["Status", "Name", "Field", "Old Value", "New Value"]
    assert lines[1][0] == "Added"
    assert lines[1][1] == "New Card"

def test_query_diff_outfile_auto_json():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tf:
        temp_path = tf.name
    try:
        data1 = []
        data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
        stdout, stderr = run_query_diff(["-o", temp_path], data1, data2)
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        parsed = json.loads(content)
        assert parsed["summary"]["added"] == 1
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_query_shell_diff_command():
    from lib import cardlib
    mock_card = cardlib.Card({"name": "Test Card", "types": ["Creature"], "pt": "1/1"})

    mock_input = patch('builtins.input', side_effect=['/diff file1.json file2.json', 'exit'])

    with patch('scripts.mtg_query.cli_utils.load_and_filter_cards', return_value=[mock_card]), \
         patch('scripts.mtg_query.handle_diff') as mock_diff, \
         mock_input:

        args = MagicMock()
        args.color = False
        args.quiet = True
        args.infile = 'AllPrintings.json'
        mtg_query.handle_shell(args)

        assert mock_diff.called
        d_args = mock_diff.call_args[0][0]
        assert d_args.file1 == 'file1.json'
        assert d_args.file2 == 'file2.json'
