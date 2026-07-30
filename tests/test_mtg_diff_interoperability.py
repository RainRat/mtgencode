import io
import os
import json
import csv
import tempfile
from unittest.mock import patch, MagicMock
from scripts import mtg_diff

def run_diff_interop(args, input_data1, input_data2, isatty=False):
    """Helper to run mtg_diff.main with mocked files and capture output."""
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
         patch('scripts.mtg_diff.jdecode.mtg_open_file') as mock_open:

        def mock_open_side_effect(infile, **kwargs):
            from lib import cardlib
            return [cardlib.Card(c) for c in (input_data1 if infile == 'file1.json' else input_data2)]

        mock_open.side_effect = mock_open_side_effect

        with patch('sys.argv', ['mtg_diff.py', 'file1.json', 'file2.json'] + args):
            try:
                mtg_diff.main()
            except SystemExit:
                pass

        return mock_stdout.getvalue(), mock_stderr.getvalue()

def test_diff_json_output():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"}]
    data2 = [
        {"name": "New Card", "types": ["Creature"], "pt": "1/1", "rarity": "common"},
        {"name": "Old Card", "types": ["Creature"], "pt": "2/2", "rarity": "common"}
    ]
    stdout, stderr = run_diff_interop(["--json"], data1, data2)

    # Parse output as JSON
    parsed = json.loads(stdout)
    assert "summary" in parsed
    assert parsed["summary"]["added"] == 1
    assert parsed["summary"]["removed"] == 0
    assert parsed["summary"]["modified"] == 1
    assert parsed["summary"]["unchanged"] == 0
    assert parsed["summary"]["total_distinct"] == 2

    # Verify lists
    assert len(parsed["added"]) == 1
    assert parsed["added"][0]["name"] == "New Card"
    assert len(parsed["removed"]) == 0
    assert len(parsed["modified"]) == 1
    assert parsed["modified"][0]["name"] == "old card"
    assert parsed["modified"][0]["diffs"][0]["field"] == "P/T"
    assert parsed["modified"][0]["diffs"][0]["old"] == "1/1"
    assert parsed["modified"][0]["diffs"][0]["new"] == "2/2"

def test_diff_json_summary_only():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1"}]
    data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1"}]
    stdout, stderr = run_diff_interop(["--json", "--summary-only"], data1, data2)
    parsed = json.loads(stdout)

    assert "summary" in parsed
    assert parsed["summary"]["added"] == 1
    assert parsed["summary"]["removed"] == 1
    assert "added" not in parsed
    assert "removed" not in parsed
    assert "modified" not in parsed

def test_diff_csv_output():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1"}]
    data2 = [
        {"name": "New Card", "types": ["Creature"], "pt": "1/1"},
        {"name": "Old Card", "types": ["Creature"], "pt": "2/2"}
    ]
    stdout, stderr = run_diff_interop(["--csv"], data1, data2)

    # Parse as CSV
    reader = csv.reader(io.StringIO(stdout))
    rows = list(reader)
    assert rows[0] == ["Status", "Name", "Field", "Old", "New"]

    # Expect Added row and Modified row
    added_row = next((r for r in rows if r[0] == 'Added'), None)
    assert added_row is not None
    assert added_row[1] == "New Card"

    modified_row = next((r for r in rows if r[0] == 'Modified'), None)
    assert modified_row is not None
    assert modified_row[1] == "Old Card"
    assert modified_row[2] == "P/T"
    assert modified_row[3] == "1/1"
    assert modified_row[4] == "2/2"

def test_diff_csv_summary_only():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1"}]
    data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1"}]
    stdout, stderr = run_diff_interop(["--csv", "--summary-only"], data1, data2)
    reader = csv.reader(io.StringIO(stdout))
    rows = list(reader)

    assert rows[0] == ["Metric", "Count"]
    assert ["Added", "1"] in rows
    assert ["Removed", "1"] in rows
    assert ["Modified", "0"] in rows

def test_diff_outfile_json_detection():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1"}]
    data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1"}]

    # Create temp file with .json extension
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name

    try:
        stdout, stderr = run_diff_interop(["-o", temp_path], data1, data2)
        assert stdout == "" # No output to stdout when printing to file

        # Read the file
        with open(temp_path, "r", encoding="utf-8") as f:
            content = f.read()

        parsed = json.loads(content)
        assert parsed["summary"]["added"] == 1
        assert parsed["summary"]["removed"] == 1
    finally:
        os.remove(temp_path)

def test_diff_outfile_csv_detection():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1"}]
    data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1"}]

    # Create temp file with .csv extension
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
        temp_path = tf.name

    try:
        stdout, stderr = run_diff_interop(["-o", temp_path], data1, data2)
        assert stdout == ""

        # Read the file
        with open(temp_path, "r", encoding="utf-8") as f:
            content = f.read()

        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        assert rows[0] == ["Status", "Name", "Field", "Old", "New"]
    finally:
        os.remove(temp_path)

def test_diff_outfile_text():
    data1 = [{"name": "Old Card", "types": ["Creature"], "pt": "1/1"}]
    data2 = [{"name": "New Card", "types": ["Creature"], "pt": "1/1"}]

    # Create temp file with .txt extension
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
        temp_path = tf.name

    try:
        stdout, stderr = run_diff_interop(["-o", temp_path], data1, data2)
        assert stdout == ""

        # Read the file
        with open(temp_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "SUMMARY" in content
        assert "ADDED CARDS" in content
        assert "REMOVED CARDS" in content
    finally:
        os.remove(temp_path)

def test_diff_outfile_error_handling():
    data1 = []
    data2 = []

    # Try to write to a non-existent directory/forbidden path
    stdout, stderr = run_diff_interop(["-o", "/nonexistent_dir/file.json"], data1, data2)
    # The program should write an error to stderr and exit
    assert "Error opening output file" in stdout or "Error opening output file" in stderr
