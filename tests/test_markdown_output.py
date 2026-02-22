import pytest
import sys
import os
from io import StringIO

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
