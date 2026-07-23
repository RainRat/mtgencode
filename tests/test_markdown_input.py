import os
import sys
import tempfile

# Ensure lib is in path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import jdecode

def test_mtg_open_markdown_table_basic():
    md_text = """
| Name | Cost | CMC | Type | Stats | Rarity | Mechanics | Rules Text |
| :--- | :--- | ---: | :--- | ---: | :--- | :--- | :--- |
| Grizzly Bears | {1}{G} | 2.0 | Creature — Bear | 2/2 | Common | | Grizzly bears are common. |
| Serra Angel | {3}{W}{W} | 5.0 | Creature — Angel | 4/4 | Uncommon | Flying, Vigilance | Vigilance, flying |
"""
    srcs, bad_sets = jdecode.mtg_open_markdown_content(md_text)
    assert "grizzly bears" in srcs
    assert "serra angel" in srcs

    bear = srcs["grizzly bears"][0]
    assert bear['name'] == "Grizzly Bears"
    assert bear['manaCost'] == "{1}{G}"
    assert bear['power'] == "2"
    assert bear['toughness'] == "2"
    assert bear['rarity'] == "Common"

    angel = srcs["serra angel"][0]
    assert angel['name'] == " Serra Angel" or angel['name'] == "Serra Angel"
    assert angel['manaCost'] == "{3}{W}{W}"
    assert angel['power'] == "4"
    assert angel['toughness'] == "4"
    assert angel['rarity'] == "Uncommon"

def test_mtg_open_markdown_table_escaped_pipe():
    md_text = """
| Name | Cost | Type | Stats | Rules Text |
| :--- | :--- | :--- | :--- | :--- |
| Test Card | {U} | Instant | | Choice: Choose one \\| Draw a card \\| Return a card. |
"""
    srcs, bad_sets = jdecode.mtg_open_markdown_content(md_text)
    assert "test card" in srcs
    card = srcs["test card"][0]
    assert "Choose one | Draw a card | Return a card" in card['text']

def test_mtg_open_markdown_table_multi_face():
    md_text = """
| Name | Cost | Type | Stats | Rules Text |
| :--- | :--- | :--- | :--- | :--- |
| Fire // Ice | {R} // {U} | Instant // Instant | | Fire deals 2 damage. // Ice draws a card. |
"""
    srcs, bad_sets = jdecode.mtg_open_markdown_content(md_text)
    assert "fire" in srcs
    card = srcs["fire"][0]
    assert card['name'] == "Fire"
    assert card['manaCost'] == "{R}"

    bside = card['bside']
    assert bside['name'] == "Ice"
    assert bside['manaCost'] == "{U}"
    assert bside['text'] == "Ice draws a card."

def test_mtg_open_markdown_list_basic():
    md_text = """
**Uthros, the Quiet Ruin** {5}{G}{G} (mythic)
Legendary Creature — Elder Beast
7/7
Flying, trample
When Uthros enters the battlefield, draw cards.

**Lightning Bolt** {R} (common)
Instant
Lightning Bolt deals 3 damage to any target.
"""
    srcs, bad_sets = jdecode.mtg_open_markdown_content(md_text)
    assert "uthros, the quiet ruin" in srcs
    assert "lightning bolt" in srcs

    uthros = srcs["uthros, the quiet ruin"][0]
    assert uthros['name'] == "Uthros, the Quiet Ruin"
    assert uthros['manaCost'] == "{5}{G}{G}"
    assert uthros['power'] == "7"
    assert uthros['toughness'] == "7"
    assert uthros['rarity'] == "mythic"
    assert uthros['text'] == "Flying, trample\nWhen Uthros enters the battlefield, draw cards."

def test_mtg_open_markdown_list_multi_face():
    md_text = """
[**Fire // Ice**](url) {R} // {U} (rare)
Instant // Instant
Fire deals damage. // Ice draws a card.
"""
    srcs, bad_sets = jdecode.mtg_open_markdown_content(md_text)
    assert "fire" in srcs
    card = srcs["fire"][0]
    assert card['name'] == "Fire"
    assert card['manaCost'] == "{R}"

    bside = card['bside']
    assert bside['name'] == "Ice"
    assert bside['manaCost'] == "{U}"

def test_mtg_open_file_markdown_table(tmp_path):
    f = tmp_path / "test.md"
    f.write_text("""
| Name | Cost | Type | Stats | Rarity | Rules Text |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Grizzly Bears | {1}{G} | Creature — Bear | 2/2 | Common | Grizzly bears. |
""", encoding='utf8')

    cards = jdecode.mtg_open_file(str(f))
    assert len(cards) == 1
    assert cards[0].name == "grizzly bears"
    assert cards[0].rarity == "O"
