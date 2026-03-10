import sys
import os
import pytest

# Add lib directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
from utils import Ansi, rarity_uncommon_marker, rarity_rare_marker, rarity_mythic_marker, rarity_common_marker

def test_get_rarity_color_names():
    assert Ansi.get_rarity_color('uncommon') == Ansi.BOLD + Ansi.CYAN
    assert Ansi.get_rarity_color('rare') == Ansi.BOLD + Ansi.YELLOW
    assert Ansi.get_rarity_color('mythic') == Ansi.BOLD + Ansi.RED
    assert Ansi.get_rarity_color('mythic rare') == Ansi.BOLD + Ansi.RED
    assert Ansi.get_rarity_color('common') == Ansi.BOLD

def test_get_rarity_color_markers():
    # These are expected to fail currently due to the bug
    assert Ansi.get_rarity_color(rarity_uncommon_marker) == Ansi.BOLD + Ansi.CYAN
    assert Ansi.get_rarity_color(rarity_rare_marker) == Ansi.BOLD + Ansi.YELLOW
    assert Ansi.get_rarity_color(rarity_mythic_marker) == Ansi.BOLD + Ansi.RED
    assert Ansi.get_rarity_color(rarity_common_marker) == Ansi.BOLD

def test_get_rarity_color_edge_cases():
    assert Ansi.get_rarity_color(None) == Ansi.BOLD
    assert Ansi.get_rarity_color('') == Ansi.BOLD
    assert Ansi.get_rarity_color('unknown') == Ansi.BOLD
