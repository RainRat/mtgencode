import os
import sys
import json
import csv
import io
import tempfile
import runpy
import pytest
from unittest.mock import patch

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
