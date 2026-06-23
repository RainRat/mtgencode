import pytest
from lib.cardlib import Card

def test_exile_all_removal():
    card = Card({
        "name": "Final Farewell",
        "manaCost": "{4}{W}{W}",
        "types": ["Sorcery"],
        "text": "Exile all creatures."
    })
    assert "Removal" in card.actions

def test_any_target_removal():
    card = Card({
        "name": "Lightning Bolt",
        "manaCost": "{R}",
        "types": ["Instant"],
        "text": "@ deals &^^^ damage to any target."
    })
    assert "Removal" in card.actions

def test_impulsive_draw_card_advantage():
    card = Card({
        "name": "Light Up the Stage",
        "manaCost": "{2}{R}",
        "types": ["Sorcery"],
        "text": "Exile the top two cards of your library. Until the end of your next turn, you may play those cards."
    })
    assert "Card Advantage" in card.actions

def test_cant_attack_block_disruption():
    card_attack = Card({
        "name": "Pacifism",
        "manaCost": "{1}{W}",
        "types": ["Enchantment", "Aura"],
        "text": "Enchanted creature can't attack."
    })
    assert "Disruption" in card_attack.actions

    card_block = Card({
        "name": "Falter",
        "manaCost": "{1}{R}",
        "types": ["Sorcery"],
        "text": "Creatures without flying can't block this turn."
    })
    assert "Disruption" in card_block.actions

def test_freeze_disruption():
    card = Card({
        "name": "Sleep",
        "manaCost": "{2}{U}{U}",
        "types": ["Sorcery"],
        "text": "Tap all creatures target player controls. Those creatures don't untap during their controller's next untap step."
    })
    assert "Disruption" in card.actions

def test_treasure_mana():
    card = Card({
        "name": "Strike It Rich",
        "manaCost": "{R}",
        "types": ["Sorcery"],
        "text": "Create a Treasure token."
    })
    assert "Mana" in card.actions

def test_mass_tap_disruption():
    card2 = Card({
        "name": "Ensnare",
        "manaCost": "{2}{U}{U}",
        "types": ["Sorcery"],
        "text": "Tap all creatures."
    })
    assert "Disruption" in card2.actions

def test_treasure_and_specific_mana():
    card = Card({
        "name": "Wealthy Druid",
        "manaCost": "{1}{G}",
        "types": ["Creature"],
        "text": "T: Add {G}. Create a Treasure token."
    })
    produced = card.produced_colors
    assert "G" in produced
    assert "Any" in produced
