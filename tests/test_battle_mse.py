from lib.cardlib import Card
from lib import utils

def test_battle_to_mse():
    battle_json = {
        "name": "Invasion of Zendikar",
        "manaCost": "{3}{G}",
        "types": ["Battle"],
        "subtypes": ["Siege"],
        "rarity": "Uncommon",
        "defense": "3",
        "text": "When Invasion of Zendikar enters the battlefield, search your library for up to two basic land cards..."
    }

    card = Card(battle_json)
    mse_out = card.to_mse()

    assert "super type: Battle" in mse_out
    assert "sub type: Siege" in mse_out
    assert "stylesheet: magic-m15-extra-improved" in mse_out
    assert "defense: 3" in mse_out
    # Unary check
    assert "&^^^" not in mse_out
