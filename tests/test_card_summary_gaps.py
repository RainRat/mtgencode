from lib.cardlib import Card
from lib import utils

def test_summary_invalid_colored_status_indicator():
    invalid_json = {"name": "Invalid Creature", "types": ["Creature"], "rarity": "Common"}
    card = Card(invalid_json)
    assert not card.valid

    summary = card.summary(ansi_color=True)
    expected_status = utils.colorize("[?] ", utils.Ansi.YELLOW)
    assert summary.startswith(expected_status)

def test_summary_planeswalker_loyalty_parentheses():
    pw_json = {
        "name": "Jace",
        "manaCost": "{1}{U}{U}",
        "types": ["Planeswalker"],
        "rarity": "Rare",
        "loyalty": 3
    }
    card = Card(pw_json)
    assert card.loyalty == "&^^^"

    summary = card.summary()
    assert "(3)" in summary
    assert "[[3]]" not in summary

def test_summary_battle_defense_brackets():
    battle_json = {
        "name": "Invasion",
        "manaCost": "{1}{G}",
        "types": ["Battle"],
        "rarity": "Uncommon",
        "defense": 5
    }
    card = Card(battle_json)
    assert card.loyalty == "&^^^^^"

    summary = card.summary()
    assert "[[5]]" in summary
    assert "(5)" not in summary
