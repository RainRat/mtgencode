import sys
import os
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
from cardlib import Card

def test_compleated():
    card = Card({
        "name": "Ajani, Sleeper Agent",
        "manaCost": "{1}{G}{G/W/P}{W}",
        "text": "Compleated ({G/W/P} can be paid with {G}, {W}, or 2 life.)",
        "types": ["Planeswalker"],
        "rarity": "mythic",
        "loyalty": "4",
        "supertypes": ["Legendary"]
    })
    assert card.parsed
    assert card.valid

def test_station():
    card = Card({
        "name": "Atmospheric Greenhouse",
        "text": "Station (Tap another creature you control: Put charge counters equal to its power on this Spacecraft. Station only as a sorcery. It's an artifact creature at 8+.)\nSTATION 8+\nFlying, trample",
        "types": ["Artifact"],
        "rarity": "Common"
    })
    assert card.parsed
    assert card.valid

def test_ulalek():
    card = Card({
        "name": "Ulalek, Fused Atrocity",
        "manaCost": "{C/W}{C/U}{C/B}{C/R}{C/G}",
        "text": "Devoid (This card has no color.)\nWhenever you cast an Eldrazi spell, you may pay {C}{C}. If you do, copy all spells you control, then copy all other activated and triggered abilities you control. You may choose new targets for the copies. (Mana abilities can't be copied.)",
        "types": ["Creature"],
        "subtypes": ["Eldrazi"],
        "rarity": "Mythic",
        "pt": "2/5"
    })
    assert card.parsed
    assert card.valid
