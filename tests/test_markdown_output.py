import sys
import os

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import cardlib
import decode

def test_markdown_format():
    src = "|1Markdown Card|5Creature|6Human|3{W}|81/1|9Lifelink"
    card = cardlib.Card(src)
    formatted = card.format(for_md=True)
    assert "**Markdown Card**" in formatted
    assert "Creature ~ Human" in formatted
    assert "(1/1)" in formatted
    assert "Lifelink" in formatted

def test_decode_markdown_cli(tmp_path):
    infile = tmp_path / "input.txt"
    infile.write_text("|1Markdown Card|5Creature|6Human|3{W}|81/1|9Lifelink", encoding="utf-8")
    outfile = tmp_path / "output.md"

    # Run main via programmatic call
    decode.main(str(infile), str(outfile), md_out=True, quiet=True, verbose=False)

    content = outfile.read_text(encoding="utf-8")
    assert "**Markdown Card**" in content
    assert "Creature — Human (1/1)" in content

def test_decode_markdown_auto_extension(tmp_path):
    infile = tmp_path / "input.txt"
    infile.write_text("|1Auto Card|5Sorcery|9Draw a card.", encoding="utf-8")
    outfile = tmp_path / "output.md"

    # Should detect .md extension
    decode.main(str(infile), str(outfile), quiet=True, verbose=False)

    content = outfile.read_text(encoding="utf-8")
    assert "**Auto Card**" in content

def test_markdown_table_format():
    src = "|1Table Card|5Creature|6Human|3{WW}|8&^/&^|9Lifelink|0O"
    card = cardlib.Card(src)
    row = card.to_markdown_row()
    # Mechanics "Lifelink" is now present
    assert "| Table Card | {W} | 1 | Creature — Human | 1/1 | common | Lifelink | Lifelink |" in row

def test_markdown_table_split_card():
    src = "|1Fire|5Sorcery|3{RR}|9Fire deals &^^ damage to any target.\n|1Ice|5Sorcery|3{^}{UU}|9Draw a card."
    card = cardlib.Card(src)
    row = card.to_markdown_row()
    # Mechanics "Draw A Card" is now present for Ice
    assert "| Fire // Ice | {R} // {1}{U} | 1 // 2 | Sorcery // Sorcery |  |  | Draw A Card | Fire deals 2 damage to any target.<br>---<br>Draw a card. |" in row

def test_decode_markdown_table_cli(tmp_path):
    infile = tmp_path / "input.txt"
    infile.write_text("|1Table Card|5Creature|6Human|3{WW}|8&^/&^|9Lifelink|0O", encoding="utf-8")
    outfile = tmp_path / "output.mdt"

    # Run main via programmatic call, should detect .mdt extension
    decode.main(str(infile), str(outfile), quiet=True, verbose=False)

    content = outfile.read_text(encoding="utf-8")
    assert "| Name | Cost | CMC | Type | Stats | Rarity | Mechanics | Rules Text |" in content
    assert "| Table Card | {W} | 1 | Creature — Human | 1/1 | common | Lifelink | Lifelink |" in content

def test_decode_markdown_table_flag(tmp_path):
    infile = tmp_path / "input.txt"
    infile.write_text("|1Flag Card|5Sorcery|3{GG}|9Add {GG}.|0A", encoding="utf-8")
    outfile = tmp_path / "output.txt" # Not .mdt

    # Force md_table_out
    decode.main(str(infile), str(outfile), md_table_out=True, quiet=True, verbose=False)

    content = outfile.read_text(encoding="utf-8")
    assert "| Name | Cost | CMC | Type | Stats | Rarity | Mechanics | Rules Text |" in content
    assert "| Flag Card | {G} | 1 | Sorcery |  | rare |  | Add {G}. |" in content
