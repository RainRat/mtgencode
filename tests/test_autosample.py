import os
import sys
import runpy
import pytest
from unittest.mock import patch

# Ensure repo root and scripts are in sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
scripts_dir = os.path.join(repo_root, 'scripts')
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from scripts.autosample import (
    extract_cp_name,
    find_best_cp,
    sample,
    process_dir,
    main,
)


def test_extract_cp_name_valid():
    epoch, vloss = extract_cp_name("lm_lstm_epoch50.00_0.1870.t7")
    assert epoch == 50.0
    assert vloss == 0.1870


def test_extract_cp_name_invalid_prefix_or_suffix():
    assert extract_cp_name("other_prefix_epoch50.00_0.1870.t7") is None
    assert extract_cp_name("lm_lstm_epoch50.00_0.1870.txt") is None


def test_find_best_cp_selects_lowest_vloss(tmp_path):
    cp_dir = tmp_path / "checkpoints"
    cp_dir.mkdir()

    file1 = cp_dir / "lm_lstm_epoch10.00_0.5000.t7"
    file2 = cp_dir / "lm_lstm_epoch20.00_0.2500.t7"
    file3 = cp_dir / "lm_lstm_epoch30.00_0.3500.t7"
    file1.write_text("data")
    file2.write_text("data")
    file3.write_text("data")

    # Subdirectory to test directory filtering
    (cp_dir / "subdir").mkdir()

    best = find_best_cp(str(cp_dir))
    assert best == str(file2)


def test_find_best_cp_empty_or_no_matching(tmp_path):
    cp_dir = tmp_path / "empty"
    cp_dir.mkdir()
    assert find_best_cp(str(cp_dir)) is None

    (cp_dir / "unrelated.txt").write_text("data")
    assert find_best_cp(str(cp_dir)) is None


def test_sample_skips_existing_outfile(tmp_path, capsys):
    cp = str(tmp_path / "lm_lstm_epoch10.00_0.5000.t7")
    temp = 1.0
    ident = "test"
    outfile = f"{cp}.{ident}.{temp}.txt"

    with open(outfile, "w") as f:
        f.write("existing content\n")

    result = sample(cp, temp, 100, seed=12345, ident=ident)
    assert result is False

    captured = capsys.readouterr()
    assert "already exists, skipping" in captured.out


@patch("subprocess.run")
def test_sample_creates_new_outfile(mock_run, tmp_path):
    cp = str(tmp_path / "lm_lstm_epoch10.00_0.5000.t7")
    temp = 0.8
    ident = "out"

    sample(cp, temp, 500, seed=42, ident=ident)

    outfile = f"{cp}.{ident}.{temp}.txt"
    assert os.path.exists(outfile)

    with open(outfile, "r") as f:
        content = f.read()

    assert "th sample.lua" in content
    assert "-temperature 0.8" in content
    assert "-length 500" in content
    assert "-seed 42" in content
    assert mock_run.called


@patch("subprocess.run")
def test_sample_default_random_seed(mock_run, tmp_path):
    cp = str(tmp_path / "lm_lstm_epoch10.00_0.5000.t7")
    temp = 1.0

    sample(cp, temp, 100)

    outfile = f"{cp}.output.{temp}.txt"
    assert os.path.exists(outfile)
    assert mock_run.called


@patch("subprocess.run")
def test_process_dir_recursive(mock_run, tmp_path, capsys):
    base_dir = tmp_path / "models"
    sub_dir = base_dir / "run1"
    sub_dir.mkdir(parents=True)

    cp_file = sub_dir / "lm_lstm_epoch5.00_0.1234.t7"
    cp_file.write_text("dummy model")

    process_dir(str(base_dir), 1.0, 200, seed=1, verbose=True)

    captured = capsys.readouterr()
    assert f"processing {base_dir}" in captured.out
    assert mock_run.called


def test_main_invalid_dirs(tmp_path):
    valid_dir = str(tmp_path)
    invalid_dir = str(tmp_path / "non_existent")

    with pytest.raises(ValueError, match="bad rnndir"):
        main(invalid_dir, valid_dir, 1.0, 100)

    with pytest.raises(ValueError, match="bad cpdir"):
        main(valid_dir, invalid_dir, 1.0, 100)


@patch("subprocess.run")
def test_main_valid_execution(mock_run, tmp_path):
    rnn_dir = tmp_path / "rnn"
    rnn_dir.mkdir()
    cp_dir = tmp_path / "checkpoints"
    cp_dir.mkdir()

    cp_file = cp_dir / "lm_lstm_epoch1.00_0.9900.t7"
    cp_file.write_text("model data")

    original_cwd = os.getcwd()
    try:
        main(str(rnn_dir), str(cp_dir), 1.0, 100, seed=7)
        assert os.getcwd() == str(rnn_dir)
        assert mock_run.called
    finally:
        os.chdir(original_cwd)


@patch("subprocess.run")
def test_cli_execution_with_seed(mock_run, tmp_path):
    rnn_dir = tmp_path / "rnn"
    rnn_dir.mkdir()
    cp_dir = tmp_path / "checkpoints"
    cp_dir.mkdir()

    cp_file = cp_dir / "lm_lstm_epoch2.00_0.8000.t7"
    cp_file.write_text("model")

    test_args = [
        "autosample.py",
        str(rnn_dir),
        str(cp_dir),
        "-t", "0.7",
        "-c", "300",
        "-s", "999",
        "-i", "custom",
        "-v"
    ]

    original_cwd = os.getcwd()
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(os.path.join(scripts_dir, "autosample.py"), run_name="__main__")
        assert exc_info.value.code == 0

    os.chdir(original_cwd)


@patch("subprocess.run")
def test_cli_execution_default_seed(mock_run, tmp_path):
    rnn_dir = tmp_path / "rnn"
    rnn_dir.mkdir()
    cp_dir = tmp_path / "checkpoints"
    cp_dir.mkdir()

    cp_file = cp_dir / "lm_lstm_epoch3.00_0.7000.t7"
    cp_file.write_text("model")

    test_args = [
        "autosample.py",
        str(rnn_dir),
        str(cp_dir)
    ]

    original_cwd = os.getcwd()
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(os.path.join(scripts_dir, "autosample.py"), run_name="__main__")
        assert exc_info.value.code == 0

    os.chdir(original_cwd)
