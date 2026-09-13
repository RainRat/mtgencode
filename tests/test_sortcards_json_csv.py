import os
import sys
import json
import csv
import io
from unittest.mock import patch

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import sortcards
import cardlib


def create_sample_input(tmp_path):
    card1 = {
        "name": "Fireball",
        "manaCost": "{X}{R}",
        "types": ["Sorcery"],
        "text": "Fireball deals X damage.",
        "rarity": "uncommon"
    }
    card2 = {
        "name": "Grizzly Bears",
        "manaCost": "{1}{G}",
        "types": ["Creature"],
        "subtypes": ["Bear"],
        "power": "2",
        "toughness": "2",
        "rarity": "common"
    }
    infile = tmp_path / "input.json"
    data = {"data": {"TST": {"name": "Test", "code": "TST", "type": "expansion", "cards": [card1, card2]}}}
    infile.write_text(json.dumps(data), encoding="utf-8")
    return str(infile)


def test_json_output_explicit(tmp_path):
    infile = create_sample_input(tmp_path)
    outfile = tmp_path / "sorted_output.txt"

    sortcards.main(infile, str(outfile), use_json=True, quiet=True, verbose=False)

    content = outfile.read_text(encoding="utf-8")
    data = json.loads(content)

    assert isinstance(data, dict)
    assert "sorceries" in data or "X cards" in data or "creatures" in data or "common" in data
    # Check that values are lists of string representations
    for cat, cards in data.items():
        assert isinstance(cards, list)
        assert len(cards) > 0


def test_json_output_autodetect(tmp_path):
    infile = create_sample_input(tmp_path)
    outfile = tmp_path / "sorted_output.json"

    # Auto-detection should trigger because filename ends with .json
    sortcards.main(infile, str(outfile), quiet=True, verbose=False)

    content = outfile.read_text(encoding="utf-8")
    data = json.loads(content)

    assert isinstance(data, dict)
    assert "creatures" in data or "common" in data


def test_csv_output_explicit(tmp_path):
    infile = create_sample_input(tmp_path)
    outfile = tmp_path / "sorted_output.txt"

    sortcards.main(infile, str(outfile), use_csv=True, quiet=True, verbose=False)

    content = outfile.read_text(encoding="utf-8")
    reader = list(csv.reader(content.splitlines()))

    assert len(reader) > 1
    assert reader[0] == ["Category", "Card"]
    categories = [row[0] for row in reader[1:]]
    assert any(cat in categories for cat in ["creatures", "sorceries", "common", "uncommon", "CMC 2"])


def test_csv_output_autodetect(tmp_path):
    infile = create_sample_input(tmp_path)
    outfile = tmp_path / "sorted_output.csv"

    # Auto-detection should trigger because filename ends with .csv
    sortcards.main(infile, str(outfile), quiet=True, verbose=False)

    content = outfile.read_text(encoding="utf-8")
    reader = list(csv.reader(content.splitlines()))

    assert len(reader) > 1
    assert reader[0] == ["Category", "Card"]


def test_json_stdout(tmp_path):
    infile = create_sample_input(tmp_path)
    captured = io.StringIO()

    with patch("sys.stdout", captured):
        sortcards.main(infile, oname=None, use_json=True, quiet=True, verbose=False)

    output = captured.getvalue()
    data = json.loads(output)
    assert isinstance(data, dict)


def test_csv_stdout(tmp_path):
    infile = create_sample_input(tmp_path)
    captured = io.StringIO()

    with patch("sys.stdout", captured):
        sortcards.main(infile, oname=None, use_csv=True, quiet=True, verbose=False)

    output = captured.getvalue()
    reader = list(csv.reader(output.splitlines()))
    assert len(reader) > 1
    assert reader[0] == ["Category", "Card"]


def test_json_with_summary(tmp_path):
    infile = create_sample_input(tmp_path)
    outfile = tmp_path / "sorted_summary.json"

    sortcards.main(infile, str(outfile), use_summary=True, quiet=True, verbose=False)

    content = outfile.read_text(encoding="utf-8")
    data = json.loads(content)

    assert isinstance(data, dict)
    for cat, cards in data.items():
        for c_str in cards:
            # Summary format includes card name and mana cost
            assert ("Grizzly Bears" in c_str or "Fireball" in c_str)
