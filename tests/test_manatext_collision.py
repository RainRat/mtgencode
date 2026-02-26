import pytest
from lib.manalib import Manatext
from lib import utils

def test_manatext_placeholder_collision():
    # utils.reserved_mana_marker is '$'
    src = "Costs $10. {W}"
    # When initialized, {W} is replaced by '$'
    # So internal text becomes "Costs $10. $"
    mt = Manatext(src, fmt='json')

    # When formatting, the first '$' is replaced by the first cost ({W})
    # Resulting in "Costs {W}10. $" instead of "Costs $10. {W}"
    formatted = mt.format()

    # This assertion is expected to FAIL before the fix
    assert formatted == "Costs $10. {W}"

def test_manatext_multiple_collisions():
    src = "$1 and $2. {W} {U}"
    mt = Manatext(src, fmt='json')

    formatted = mt.format()
    assert formatted == "$1 and $2. {W} {U}"

def test_manatext_encode_collision():
    src = "Costs $10. {W}"
    mt = Manatext(src, fmt='json')

    # encode() should also handle the collision
    encoded = mt.encode()
    assert encoded == "Costs $10. {WW}" # {W} is encoded as {WW}

def test_manatext_str_collision():
    src = "Costs $10. {W}"
    mt = Manatext(src, fmt='json')

    assert str(mt) == "Costs $10. {W}"
