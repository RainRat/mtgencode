
import sys
import os
import subprocess

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
from cardlib import Card

def test_to_table_row():
    card_json = {
        "name": "Grizzly Bears",
        "manaCost": "{1}{G}",
        "types": ["Creature"],
        "subtypes": ["Bear"],
        "power": "2",
        "toughness": "2",
        "rarity": "Common"
    }
    card = Card(card_json)
    row = card.to_table_row(ansi_color=False)
    print(f"Row: {row}")
    # Rarity is lowercase from MTGJSON if not in map, but Card(card_json) uses fields_from_json
    # which uses utils.json_rarity_map if available.
    assert row == ["Grizzly Bears", "{1}{G}", "2", "Creature \u2014 Bear", "2/2", "common"]

def test_to_table_row_bside():
    card_json = {
        "name": "Fire",
        "manaCost": "{1}{R}",
        "types": ["Instant"],
        "rarity": "Uncommon",
        "bside": {
            "name": "Ice",
            "manaCost": "{1}{U}",
            "types": ["Instant"],
            "rarity": "Uncommon"
        }
    }
    card = Card(card_json)
    row = card.to_table_row(ansi_color=False)
    print(f"Bside Row: {row}")
    assert row == ["Fire // Ice", "{1}{R} // {1}{U}", "2 // 2", "Instant // Instant", "", "uncommon"]

def test_cli_table():
    # Encode a sample card and decode it with --table
    # Use - to avoid file not found
    cmd = "echo '1Grizzly Bears|3{1}{G}|5creature|6bear|8&^^/&^^|0O' | python3 decode.py - --table"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert "Name" in result.stdout
    assert "Grizzly Bears" in result.stdout
    assert "2/2" in result.stdout
    # 'common' is used internally
    assert "common" in result.stdout

if __name__ == "__main__":
    test_to_table_row()
    test_to_table_row_bside()
    test_cli_table()
    print("All table tests passed!")
