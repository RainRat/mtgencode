import sys
import os
import pytest

libdir = os.path.join(os.getcwd(), 'lib')
sys.path.append(libdir)
import cardlib
import decode

def test_card_to_cockatrice_xml():
    card_json = {
        "name": "Testing Card",
        "manaCost": "{1}{W}{U}",
        "types": ["Creature"],
        "subtypes": ["Angel"],
        "power": "&^^",
        "toughness": "&^^^",
        "text": "Flying\nWhen this enters, draw a card.",
        "rarity": "rare",
        "setCode": "TST"
    }
    card = cardlib.Card(card_json)
    xml = card.to_cockatrice_xml()

    assert "<name>Testing Card</name>" in xml
    assert "<set>TST</set>" in xml
    assert "<color>UW</color>" in xml
    assert "<manacost>1WU</manacost>" in xml
    assert "<type>Creature — Angel</type>" in xml
    assert "<pt>2/3</pt>" in xml
    assert "<tablerow>2</tablerow>" in xml
    assert "Flying" in xml
    assert "draw a card" in xml

def test_decode_xml_output():
    # Use a real file if available or a temp one
    infile = "testdata/uthros.json"
    outfile = "test_output.xml"

    # Run decode main with xml_out=True
    decode.main(infile, oname=outfile, xml_out=True, verbose=False)

    assert os.path.exists(outfile)
    with open(outfile, 'r') as f:
        content = f.read()

    assert '<?xml version="1.0" encoding="UTF-8"?>' in content
    assert '<cockatrice_carddatabase version="4">' in content
    assert '<sets>' in content
    assert '<set>' in content
    assert '<name>EOC</name>' in content
    assert '<cards>' in content
    assert '<card>' in content
    assert '<name>Uthros Research Craft</name>' in content
    assert '</card>' in content
    assert '</cards>' in content
    assert '</cockatrice_carddatabase>' in content

    os.remove(outfile)

if __name__ == "__main__":
    pytest.main([__file__])
