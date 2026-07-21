import pytest
import tempfile
import os
import sys

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import jdecode
import cardlib

def test_markdown_table_import():
    table_content = """
| Name | Cost | Type | Stats | Rarity | Rules Text |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Grizzly Bears | {1}{G} | Creature - Bear | 2/2 | Common | |
| Elite Vanguard | {W} | Creature - Human Soldier | 2/1 | Uncommon | |
| Lightning Bolt | {R} | Instant | | Common | Lightning Bolt deals &^^^ damage to any target. |
| Fire // Ice | {1}{R} // {1}{U} | Instant // Instant | | Rare | Fire deals &^^ damage divided as you choose among one or two targets. // Tap target permanent.\\nDraw a card. |
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mdt', delete=False, encoding='utf-8') as tf:
        tf.write(table_content)
        tf_path = tf.name

    try:
        cards = jdecode.mtg_open_file(tf_path, verbose=True)
        assert len(cards) == 4

        # Test standard card
        gb = next(c for c in cards if c.name.lower() == 'grizzly bears')
        assert gb.cost.format() == '{1}{G}'
        assert gb.rarity_name == 'common'
        assert 'creature' in gb.types
        assert 'bear' in gb.subtypes
        assert gb.get_pt_display(include_parens=False) == '2/2'

        # Test split card
        fire_ice = next(c for c in cards if 'fire' in c.name.lower())
        assert fire_ice.bside is not None
        assert fire_ice.name.lower() == 'fire'
        assert fire_ice.cost.format() == '{1}{R}'
        assert fire_ice.bside.name.lower() == 'ice'
        assert fire_ice.bside.cost.format() == '{1}{U}'
    finally:
        os.remove(tf_path)

def test_markdown_text_import():
    text_content = """
**Elite Vanguard** {W} (uncommon)
Creature — Human Soldier (uncommon)
(2/1)

---

**Fire** {1}{R} (rare)
Instant (rare)
Fire deals &^^ damage divided as you choose among one or two targets.

---- B-Side -------------------
**Ice** {1}{U}
Instant
Tap target permanent.
Draw a card.
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tf:
        tf.write(text_content)
        tf_path = tf.name

    try:
        cards = jdecode.mtg_open_file(tf_path, verbose=True)
        assert len(cards) == 2

        ev = next(c for c in cards if c.name.lower() == 'elite vanguard')
        assert ev.cost.format() == '{W}'
        assert ev.rarity_name == 'uncommon'
        assert 'creature' in ev.types
        assert 'human' in ev.subtypes
        assert 'soldier' in ev.subtypes
        assert ev.get_pt_display(include_parens=False) == '2/1'

        fire = next(c for c in cards if c.name.lower() == 'fire')
        assert fire.bside is not None
        assert fire.bside.name.lower() == 'ice'
        assert fire.bside.cost.format() == '{1}{U}'
        assert 'Tap target permanent.' in fire.bside.get_text(force_unpass=True)
    finally:
        os.remove(tf_path)
