
import pytest
import sys
import os

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

from datalib import add_separator_row

def test_add_separator_row_empty():
    """Verify that add_separator_row handles empty input gracefully."""
    rows = []
    add_separator_row(rows)
    assert rows == []

def test_add_separator_row_default_index():
    """Verify that add_separator_row inserts a separator at the default index 1."""
    rows = [
        ['Header1', 'Header2'],
        ['Data1', 'Data2']
    ]
    add_separator_row(rows)
    # col widths: 7, 7
    assert len(rows) == 3
    assert rows[0] == ['Header1', 'Header2']
    assert rows[1] == ['-------', '-------']
    assert rows[2] == ['Data1', 'Data2']

def test_add_separator_row_custom_index():
    """Verify that add_separator_row inserts a separator at a custom index."""
    rows = [
        ['Header1', 'Header2'],
        ['Data1', 'Data2'],
        ['Total1', 'Total2']
    ]
    # Insert at end
    add_separator_row(rows, index=len(rows))
    assert len(rows) == 4
    assert rows[0] == ['Header1', 'Header2']
    assert rows[1] == ['Data1', 'Data2']
    assert rows[2] == ['Total1', 'Total2']
    assert rows[3] == ['-------', '-------']
