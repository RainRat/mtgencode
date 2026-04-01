
import pytest
import os
import struct
import tempfile
import numpy as np
from cbow import CBOW, read_vector_file, f_nearest
from cardlib import Card

def test_read_vector_file_malformed_header():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        # Header with only one part
        tmp.write(b"10\n")
        tmp_path = tmp.name

    try:
        with pytest.raises(struct.error, match="Invalid header format"):
            read_vector_file(tmp_path)
    finally:
        os.remove(tmp_path)

def test_f_nearest_empty_input():
    # vocab, vecs, cardvecs, n
    vocab = ["foo"]
    vecs = [[1.0, 0.0]]
    cardvecs = [("card_foo", [1.0, 0.0])]

    # Empty string should return []
    assert f_nearest("", vocab, vecs, cardvecs, 5) == []

    # Card with no vectorizable content (if possible)
    # Most cards have names, but let's try a blank card
    card = Card("")
    assert f_nearest(card, vocab, vecs, cardvecs, 5) == []

def test_f_nearest_bside_recursion():
    vocab = ["fire", "ice"]
    vecs = [[1.0, 0.0], [0.0, 1.0]]
    # Simplified cardvecs
    cardvecs = [("fire", [1.0, 0.0]), ("ice", [0.0, 1.0])]

    # Create a split card
    # Fire // Ice
    card_src = "|1fire|9fire\n\n|1ice|9ice"
    card = Card(card_src)
    assert card.bside is not None

    # f_nearest(card, ...) should call f_nearest(card.bside, ...)
    results = f_nearest(card, vocab, vecs, cardvecs, n=1)

    # Should contain matches for both sides
    names = [r[1] for r in results]
    assert "fire" in names
    assert "ice" in names

def test_cbow_disabled_missing_card_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        bin_path = os.path.join(tmpdir, 'cbow.bin')
        txt_path = os.path.join(tmpdir, 'missing.txt')

        # Valid bin file
        with open(bin_path, 'wb') as f:
            f.write(b"1 1\nfoo \x00\x00\x80\x3f") # "foo" and [1.0]

        model = CBOW(verbose=False, vector_fname=bin_path, card_fname=txt_path)
        assert model.disabled is True
        assert model.nearest("foo") == []
        assert model.nearest_par(["foo"]) == [[]]

def test_cbow_disabled_malformed_bin_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        bin_path = os.path.join(tmpdir, 'malformed.bin')
        txt_path = os.path.join(tmpdir, 'output.txt')

        # Malformed bin file (header triggers struct.error)
        with open(bin_path, 'wb') as f:
            f.write(b"bad header\n")

        with open(txt_path, 'w') as f:
            f.write("|1foo|9foo")

        model = CBOW(verbose=False, vector_fname=bin_path, card_fname=txt_path)
        assert model.disabled is True
