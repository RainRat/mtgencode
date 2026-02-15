import pytest
from lib import cardlib
from lib import sortlib

def test_sort_cards_empty():
    assert sortlib.sort_cards([], 'name') == []

def test_sort_cards_no_criterion():
    c1 = cardlib.Card({"name": "Zebra", "types": ["Creature"]})
    cards = [c1]
    assert sortlib.sort_cards(cards, None) == cards
    assert sortlib.sort_cards(cards, "") == cards

def test_sort_cards_invalid_criterion():
    c1 = cardlib.Card({"name": "Zebra", "types": ["Creature"]})
    cards = [c1]
    assert sortlib.sort_cards(cards, "invalid") == cards

def test_sort_by_name():
    c1 = cardlib.Card({"name": "Zebra", "types": ["Creature"]})
    c2 = cardlib.Card({"name": "apple", "types": ["Creature"]})
    c3 = cardlib.Card({"name": "Banana", "types": ["Creature"]})
    cards = [c1, c2, c3]
    sorted_cards = sortlib.sort_cards(cards, 'name')
    # Card names are lowercased during parsing
    assert sorted_cards[0].name == "apple"
    assert sorted_cards[1].name == "banana"
    assert sorted_cards[2].name == "zebra"

def test_sort_by_cmc():
    c1 = cardlib.Card({"name": "Big", "manaCost": "{6}{G}", "types": ["Creature"]})
    c2 = cardlib.Card({"name": "Small", "manaCost": "{G}", "types": ["Creature"]})
    c3 = cardlib.Card({"name": "Medium", "manaCost": "{2}{G}", "types": ["Creature"]})
    cards = [c1, c2, c3]
    sorted_cards = sortlib.sort_cards(cards, 'cmc')
    assert sorted_cards[0].name == "small"
    assert sorted_cards[1].name == "medium"
    assert sorted_cards[2].name == "big"

def test_sort_by_color_extended():
    c_w = cardlib.Card({"name": "White", "manaCost": "{W}", "types": ["Creature"]})
    c_u = cardlib.Card({"name": "Blue", "manaCost": "{U}", "types": ["Creature"]})
    c_b = cardlib.Card({"name": "Black", "manaCost": "{B}", "types": ["Creature"]})
    c_r = cardlib.Card({"name": "Red", "manaCost": "{R}", "types": ["Creature"]})
    c_g = cardlib.Card({"name": "Green", "manaCost": "{G}", "types": ["Creature"]})
    c_m = cardlib.Card({"name": "Multi", "manaCost": "{R}{G}", "types": ["Creature"]})
    c_c = cardlib.Card({"name": "Colorless", "manaCost": "{2}", "types": ["Artifact"]})
    c_l = cardlib.Card({"name": "Land", "types": ["Land"]})

    cards = [c_l, c_c, c_m, c_g, c_r, c_b, c_u, c_w]
    sorted_cards = sortlib.sort_cards(cards, 'color')

    # Expected order: W, U, B, R, G, multi, colorless, lands
    names = [c.name for c in sorted_cards]
    assert names == ["white", "blue", "black", "red", "green", "multi", "colorless", "land"]

def test_sort_by_type_comprehensive():
    c_cre = cardlib.Card({"name": "Creature", "types": ["Creature"]})
    c_enc = cardlib.Card({"name": "Enchantment", "types": ["Enchantment"]})
    c_ins = cardlib.Card({"name": "Instant", "types": ["Instant"]})
    c_sor = cardlib.Card({"name": "Sorcery", "types": ["Sorcery"]})
    c_art = cardlib.Card({"name": "Artifact", "types": ["Artifact"]})
    c_pla = cardlib.Card({"name": "Planeswalker", "types": ["Planeswalker"], "loyalty": "3"})
    c_oth = cardlib.Card({"name": "Other", "types": ["Land"]})

    # Priority: creature, enchantment, instant, sorcery, artifact, planeswalker, other
    cards = [c_oth, c_pla, c_art, c_sor, c_ins, c_enc, c_cre]
    sorted_cards = sortlib.sort_cards(cards, 'type')

    names = [c.name for c in sorted_cards]
    assert names == ["creature", "enchantment", "instant", "sorcery", "artifact", "planeswalker", "other"]

def test_sort_type_priority():
    # Card with multiple types should be sorted by the highest priority type
    # Creature (0) vs Artifact (4). Should be 0.
    c_art_cre = cardlib.Card({"name": "ArtCre", "types": ["Artifact", "Creature"], "pt": "1/1"})

    c_art = cardlib.Card({"name": "Art", "types": ["Artifact"]})

    cards = [c_art, c_art_cre]
    sorted_cards = sortlib.sort_cards(cards, 'type')
    assert sorted_cards[0].name == "artcre"
    assert sorted_cards[1].name == "art"

def test_sort_colors_quiet():
    c1 = cardlib.Card({"name": "White", "manaCost": "{W}", "types": ["Creature"]})
    # Just ensuring quiet=True/False doesn't break anything
    # We call sort_colors directly to ensure coverage
    segments = sortlib.sort_colors([c1], quiet=True)
    assert len(segments) == 8
    assert segments[0][0].name == "white"

    segments = sortlib.sort_colors([c1], quiet=False)
    assert len(segments) == 8
    assert segments[0][0].name == "white"

def test_sort_stability():
    c1 = cardlib.Card({"name": "A1", "manaCost": "{W}", "types": ["Creature"]})
    c2 = cardlib.Card({"name": "A2", "manaCost": "{W}", "types": ["Creature"]})

    # Sort by color (both white)
    cards = [c1, c2]
    sorted_cards = sortlib.sort_cards(cards, 'color')
    assert sorted_cards[0].name == "a1"
    assert sorted_cards[1].name == "a2"

    cards = [c2, c1]
    sorted_cards = sortlib.sort_cards(cards, 'color')
    assert sorted_cards[0].name == "a2"
    assert sorted_cards[1].name == "a1"
