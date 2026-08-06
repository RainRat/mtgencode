import sys
import os
import io

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

from datalib import (
    Datamine,
    get_col_widths,
    padrows,
    get_bar_chart,
    _print_mechanical_profile,
    _print_breakdown,
    _print_color_pie,
    inc,
    printrows,
    color_count,
    color_line,
    _colorize_header,
    plimit
)

def test_get_col_widths_empty():
    assert get_col_widths([]) == []

def test_padrows_empty():
    assert padrows([]) == []

def test_get_bar_chart_minimal_percent():
    bar = get_bar_chart(1, use_color=False)
    assert '█' in bar
    assert bar.count('█') == 1

def test_summarize_with_search_stats(capsys):
    search_stats = {'matched': 10, 'filtered': 5}
    dm = Datamine([], search_stats=search_stats)
    dm.summarize(use_color=True)
    output = capsys.readouterr().out
    assert "SEARCH STATISTICS" in output
    assert "Matched" in output
    assert "Filtered Out" in output

def test_print_breakdown_mechanic_header(capsys):
    _print_breakdown('Breakdown by mechanic:', {'Flying': [None]}, 1, False)
    output = capsys.readouterr().out
    assert "Mechanic" in output

def test_print_mechanical_profile_partial_stats(capsys):
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
    pie_groups = {c: 10 for c in 'WUBRGAM'}
    pie_mechanics = {c: {'Flying': 0} for c in 'WUBRGAM'}
    pie_mechanics['W']['Flying'] = 10
    all_mechanics = {'Flying': [None]*10}

    _print_color_pie(pie_groups, pie_mechanics, all_mechanics, use_color=True)
    output = capsys.readouterr().out
    assert "\033[4m" in output

    pie_mechanics['U']['Flying'] = 5
    capsys.readouterr()
    _print_color_pie(pie_groups, pie_mechanics, all_mechanics, use_color=True)
    output = capsys.readouterr().out
    assert "\033[96m" in output
    assert "\033[96m\033[4m" not in output

    capsys.readouterr()
    _print_color_pie(pie_groups, pie_mechanics, all_mechanics, use_color=False)
    output = capsys.readouterr().out
    assert " 100%" in output
    assert "  50%" in output

def test_outliers_duplicate_names_limit(capsys):
    cards = [
        {"name": "A", "types": ["Land"], "rarity": "Common"},
        {"name": "A", "types": ["Land"], "rarity": "Common"},
        {"name": "B", "types": ["Land"], "rarity": "Common"},
        {"name": "B", "types": ["Land"], "rarity": "Common"}
    ]
    dm = Datamine(cards)
    dm.outliers(vsize=1, use_color=False)
    output = capsys.readouterr().out

    assert "Most duplicated names:" in output
    import re
    assert re.search(r'^\s+a\s+2', output, re.MULTILINE)
    assert not re.search(r'^\s+b\s+2', output, re.MULTILINE)

def test_inc_helper():
    d = {}
    inc(d, 'key', [1])
    assert d['key'] == [1]
    inc(d, 'key', [2])
    assert d['key'] == [1, 2]
    inc(d, 0, [3])
    assert d[0] == [3]
    inc(d, None, [4])
    assert None not in d

def test_printrows_helper():
    f = io.StringIO()
    printrows(['row1', 'row2'], indent=2, file=f)
    assert f.getvalue() == "  row1\n  row2\n"

def test_color_count_helper():
    assert color_count(0, use_color=True) == "0"
    assert color_count(-1, use_color=True) == "-1"
    assert color_count(5, use_color=False) == "5"
    assert "\033[" in color_count(5, use_color=True)

def test_color_line_helper():
    assert color_line("test", use_color=False) == "test"
    assert "\033[" in color_line("test", use_color=True)

def test_colorize_header_helper():
    assert _colorize_header(["header"], use_color=False) == ["header"]
    res = _colorize_header(["header"], use_color=True)
    assert "\033[" in res[0]

def test_plimit_plain_truncation_helper():
    assert plimit("12345", mlen=3) == "123[...]"

def test_print_breakdown_context_aware_coloring(capsys):
    _print_breakdown('Rarity Breakdown', {'Common': [None]}, 1, use_color=True)
    output = capsys.readouterr().out
    assert "Common" in output
    assert "\033[" in output

    _print_breakdown('Color Breakdown', {'W': [None]}, 1, use_color=True)
    output = capsys.readouterr().out
    assert "W" in output
    assert "\033[" in output

    _print_breakdown('Identity Breakdown', {'B': [None]}, 1, use_color=True)
    output = capsys.readouterr().out
    assert "B" in output
    assert "\033[" in output

    _print_breakdown('Mana Costs Breakdown', {'WW': [None]}, 1, use_color=True)
    output = capsys.readouterr().out
    assert "\033[" in output

    _print_breakdown('P/T Breakdown', {'1/1': [None]}, 1, use_color=True)
    output = capsys.readouterr().out
    assert "1/1" in output
    assert "\033[" in output

    _print_breakdown('Loyalty Breakdown', {'3': [None]}, 1, use_color=True)
    output = capsys.readouterr().out
    assert "3" in output
    assert "\033[" in output

def test_datamine_none_input():
    dm = Datamine([None])
    assert dm.cards == []
