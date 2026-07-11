import pytest
from lib.cardlib import Card

def test_x_damage_removal():
    card = Card({
        "name": "Fireball",
        "manaCost": "{X}{R}",
        "types": ["Sorcery"],
        "text": "@ deals X damage to any target.",
        "rarity": "uncommon"
    })
    assert "Removal" in card.actions

def test_mass_bounce_removal():
    card = Card({
        "name": "River's Rebuke",
        "manaCost": "{4}{U}{U}",
        "types": ["Sorcery"],
        "text": "Return all nonland permanents target player controls to their owner's hand.",
        "rarity": "rare"
    })
    assert "Removal" in card.actions

def test_x_pt_reduction_removal():
    card = Card({
        "name": "Death Wind",
        "manaCost": "{X}{B}",
        "types": ["Instant"],
        "text": "Target creature gets -X/-X until end of turn.",
        "rarity": "common"
    })
    assert "Removal" in card.actions

def test_x_draw_card_advantage():
    card = Card({
        "name": "Blue Sun's Zenith",
        "manaCost": "{X}{U}{U}{U}",
        "types": ["Instant"],
        "text": "Target player draws X cards. Shuffle @ into its owner's library.",
        "rarity": "rare"
    })
    assert "Card Advantage" in card.actions

def test_x_discard_disruption():
    card = Card({
        "name": "Mind Twist",
        "manaCost": "{X}{B}",
        "types": ["Sorcery"],
        "text": "Target player discards X cards at random.",
        "rarity": "rare"
    })
    assert "Disruption" in card.actions

def test_x_buff():
    card = Card({
        "name": "Strength of the Tajuru",
        "manaCost": "{X}{G}{G}",
        "types": ["Instant"],
        "text": "Multikicker {1}. Choose target creature, then choose another target creature for each time @ was kicked. Put X +1/+1 counters on each of them.",
        "rarity": "rare"
    })
    assert "Buffs" in card.actions

def test_x_static_buff():
    card = Card({
        "name": "Enlarge",
        "manaCost": "{3}{G}{G}",
        "types": ["Sorcery"],
        "text": "Target creature gets +7/+7 and gains trample until end of turn.",
        "rarity": "uncommon"
    })
    assert "Buffs" in card.actions

def test_pt_reduction_literal_removal():
    card = Card({
        "name": "Dead Weight",
        "manaCost": "{B}",
        "types": ["Enchantment"],
        "text": "Enchanted creature gets -2/-2.",
        "rarity": "common"
    })
    assert "Removal" in card.actions
