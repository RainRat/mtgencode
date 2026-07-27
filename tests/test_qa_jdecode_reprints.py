import io
import json
from unittest.mock import patch
from lib import jdecode, utils

def test_reprint_set_filtering_activates_reprint():
    cards_json = {
        "data": {
            "ORI": {
                "code": "ORI",
                "name": "Original Set",
                "type": "expansion",
                "cards": [
                    {
                        "name": "Healing Salve",
                        "manaCost": "{W}",
                        "text": "Prevent 3 damage.",
                        "types": ["Instant"],
                        "rarity": "Common",
                        "number": "1"
                    }
                ]
            },
            "REP": {
                "code": "REP",
                "name": "Reprint Set",
                "type": "expansion",
                "cards": [
                    {
                        "name": "Healing Salve",
                        "manaCost": "{W}",
                        "text": "Prevent 3 damage.",
                        "types": ["Instant"],
                        "rarity": "Uncommon",
                        "number": "42"
                    }
                ]
            }
        }
    }

    json_str = json.dumps(cards_json)

    with patch('sys.stdin', io.StringIO(json_str)):
        cards = jdecode.mtg_open_file('-', sets=["REP"])

    assert len(cards) == 1
    card = cards[0]
    assert card.name == "healing salve"
    assert card.set_code == "REP"
    assert card.rarity == utils.rarity_uncommon_marker
    assert card.number == "42"
