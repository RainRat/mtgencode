import pytest
import io
from lib.cardlib import Card
from scripts.mtg_forge import print_detailed_card

def test_print_detailed_card_use_color_and_rating_high():
    c = Card({
        'name': 'High Power Creature',
        'manaCost': '{1}{G}',
        'types': ['Creature'],
        'subtypes': ['Beast'],
        'power': '5',
        'toughness': '5',
        'text': 'Trample\n{T}: Add {G}.\nDestroy target creature. Create a 2/2 green Bear creature token.',
        'rarity': 'Rare',
        'set': 'TST'
    })
    c.legalities = {'standard': 'legal', 'commander': 'legal'}

    buf = io.StringIO()
    print_detailed_card(c, use_color=True, output_f=buf)
    formatted = buf.getvalue()

    assert 'COMPLEXITY:' in formatted
    assert 'RATING:' in formatted
    assert 'FAIR MV:' in formatted
    assert 'PRODUCED:' in formatted
    assert 'ACTIONS:' in formatted
    assert 'TOKENS:' in formatted
    assert 'MECHANICS:' in formatted
    assert 'LEGALITIES:' in formatted

def test_print_detailed_card_rating_low_and_no_color():
    c = Card({
        'name': 'Low Power Mana Tap',
        'manaCost': '{5}{G}',
        'types': ['Creature'],
        'subtypes': ['Beast'],
        'power': '1',
        'toughness': '1',
        'text': '{T}: Add one mana of any color.',
        'rarity': 'Common',
        'set': 'TST'
    })

    buf = io.StringIO()
    print_detailed_card(c, use_color=False, output_f=buf)
    formatted = buf.getvalue()

    assert 'COMPLEXITY:' in formatted
    assert f'RATING: {c.power_rating:.3f}' in formatted
    assert f'FAIR MV: {c.recommended_cmc}' in formatted
    assert 'PRODUCED: Any' in formatted

def test_print_detailed_card_color_pie_break():
    c = Card({
        'name': 'Green Haste Guy',
        'manaCost': '{G}',
        'types': ['Creature'],
        'subtypes': ['Elf'],
        'power': '2',
        'toughness': '2',
        'text': 'Haste',
        'rarity': 'Uncommon',
        'set': 'TST'
    })

    def mock_check_color_pie():
        return "Color Pie Break: Green should not have standalone Haste."

    c.check_color_pie = mock_check_color_pie

    buf = io.StringIO()
    print_detailed_card(c, use_color=True, output_f=buf)
    formatted_color = buf.getvalue()

    assert 'COLOR PIE:' in formatted_color
    assert 'Green should not' in formatted_color

    buf = io.StringIO()
    print_detailed_card(c, use_color=False, output_f=buf)
    formatted_plain = buf.getvalue()

    assert 'COLOR PIE: Green should not' in formatted_plain

def test_print_detailed_card_colorless_non_creature():
    c = Card({
        'name': 'Ancient Artifact',
        'manaCost': '{3}',
        'types': ['Artifact'],
        'text': 'When Ancient Artifact enters the battlefield, draw a card.',
        'rarity': 'Common',
        'set': 'TST'
    })

    buf = io.StringIO()
    print_detailed_card(c, use_color=False, output_f=buf)
    formatted = buf.getvalue()

    assert 'IDENTITY: C' in formatted
    assert 'RATING:' not in formatted
    assert 'FAIR MV:' not in formatted
    assert 'COLOR PIE: Valid' in formatted
