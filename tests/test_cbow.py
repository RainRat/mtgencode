
import pytest
import os
import struct
import sys
import tempfile
import numpy as np

# Adjust path to import lib
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

import cbow
from cbow import CBOW, read_vector_file, makevector, cosine_similarity
from cardlib import Card

@pytest.fixture
def mock_cbow_files():
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        bin_path = os.path.join(tmpdir, 'cbow.bin')
        txt_path = os.path.join(tmpdir, 'output.txt')

        # Create cbow.bin
        words = 2
        size = 3
        # Header: 4 bytes words, 4 bytes size. Assumed to be text based on int(f.read(4)) usage
        # e.g. "   2" and "   3"
        header = f"{words:<4}{size:<4}".encode('ascii')

        # Word 1: "foo" + space
        w1 = b"foo "
        # Vector 1: [1.0, 0.0, 0.0] (float32)
        v1 = struct.pack('f'*size, 1.0, 0.0, 0.0)

        # Word 2: "bar" + space
        w2 = b"bar "
        # Vector 2: [0.0, 1.0, 0.0] (float32)
        v2 = struct.pack('f'*size, 0.0, 1.0, 0.0)

        with open(bin_path, 'wb') as f:
            f.write(header)
            f.write(w1)
            f.write(v1)
            f.write(w2)
            f.write(v2)

        # Create output.txt (encoded cards) using labeled format
        card1 = "|1card_foo|9foo"
        card2 = "|1card_bar|9bar"

        with open(txt_path, 'w') as f:
            f.write(card1 + "\n\n" + card2)

        yield bin_path, txt_path

def test_read_vector_file(mock_cbow_files):
    bin_path, _ = mock_cbow_files

    # This is expected to fail with current code on Python 3
    vocab, vecs = read_vector_file(bin_path)

    assert len(vocab) == 2
    assert vocab[0] == 'foo'
    assert vocab[1] == 'bar'
    assert len(vecs) == 2
    assert len(vecs[0]) == 3
    # Check normalized vectors
    assert np.allclose(vecs[0], [1.0, 0.0, 0.0])
    assert np.allclose(vecs[1], [0.0, 1.0, 0.0])

def test_makevector():
    vocab = ['foo', 'bar']
    vecs = [[1.0, 0.0], [0.0, 1.0]]

    # 'foo' -> [1, 0]
    v = makevector(vocab, vecs, "foo")
    assert np.allclose(v, [1.0, 0.0])

    # 'foo bar' -> sum([1,0], [0,1]) -> [1,1] -> normalized -> [1/sqrt(2), 1/sqrt(2)]
    v = makevector(vocab, vecs, "foo bar")
    expected = np.array([1.0, 1.0])
    expected /= np.linalg.norm(expected)
    assert np.allclose(v, expected)

    # Unknown word
    v = makevector(vocab, vecs, "baz")
    assert np.allclose(v, [0.0, 0.0])

def test_cosine_similarity():
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    # Orthogonal
    assert abs(cosine_similarity(v1, v2)) < 1e-6

    v3 = [1.0, 0.0]
    # Identical
    assert abs(cosine_similarity(v1, v3) - 1.0) < 1e-6

    v4 = [-1.0, 0.0]
    # Opposite
    assert abs(cosine_similarity(v1, v4) - (-1.0)) < 1e-6

def test_cbow_init(mock_cbow_files):
    bin_path, txt_path = mock_cbow_files

    model = CBOW(verbose=False, vector_fname=bin_path, card_fname=txt_path)

    assert not model.disabled
    assert len(model.vocab) == 2
    assert len(model.vecs) == 2

def test_cbow_nearest(mock_cbow_files):
    bin_path, txt_path = mock_cbow_files
    model = CBOW(verbose=False, vector_fname=bin_path, card_fname=txt_path)

    # Test nearest with a string
    # "foo" should be most similar to "card_foo"
    results = model.nearest("foo", n=1)
    assert len(results) == 1
    assert results[0][1] == "card_foo"

    # Test nearest with a Card object
    card = Card("|1card_foo|9foo")
    results = model.nearest(card, n=1)
    assert len(results) == 1
    assert results[0][1] == "card_foo"

def test_cbow_nearest_par(mock_cbow_files):
    bin_path, txt_path = mock_cbow_files
    model = CBOW(verbose=False, vector_fname=bin_path, card_fname=txt_path)

    # Test nearest_par
    results = model.nearest_par(["foo", "bar"], n=1)
    assert len(results) == 2
    assert len(results[0]) == 1
    assert results[0][0][1] == "card_foo"
    assert len(results[1]) == 1
    assert results[1][0][1] == "card_bar"
