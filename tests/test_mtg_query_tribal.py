import os
import re
import sys
import argparse
import pytest
from unittest.mock import MagicMock, patch

# Add lib and scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

import utils
import cardlib
import jdecode
from mtg_query import get_subtype_forms, handle_tribal

# Minimal mock card data
C_ELVISH_ARCHDRUID = {
    "name": "Elvish Archdruid",
    "manaCost": "{1}{G}{G}",
    "rarity": "rare",
    "type": "Creature — Elf Druid",
    "types": ["Creature"],
    "subtypes": ["Elf", "Druid"],
    "text": "Other Elf creatures you control get +1/+1.\n{T}: Add {G} for each Elf you control.",
    "power": "2",
    "toughness": "2",
    "setCode": "TST"
}

C_LLANOWAR_ELVES = {
    "name": "Llanowar Elves",
    "manaCost": "{G}",
    "rarity": "common",
    "type": "Creature — Elf Druid",
    "types": ["Creature"],
    "subtypes": ["Elf", "Druid"],
    "text": "{T}: Add {G}.",
    "power": "1",
    "toughness": "1",
    "setCode": "TST"
}

C_ELF_BLESSING = {
    "name": "Elf Blessing",
    "manaCost": "{G}",
    "rarity": "common",
    "type": "Instant",
    "types": ["Instant"],
    "subtypes": [],
    "text": "Regenerate target Elf or Elves.",
    "setCode": "TST"
}

C_GIANT_GROWTH = {
    "name": "Giant Growth",
    "manaCost": "{G}",
    "rarity": "common",
    "type": "Instant",
    "types": ["Instant"],
    "subtypes": [],
    "text": "Target creature gets +3/+3 until end of turn.",
    "setCode": "TST"
}

C_NO_SUBTYPE = {
    "name": "Nameless Spell",
    "manaCost": "{1}",
    "rarity": "common",
    "type": "Sorcery",
    "types": ["Sorcery"],
    "subtypes": [],
    "text": "Draw a card.",
    "setCode": "TST"
}

# Double-faced card
C_DF_CARD = {
    "name": "Double Front",
    "manaCost": "{W}",
    "rarity": "common",
    "type": "Creature — Elf",
    "types": ["Creature"],
    "subtypes": ["Elf"],
    "text": "Front rules text.",
    "power": "1",
    "toughness": "1",
    "setCode": "TST",
    "bside": {
        "name": "Double Back",
        "manaCost": "{U}",
        "rarity": "uncommon",
        "type": "Creature — Merfolk",
        "types": ["Creature"],
        "subtypes": ["Merfolk"],
        "text": "Other Merfolk get +1/+1.",
        "power": "2",
        "toughness": "2"
    },
    "layout": "transform"
}

def test_get_subtype_forms():
    # Irregulars
    assert "elves" in get_subtype_forms("elf")
    assert "elf" in get_subtype_forms("elves")
    assert "wolves" in get_subtype_forms("wolf")
    assert "wolf" in get_subtype_forms("wolves")
    assert "fungi" in get_subtype_forms("fungus")
    assert "fungus" in get_subtype_forms("fungi")
    assert "mice" in get_subtype_forms("mouse")
    assert "mouse" in get_subtype_forms("mice")

    # Regular 'y' ending
    assert "faeries" in get_subtype_forms("faerie")
    assert "faerie" in get_subtype_forms("faeries")
    assert "allies" in get_subtype_forms("ally")
    assert "ally" in get_subtype_forms("allies")

    # Standard plurals
    assert "goblins" in get_subtype_forms("goblin")
    assert "goblin" in get_subtype_forms("goblins")
    assert "dragons" in get_subtype_forms("dragon")
    assert "dragon" in get_subtype_forms("dragons")

    # Singularization tests
    assert "dwarf" in get_subtype_forms("dwarves")
    assert "dwarves" in get_subtype_forms("dwarf")


@patch("cli_utils.load_and_filter_cards")
def test_handle_tribal_basic(mock_load):
    # Setup card pool
    pool = [
        cardlib.Card(C_ELVISH_ARCHDRUID),
        cardlib.Card(C_LLANOWAR_ELVES),
        cardlib.Card(C_ELF_BLESSING),
        cardlib.Card(C_GIANT_GROWTH)
    ]
    mock_load.return_value = pool

    # We want to find tribal cards for "Elvish Archdruid"
    args = argparse.Namespace(
        query="Elvish Archdruid",
        infile="dummy.json",
        quiet=False,
        fields="name",
        color=None,
        limit=0,
        reverse=False,
        sort=None,
        delimiter=" | "
    )

    # Execute
    results = handle_tribal(args, include_indices=True)

    # Llanowar Elves shares subtypes "Elf", "Druid"
    # Elf Blessing mentions "Elf" in rules text
    # Giant Growth has no relation
    matched_names = [c.name.lower() for c in results]
    assert "llanowar elves" in matched_names
    assert "elf blessing" in matched_names
    assert "giant growth" not in matched_names


@patch("cli_utils.load_and_filter_cards")
def test_handle_tribal_no_subtypes(mock_load):
    pool = [
        cardlib.Card(C_ELVISH_ARCHDRUID),
        cardlib.Card(C_NO_SUBTYPE)
    ]
    mock_load.return_value = pool

    args = argparse.Namespace(
        query="Nameless Spell",
        infile="dummy.json",
        quiet=False,
        fields="name",
        color=None,
        limit=0,
        reverse=False,
        sort=None,
        delimiter=" | "
    )

    # Should print error and return empty list
    results = handle_tribal(args)
    assert results == []


@patch("cli_utils.load_and_filter_cards")
def test_handle_tribal_double_faced(mock_load):
    pool = [
        cardlib.Card(C_DF_CARD),
        cardlib.Card(C_ELVISH_ARCHDRUID), # shares 'Elf' on front side
        cardlib.Card(C_LLANOWAR_ELVES),   # shares 'Elf' on front side
        cardlib.Card(C_ELF_BLESSING),     # mentions 'Elf' on front
        cardlib.Card(C_GIANT_GROWTH)
    ]
    mock_load.return_value = pool

    # Target is C_DF_CARD which has front 'Elf' and back 'Merfolk'
    args = argparse.Namespace(
        query="Double Front",
        infile="dummy.json",
        quiet=True,
        fields="name",
        color=None,
        limit=0,
        reverse=False,
        sort=None,
        delimiter=" | "
    )

    results = handle_tribal(args)
    matched_names = [c.name.lower() for c in results]

    assert "elvish archdruid" in matched_names
    assert "llanowar elves" in matched_names
    assert "elf blessing" in matched_names
    assert "giant growth" not in matched_names
