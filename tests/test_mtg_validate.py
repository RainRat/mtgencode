import sys
import os
import pytest

# Add lib and scripts directories to the path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
scriptsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../scripts')
sys.path.append(libdir)
sys.path.append(scriptsdir)

from mtg_validate import (
    check_types, check_pt, check_lands, check_X, check_kicker,
    check_counters, check_choices, check_auras, check_equipment,
    check_vehicles, check_planeswalkers, check_levelup,
    check_activated, check_triggered, check_chosen, check_shuffle,
    check_quotes
)
import cardlib

def test_check_types():
    # Instant
    c = cardlib.Card({"name": "Opt", "types": ["Instant"]})
    assert check_types(c) is True
    c = cardlib.Card({"name": "Tribal Opt", "types": ["Tribal", "Instant"]})
    assert check_types(c) is True
    c = cardlib.Card({"name": "Bad Opt", "types": ["Instant", "Creature"]})
    assert check_types(c) is False

    # Sorcery
    c = cardlib.Card({"name": "Divination", "types": ["Sorcery"]})
    assert check_types(c) is True

    # Creature
    c = cardlib.Card({"name": "Bear", "types": ["Creature"], "power": "2", "toughness": "2"})
    assert check_types(c) is True
    c = cardlib.Card({"name": "Artifact Bear", "types": ["Artifact", "Creature"], "power": "2", "toughness": "2"})
    assert check_types(c) is True
    c = cardlib.Card({"name": "Bad Bear", "types": ["Creature", "Sorcery"], "power": "2", "toughness": "2"})
    assert check_types(c) is False

    # Planeswalker
    c = cardlib.Card({"name": "Jace", "types": ["Planeswalker"], "loyalty": "3"})
    assert check_types(c) is True

    # Battle
    c = cardlib.Card({"name": "Invasion", "types": ["Battle"], "defense": "4"})
    assert check_types(c) is True

    # Other
    c = cardlib.Card({"name": "Sol Ring", "types": ["Artifact"]})
    assert check_types(c) is True
    c = cardlib.Card({"name": "Bad Artifact", "types": ["Artifact", "Instant"]})
    assert check_types(c) is False

def test_check_pt():
    # Battle -> None
    c = cardlib.Card({"name": "Invasion", "types": ["Battle"], "defense": "4"})
    assert check_pt(c) is None

    # Station -> None
    c = cardlib.Card({"name": "Summoning Station", "types": ["Artifact"], "text": "Station."})
    assert check_pt(c) is None

    # Creature
    c = cardlib.Card({"name": "Bear", "types": ["Creature"], "power": "2", "toughness": "2"})
    assert check_pt(c) is True
    c = cardlib.Card({"name": "Bad Bear", "types": ["Creature"]})
    assert check_pt(c) is False

    # Vehicle
    c = cardlib.Card({"name": "Copter", "types": ["Artifact"], "subtypes": ["Vehicle"], "power": "3", "toughness": "3"})
    assert check_pt(c) is True

    # Planeswalker
    c = cardlib.Card({"name": "Jace", "types": ["Planeswalker"], "loyalty": "3"})
    assert check_pt(c) is True
    c = cardlib.Card({"name": "Bad Jace", "types": ["Planeswalker"], "power": "1", "toughness": "1"})
    assert check_pt(c) is False

    # Instant
    c = cardlib.Card({"name": "Opt", "types": ["Instant"]})
    assert check_pt(c) is None
    c = cardlib.Card({"name": "Bad Opt", "types": ["Instant"], "power": "1", "toughness": "1"})
    assert check_pt(c) is False

def test_check_lands():
    c = cardlib.Card({"name": "Forest", "types": ["Land"]})
    assert check_lands(c) is True
    c = cardlib.Card({"name": "Dryad Arbor", "types": ["Land", "Creature"], "power": "1", "toughness": "1"})
    assert check_lands(c) is True
    c = cardlib.Card({"name": "Bad Land", "types": ["Land"], "manaCost": "{G}"})
    assert check_lands(c) is False
    c = cardlib.Card({"name": "Opt", "types": ["Instant"], "manaCost": "{U}"})
    assert check_lands(c) is None

def test_check_X():
    # Good X in cost and text
    c = cardlib.Card({"name": "Fireball", "manaCost": "{X}{R}", "types": ["Sorcery"], "text": "Deal X damage."})
    assert check_X(c) is True

    # check_X in mtg_validate has some special case logic.
    # It returns True if incost and intext.
    # It returns False if incost and not correct (and not sunburst/spent to cast).

    # A card with {X} in cost and "X" in text should be True.
    c = cardlib.Card({"name": "Fireball", "manaCost": "{X}{R}", "types": ["Sorcery"], "text": "Deal X damage."})
    assert check_X(c) is True

    # mtg_validate: defs = count of 'X is', 'pay {X', etc.
    # if not incost and intext > 0: if intext > 1 and defs > 0: correct = True
    c = cardlib.Card({"name": "Good X Text", "types": ["Instant"], "text": "X is the number of creatures. Deal X damage."})
    assert check_X(c) is True

    # Bad X: incost is True, but correct remains None if 'X' is not found in text lines
    # Wait, the code says: if incost: if intext: correct = True
    # If intext is 0, correct remains None.
    # At the end: if incost and not correct: return False
    c = cardlib.Card({"name": "Bad X", "manaCost": "{X}{G}", "types": ["Creature"], "text": "No rules text.", "power": "1", "toughness": "1"})
    # But wait, in cardlib, {X} in manaCost is NOT replaced in rule text usually.
    # check_X uses mt.encode() which is Manatext.encode().
    # Manatext.encode() replaces costs with {X}.
    # So 'intext' should find 'X' if {X} was in the text.

    # Let's see what happens with a truly missing X.
    c = cardlib.Card({"name": "Missing X", "manaCost": "{X}{R}", "types": ["Sorcery"], "text": "Deal 3 damage."})
    assert check_X(c) is False

    # Good X in activation cost and text
    c = cardlib.Card({"name": "Act X", "types": ["Artifact"], "text": "{X}, {T}: Gain X life."})
    assert check_X(c) is True

    # Bad duplicated X in cost and activation
    c = cardlib.Card({"name": "Double X", "manaCost": "{X}{W}", "types": ["Instant"], "text": "{X}: Do something."})
    assert check_X(c) is False

    # Special case sunburst
    c = cardlib.Card({"name": "Engineered Explosives", "manaCost": "{X}", "types": ["Artifact"], "text": "Sunburst."})
    assert check_X(c) is True

def test_check_kicker():
    c = cardlib.Card({"name": "Good Kicker", "types": ["Instant"], "text": "Kicker {1}. If this spell was kicked, do more."})
    assert check_kicker(c) is True
    c = cardlib.Card({"name": "Bad Kicker", "types": ["Instant"], "text": "Kicker {1}."})
    assert check_kicker(c) is False
    c = cardlib.Card({"name": "No Kicker", "types": ["Instant"], "text": "Opt."})
    assert check_kicker(c) is None

def test_check_counters():
    c = cardlib.Card({"name": "Good Counters", "types": ["Creature"], "text": "Put a % counter on @. Countertype % counter.", "power": "1", "toughness": "1"})
    assert check_counters(c) is True
    c = cardlib.Card({"name": "Bad Counters", "types": ["Creature"], "text": "Put a % counter on @.", "power": "1", "toughness": "1"})
    assert check_counters(c) is False
    c = cardlib.Card({"name": "No Counters", "types": ["Creature"], "text": "Bear.", "power": "2", "toughness": "2"})
    assert check_counters(c) is None

def test_check_choices():
    # check_choices expects the markers defined in utils/config:
    # choice_open_delimiter ([), choice_close_delimiter (]), bullet_marker (=)

    # Manually setting up the text to match what check_choices expects
    c = cardlib.Card({"name": "Good Choice", "types": ["Instant"], "text": "Opt."})
    # [&^ = option 1 = option 2]
    # &^ is unary 1.
    c.text.text = "[&^ = option 1 = option 2]"
    assert check_choices(c) is True

    # Manually creating a card with mismatched brackets
    c = cardlib.Card({"name": "Bad Choice", "types": ["Instant"], "text": "Opt."})
    # Manually override the text to bypass standard transformation for testing
    c.text.text = "[ = option 1"
    assert check_choices(c) is False
    c = cardlib.Card({"name": "No Choice", "types": ["Instant"], "text": "Opt."})
    assert check_choices(c) is None

def test_check_auras_equip_vehicles():
    # Auras
    c = cardlib.Card({"name": "Rancor", "types": ["Enchantment"], "subtypes": ["Aura"], "text": "Enchant creature."})
    assert check_auras(c) is True
    c = cardlib.Card({"name": "Opt", "types": ["Instant"]})
    assert check_auras(c) is None

    # Equipment
    c = cardlib.Card({"name": "Sled", "types": ["Artifact"], "subtypes": ["Equipment"], "text": "Equip {2}."})
    # transformed text should contain 'equip'
    assert check_equipment(c) is True
    # check_equipment only checks if 'equipment' in subtypes. If so, it returns 'equip' in text.
    # Actually: if 'equipment' in card.subtypes: return 'equip' in card.text.text
    c = cardlib.Card({"name": "Bad Sled", "types": ["Artifact"], "subtypes": ["Equipment"], "text": "No E-word here."})
    assert check_equipment(c) is False

    # Vehicles
    c = cardlib.Card({"name": "Copter", "types": ["Artifact"], "subtypes": ["Vehicle"], "text": "Crew 1."})
    assert check_vehicles(c) is True
    c = cardlib.Card({"name": "Bad Copter", "types": ["Artifact"], "subtypes": ["Vehicle"], "text": "No C-word here."})
    assert check_vehicles(c) is False

def test_check_planeswalkers():
    # check_planeswalkers uses initial_re = r'^[+-]?' + re.escape(utils.unary_marker) + re.escape(utils.unary_counter) + '*:'
    # which means something like &^:
    # Wait, unary_marker is &, unary_counter is ^.
    # regex is ^[+-]?&\^*:
    c = cardlib.Card({"name": "Jace", "types": ["Planeswalker"], "loyalty": "3"})
    # It checks card.text_lines.
    # Let's manually set up the lines.
    c = cardlib.Card({"name": "Jace", "types": ["Planeswalker"], "loyalty": "3", "text": "+&^: Ability 1.\n-&^^: Ability 2."})
    assert check_planeswalkers(c) is True

    # Bad PW: only one line
    c = cardlib.Card({"name": "Bad Jace", "types": ["Planeswalker"], "loyalty": "3"})
    c.text.text = "+&^: Draw a card."
    assert check_planeswalkers(c) is False

def test_check_levelup():
    c = cardlib.Card({"name": "Student", "types": ["Creature"], "text": "Level up {1}. countertype % level. level &^^+ 2/2.", "power": "1", "toughness": "1"})
    assert check_levelup(c) is True
    c = cardlib.Card({"name": "Opt", "types": ["Instant"]})
    assert check_levelup(c) is None

def test_check_activated_triggered():
    # Activated
    c = cardlib.Card({"name": "Sol Ring", "types": ["Artifact"], "text": "{T}: Add {C}{C}."})
    assert check_activated(c) is True
    c = cardlib.Card({"name": "Bad Instant Act", "types": ["Instant"], "text": "{1}: Gain 1 life."})
    assert check_activated(c) is False

    # Triggered
    c = cardlib.Card({"name": "ETB", "types": ["Creature"], "text": "When @ enters the battlefield, gain 1 life.", "power": "1", "toughness": "1"})
    assert check_triggered(c) is True
    c = cardlib.Card({"name": "Bad Instant Trigger", "types": ["Instant"], "text": "When @ enters the battlefield, gain 1 life."})
    assert check_triggered(c) is False

def test_check_chosen_shuffle_quotes():
    # check_chosen checks if 'chosen' in card.text.text.
    # if so, it checks if 'choose', 'chosen at random', 'name', 'is chosen', or 'search' in it.
    c = cardlib.Card({"name": "Choice", "types": ["Sorcery"], "text": "As @ enters the battlefield, choose a card name. The chosen name..."})
    assert check_chosen(c) is True
    c = cardlib.Card({"name": "Opt", "types": ["Instant"]})
    assert check_chosen(c) is None

    # Shuffle
    # check_shuffle uses card.text_lines and checks if 'search' AND 'library' in line.text.
    # Note: 'search' might be replaced by this_marker (@) if it's the card name or part of it,
    # but here we use a card named "Searcher" to avoid replacing the verb 'search'.
    c = cardlib.Card({"name": "Searcher", "types": ["Sorcery"], "text": "Search your library, then shuffle."})
    assert check_shuffle(c) is True
    c = cardlib.Card({"name": "Bad Search", "types": ["Sorcery"], "text": "Search your library."})
    assert check_shuffle(c) is False
    c = cardlib.Card({"name": "Opt", "types": ["Instant"]})
    assert check_shuffle(c) is None

    # Quotes
    c = cardlib.Card({"name": "Quotes", "types": ["Instant"], "text": 'Named "Fireball".'})
    assert check_quotes(c) is True
    c = cardlib.Card({"name": "Bad Quotes", "types": ["Instant"], "text": 'Named "Fireball.'})
    assert check_quotes(c) is False
