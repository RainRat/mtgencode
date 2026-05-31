import pytest
import sys
import os
import re

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
scriptsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../scripts')
if libdir not in sys.path:
    sys.path.append(libdir)
if scriptsdir not in sys.path:
    sys.path.append(scriptsdir)

from cardlib import Card
import mtg_validate

def test_station_mechanic_no_false_positive():
    # 'manifestation' contains 'station' but should not trigger the Station mechanic
    c = Card({
        "name": "Soulbeam Manifestation",
        "types": ["Enchantment"],
        "text": "Manifestation is cool."
    })
    assert "Station" not in c.mechanics

def test_station_mechanic_legitimate():
    # Actual Station card should still trigger the mechanic
    c = Card({
        "name": "Summoning Station",
        "types": ["Artifact"],
        "text": "Station."
    })
    assert "Station" in c.mechanics

def test_station_validation_no_false_positive():
    # In mtg_validate, a 'manifestation' artifact without P/T should still be invalid (not exempt)
    c = Card({
        "name": "Manifestation Artifact",
        "types": ["Artifact"],
        "text": "This manifestation is weird."
    })
    # check_pt returns None if exempt or if it doesn't apply.
    # If it is NOT a creature and NOT a station, it should return None at the end.
    # Wait, check_pt(card) logic:
    # if 'station' in text: return None
    # if 'creature' in types or card.pt: ...
    # return None

    # Let's test an artifact with P/T that is NOT a station.
    c_pt = Card({
        "name": "Non-Station Artifact with PT",
        "types": ["Artifact"],
        "text": "Manifestation.",
        "pt": "1/1"
    })
    # This should return False (Invalid) because it's not a creature but has PT, and is not a station.
    assert mtg_validate.check_pt(c_pt) is False

def test_station_validation_legitimate():
    # Legitimate station artifact with PT should be exempt from normal PT checks in mtg_validate
    c = Card({
        "name": "Summoning Station",
        "types": ["Artifact"],
        "text": "Station 3+.",
        "pt": "2/2"
    })
    # It returns None when exempt.
    assert mtg_validate.check_pt(c) is None
