import os
import sys
import json
import csv
import io
import tempfile
import runpy
import pytest
from unittest.mock import patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

from scripts.splitcards import main

def test_splitcards_basic(tmp_path):
    infile = tmp_path / "input.txt"
    cards = [
        "|1Card A|7common|5Creature\n\n",
        "|1Card B|7common|5Creature\n\n",
        "|1Card C|7common|5Creature\n\n",
        "|1Card D|7common|5Creature\n\n"
    ]
    infile.write_text("".join(cards))

    out1 = tmp_path / "out1.txt"
    out2 = tmp_path / "out2.txt"

    args = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out1), str(out2),
        "--ratios", "0.75", "0.25",
        "-s"
    ]
    with patch("sys.argv", args):
        main()

    assert out1.exists()
    assert out2.exists()

    content1 = out1.read_text()
    content2 = out2.read_text()

    assert content1.count("|1") == 3
    assert content2.count("|1") == 1

def test_splitcards_json(tmp_path):
    infile = tmp_path / "input.json"
    data = {
        "data": {
            "TEST": {
                "name": "Test Set",
                "code": "TEST",
                "type": "expansion",
                "cards": [
                    {"name": "Card 1", "types": ["Creature"], "rarity": "common", "power": "1", "toughness": "1"},
                    {"name": "Card 2", "types": ["Instant"], "rarity": "uncommon"},
                    {"name": "Card 3", "types": ["Sorcery"], "rarity": "rare"}
                ]
            }
        }
    }
    infile.write_text(json.dumps(data))

    out1 = tmp_path / "out1.json"
    out2 = tmp_path / "out2.json"

    args = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out1), str(out2),
        "--ratios", "0.7", "0.3",
        "--format", "json",
        "-s"
    ]
    with patch("sys.argv", args):
        main()

    with open(out1, encoding="utf-8") as f:
        data1 = json.load(f)
    with open(out2, encoding="utf-8") as f:
        data2 = json.load(f)

    assert len(data1) == 2
    assert len(data2) == 1
    assert data1[0]['name'] == "Card 1"
    assert data2[0]['name'] == "Card 3"

def test_splitcards_csv(tmp_path):
    infile = tmp_path / "input.jsonl"
    infile.write_text('{"name": "C1", "types": ["T1"]}\n{"name": "C2", "types": ["T2"]}\n')

    out1 = tmp_path / "out1.csv"
    out2 = tmp_path / "out2.csv"

    args = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out1), str(out2),
        "--ratios", "0.5", "0.5",
        "--format", "csv",
        "-s"
    ]
    with patch("sys.argv", args):
        main()

    with open(out1, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]['name'] == "C1"

def test_splitcards_jsonl(tmp_path):
    infile = tmp_path / "input.txt"
    cards = ["|1Card Alpha|7common|5Creature\n\n", "|1Card Beta|7common|5Creature\n\n"]
    infile.write_text("".join(cards))

    out1 = tmp_path / "out1.jsonl"
    out2 = tmp_path / "out2.jsonl"

    args = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out1), str(out2),
        "--ratios", "0.5", "0.5",
        "--format", "jsonl",
        "-s"
    ]
    with patch("sys.argv", args):
        main()

    lines = [line.strip() for line in out1.read_text().strip().split("\n") if line.strip()]
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["name"] == "Card Alpha"

def test_splitcards_three_way(tmp_path):
    infile = tmp_path / "input.txt"
    cards = ["|1C{:d}|7common|5Type\n\n".format(i) for i in range(10)]
    infile.write_text("".join(cards))

    outputs = [str(tmp_path / f"f{i}.txt") for i in range(3)]

    args = [
        "splitcards.py",
        str(infile),
        "--outputs", outputs[0], outputs[1], outputs[2],
        "--ratios", "0.7", "0.2", "0.1",
        "-s"
    ]
    with patch("sys.argv", args):
        main()

    assert os.path.getsize(outputs[0]) > 0
    assert os.path.getsize(outputs[1]) > 0
    assert os.path.getsize(outputs[2]) > 0

    with open(outputs[0], encoding="utf-8") as f:
        assert f.read().count("|1") == 7
    with open(outputs[1], encoding="utf-8") as f:
        assert f.read().count("|1") == 2
    with open(outputs[2], encoding="utf-8") as f:
        assert f.read().count("|1") == 1

def test_splitcards_dry_run(tmp_path):
    infile = tmp_path / "input.txt"
    cards = ["|1Card Alpha|7common|5Type\n\n", "|1Card Beta|7common|5Type\n\n"]
    infile.write_text("".join(cards))

    out1 = tmp_path / "out1.txt"
    out2 = tmp_path / "out2.txt"

    args = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out1), str(out2),
        "--ratios", "0.5", "0.5",
        "--dry-run",
        "-s"
    ]
    with patch("sys.argv", args):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            main()

    stdout = mock_stdout.getvalue()
    assert "Dry Run Summary: 2 card(s) matched." in stdout
    assert "Dataset Split Breakdown:" in stdout
    assert str(out1) in stdout
    assert str(out2) in stdout

    assert not out1.exists()
    assert not out2.exists()

def test_mismatched_outputs_ratios(tmp_path):
    infile = tmp_path / "input.txt"
    infile.write_text("|1Card A|7common|5Creature\n\n")

    out1 = tmp_path / "out1.txt"

    args = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out1),
        "--ratios", "0.5", "0.5"
    ]
    with patch("sys.argv", args):
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 1
    assert "Error: The number of outputs must match the number of ratios." in mock_stderr.getvalue()

def test_ratios_normalization_warning(tmp_path):
    infile = tmp_path / "input.txt"
    infile.write_text("|1Card A|7common|5Creature\n\n|1Card B|7common|5Creature\n\n")

    out1 = tmp_path / "out1.txt"
    out2 = tmp_path / "out2.txt"

    args = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out1), str(out2),
        "--ratios", "0.4", "0.4",
        "-s"
    ]
    with patch("sys.argv", args):
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            main()

    assert "Warning: Ratios sum to 0.8000, normalizing to 1.0." in mock_stderr.getvalue()
    assert out1.exists()
    assert out2.exists()

def test_no_cards_matched(tmp_path):
    infile = tmp_path / "input.txt"
    infile.write_text("|1Card A|7common|5Creature\n\n")

    out1 = tmp_path / "out1.txt"

    args = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out1),
        "--ratios", "1.0",
        "--grep-name", "Nonexistent"
    ]
    with patch("sys.argv", args):
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 1
    assert "Error: No cards matched filters." in mock_stderr.getvalue()

def test_sample_and_sort(tmp_path):
    infile = tmp_path / "input.txt"
    cards = [
        "|1Card A|3{1}|7common|5Creature\n\n",
        "|1Card B|3{3}|7common|5Creature\n\n",
        "|1Card C|3{2}|7common|5Creature\n\n"
    ]
    infile.write_text("".join(cards))

    out1 = tmp_path / "out1.txt"
    out2 = tmp_path / "out2.txt"

    args = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out1), str(out2),
        "--ratios", "0.5", "0.5",
        "--sample", "2",
        "--sort", "cmc",
        "--reverse"
    ]
    with patch("sys.argv", args):
        main()

    assert out1.exists()
    assert out2.exists()

def test_encoding_options(tmp_path):
    infile = tmp_path / "input.txt"
    cards = ["|1Card Alpha|7common|5Creature\n\n", "|1Card Beta|7common|5Creature\n\n"]
    infile.write_text("".join(cards))

    out1 = tmp_path / "out1.txt"
    out2 = tmp_path / "out2.txt"

    # Test vec format
    args_vec = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out1), str(out2),
        "--ratios", "0.5", "0.5",
        "-e", "vec",
        "-s"
    ]
    with patch("sys.argv", args_vec):
        main()
    assert out1.exists()

    # Test rfields and --nolabel
    args_rfields = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out1), str(out2),
        "--ratios", "0.5", "0.5",
        "-e", "rfields",
        "--nolabel",
        "-s"
    ]
    with patch("sys.argv", args_rfields):
        main()
    assert out1.exists()

def test_main_cli_execution(tmp_path):
    infile = tmp_path / "input.txt"
    cards = ["|1Card Alpha|7common|5Creature\n\n"]
    infile.write_text("".join(cards))

    out1 = tmp_path / "out1.txt"

    args = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out1),
        "--ratios", "1.0",
        "-s"
    ]
    with patch("sys.argv", args):
        runpy.run_path("scripts/splitcards.py", run_name="__main__")

    assert out1.exists()

def test_splitcards_presets_and_defaults(tmp_path):
    infile = tmp_path / "input.txt"
    cards = ["|1C{:d}|7common|5Type\n\n".format(i) for i in range(10)]
    infile.write_text("".join(cards))

    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # Default run (no outputs, no ratios, no preset -> preset train-val 90/10)
        args_default = ["splitcards.py", str(infile), "-s"]
        with patch("sys.argv", args_default):
            main()
        assert os.path.exists("train.txt")
        assert os.path.exists("val.txt")

        # Clean up created files
        os.remove("train.txt")
        os.remove("val.txt")

        # Preset train-val-test
        args_tvt = ["splitcards.py", str(infile), "--preset", "train-val-test", "-s"]
        with patch("sys.argv", args_tvt):
            main()
        assert os.path.exists("train.txt")
        assert os.path.exists("val.txt")
        assert os.path.exists("test.txt")
        os.remove("train.txt")
        os.remove("val.txt")
        os.remove("test.txt")

        # Preset 50-50 with JSON format
        args_5050 = ["splitcards.py", str(infile), "--preset", "50-50", "--format", "json", "-s"]
        with patch("sys.argv", args_5050):
            main()
        assert os.path.exists("split1.json")
        assert os.path.exists("split2.json")
        os.remove("split1.json")
        os.remove("split2.json")

        # Preset train-test
        args_tt = ["splitcards.py", str(infile), "--preset", "train-test", "-s"]
        with patch("sys.argv", args_tt):
            main()
        assert os.path.exists("train.txt")
        assert os.path.exists("test.txt")
        os.remove("train.txt")
        os.remove("test.txt")

        # Outputs without ratios (auto-derived equal ratios)
        args_no_ratios = ["splitcards.py", str(infile), "--outputs", "custom1.txt", "custom2.txt", "-s"]
        with patch("sys.argv", args_no_ratios):
            main()
        assert os.path.exists("custom1.txt")
        assert os.path.exists("custom2.txt")
        os.remove("custom1.txt")
        os.remove("custom2.txt")

        # Ratios without outputs (2 ratios -> train/val)
        args_ratios_2 = ["splitcards.py", str(infile), "--ratios", "0.8", "0.2", "-s"]
        with patch("sys.argv", args_ratios_2):
            main()
        assert os.path.exists("train.txt")
        assert os.path.exists("val.txt")
        os.remove("train.txt")
        os.remove("val.txt")

        # Ratios without outputs (3 ratios -> train/val/test)
        args_ratios_3 = ["splitcards.py", str(infile), "--ratios", "0.7", "0.2", "0.1", "-s"]
        with patch("sys.argv", args_ratios_3):
            main()
        assert os.path.exists("train.txt")
        assert os.path.exists("val.txt")
        assert os.path.exists("test.txt")
        os.remove("train.txt")
        os.remove("val.txt")
        os.remove("test.txt")

        # Ratios without outputs (4 ratios -> split_1..4)
        args_ratios_4 = ["splitcards.py", str(infile), "--ratios", "0.25", "0.25", "0.25", "0.25", "-s"]
        with patch("sys.argv", args_ratios_4):
            main()
        assert os.path.exists("split_1.txt")
        assert os.path.exists("split_2.txt")
        assert os.path.exists("split_3.txt")
        assert os.path.exists("split_4.txt")
        os.remove("split_1.txt")
        os.remove("split_2.txt")
        os.remove("split_3.txt")
        os.remove("split_4.txt")

    finally:
        os.chdir(old_cwd)

def test_splitcards_default_infile_and_interactive(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # Create a mock default dataset data/AllPrintings.json
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        default_file = data_dir / "AllPrintings.json"
        data = {
            "data": {
                "TEST": {
                    "name": "Test Set",
                    "code": "TEST",
                    "type": "expansion",
                    "cards": [
                        {"name": "Card 1", "types": ["Creature"], "rarity": "common"},
                        {"name": "Card 2", "types": ["Instant"], "rarity": "uncommon"}
                    ]
                }
            }
        }
        default_file.write_text(json.dumps(data))

        # Omitted infile with default dataset existing
        args_no_infile = ["splitcards.py", "-s"]
        with patch("sys.argv", args_no_infile):
            with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
                main()
        assert "Notice: No input dataset specified. Using default dataset:" in mock_stderr.getvalue()
        assert os.path.exists("train.txt")
        assert os.path.exists("val.txt")
        os.remove("train.txt")
        os.remove("val.txt")

        # Remove default dataset and test interactive TTY execution
        default_file.unlink()
        args_interactive = ["splitcards.py"]
        with patch("sys.argv", args_interactive):
            with patch("sys.stdin.isatty", return_value=True):
                with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
                    with pytest.raises(SystemExit) as exc_info:
                        main()

        assert exc_info.value.code == 0
        assert "usage: splitcards.py" in mock_stderr.getvalue() or "Splits a card dataset" in mock_stderr.getvalue()
    finally:
        os.chdir(old_cwd)


def test_splitcards_auto_format_detection(tmp_path):
    infile = tmp_path / "input.txt"
    cards = ["|1Card Alpha|7common|5Creature\n\n", "|1Card Beta|7common|5Creature\n\n"]
    infile.write_text("".join(cards))

    # 1. Test .json extension auto-detection
    out_json1 = tmp_path / "split1.json"
    out_json2 = tmp_path / "split2.json"
    args_json = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out_json1), str(out_json2),
        "--ratios", "0.5", "0.5",
        "-s"
    ]
    with patch("sys.argv", args_json):
        main()

    with open(out_json1, encoding="utf-8") as f:
        data1 = json.load(f)
        assert isinstance(data1, list)
        assert data1[0]['name'] == "Card Alpha"

    # 2. Test .csv extension auto-detection
    out_csv1 = tmp_path / "split1.csv"
    out_csv2 = tmp_path / "split2.csv"
    args_csv = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out_csv1), str(out_csv2),
        "--ratios", "0.5", "0.5",
        "-s"
    ]
    with patch("sys.argv", args_csv):
        main()

    with open(out_csv1, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]['name'] == "Card Alpha"

    # 3. Test .jsonl extension auto-detection
    out_jsonl1 = tmp_path / "split1.jsonl"
    out_jsonl2 = tmp_path / "split2.jsonl"
    args_jsonl = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out_jsonl1), str(out_jsonl2),
        "--ratios", "0.5", "0.5",
        "-s"
    ]
    with patch("sys.argv", args_jsonl):
        main()

    line = out_jsonl1.read_text().strip()
    data_jsonl = json.loads(line)
    assert data_jsonl['name'] == "Card Alpha"

    # 4. Test explicit -f/--format overriding output file extension
    out_override1 = tmp_path / "override1.json"
    out_override2 = tmp_path / "override2.json"
    args_override = [
        "splitcards.py",
        str(infile),
        "--outputs", str(out_override1), str(out_override2),
        "--ratios", "0.5", "0.5",
        "-f", "text",
        "-s"
    ]
    with patch("sys.argv", args_override):
        main()

    # Content should be encoded text format even though file ends in .json
    content = out_override1.read_text()
    assert "|1Card Alpha" in content
