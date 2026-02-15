import json
import os
import subprocess
import pytest
from lib import jdecode

def test_jsonl_write_read(tmp_path):
    # 1. Create a sample JSON file
    json_file = tmp_path / "card.json"
    card_data = {
        "name": "Uthros",
        "manaCost": "{1}{R}",
        "types": ["Creature"],
        "subtypes": ["Human", "Warrior"],
        "text": "Haste",
        "power": "2",
        "toughness": "2",
        "rarity": "Uncommon"
    }
    json_file.write_text(json.dumps(card_data), encoding="utf-8")

    # 2. Use encode.py to get encoded text
    encoded_file = tmp_path / "card.txt"
    subprocess.run(["python3", "encode.py", str(json_file), str(encoded_file), "--stable"], check=True)

    # 3. Use decode.py to convert it to JSONL
    jsonl_file = tmp_path / "card.jsonl"
    subprocess.run(["python3", "decode.py", str(encoded_file), str(jsonl_file)], check=True)

    # 4. Verify the JSONL file content
    assert jsonl_file.exists()
    lines = jsonl_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    card_dict = json.loads(lines[0])
    assert card_dict["name"] == "Uthros"
    assert card_dict["manaCost"] == "{1}{R}"

    # 5. Use jdecode to read the JSONL file
    cards = jdecode.mtg_open_file(str(jsonl_file))
    assert len(cards) == 1
    assert cards[0].name == "uthros"

def test_jsonl_directory_scan(tmp_path):
    # 1. Create a directory with multiple card files including JSONL
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # JSON file
    json_file = data_dir / "card1.json"
    json_file.write_text(json.dumps({"name": "Card 1", "types": ["Creature"], "power": "1", "toughness": "1", "rarity": "Common", "layout": "normal"}), encoding="utf-8")

    # JSONL file
    jsonl_file = data_dir / "card2.jsonl"
    jsonl_file.write_text(json.dumps({"name": "Card 2", "types": ["Instant"], "rarity": "Rare", "layout": "normal"}) + "\n", encoding="utf-8")

    # 2. Use jdecode to scan the directory
    cards = jdecode.mtg_open_file(str(data_dir))

    # 3. Verify both cards were loaded
    names = sorted([c.name for c in cards])
    assert "card 1" in names
    assert "card 2" in names
    assert len(cards) == 2

def test_jsonl_stdin(tmp_path):
    # 1. Prepare JSONL content
    card_data = {"name": "Stdin Card", "types": ["Sorcery"], "rarity": "Uncommon", "layout": "normal"}
    jsonl_content = json.dumps(card_data) + "\n"

    # 2. Run encode.py reading from stdin
    process = subprocess.Popen(
        ["python3", "encode.py", "-", "--stable"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(input=jsonl_content)

    # 3. Verify encoded output contains the card name
    assert "stdin card" in stdout.lower()
    assert process.returncode == 0
