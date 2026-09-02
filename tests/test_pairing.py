import os
import runpy
import sys
from unittest.mock import MagicMock, patch
import pytest

from scripts import pairing


class DummyCost:
    def __init__(self, colors):
        self.colors = colors


class DummyCard:
    def __init__(self, name="Test Card", types=None, colors=None, card_json=None, raw=""):
        self.name = name
        self.types = types or ["Creature"]
        self.cost = DummyCost(colors or ["U"])
        self.json = card_json
        self.raw = raw

    def format(self, gatherer=False, for_forum=True, vdump=True):
        return f"Formatted {self.name}"

    def to_mse(self):
        return f"MSE {self.name}\n"


def test_select_card_filters():
    card = DummyCard()

    # Case 1: nearest > 0.9 -> None
    stats1 = {
        'dists': {'cbow': [0.95]},
        'ngram': {'perp': [1.0], 'perp_per': [1.0], 'perp_max': [5.0]}
    }
    assert pairing.select_card([card], stats1, 0) is None

    # Case 2: perp_per > 2.0 -> None
    stats2 = {
        'dists': {'cbow': [0.5]},
        'ngram': {'perp': [1.0], 'perp_per': [2.5], 'perp_max': [5.0]}
    }
    assert pairing.select_card([card], stats2, 0) is None

    # Case 3: perp_max > 10.0 -> None
    stats3 = {
        'dists': {'cbow': [0.5]},
        'ngram': {'perp': [1.0], 'perp_per': [1.0], 'perp_max': [15.0]}
    }
    assert pairing.select_card([card], stats3, 0) is None

    # Case 4: validation fails (total_good != 1) -> False
    stats_valid = {
        'dists': {'cbow': [0.5]},
        'ngram': {'perp': [1.0], 'perp_per': [1.0], 'perp_max': [5.0]}
    }
    with patch('scripts.pairing.mtg_validate.process_props', return_value=((None, 0, None, None), None)):
        assert pairing.select_card([card], stats_valid, 0) is False

    # Case 5: validation succeeds (total_good == 1) -> True
    with patch('scripts.pairing.mtg_validate.process_props', return_value=((None, 1, None, None), None)):
        assert pairing.select_card([card], stats_valid, 0) is True


def test_compare_to_real():
    card1 = DummyCard(types=["Creature", "Artifact"], colors=["U", "R"])
    real_match = DummyCard(types=["Artifact", "Creature"], colors=["U", "R", "W"])
    real_type_mismatch = DummyCard(types=["Creature"], colors=["U", "R"])
    real_color_mismatch = DummyCard(types=["Creature", "Artifact"], colors=["U"])

    assert pairing.compare_to_real(card1, real_match) is True
    assert pairing.compare_to_real(card1, real_type_mismatch) is False
    assert pairing.compare_to_real(card1, real_color_mismatch) is False


def test_writecard():
    class DummyWriter:
        def __init__(self):
            self.content = []

        def write(self, data):
            self.content.append(data)

    writer = DummyWriter()
    card = DummyCard(name="Original", card_json={"name": "Original"}, raw="<raw_text>")

    pairing.writecard(card, "Renamed", writer)

    assert card.name == "Original"
    written_text = "".join(writer.content)
    assert "MSE Renamed" in written_text
    assert "JSON:" in written_text
    assert "raw:" in written_text
    assert "(raw_text)" in written_text


def test_main_execution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    card_fake = DummyCard(name="Fake Card", types=["Creature"], colors=["U"])
    card_real = DummyCard(name="Real Card", types=["Creature"], colors=["U"])

    mock_cbow = MagicMock()
    mock_cbow.nearest_par.return_value = [[(0.1, "Real Card")]]

    stats = {
        'dists': {'cbow': [0.5]},
        'ngram': {'perp': [1.0], 'perp_per': [1.0], 'perp_max': [5.0]}
    }

    out_file = str(tmp_path / "output.txt")

    with patch('scripts.pairing.CBOW', return_value=mock_cbow), \
         patch('scripts.pairing.jdecode.mtg_open_file', side_effect=[[card_real], [card_fake]]), \
         patch('scripts.pairing.ngrams.build_ngram_model', return_value=MagicMock()), \
         patch('scripts.pairing.analysis.get_statistics', return_value=stats), \
         patch('scripts.pairing.mtg_validate.process_props', return_value=((None, 1, None, None), None)):

        pairing.main("fake_input.txt", out_file, verbose=True)

    assert os.path.exists(out_file)
    assert os.path.exists(out_file + ".mse-set")


def test_main_existing_set_file_collision(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    set_file = tmp_path / "set"
    set_file.write_text("existing set content")

    card_fake = DummyCard(name="Fake Card", types=["Creature"], colors=["U"])
    card_real = DummyCard(name="Real Card", types=["Creature"], colors=["U"])

    mock_cbow = MagicMock()
    mock_cbow.nearest_par.return_value = [[(0.1, "Real Card")]]

    stats = {
        'dists': {'cbow': [0.5]},
        'ngram': {'perp': [1.0], 'perp_per': [1.0], 'perp_max': [5.0]}
    }

    out_file = str(tmp_path / "output.txt")

    with patch('scripts.pairing.CBOW', return_value=mock_cbow), \
         patch('scripts.pairing.jdecode.mtg_open_file', side_effect=[[card_real], [card_fake]]), \
         patch('scripts.pairing.ngrams.build_ngram_model', return_value=MagicMock()), \
         patch('scripts.pairing.analysis.get_statistics', return_value=stats), \
         patch('scripts.pairing.mtg_validate.process_props', return_value=((None, 1, None, None), None)):

        pairing.main("fake_input.txt", out_file, verbose=False)

    captured = capsys.readouterr()
    assert 'ERROR: tried to overwrite existing file "set" - aborting.' in captured.out


def test_main_cli_execution(tmp_path):
    out_file = str(tmp_path / "output_cli.txt")
    test_args = ['scripts/pairing.py', 'fake_input.txt', out_file, '-n', '10', '-v']

    card_fake = DummyCard(name="Fake Card", types=["Creature"], colors=["U"])
    card_real = DummyCard(name="Real Card", types=["Creature"], colors=["U"])
    mock_cbow = MagicMock()
    mock_cbow.nearest_par.return_value = [[(0.1, "Real Card")]]
    stats = {
        'dists': {'cbow': [0.5]},
        'ngram': {'perp': [1.0], 'perp_per': [1.0], 'perp_max': [5.0]}
    }

    script_path = os.path.abspath('scripts/pairing.py')

    with patch.object(sys, 'argv', test_args), \
         patch('scripts.pairing.CBOW', return_value=mock_cbow), \
         patch('scripts.pairing.jdecode.mtg_open_file', side_effect=[[card_real], [card_fake]]), \
         patch('scripts.pairing.ngrams.build_ngram_model', return_value=MagicMock()), \
         patch('scripts.pairing.analysis.get_statistics', return_value=stats), \
         patch('scripts.pairing.mtg_validate.process_props', return_value=((None, 1, None, None), None)):

        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(script_path, run_name='__main__')
        assert exc_info.value.code == 0
