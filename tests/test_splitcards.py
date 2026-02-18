import pytest
import os
import subprocess
import json
import csv

def test_splitcards_basic(tmp_path):
    # Create a dummy input file
    infile = tmp_path / "input.txt"
    # Using labeled format to ensure jdecode handles it correctly
    cards = [
        "|1Card A|7common|5Creature\n\n",
        "|1Card B|7common|5Creature\n\n",
        "|1Card C|7common|5Creature\n\n",
        "|1Card D|7common|5Creature\n\n"
    ]
    infile.write_text("".join(cards))

    out1 = tmp_path / "out1.txt"
    out2 = tmp_path / "out2.txt"

    # Run splitcards.py
    cmd = [
        "python3", "scripts/splitcards.py",
        str(infile),
        "--outputs", str(out1), str(out2),
        "--ratios", "0.75", "0.25",
        "--no-shuffle"
    ]
    subprocess.run(cmd, check=True)

    # Check that outputs exist
    assert out1.exists()
    assert out2.exists()

    # Check content counts
    content1 = out1.read_text()
    content2 = out2.read_text()

    # Since we have 4 cards and 0.75 ratio, out1 should have 3 cards, out2 should have 1.
    # jdecode.mtg_open_file will have correctly parsed these.
    # Re-encoded output will have labels because default is labeled.
    assert content1.count("|1") == 3
    assert content2.count("|1") == 1

def test_splitcards_json(tmp_path):
    # Create a dummy input JSON file
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

    cmd = [
        "python3", "scripts/splitcards.py",
        str(infile),
        "--outputs", str(out1), str(out2),
        "--ratios", "0.7", "0.3",
        "--format", "json",
        "--no-shuffle"
    ]
    subprocess.run(cmd, check=True)

    # Verify JSON output
    with open(out1) as f:
        data1 = json.load(f)
    with open(out2) as f:
        data2 = json.load(f)

    assert len(data1) == 2
    assert len(data2) == 1
    assert data1[0]['name'] == "Card 1"
    assert data2[0]['name'] == "Card 3"

def test_splitcards_csv(tmp_path):
     # Create dummy input
    infile = tmp_path / "input.jsonl"
    # Card objects need a type to be valid
    infile.write_text('{"name": "C1", "types": ["T1"]}\n{"name": "C2", "types": ["T2"]}\n')

    out1 = tmp_path / "out1.csv"
    out2 = tmp_path / "out2.csv"

    cmd = [
        "python3", "scripts/splitcards.py",
        str(infile),
        "--outputs", str(out1), str(out2),
        "--ratios", "0.5", "0.5",
        "--format", "csv",
        "--no-shuffle"
    ]
    subprocess.run(cmd, check=True)

    # Verify CSV output
    with open(out1, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]['name'] == "C1"

def test_splitcards_three_way(tmp_path):
    infile = tmp_path / "input.txt"
    cards = ["|1C{:d}|7common|5Type\n\n".format(i) for i in range(10)]
    infile.write_text("".join(cards))

    outputs = [str(tmp_path / "f{:d}.txt".format(i)) for i in range(3)]

    cmd = [
        "python3", "scripts/splitcards.py",
        str(infile),
        "--outputs", outputs[0], outputs[1], outputs[2],
        "--ratios", "0.7", "0.2", "0.1",
        "--no-shuffle"
    ]
    subprocess.run(cmd, check=True)

    assert os.path.getsize(outputs[0]) > 0
    assert os.path.getsize(outputs[1]) > 0
    assert os.path.getsize(outputs[2]) > 0

    with open(outputs[0]) as f: assert f.read().count("|1") == 7
    with open(outputs[1]) as f: assert f.read().count("|1") == 2
    with open(outputs[2]) as f: assert f.read().count("|1") == 1
