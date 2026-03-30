
import pytest
import sys
import os

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

from datalib import Datamine, get_col_widths, padrows, get_bar_chart, _print_mechanical_profile, _print_breakdown, _print_color_pie
from cardlib import Card
import utils

def test_get_col_widths_empty():
    # Line 10 coverage
    assert get_col_widths([]) == []

def test_padrows_empty():
    # Line 30 coverage
    assert padrows([]) == []

def test_get_bar_chart_minimal_percent():
    # Line 128 coverage: filled = 1 if filled == 0 and percent > 0
    # bar_width is 10. percent / 100 * 10 = 0.1. round(0.1) = 0.
    bar = get_bar_chart(1, use_color=False)
    assert '█' in bar
    assert bar.count('█') == 1

def test_summarize_with_search_stats(capsys):
    # Line 493-515 coverage
    search_stats = {'matched': 10, 'filtered': 5}
    dm = Datamine([], search_stats=search_stats)
    dm.summarize(use_color=True)
    output = capsys.readouterr().out
    assert "SEARCH STATISTICS" in output
    assert "Matched" in output
    assert "Filtered Out" in output

def test_print_breakdown_mechanic_header(capsys):
    # Line 177-178 coverage
    _print_breakdown('Breakdown by mechanic:', {'Flying': [None]}, 1, False)
    output = capsys.readouterr().out
    assert "Mechanic" in output

def test_print_mechanical_profile_partial_stats(capsys):
    # Line 245, 247 coverage
    # Need to manually mess with mechanical_stats to trigger these because Card usually has both or neither
    dm = Datamine([{"name": "Test", "types": ["Creature"], "text": "Flying", "rarity": "Common", "pt": "1/1"}])
    dm.mechanical_stats['Flying']['avg_toughness'] = None
    _print_mechanical_profile(dm.mechanical_stats, 1, False)
    output = capsys.readouterr().out
    assert "1.0/?" in output

    dm.mechanical_stats['Flying']['avg_power'] = None
    dm.mechanical_stats['Flying']['avg_toughness'] = 1.0
    _print_mechanical_profile(dm.mechanical_stats, 1, False)
    output = capsys.readouterr().out
    assert "?/1.0" in output

def test_print_color_pie_dominant_color_direct(capsys):
    # Line 306-309 coverage
    pie_groups = {c: 10 for c in 'WUBRGAM'}
    pie_mechanics = {c: {'Flying': 0} for c in 'WUBRGAM'}
    pie_mechanics['W']['Flying'] = 10 # 100% in White, 0% elsewhere
    all_mechanics = {'Flying': [None]*10}

    _print_color_pie(pie_groups, pie_mechanics, all_mechanics, use_color=True)
    output = capsys.readouterr().out
    # Check for Underline ANSI code \033[4m
    assert "\033[4m" in output

    # Test line 307 (non-dominant but > 0 with color)
    pie_mechanics['U']['Flying'] = 5 # 50% in Blue
    capsys.readouterr() # clear
    _print_color_pie(pie_groups, pie_mechanics, all_mechanics, use_color=True)
    output = capsys.readouterr().out
    # Both should be present. Blue should have Cyan code \033[96m but NOT underline \033[4m
    assert "\033[96m" in output
    assert "\033[96m\033[4m" not in output # Blue is not dominant

    # Test line 309 (no color, but > 0)
    capsys.readouterr() # clear
    _print_color_pie(pie_groups, pie_mechanics, all_mechanics, use_color=False)
    output = capsys.readouterr().out
    assert " 100%" in output
    assert "  50%" in output

def test_outliers_duplicate_names_limit(capsys):
    # Line 653 coverage: break when rows >= vsize
    cards = [
        {"name": "A", "types": ["Land"], "rarity": "Common"},
        {"name": "A", "types": ["Land"], "rarity": "Common"},
        {"name": "B", "types": ["Land"], "rarity": "Common"},
        {"name": "B", "types": ["Land"], "rarity": "Common"}
    ]
    dm = Datamine(cards)
    # Set vsize to 1
    dm.outliers(vsize=1, use_color=False)
    output = capsys.readouterr().out

    assert "Most duplicated names:" in output
    import re
    assert re.search(r'^\s+a\s+2', output, re.MULTILINE)
    assert not re.search(r'^\s+b\s+2', output, re.MULTILINE)
