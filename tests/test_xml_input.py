import os
import sys

# Ensure lib is in path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import jdecode

def test_mtg_open_xml_content_basic():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<cockatrice_carddatabase version="4">
  <cards>
    <card>
      <name>Grizzly Bears</name>
      <manacost>1G</manacost>
      <type>Creature — Bear</type>
      <pt>2/2</pt>
      <text>Some text.</text>
      <rarity>Common</rarity>
    </card>
  </cards>
</cockatrice_carddatabase>"""

    srcs, bad_sets = jdecode.mtg_open_xml_content(xml_text)
    assert "grizzly bears" in srcs
    card_dict = srcs["grizzly bears"][0]
    assert card_dict['name'] == "Grizzly Bears"
    assert card_dict['manaCost'] == "{1}{G}"
    assert card_dict['power'] == "2"
    assert card_dict['toughness'] == "2"
    assert card_dict['rarity'] == "Common"
    assert 'Creature' in card_dict['types']
    assert 'Bear' in card_dict['subtypes']

def test_mtg_open_xml_content_planeswalker():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<cockatrice_carddatabase version="4">
  <cards>
    <card>
      <name>Jace</name>
      <manacost>2UU</manacost>
      <type>Legendary Planeswalker — Jace</type>
      <pt>3</pt>
      <text>PW text</text>
      <rarity>Mythic</rarity>
    </card>
  </cards>
</cockatrice_carddatabase>"""

    srcs, bad_sets = jdecode.mtg_open_xml_content(xml_text)
    card_dict = srcs["jace"][0]
    assert card_dict['loyalty'] == "3"
    assert 'Planeswalker' in card_dict['types']

def test_mtg_open_xml_content_battle():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<cockatrice_carddatabase version="4">
  <cards>
    <card>
      <name>Invasion</name>
      <manacost>WUBRG</manacost>
      <type>Battle — Siege</type>
      <pt>7</pt>
      <text>Battle text</text>
      <rarity>Rare</rarity>
    </card>
  </cards>
</cockatrice_carddatabase>"""

    srcs, bad_sets = jdecode.mtg_open_xml_content(xml_text)
    card_dict = srcs["invasion"][0]
    assert card_dict['defense'] == "7"
    assert 'Battle' in card_dict['types']

def test_mtg_open_xml_content_invalid_xml():
    xml_text = "not xml"
    srcs, bad_sets = jdecode.mtg_open_xml_content(xml_text)
    assert srcs == {}

def test_mtg_open_file_xml(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    f = d / "test.xml"
    f.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<cockatrice_carddatabase version="4">
  <cards>
    <card>
      <name>Test Card</name>
      <manacost>U</manacost>
      <type>Instant</type>
      <text>Counter target spell.</text>
    </card>
  </cards>
</cockatrice_carddatabase>""", encoding='utf8')

    cards = jdecode.mtg_open_file(str(f))
    assert len(cards) == 1
    assert cards[0].name == "test card"
    assert "instant" in cards[0].types

def test_mtg_open_file_directory_with_xml(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    f1 = d / "c1.json"
    f1.write_text('{"name": "Json Card", "types": ["Artifact"]}', encoding='utf8')
    f2 = d / "c2.xml"
    f2.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<cockatrice_carddatabase version="4">
  <cards>
    <card>
      <name>XML Card</name>
      <type>Sorcery</type>
    </card>
  </cards>
</cockatrice_carddatabase>""", encoding='utf8')

    cards = jdecode.mtg_open_file(str(d))
    names = [c.name for c in cards]
    assert "json card" in names
    assert "xml card" in names
