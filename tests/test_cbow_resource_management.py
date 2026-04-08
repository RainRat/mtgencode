
import pytest
import os
import struct
import sys
import tempfile
import multiprocessing
from unittest.mock import patch, MagicMock

# Adjust path to import lib
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

from cbow import CBOW

@pytest.fixture
def mock_cbow_data():
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        bin_path = os.path.join(tmpdir, 'cbow.bin')
        txt_path = os.path.join(tmpdir, 'output.txt')

        # Create cbow.bin
        words = 2
        size = 3
        # Header: words and size
        header = f"{words} {size}\n".encode('ascii')

        # Word 1: "foo" + space
        w1 = b"foo "
        v1 = struct.pack('f'*size, 1.0, 0.0, 0.0)

        # Word 2: "bar" + space
        w2 = b"bar "
        v2 = struct.pack('f'*size, 0.0, 1.0, 0.0)

        with open(bin_path, 'wb') as f:
            f.write(header)
            f.write(w1)
            f.write(v1)
            f.write(w2)
            f.write(v2)

        # Create output.txt
        card1 = "|1card_foo|9foo"
        card2 = "|1card_bar|9bar"

        with open(txt_path, 'w') as f:
            f.write(card1 + "\n\n" + card2)

        yield bin_path, txt_path

def test_cbow_verbose_init(mock_cbow_data, capsys):
    bin_path, txt_path = mock_cbow_data
    # Initialize with verbose=True to cover print statements
    model = CBOW(verbose=True, vector_fname=bin_path, card_fname=txt_path)

    captured = capsys.readouterr()
    assert "Building a cbow model..." in captured.out
    assert "Reading binary vector data from:" in captured.out
    assert "Reading encoded cards from:" in captured.out
    assert "... Done." in captured.out
    assert not model.disabled

def test_cbow_nearest_par_tqdm_fallback(mock_cbow_data):
    bin_path, txt_path = mock_cbow_data
    model = CBOW(verbose=False, vector_fname=bin_path, card_fname=txt_path)

    # patch sys.modules to simulate tqdm being missing
    with patch.dict(sys.modules, {'tqdm': None}):
        results = model.nearest_par(["foo", "bar"], n=1, threads=2)
        assert len(results) == 2
        assert results[0][0][1] == "card_foo"
        assert results[1][0][1] == "card_bar"

def test_cbow_pool_cleanup(mock_cbow_data):
    bin_path, txt_path = mock_cbow_data
    model = CBOW(verbose=False, vector_fname=bin_path, card_fname=txt_path)

    # We want to verify that the pool is closed.
    # Since we use 'with multiprocessing.Pool(threads) as workpool',
    # the pool should be terminated after the block.

    # Mock the Pool context manager
    mock_pool_instance = MagicMock()
    # Configure it to work as a context manager
    mock_pool_instance.__enter__.return_value = mock_pool_instance
    # Return a dummy result from imap
    mock_pool_instance.imap.return_value = [[[ (1.0, "card_foo") ]]]

    with patch('multiprocessing.Pool', return_value=mock_pool_instance) as mock_pool_class:
        model.nearest_par(["foo"], n=1, threads=1)

        # Check that Pool was called
        mock_pool_class.assert_called_once()
        # In a 'with' statement, __enter__ and __exit__ should be called
        assert mock_pool_instance.__enter__.called
        assert mock_pool_instance.__exit__.called

def test_cbow_disabled_paths(tmp_path):
    # Test path where files are missing
    bin_path = str(tmp_path / "nonexistent.bin")
    txt_path = str(tmp_path / "nonexistent.txt")

    model = CBOW(verbose=False, vector_fname=bin_path, card_fname=txt_path)
    assert model.disabled

    # Test methods when disabled
    assert model.nearest("foo") == []
    assert model.nearest_par(["foo"]) == [[]]
