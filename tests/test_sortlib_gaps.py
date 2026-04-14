import pytest
from unittest.mock import patch
import importlib
import sys
from lib import cardlib
from lib import sortlib
from lib import utils

def test_sort_type_battle():
    c_battle = cardlib.Card({"name": "Invasion", "types": ["Battle"], "defense": "5"})
    c_land = cardlib.Card({"name": "Plains", "types": ["Land"]})
    cards = [c_land, c_battle]
    sorted_cards = sortlib.sort_cards(cards, 'type')
    assert sorted_cards[0].name == "invasion"
    assert sorted_cards[1].name == "plains"

def test_sort_rarity_comprehensive():
    c_mythic = cardlib.Card({"name": "M", "rarity": "mythic"})
    c_rare = cardlib.Card({"name": "R", "rarity": "rare"})
    c_uncommon = cardlib.Card({"name": "U", "rarity": "uncommon"})
    c_common = cardlib.Card({"name": "C", "rarity": "common"})
    c_basic = cardlib.Card({"name": "L", "rarity": "basic land"})
    c_special = cardlib.Card({"name": "I", "rarity": "special"})
    c_other = cardlib.Card({"name": "O", "rarity": "unknown"})

    cards = [c_other, c_special, c_basic, c_common, c_uncommon, c_rare, c_mythic]
    sorted_cards = sortlib.sort_cards(cards, 'rarity')

    names = [c.name for c in sorted_cards]
    assert names == ["m", "r", "u", "c", "l", "i", "o"]

    # Test markers
    c_y = cardlib.Card({"name": "Y", "rarity": utils.rarity_mythic_marker})
    c_a = cardlib.Card({"name": "A", "rarity": utils.rarity_rare_marker})
    c_n = cardlib.Card({"name": "N", "rarity": utils.rarity_uncommon_marker})
    c_o = cardlib.Card({"name": "O", "rarity": utils.rarity_common_marker})
    c_l = cardlib.Card({"name": "LL", "rarity": utils.rarity_basic_land_marker})
    c_i = cardlib.Card({"name": "II", "rarity": utils.rarity_special_marker})

    cards = [c_i, c_l, c_o, c_n, c_a, c_y]
    sorted_cards = sortlib.sort_cards(cards, 'rarity')
    names = [c.name for c in sorted_cards]
    assert names == ["y", "a", "n", "o", "ll", "ii"]

def test_sort_identity_tiebreak():
    # Tiebreak: (len(c.color_identity), c.color_identity, c.name.lower())
    c1 = cardlib.Card({"name": "Alpha", "manaCost": "{W}{U}", "types": ["Creature"]}) # Identity WU, len 2
    c2 = cardlib.Card({"name": "Zebra", "manaCost": "{W}{B}", "types": ["Creature"]}) # Identity WB, len 2
    c3 = cardlib.Card({"name": "Beta", "manaCost": "{W}{B}", "types": ["Creature"]})  # Identity WB, len 2
    c4 = cardlib.Card({"name": "Apple", "manaCost": "{W}", "types": ["Creature"]})    # Identity W, len 1

    cards = [c1, c2, c3, c4]
    sorted_cards = sortlib.sort_cards(cards, 'identity')

    names = [c.name for c in sorted_cards]
    # Expected order:
    # 1. Apple (len 1)
    # 2. Beta (len 2, WB < WU, beta < zebra)
    # 3. Zebra (len 2, WB < WU)
    # 4. Alpha (len 2, WU)
    assert names == ["apple", "beta", "zebra", "alpha"]

def test_tqdm_fallback():
    import builtins
    original_import = builtins.__import__

    def mocked_import(name, *args, **kwargs):
        if name == 'tqdm':
            raise ImportError
        return original_import(name, *args, **kwargs)

    # Clear sortlib from sys.modules to force reload
    if 'lib.sortlib' in sys.modules:
        del sys.modules['lib.sortlib']

    with patch('builtins.__import__', side_effect=mocked_import):
        import lib.sortlib as sortlib_fallback
        # Verify tqdm is the fallback one
        assert sortlib_fallback.tqdm([1, 2, 3]) == [1, 2, 3]

    # Reload again to restore normal state for other tests
    if 'lib.sortlib' in sys.modules:
        del sys.modules['lib.sortlib']
    importlib.import_module('lib.sortlib')
