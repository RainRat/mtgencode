import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.cardlib import Card

def test_mechanics_keywords_comprehensive():
    card_json = {
        "name": "Keyword Soup",
        "types": ["Creature"],
        "text": "Flying, haste, deathtouch, vigilance, ward {2}, prowess, menace, reach, flash, indestructible, scry 2, draw a card, mill three cards, exile target permanent, create a token, discard a card, cycling {2}",
        "rarity": "Rare",
        "power": "1",
        "toughness": "1"
    }
    card = Card(card_json)
    m = card.mechanics

    expected_keywords = {
        'Flying', 'Haste', 'Deathtouch', 'Vigilance', 'Ward', 'Prowess', 'Menace',
        'Reach', 'Flash', 'Indestructible', 'Scry', 'Draw A Card', 'Mill',
        'Exile', 'Token', 'Discard', 'Cycling'
    }

    for kw in expected_keywords:
        assert kw in m, f"Missing keyword: {kw}"

def test_mechanics_structural_markers():
    kicker_card = Card({"name": "Kicker Card", "types": ["Instant"], "text": "Kicker {R}\nIf this spell was kicked...", "rarity": "Common"})
    assert 'Kicker' in kicker_card.mechanics

    uncast_card = Card({"name": "Uncast Card", "types": ["Instant"], "text": "Uncast target spell.", "rarity": "Common"})
    assert 'Uncast' in uncast_card.mechanics

    equip_card = Card({"name": "Sword", "types": ["Artifact"], "subtypes": ["Equipment"], "rarity": "Uncommon", "text": "Equipped creature gets +1/+1."})
    assert 'Equipment' in equip_card.mechanics

    equip_text_card = Card({"name": "Non-Equipment Gear", "types": ["Artifact"], "text": "Equip {2}", "rarity": "Uncommon"})
    assert 'Equipment' in equip_text_card.mechanics

    leveler_card = Card({"name": "Leveler", "types": ["Creature"], "text": "Level up {1}", "rarity": "Rare", "power": "1", "toughness": "1"})
    assert 'Leveler' in leveler_card.mechanics

def test_mechanics_triggered_variations():
    whenever_card = Card({"name": "Trigger Card", "types": ["Enchantment"], "text": "Whenever you cast a spell, draw a card.", "rarity": "Rare"})
    assert 'Triggered' in whenever_card.mechanics

    at_card = Card({"name": "Trigger Card", "types": ["Enchantment"], "text": "At the beginning of your upkeep, scry 1.", "rarity": "Rare"})
    assert 'Triggered' in at_card.mechanics

def test_mechanics_triggered_newline():
    card = Card({
        "name": "Trigger Card",
        "types": ["Creature"],
        "text": "Flying\nWhenever you gain life, draw a card.",
        "rarity": "Rare",
        "power": "2",
        "toughness": "2"
    })
    assert 'Triggered' in card.mechanics

def test_mechanics_etb_variations():
    etb1 = Card({"name": "ETB Card", "types": ["Creature"], "text": "When @ enters the battlefield, gain 2 life.", "rarity": "Common", "power": "1", "toughness": "1"})
    assert 'ETB Effect' in etb1.mechanics

    etb2 = Card({"name": "ETB Card", "types": ["Creature"], "text": "When @ enters, gain 2 life.", "rarity": "Common", "power": "1", "toughness": "1"})
    assert 'ETB Effect' in etb2.mechanics

    etb3 = Card({"name": "ETB Card", "types": ["Creature"], "text": "When @ enters. Gain 2 life.", "rarity": "Common", "power": "1", "toughness": "1"})
    assert 'ETB Effect' in etb3.mechanics

def test_mechanics_encoded_markers():
    level_encoded = "|1Student|5Creature|7common|81/1|9level &^|6{1}|"
    card_level = Card(level_encoded)
    assert 'Leveler' in card_level.mechanics

    counter_encoded_pct = "|1Gideon|5Planeswalker|7rare|9+1: put a % counter on @.|6{3}|"
    card_pct = Card(counter_encoded_pct)
    assert 'Counters' in card_pct.mechanics

    counter_encoded_hash = "|1Hydra|5Creature|7rare|80/0|9@ enters with # # counters on it.|"
    card_hash = Card(counter_encoded_hash)
    assert 'Counters' in card_hash.mechanics

def test_mechanics_word_boundaries():
    fake_keywords = Card({
        "name": "Fake",
        "types": ["Creature"],
        "text": "I have a million dollars and I feel chasten.",
        "rarity": "Common",
        "power": "1",
        "toughness": "1"
    })
    m = fake_keywords.mechanics
    assert 'Mill' not in m
    assert 'Haste' not in m

def test_mechanics_bside_recursive():
    split_card = {
        "name": "Fire",
        "types": ["Instant"],
        "text": "Fire deals 2 damage.",
        "rarity": "Uncommon",
        "bside": {
            "name": "Ice",
            "types": ["Instant"],
            "text": "Tap target permanent. Draw a card."
        }
    }
    card = Card(split_card)
    assert 'Draw A Card' in card.mechanics
