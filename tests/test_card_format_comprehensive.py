import pytest
from lib.cardlib import Card
from lib import utils

def test_card_summary_all_colors():
    # White
    card_w = Card({"name": "White Card", "manaCost": "{W}", "types": ["Enchantment"], "rarity": "Common"})
    summary_w = card_w.summary(ansi_color=True)
    assert utils.Ansi.WHITE in summary_w

    # Blue
    card_u = Card({"name": "Blue Card", "manaCost": "{U}", "types": ["Instant"], "rarity": "Common"})
    summary_u = card_u.summary(ansi_color=True)
    assert utils.Ansi.CYAN in summary_u

    # Black
    card_b = Card({"name": "Black Card", "manaCost": "{B}", "types": ["Sorcery"], "rarity": "Common"})
    summary_b = card_b.summary(ansi_color=True)
    assert utils.Ansi.MAGENTA in summary_b

    # Red
    card_r = Card({"name": "Red Card", "manaCost": "{R}", "types": ["Creature"], "rarity": "Common", "pt": "1/1"})
    summary_r = card_r.summary(ansi_color=True)
    assert utils.Ansi.RED in summary_r

    # Green
    card_g = Card({"name": "Green Card", "manaCost": "{G}", "types": ["Land"], "rarity": "Common"})
    summary_g = card_g.summary(ansi_color=True)
    assert utils.Ansi.GREEN in summary_g

    # Multicolored
    card_multi = Card({"name": "Multi Card", "manaCost": "{W}{U}", "types": ["Creature"], "rarity": "Common", "pt": "2/2"})
    summary_multi = card_multi.summary(ansi_color=True)
    assert utils.Ansi.YELLOW in summary_multi

    # Colorless (non-land) -> Cyan
    card_colorless = Card({"name": "Artifact Card", "manaCost": "{1}", "types": ["Artifact"], "rarity": "Common"})
    summary_colorless = card_colorless.summary(ansi_color=True)
    assert utils.Ansi.CYAN in summary_colorless

    # Land -> just BOLD
    card_land = Card({"name": "Plain Land", "types": ["Land"], "rarity": "Common"})
    summary_land = card_land.summary(ansi_color=True)
    assert utils.Ansi.BOLD in summary_land
    assert utils.Ansi.CYAN not in summary_land.split(utils.Ansi.BOLD)[1] # Check that no other color was added to name

def test_battle_formatting():
    card_json = {
        "name": "Invasion of Alara",
        "manaCost": "{W}{U}{B}{R}{G}",
        "type": "Battle — Siege",
        "types": ["Battle"],
        "subtypes": ["Siege"],
        "rarity": "Rare",
        "text": "When Invasion of Alara enters the battlefield, reveal cards from the top of your library...",
        "loyalty": "7"
    }
    card = Card(card_json)

    # Summary
    summary = card.summary()
    assert "[[7]]" in summary

    # Format default
    fmt = card.format()
    assert "[[7]]" in fmt

    # Format gatherer
    fmt_g = card.format(gatherer=True)
    assert "[[7]]" in fmt_g

def test_format_variants():
    card_json = {
        "name": "Variant Card",
        "manaCost": "{2}{U}",
        "types": ["Instant"],
        "rarity": "Uncommon",
        "text": "Draw two cards."
    }
    card = Card(card_json)

    # Markdown
    fmt_md = card.format(for_md=True)
    assert "**Variant Card**" in fmt_md
    assert "Draw two cards." in fmt_md

    # Forum
    fmt_forum = card.format(for_forum=True)
    assert "[b]Variant Card[/b]" in fmt_forum

    # HTML
    fmt_html = card.format(for_html=True)
    assert '<div class="card-text">' in fmt_html
    assert '<b>Variant Card</b>' in fmt_html

    # HTML + Forum
    fmt_both = card.format(for_html=True, for_forum=True)
    assert '[F]' in fmt_both
    assert 'hover_img' in fmt_both

def test_format_ansi_rarities():
    base_json = {"name": "Test", "types": ["Instant"]}

    # Common
    card_c = Card({**base_json, "rarity": "Common"})
    fmt_c = card_c.format(ansi_color=True)
    assert utils.Ansi.BOLD in fmt_c

    # Uncommon
    card_u = Card({**base_json, "rarity": "Uncommon"})
    fmt_u = card_u.format(ansi_color=True)
    assert utils.Ansi.CYAN in fmt_u

    # Rare
    card_r = Card({**base_json, "rarity": "Rare"})
    fmt_r = card_r.format(ansi_color=True)
    assert utils.Ansi.YELLOW in fmt_r

    # Mythic
    card_m = Card({**base_json, "rarity": "Mythic Rare"})
    fmt_m = card_m.format(ansi_color=True)
    assert utils.Ansi.RED in fmt_m

def test_vdump_and_other():
    # Trigger field_other by providing duplicate fields in encoded text
    # The Card constructor handles multiple fields by putting subsequent ones into field_other
    # We need to make sure we use fmt_ordered that includes the field twice or just let it fall through

    # If we have more fields than fmt_ordered, they go to field_other.
    encoded = "|Variant Card|Instant|{2}{U}|Extra Field|"
    # Default fmt_ordered is name, supertypes, types, loyalty, subtypes, rarity, pt, cost, text
    # We provide 4 fields.
    # 1: Variant Card (name)
    # 2: Instant (supertypes) -> wait, supertypes is empty normally.
    # Actually, it depends on the format.

    from lib.cardlib import field_name, field_supertypes, field_types, field_cost, field_other
    custom_fmt = [field_name, field_types, field_cost]
    card = Card(encoded, fmt_ordered=custom_fmt)

    assert len(getattr(card, field_other)) > 0

    fmt_vdump = card.format(vdump=True)
    assert "_INVALID_" in fmt_vdump
    assert "(3) Extra Field" in fmt_vdump # 3 is the index of "Extra Field"

    # Test vdump with Markdown and HTML other formatting
    assert "_" in card.format(vdump=True, for_md=True)
    assert "<i>" in card.format(vdump=True, for_html=True)
    assert "[i]" in card.format(vdump=True, for_forum=True)

def test_gatherer_visual_spoiler():
    card = Card({"name": "Vis-Spoi", "rarity": "Rare", "types": ["Creature"], "pt": "2/2", "manaCost": "{2}{R}"})
    fmt = card.format(gatherer=True)
    assert "Vis-Spoi {2}{R} (rare)" in fmt
    assert "Creature (2/2)" in fmt
