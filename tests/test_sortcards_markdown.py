import pytest
import os
import sys

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import sortcards
import cardlib
import utils

def test_markdown_output_format(tmp_path):
    # Test that Markdown output uses <details> and <summary> tags
    # and that cards are formatted as Markdown
    card_data = {
        "name": "Markdown Card",
        "manaCost": "{1}{W}",
        "types": ["Creature"],
        "subtypes": ["Human"],
        "power": "1",
        "toughness": "1",
        "text": "Lifelink",
        "rarity": "common"
    }
    card = cardlib.Card(card_data)

    infile = tmp_path / "input.json"
    import json
    infile.write_text(json.dumps({"data": {"TST": {"name": "Test", "code": "TST", "type": "expansion", "cards": [card_data]}}}), encoding="utf-8")

    outfile = tmp_path / "output.md"

    # Run sortcards main
    sortcards.main(str(infile), str(outfile), use_markdown=True, quiet=True, verbose=False)

    content = outfile.read_text(encoding="utf-8")
    assert "<details><summary>" in content
    assert "</details>" in content
    assert "**Markdown Card**" in content
    assert "Creature ~ Human" in content
    assert "(1/1)" in content

def test_markdown_auto_detection(tmp_path):
    # Test that .md extension triggers Markdown mode automatically
    card_data = {
        "name": "Auto MD Card",
        "types": ["Instant"],
        "rarity": "rare"
    }

    infile = tmp_path / "input.json"
    import json
    infile.write_text(json.dumps({"data": {"TST": {"name": "Test", "code": "TST", "type": "expansion", "cards": [card_data]}}}), encoding="utf-8")

    outfile = tmp_path / "auto.md"

    # Run sortcards main without explicit use_markdown=True
    sortcards.main(str(infile), str(outfile), quiet=True, verbose=False)

    content = outfile.read_text(encoding="utf-8")
    assert "<details><summary>" in content
    assert "**Auto Md Card**" in content

def test_markdown_summary_mode(tmp_path):
    # Test that --summary flag still produces summaries even in Markdown mode
    card_data = {
        "name": "Summary MD Card",
        "manaCost": "{U}",
        "types": ["Sorcery"],
        "rarity": "common"
    }

    infile = tmp_path / "input.json"
    import json
    infile.write_text(json.dumps({"data": {"TST": {"name": "Test", "code": "TST", "type": "expansion", "cards": [card_data]}}}), encoding="utf-8")

    outfile = tmp_path / "summary.md"

    # Run sortcards main with both summary and markdown
    sortcards.main(str(infile), str(outfile), use_markdown=True, use_summary=True, quiet=True, verbose=False)

    content = outfile.read_text(encoding="utf-8")
    assert "<details><summary>" in content
    # Card should be a summary line, not full format
    # Summary includes rarity indicator [C] and titlecase "Md"
    assert "Summary Md Card {U} \u2022 Sorcery" in content
    assert "**Summary Md Card**" not in content

def test_markdown_no_cards(tmp_path):
    # Test that headers are not printed if no cards match
    infile = tmp_path / "empty.json"
    import json
    infile.write_text(json.dumps({"data": {"TST": {"name": "Test", "code": "TST", "type": "expansion", "cards": []}}}), encoding="utf-8")

    outfile = tmp_path / "empty.md"

    sortcards.main(str(infile), str(outfile), use_markdown=True, quiet=True, verbose=False)

    content = outfile.read_text(encoding="utf-8")
    assert content.strip() == ""
