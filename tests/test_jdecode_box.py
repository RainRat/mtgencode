import pytest
import sys
import os
from unittest.mock import MagicMock
import tempfile
import json
import copy

# Ensure lib is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import jdecode, utils, cardlib, sortlib

def create_mock_card(name, rarity, types=None):
    card = MagicMock(spec=cardlib.Card)
    card.name = name
    card.rarity = rarity
    card.types = types if types else []
    # Manacost is needed for some sorting/processing
    card.cost = MagicMock()
    card.cost.colors = []
    card.cost.cmc = 0
    # Add a mock format method
    card.cost.format.return_value = ""
    card.cost.encode.return_value = ""
    return card

def test_simulate_boxes_counts():
    # Pool with enough cards for standard pack distribution
    pool = []
    for i in range(15):
        pool.append(create_mock_card(f"C{i}", utils.rarity_common_marker))
    for i in range(5):
        pool.append(create_mock_card(f"U{i}", utils.rarity_uncommon_marker))
    for i in range(2):
        pool.append(create_mock_card(f"R{i}", utils.rarity_rare_marker))
    for i in range(2):
        pool.append(create_mock_card(f"L{i}", utils.rarity_basic_land_marker))

    # 1 box = 36 packs. Each pack has 15 cards (standard distribution)
    # distribution: 10C, 3U, 1R/M, 1L. Total 15.
    # Total cards = 36 * 15 = 540.

    box_size = jdecode.BOOSTER_BOX_SIZE # 36
    cards_per_pack = 10 + 3 + 1 + 1 # 15

    boxes = jdecode._simulate_boxes(pool, count=1, seed=42)

    assert len(boxes) == box_size * cards_per_pack

    # Check pack IDs
    pack_ids = set(getattr(c, 'pack_id', None) for c in boxes)
    assert len(pack_ids) == box_size
    assert min(pack_ids) == 1
    assert max(pack_ids) == box_size

def test_simulate_boxes_tagging():
    # Pool with enough cards for standard pack distribution
    pool = []
    for i in range(10): pool.append(create_mock_card(f"C{i}", utils.rarity_common_marker))
    for i in range(3): pool.append(create_mock_card(f"U{i}", utils.rarity_uncommon_marker))
    pool.append(create_mock_card("R", utils.rarity_rare_marker))
    pool.append(create_mock_card("L", utils.rarity_basic_land_marker))

    count = 2
    boxes = jdecode._simulate_boxes(pool, count=count, seed=42)

    # Check box IDs
    box_ids = set(getattr(c, 'box_id', None) for c in boxes)
    assert box_ids == {1, 2}

    # Check first box cards
    box1_cards = [c for c in boxes if c.box_id == 1]
    assert len(box1_cards) == jdecode.BOOSTER_BOX_SIZE * 15
    for c in box1_cards:
        assert 1 <= c.pack_id <= jdecode.BOOSTER_BOX_SIZE

    # Check second box cards
    box2_cards = [c for c in boxes if c.box_id == 2]
    assert len(box2_cards) == jdecode.BOOSTER_BOX_SIZE * 15
    for c in box2_cards:
        assert 1 <= c.pack_id <= jdecode.BOOSTER_BOX_SIZE

def test_sort_by_box_and_pack():
    c1 = create_mock_card("z", utils.rarity_common_marker)
    c1.box_id = 1
    c1.pack_id = 2

    c2 = create_mock_card("a", utils.rarity_common_marker)
    c2.box_id = 1
    c2.pack_id = 1

    c3 = create_mock_card("b", utils.rarity_common_marker)
    c3.box_id = 2
    c3.pack_id = 1

    cards = [c1, c2, c3]

    # Sort by 'box' (or 'pack', they use same logic in sortlib)
    # Logic: box_id ascending, then pack_id ascending, then name ascending
    sorted_cards = sortlib.sort_cards(cards, 'box')

    assert sorted_cards[0].name == "a" # Box 1, Pack 1
    assert sorted_cards[1].name == "z" # Box 1, Pack 2
    assert sorted_cards[2].name == "b" # Box 2, Pack 1

    # Verify 'pack' criterion works the same
    sorted_cards_pack = sortlib.sort_cards(cards, 'pack')
    assert sorted_cards_pack == sorted_cards

def test_jdecode_box_integration():
    # Test integration with mtg_open_file using a temp JSON file
    cards_list = []
    # mtg_open_file filters by validity. Creatures need P/T.
    for i in range(10): cards_list.append({"name": f"C{i}", "types": ["Creature"], "rarity": "Common", "power": "1", "toughness": "1"})
    for i in range(3): cards_list.append({"name": f"U{i}", "types": ["Creature"], "rarity": "Uncommon", "power": "1", "toughness": "1"})
    cards_list.append({"name": "R", "types": ["Creature"], "rarity": "Rare", "power": "1", "toughness": "1"})
    cards_list.append({"name": "L", "types": ["Land"], "rarity": "Basic Land"})

    test_data = {
        "data": {
            "SET": {
                "name": "Test Set",
                "code": "SET",
                "type": "expansion",
                "cards": cards_list
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False, encoding='utf-8') as tmp:
        json.dump(test_data, tmp)
        tmp_path = tmp.name

    try:
        # Open 1 box
        cards = jdecode.mtg_open_file(tmp_path, box=1, seed=123)

        # 36 packs * 15 cards = 540
        assert len(cards) == jdecode.BOOSTER_BOX_SIZE * 15
        assert all(hasattr(c, 'box_id') for c in cards)
        assert all(hasattr(c, 'pack_id') for c in cards)
        assert all(c.box_id == 1 for c in cards)

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
