
import sys
import os

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.cardlib import Card

def test_action_categories_x_damage():
    """Verify that 'Removal' is identified for cards that deal X damage."""
    card = Card({
        "name": "Fireball",
        "manaCost": "{X}{R}",
        "types": ["Sorcery"],
        "text": "@ deals X damage to any target.",
        "rarity": "Uncommon"
    })
    # Current regex: r'deals? [\d&^]+ damage to ...'
    # 'X' is not in [\d&^]+
    assert 'Removal' in card.actions

def test_action_categories_x_pt_reduction():
    """Verify that 'Removal' is identified for cards that give -X/-X."""
    card = Card({
        "name": "Gaze of Granite",
        "manaCost": "{X}{B}{G}",
        "types": ["Sorcery"],
        "text": "Creatures you control get -X/-X until end of turn.",
        "rarity": "Rare"
    })
    # Current regex: r'gets? \-&[\^]+/\-&[\^]+'
    # '-X/-X' won't match.
    assert 'Removal' in card.actions

def test_action_categories_x_buff():
    """Verify that 'Buffs' is identified for cards that give +X/+X."""
    card = Card({
        "name": "Strength from the Fallen",
        "manaCost": "{1}{G}",
        "types": ["Enchantment"],
        "text": "Target creature gets +X/+X until end of turn, where X is...",
        "rarity": "Uncommon"
    })
    # Current regex: r'gets? \+&[\^]*/\+&[\^]*'
    assert 'Buffs' in card.actions

def test_action_categories_x_discard():
    """Verify that 'Disruption' is identified for cards that cause discarding X cards."""
    card = Card({
        "name": "Mind Twist",
        "manaCost": "{X}{B}",
        "types": ["Sorcery"],
        "text": "Target player discards X cards.",
        "rarity": "Rare"
    })
    # Current regex: r'\bdiscard(s|ing)? (a|&[\^]+)?\b'
    assert 'Disruption' in card.actions

def test_action_categories_mass_bounce():
    """Verify that 'Removal' is identified for mass bounce effects using 'all'."""
    card = Card({
        "name": "Cyclonic Rift",
        "manaCost": "{1}{U}",
        "types": ["Instant"],
        "text": "Return all nonland permanents you don't control to their owners' hands.",
        "rarity": "Rare"
    })
    # Current regex: r'return (target|each) [^:]* to (its|their) owner\'s hand'
    # Misses 'all' and 'owners\' hands' (plural)
    assert 'Removal' in card.actions

def test_action_categories_sacrifice_multiple():
    """Verify that 'Removal' is identified for sacrificing multiple permanents."""
    card = Card({
        "name": "Barter in Blood",
        "manaCost": "{2}{B}{B}",
        "types": ["Sorcery"],
        "text": "Each player sacrifices two creatures.",
        "rarity": "Uncommon"
    })
    # Current regex: r'sacrifice (a|target|an)\b'
    assert 'Removal' in card.actions
