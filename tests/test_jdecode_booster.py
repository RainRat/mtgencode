import pytest
import sys
import os
from unittest.mock import MagicMock

# Ensure lib is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import jdecode, utils, cardlib

def create_mock_card(name, rarity, types=None):
    card = MagicMock(spec=cardlib.Card)
    card.name = name
    card.rarity = rarity
    card.types = types if types else []
    return card

def test_simulate_boosters_standard_distribution():
    # 15 cards per pack: 10 Common, 3 Uncommon, 1 Rare/Mythic, 1 Land
    pool = []
    for i in range(20):
        pool.append(create_mock_card(f"Common {i}", utils.rarity_common_marker))
    for i in range(10):
        pool.append(create_mock_card(f"Uncommon {i}", utils.rarity_uncommon_marker))
    for i in range(5):
        pool.append(create_mock_card(f"Rare {i}", utils.rarity_rare_marker))
    for i in range(5):
        pool.append(create_mock_card(f"Land {i}", utils.rarity_basic_land_marker))

    boosters = jdecode._simulate_boosters(pool, count=2, seed=42)

    assert len(boosters) == 30 # 15 * 2

    # Check first pack (cards 0-14)
    pack1 = boosters[0:15]
    assert len([c for c in pack1 if c.rarity == utils.rarity_common_marker]) == 10
    assert len([c for c in pack1 if c.rarity == utils.rarity_uncommon_marker]) == 3
    assert len([c for c in pack1 if c.rarity == utils.rarity_rare_marker]) == 1
    assert len([c for c in pack1 if c.rarity == utils.rarity_basic_land_marker]) == 1
    for c in pack1:
        assert c.pack_id == 1

    # Check second pack (cards 15-29)
    pack2 = boosters[15:30]
    for c in pack2:
        assert c.pack_id == 2

def test_simulate_boosters_fallback_logic(capsys):
    # Test fallback to all cards when a rarity is missing
    pool = [create_mock_card("Only Card", utils.rarity_common_marker)]

    # Standard distribution: 10 Common, 3 Uncommon, 1 Rare/Mythic, 1 Land
    # With only 1 card in pool and using random.sample(pool, min(len(pool), N)):
    # Pack will have 1 + 1 + 1 + 1 = 4 cards (all the same card)
    boosters = jdecode._simulate_boosters(pool, count=1, verbose=True)

    assert len(boosters) == 4
    for c in boosters:
        assert c.name == "Only Card"

    captured = capsys.readouterr()
    assert "No uncommons found" in captured.err
    assert "No rares/mythics found" in captured.err
    assert "No lands found" in captured.err

def test_simulate_boosters_land_by_type():
    # Test that lands are identified by type if rarity marker is missing
    pool = []
    for i in range(15):
        pool.append(create_mock_card(f"C{i}", utils.rarity_common_marker))
    for i in range(5):
        pool.append(create_mock_card(f"U{i}", utils.rarity_uncommon_marker))
    for i in range(2):
        pool.append(create_mock_card(f"R{i}", utils.rarity_rare_marker))

    # Land without rarity marker but with 'land' type
    pool.append(create_mock_card("Island", "unknown", types=["land"]))

    boosters = jdecode._simulate_boosters(pool, count=1)

    pack = boosters
    land_cards = [c for c in pack if c.name == "Island"]
    assert len(land_cards) == 1

def test_simulate_boosters_copy_isolation():
    # Ensure card instances are copies so they can have different pack_ids
    card = create_mock_card("Test", utils.rarity_common_marker)
    pool = [card]

    # Each pack will have 4 cards (1 of each rarity slot falling back to the same card)
    boosters = jdecode._simulate_boosters(pool, count=2)

    # card appearing in pack 1 and pack 2
    # booster 1 cards are 0-3, booster 2 cards are 4-7
    c1 = boosters[0]
    c2 = boosters[4]

    assert c1.pack_id == 1
    assert c2.pack_id == 2
    assert c1 is not c2
    assert c1 is not card

def test_simulate_boosters_determinism():
    pool = []
    for i in range(100):
        pool.append(create_mock_card(f"C{i}", utils.rarity_common_marker))
    pool.append(create_mock_card("R", utils.rarity_rare_marker))
    pool.append(create_mock_card("U1", utils.rarity_uncommon_marker))
    pool.append(create_mock_card("U2", utils.rarity_uncommon_marker))
    pool.append(create_mock_card("U3", utils.rarity_uncommon_marker))
    pool.append(create_mock_card("L", utils.rarity_basic_land_marker))

    b1 = jdecode._simulate_boosters(pool, count=1, seed=123)
    b2 = jdecode._simulate_boosters(pool, count=1, seed=123)
    b3 = jdecode._simulate_boosters(pool, count=1, seed=456)

    names1 = [c.name for c in b1]
    names2 = [c.name for c in b2]
    names3 = [c.name for c in b3]

    assert names1 == names2
    assert names1 != names3
