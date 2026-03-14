import pytest
import os
import sys

# Add lib directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
import utils
import cardlib
import jdecode

def test_numeric_filter_parsing():
    # Exact
    nf = utils.NumericFilter("5")
    assert nf.mode == 'exact'
    assert nf.val == 5.0

    nf = utils.NumericFilter("== 3.5")
    assert nf.mode in ['exact', 'inequality']
    assert nf.val == 3.5

    # Inequalities
    nf = utils.NumericFilter(">5")
    assert nf.mode == 'inequality'
    assert nf.op == '>'
    assert nf.val == 5.0

    nf = utils.NumericFilter("<= 10.2")
    assert nf.mode == 'inequality'
    assert nf.op == '<='
    assert nf.val == 10.2

    nf = utils.NumericFilter("!=0")
    assert nf.mode == 'inequality'
    assert nf.op == '!='
    assert nf.val == 0.0

    # Range
    nf = utils.NumericFilter("2-4")
    assert nf.mode == 'range'
    assert nf.val == 2.0
    assert nf.val2 == 4.0

    nf = utils.NumericFilter("-1 - 5")
    assert nf.mode == 'range'
    assert nf.val == -1.0
    assert nf.val2 == 5.0

    with pytest.raises(ValueError):
        utils.NumericFilter("abc")

def test_numeric_filter_evaluation():
    # Exact
    nf = utils.NumericFilter("5")
    assert nf.evaluate(5)
    assert nf.evaluate("5")
    assert nf.evaluate("&^^^^^") # unary 5
    assert not nf.evaluate(4)
    assert not nf.evaluate(6)

    # Inequality
    nf = utils.NumericFilter("> 5")
    assert nf.evaluate(6)
    assert nf.evaluate(5.1)
    assert not nf.evaluate(5)
    assert not nf.evaluate(4)

    nf = utils.NumericFilter("<= 3")
    assert nf.evaluate(3)
    assert nf.evaluate(2)
    assert nf.evaluate(0)
    assert not nf.evaluate(3.1)
    assert not nf.evaluate(4)

    # Range
    nf = utils.NumericFilter("2-4")
    assert nf.evaluate(2)
    assert nf.evaluate(3)
    assert nf.evaluate(4)
    assert not nf.evaluate(1.9)
    assert not nf.evaluate(4.1)

    # Non-numeric graceful handling
    assert not nf.evaluate(None)
    assert not nf.evaluate("star")
    assert not nf.evaluate("*")
    assert not nf.evaluate("")

    # Regression test for empty power/loyalty matching 0
    nf_zero = utils.NumericFilter("0")
    assert not nf_zero.evaluate(None)
    assert not nf_zero.evaluate("")

def test_numeric_filter_unary_exceptions():
    # Test unary exceptions from config.py
    # 30 -> "thirty"
    # 25 -> "twenty~five" (using dash_marker ~)
    nf_30 = utils.NumericFilter("30")
    assert nf_30.evaluate("thirty")

    nf_25 = utils.NumericFilter("25")
    assert nf_25.evaluate("twenty~five")

    nf_range = utils.NumericFilter("20-40")
    assert nf_range.evaluate("thirty")
    assert nf_range.evaluate("twenty~five")

def test_jdecode_numeric_filtering():
    # Mock cards for testing
    # Card 1: 1/1, CMC 1, Loyalty None
    c1_json = {
        'name': 'C1',
        'manaCost': '{W}',
        'types': ['Creature'],
        'power': '1',
        'toughness': '1',
        'rarity': 'Common'
    }
    # Card 2: 5/5, CMC 5, Loyalty None
    c2_json = {
        'name': 'C2',
        'manaCost': '{5}',
        'types': ['Creature'],
        'power': '5',
        'toughness': '5',
        'rarity': 'Rare'
    }
    # Card 3: CMC 4, Loyalty 4
    c3_json = {
        'name': 'C3',
        'manaCost': '{2}{U}{U}',
        'types': ['Planeswalker'],
        'loyalty': 4,
        'rarity': 'Mythic'
    }

    cards = [cardlib.Card(c1_json), cardlib.Card(c2_json), cardlib.Card(c3_json)]

    # Test helper for filtering
    def filter_cards(pows=None, tous=None, loys=None, cmcs=None):
        # We manually apply the logic from jdecode match_card for testing
        cmc_filters = [utils.NumericFilter(f) for f in cmcs] if cmcs else []
        pow_filters = [utils.NumericFilter(f) for f in pows] if pows else []
        tou_filters = [utils.NumericFilter(f) for f in tous] if tous else []
        loy_filters = [utils.NumericFilter(f) for f in loys] if loys else []

        res = []
        for card in cards:
            keep = True
            if cmc_filters:
                if not any(f.evaluate(card.cost.cmc) for f in cmc_filters): keep = False
            if keep and pow_filters:
                if not any(f.evaluate(card.pt_p) for f in pow_filters): keep = False
            if keep and tou_filters:
                if not any(f.evaluate(card.pt_t) for f in tou_filters): keep = False
            if keep and loy_filters:
                if not any(f.evaluate(card.loyalty) for f in loy_filters): keep = False

            if keep:
                res.append(card)
        return res

    # Exact power
    assert len(filter_cards(pows=["1"])) == 1
    assert filter_cards(pows=["1"])[0].name == 'c1'

    # Inequality power
    assert len(filter_cards(pows=[">2"])) == 1
    assert filter_cards(pows=[">2"])[0].name == 'c2'

    # Range CMC
    assert len(filter_cards(cmcs=["4-6"])) == 2 # C2 (5) and C3 (4)

    # Multiple flags (OR logic)
    assert len(filter_cards(pows=["1", "5"])) == 2

    # Combined filters (AND logic between types)
    assert len(filter_cards(pows=[">0"], cmcs=["<3"])) == 1 # Only C1

    # Loyalty
    assert len(filter_cards(loys=["4"])) == 1
    assert filter_cards(loys=["4"])[0].name == 'c3'

def test_jdecode_integration(tmp_path):
    # Verify that jdecode.mtg_open_file correctly uses the new filters
    import json
    d = tmp_path / "data"
    d.mkdir()
    p = d / "cards.json"
    p.write_text(json.dumps({
        "data": {
            "SET": {
                "name": "Test Set",
                "code": "SET",
                "type": "expansion",
                "cards": [
                    {'name': 'LowPower', 'manaCost': '{1}', 'types': ['Creature'], 'power': '1', 'toughness': '1', 'rarity': 'Common'},
                    {'name': 'HighPower', 'manaCost': '{1}', 'types': ['Creature'], 'power': '5', 'toughness': '5', 'rarity': 'Common'},
                ]
            }
        }
    }))

    # Test pow filter via mtg_open_file
    cards = jdecode.mtg_open_file(str(p), pows=[">2"])
    assert len(cards) == 1
    assert cards[0].name == 'highpower' # Card names are lowercased by jdecode

    # Test CMC filter via mtg_open_file
    cards = jdecode.mtg_open_file(str(p), cmcs=["<2"])
    assert len(cards) == 2

if __name__ == "__main__":
    # Run tests if called directly
    pytest.main([__file__])
