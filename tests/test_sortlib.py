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

    cards = [c_oth, c_pla, c_art, c_sor, c_ins, c_enc, c_cre]
    sorted_cards = sortlib.sort_cards(cards, 'type')

    names = [c.name for c in sorted_cards]
    assert names == ["creature", "enchantment", "instant", "sorcery", "artifact", "planeswalker", "other"]

def test_sort_type_priority():
    c_art_cre = cardlib.Card({"name": "ArtCre", "types": ["Artifact", "Creature"], "pt": "1/1"})
    c_art = cardlib.Card({"name": "Art", "types": ["Artifact"]})

    cards = [c_art, c_art_cre]
    sorted_cards = sortlib.sort_cards(cards, 'type')
    assert sorted_cards[0].name == "artcre"
    assert sorted_cards[1].name == "art"

def test_sort_colors_quiet():
    c1 = cardlib.Card({"name": "White", "manaCost": "{W}", "types": ["Creature"]})
    segments = sortlib.sort_colors([c1], quiet=True)
    assert len(segments) == 8
    assert segments[0][0].name == "white"

    segments = sortlib.sort_colors([c1], quiet=False)
    assert len(segments) == 8
    assert segments[0][0].name == "white"

def test_sort_stability():
    c1 = cardlib.Card({"name": "A1", "manaCost": "{W}", "types": ["Creature"]})
    c2 = cardlib.Card({"name": "A2", "manaCost": "{W}", "types": ["Creature"]})

    cards = [c1, c2]
    sorted_cards = sortlib.sort_cards(cards, 'color')
    assert sorted_cards[0].name == "a1"
    assert sorted_cards[1].name == "a2"

    cards = [c2, c1]
    sorted_cards = sortlib.sort_cards(cards, 'color')
    assert sorted_cards[0].name == "a2"
    assert sorted_cards[1].name == "a1"

def test_sort_rarity():
    c1 = cardlib.Card({"name": "Common", "rarity": "Common"})
    c2 = cardlib.Card({"name": "Rare", "rarity": "Rare"})
    c3 = cardlib.Card({"name": "Mythic", "rarity": "Mythic"})
    cards = [c1, c2, c3]
    sorted_cards = sortlib.sort_cards(cards, 'rarity')
    assert sorted_cards[0].name == "mythic"
    assert sorted_cards[1].name == "rare"
    assert sorted_cards[2].name == "common"

def test_sort_power():
    c1 = cardlib.Card({"name": "Small", "power": "1", "toughness": "1", "types": ["Creature"]})
    c2 = cardlib.Card({"name": "Big", "power": "5", "toughness": "5", "types": ["Creature"]})
    c3 = cardlib.Card({"name": "None", "types": ["Instant"]})
    cards = [c1, c2, c3]
    sorted_cards = sortlib.sort_cards(cards, 'power')
    assert sorted_cards[0].name == "big"
    assert sorted_cards[1].name == "small"
    assert sorted_cards[2].name == "none"

def test_sort_toughness():
    c1 = cardlib.Card({"name": "Small", "power": "1", "toughness": "1", "types": ["Creature"]})
    c2 = cardlib.Card({"name": "Big", "power": "5", "toughness": "5", "types": ["Creature"]})
    c3 = cardlib.Card({"name": "None", "types": ["Instant"]})
    cards = [c1, c2, c3]
    sorted_cards = sortlib.sort_cards(cards, 'toughness')
    assert sorted_cards[0].name == "big"
    assert sorted_cards[1].name == "small"
    assert sorted_cards[2].name == "none"

def test_sort_loyalty():
    c1 = cardlib.Card({"name": "Low", "types": ["Planeswalker"], "loyalty": "3"})
    c2 = cardlib.Card({"name": "High", "types": ["Planeswalker"], "loyalty": "5"})
    c3 = cardlib.Card({"name": "None", "types": ["Creature"], "pt": "1/1"})
    cards = [c1, c2, c3]
    sorted_cards = sortlib.sort_cards(cards, 'loyalty')
    assert sorted_cards[0].name == "high"
    assert sorted_cards[1].name == "low"
    assert sorted_cards[2].name == "none"

def test_sort_set():
    c1 = cardlib.Card({"name": "A", "setCode": "ABC", "number": "1"})
    c2 = cardlib.Card({"name": "B", "setCode": "ABC", "number": "10"})
    c3 = cardlib.Card({"name": "C", "setCode": "XYZ", "number": "5"})
    cards = [c3, c2, c1]
    sorted_cards = sortlib.sort_cards(cards, 'set')
    assert sorted_cards[0].name == "a"
    assert sorted_cards[1].name == "b"
    assert sorted_cards[2].name == "c"

def test_sort_set_non_numeric_number():
    c1 = cardlib.Card({"name": "A", "setCode": "ABC", "number": "a10"})
    c2 = cardlib.Card({"name": "B", "setCode": "ABC", "number": "5"})
    cards = [c1, c2]
    sorted_cards = sortlib.sort_cards(cards, 'set')
    assert sorted_cards[0].name == "b"
    assert sorted_cards[1].name == "a"

    c3 = cardlib.Card({"name": "C", "setCode": "ABC", "number": "special"})
    cards = [c3, c2]
    sorted_cards = sortlib.sort_cards(cards, 'set')
    assert sorted_cards[0].name == "b"
    assert sorted_cards[1].name == "c"

def test_sort_identity():
    c_w = cardlib.Card({"name": "White", "manaCost": "{W}", "types": ["Creature"]})
    c_wu = cardlib.Card({"name": "Azorius", "manaCost": "{W}{U}", "types": ["Creature"]})
    c_c = cardlib.Card({"name": "Colorless", "manaCost": "{1}", "types": ["Artifact"]})

    cards = [c_wu, c_w, c_c]
    sorted_cards = sortlib.sort_cards(cards, 'identity')

    assert sorted_cards[0].name == "colorless"
    assert sorted_cards[1].name == "white"
    assert sorted_cards[2].name == "azorius"

def test_sort_type_unknown_priority():
    c_tribal = cardlib.Card({"name": "Tribal", "types": ["Tribal"]})
    c_land = cardlib.Card({"name": "Land", "types": ["Land"]})

    cards = [c_tribal, c_land]
    sorted_cards = sortlib.sort_cards(cards, 'type')

    assert sorted_cards[0].name == "land"
    assert sorted_cards[1].name == "tribal"

def test_sort_pack_box():
    c1 = cardlib.Card({"name": "C1"})
    c1.box_id = 1
    c1.pack_id = 2

    c2 = cardlib.Card({"name": "C2"})
    c2.box_id = 1
    c2.pack_id = 1

    cards = [c1, c2]

    sorted_pack = sortlib.sort_cards(cards, 'pack')
    assert sorted_pack[0].name == "c2"
    assert sorted_pack[1].name == "c1"

    sorted_box = sortlib.sort_cards(cards, 'box')
    assert sorted_box[0].name == "c2"
    assert sorted_box[1].name == "c1"
