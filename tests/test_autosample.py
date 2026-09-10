import os
import runpy
import sys
from unittest.mock import patch
import pytest

from scripts.autosample import extract_cp_name, sample, find_best_cp, process_dir, main


def test_extract_cp_name_valid():
    result = extract_cp_name("lm_lstm_epoch50.00_0.1870.t7")
    assert result == (50.0, 0.1870)


def test_extract_cp_name_invalid_prefix():
    assert extract_cp_name("other_prefix_epoch50.00_0.1870.t7") is None


def test_extract_cp_name_invalid_suffix():
    assert extract_cp_name("lm_lstm_epoch50.00_0.1870.txt") is None


def test_find_best_cp_selects_lowest_vloss(tmp_path):
    cp_dir = tmp_path / "checkpoints"
    cp_dir.mkdir()
    (cp_dir / "lm_lstm_epoch10.00_0.3500.t7").write_text("model1")
    (cp_dir / "lm_lstm_epoch20.00_0.1200.t7").write_text("model2")
    (cp_dir / "lm_lstm_epoch30.00_0.2500.t7").write_text("model3")
    (cp_dir / "ignored_file.txt").write_text("ignored")

    best = find_best_cp(str(cp_dir))
    expected = os.path.join(str(cp_dir), "lm_lstm_epoch20.00_0.1200.t7")
    assert best == expected


def test_find_best_cp_empty_dir(tmp_path):
    cp_dir = tmp_path / "empty"
    cp_dir.mkdir()
    assert find_best_cp(str(cp_dir)) is None


def test_sample_skips_when_outfile_exists(tmp_path, capsys):
    cp_path = str(tmp_path / "model.t7")
    outfile = cp_path + ".output.1.0.txt"
    with open(outfile, "w") as f:
        f.write("existing content")

    with patch("subprocess.run") as mock_run:
        result = sample(cp_path, temp=1.0, count=100)
        assert result is False
        mock_run.assert_not_called()

    captured = capsys.readouterr()
    assert "already exists, skipping" in captured.out


def test_sample_executes_and_creates_outfile(tmp_path):
    cp_path = str(tmp_path / "model.t7")
    outfile = cp_path + ".test_ident.0.8.txt"

    with patch("subprocess.run") as mock_run:
        sample(cp_path, temp=0.8, count=500, seed=12345, ident="test_ident")
        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        cmd = args[0]
        assert cmd == ["th", "sample.lua", cp_path, "-temperature", "0.8", "-length", "500", "-seed", "12345"]

    assert os.path.exists(outfile)
    with open(outfile, "r") as f:
        content = f.read()
    assert "th sample.lua " in content
    assert "-temperature 0.8" in content
    assert "-length 500" in content
    assert "-seed 12345" in content


def test_sample_random_seed(tmp_path):
    cp_path = str(tmp_path / "model.t7")

    with patch("subprocess.run") as mock_run:
        sample(cp_path, temp=1.0, count=100, seed=None)
        mock_run.assert_called_once()


def test_process_dir_recursive(tmp_path, capsys):
    root_dir = tmp_path / "root"
    sub_dir = root_dir / "sub"
    sub_dir.mkdir(parents=True)

    (root_dir / "lm_lstm_epoch1.00_0.5000.t7").write_text("model1")
    (sub_dir / "lm_lstm_epoch2.00_0.1000.t7").write_text("model2")

    with patch("subprocess.run") as mock_run:
        process_dir(str(root_dir), temp=1.0, count=100, verbose=True)

        assert mock_run.call_count == 2
        captured = capsys.readouterr()
        assert "processing " in captured.out


def test_main_invalid_rnndir(tmp_path):
    cp_dir = tmp_path / "cp"
    cp_dir.mkdir()
    with pytest.raises(ValueError, match="bad rnndir"):
        main(str(tmp_path / "nonexistent_rnn"), str(cp_dir), temp=1.0, count=100)


def test_main_invalid_cpdir(tmp_path):
    rnn_dir = tmp_path / "rnn"
    rnn_dir.mkdir()
    with pytest.raises(ValueError, match="bad cpdir"):
        main(str(rnn_dir), str(tmp_path / "nonexistent_cp"), temp=1.0, count=100)


def test_main_successful_execution(tmp_path, monkeypatch):
    rnn_dir = tmp_path / "rnn"
    cp_dir = tmp_path / "cp"
    rnn_dir.mkdir()
    cp_dir.mkdir()
    (cp_dir / "lm_lstm_epoch1.00_0.2000.t7").write_text("model")

    monkeypatch.chdir(os.getcwd())

    with patch("subprocess.run") as mock_run:
        main(str(rnn_dir), str(cp_dir), temp=0.7, count=200, seed=42)
        mock_run.assert_called_once()
        assert os.getcwd() == str(rnn_dir)


def test_cli_execution(tmp_path, monkeypatch):
    script_path = os.path.abspath("scripts/autosample.py")
    rnn_dir = tmp_path / "rnn"
    cp_dir = tmp_path / "cp"
    rnn_dir.mkdir()
    cp_dir.mkdir()
    (cp_dir / "lm_lstm_epoch1.00_0.2000.t7").write_text("model")

    test_args = [
        "autosample.py",
        str(rnn_dir),
        str(cp_dir),
        "-t", "0.8",
        "-c", "500",
        "-s", "99",
        "-i", "cli_test",
        "-v"
    ]
    monkeypatch.setattr(sys, "argv", test_args)
    monkeypatch.chdir(os.getcwd())

    with patch("subprocess.run") as mock_run, pytest.raises(SystemExit) as exc_info:
        runpy.run_path(script_path, run_name="__main__")

    assert exc_info.value.code == 0
    mock_run.assert_called_once()


def test_cli_execution_no_seed(tmp_path, monkeypatch):
    script_path = os.path.abspath("scripts/autosample.py")
    rnn_dir = tmp_path / "rnn"
    cp_dir = tmp_path / "cp"
    rnn_dir.mkdir()
    cp_dir.mkdir()
    (cp_dir / "lm_lstm_epoch1.00_0.2000.t7").write_text("model")

    test_args = [
        "autosample.py",
        str(rnn_dir),
        str(cp_dir)
    ]
    monkeypatch.setattr(sys, "argv", test_args)
    monkeypatch.chdir(os.getcwd())

    with patch("subprocess.run") as mock_run, pytest.raises(SystemExit) as exc_info:
        runpy.run_path(script_path, run_name="__main__")

    assert exc_info.value.code == 0
    mock_run.assert_called_once()
