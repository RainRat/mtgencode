import io
import json
import csv
import os
from unittest.mock import patch, MagicMock
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

def test_diff_json_format():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    stdout, stderr = run_diff(["--json"], data1, data2)
    # Verify it is valid JSON
    parsed = json.loads(stdout)
    assert parsed["summary"]["added"] == 1
    assert parsed["summary"]["removed"] == 1
    assert parsed["summary"]["modified"] == 0
    assert parsed["added"][0]["name"] == "New Card"
    assert parsed["removed"][0]["name"] == "Old Card"

def test_diff_csv_format():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    data2 = [
        {"name": "Old Card", "types": ["Creature"], "pt": "2/2", "rarity": "common"},
        {"name": "New Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}
    ]
    stdout, stderr = run_diff(["--csv"], data1, data2)
    # Verify it is CSV
    lines = list(csv.reader(io.StringIO(stdout)))
    assert lines[0] == ["Status", "Name", "Field", "Old Value", "New Value"]
    # Check rows
    added_rows = [r for r in lines if r[0] == "Added"]
    mod_rows = [r for r in lines if r[0] == "Modified"]
    assert len(added_rows) == 1
    assert added_rows[0][1] == "New Card"
    assert len(mod_rows) == 1
    assert mod_rows[0][1] == "Old Card"
    assert mod_rows[0][2] == "P/T"
    assert mod_rows[0][3] == "1/1"
    assert mod_rows[0][4] == "2/2"

def test_diff_outfile_auto_detection_json():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tf:
        temp_path = tf.name
    try:
        data1 = []
        data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
        stdout, stderr = run_diff(["--outfile", temp_path], data1, data2)
        # Should be written to file
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        parsed = json.loads(content)
        assert parsed["summary"]["added"] == 1
    finally:
        os.remove(temp_path)

def test_diff_outfile_auto_detection_csv():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tf:
        temp_path = tf.name
    try:
        data1 = []
        data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
        stdout, stderr = run_diff(["-o", temp_path], data1, data2)
        # Should be written to file
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = list(csv.reader(io.StringIO(content)))
        assert lines[0] == ["Status", "Name", "Field", "Old Value", "New Value"]
        assert lines[1][0] == "Added"
        assert lines[1][1] == "New Card"
    finally:
        os.remove(temp_path)

def test_diff_outfile_text_redirect():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tf:
        temp_path = tf.name
    try:
        data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
        data2 = []
        stdout, stderr = run_diff(["--outfile", temp_path], data1, data2)
        # Verify stdout is empty and content written to file
        assert stdout == ""
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "REMOVED CARDS" in content
        # Bypasses colorization when output to file by default
        assert "\033[" not in content
    finally:
        os.remove(temp_path)
