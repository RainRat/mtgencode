from datalib import Datamine, padrows, get_bar_chart
import utils
from cardlib import Card

def test_padrows_center_alignment():
    rows = [["Short", "A bit longer"], ["Very Long Indeed", "S"]]
    # col widths will be 16 and 12
    # Row 0: "Short" (5) in 16 -> diff 11 -> left 5, right 6 -> "     Short      "
    #        "A bit longer" (12) in 12 -> diff 0 -> left 0, right 0 -> "A bit longer"
    # Row 1: "Very Long Indeed" (16) in 16 -> diff 0 -> "Very Long Indeed"
    #        "S" (1) in 12 -> diff 11 -> left 5, right 6 -> "     S      "

    padded = padrows(rows, aligns=['c', 'c'])
    # "     Short      " + "  " + "A bit longer" -> "     Short        A bit longer"
    # Join cells with 2 spaces
    assert padded[0] == "     Short        A bit longer"
    assert padded[1] == "Very Long Indeed       S"

def test_get_bar_chart_minimal_filled():
    # Covers lines 139-140 in lib/datalib.py: if filled == 0 and percent > 0: filled = 1
    # 2% of 10 is 0.2, which rounds to 0.
    bar = get_bar_chart(2, use_color=False)
    assert bar == "[█         ]"

def test_datamine_multicolored_card():
    # Covers line 467 in lib/datalib.py: group = 'M' if len(card.cost.colors) > 1
    # Card needs to be parsed successfully to reach that line in Datamine.__init__
    card_json = {
        'name': 'Multicolor Card',
        'manaCost': '{W}{U}',
        'types': ['Creature'],
        'text': 'Flying',
        'rarity': 'Rare',
        'pt': '2/2'
    }
    card = Card(card_json)
    # Even if valid is False, it should be parsed
    assert card.parsed
    assert len(card.cost.colors) == 2

    dm = Datamine([card])
    assert dm.pie_groups['M'] == 1
    assert dm.pie_groups['W'] == 0
    assert dm.pie_groups['U'] == 0
