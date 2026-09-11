import os
import sys
import tempfile
import runpy
import pytest
from unittest.mock import patch, MagicMock

# Add scripts directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

import autosample

class TestAutosample:
    def test_extract_cp_name_valid(self):
        filename = "lm_lstm_epoch50.00_0.1870.t7"
        result = autosample.extract_cp_name(filename)
        assert result == (50.0, 0.1870)

    def test_extract_cp_name_invalid(self):
        assert autosample.extract_cp_name("invalid_filename.txt") is None
        assert autosample.extract_cp_name("lm_lstm_epoch50.00.t7") is None
        assert autosample.extract_cp_name("other_prefix_epoch50.00_0.1870.t7") is None
        assert autosample.extract_cp_name("lm_lstm_epoch50.00_abc.t7") is None

    def test_find_best_cp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two fake checkpoint files
            cp1 = os.path.join(tmpdir, "lm_lstm_epoch10.00_0.3500.t7")
            cp2 = os.path.join(tmpdir, "lm_lstm_epoch20.00_0.1500.t7")
            cp3 = os.path.join(tmpdir, "lm_lstm_epoch30.00_0.2500.t7")

            for cp in [cp1, cp2, cp3]:
                with open(cp, 'w') as f:
                    f.write("dummy model content")

            best = autosample.find_best_cp(tmpdir)
            assert best == cp2

    def test_find_best_cp_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert autosample.find_best_cp(tmpdir) is None

    def test_sample_dry_run(self):
        cp_path = "/tmp/fake_cp/lm_lstm_epoch10.00_0.2000.t7"
        res = autosample.sample(cp_path, temp=0.8, count=1000, seed=123, ident="test", dry_run=True)

        assert isinstance(res, dict)
        assert res['checkpoint'] == cp_path
        assert res['outfile'] == cp_path + ".test.0.8.txt"
        assert res['exists'] is False
        assert "th sample.lua" in res['cmd']
        assert res['exec_cmd'] == ['th', 'sample.lua', cp_path, '-temperature', '0.8', '-length', '1000', '-seed', '123']

    @patch('subprocess.run')
    def test_sample_execution(self, mock_subproc):
        with tempfile.TemporaryDirectory() as tmpdir:
            cp_path = os.path.join(tmpdir, "lm_lstm_epoch10.00_0.2000.t7")
            with open(cp_path, 'w') as f:
                f.write("dummy")

            # First execution -> creates file and calls subprocess
            res1 = autosample.sample(cp_path, temp=1.0, count=500, seed=42, ident="output", dry_run=False)
            assert res1 is True
            mock_subproc.assert_called_once()

            outfile = cp_path + ".output.1.0.txt"
            assert os.path.exists(outfile)

            # Second execution on existing file -> skips
            mock_subproc.reset_mock()
            res2 = autosample.sample(cp_path, temp=1.0, count=500, seed=42, ident="output", dry_run=False)
            assert res2 is False
            mock_subproc.assert_not_called()

    def test_process_dir_dry_run(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            sub1 = os.path.join(tmpdir, "model_a")
            sub2 = os.path.join(tmpdir, "model_b")
            os.makedirs(sub1)
            os.makedirs(sub2)

            cp1 = os.path.join(sub1, "lm_lstm_epoch10.00_0.3000.t7")
            cp2 = os.path.join(sub2, "lm_lstm_epoch15.00_0.1000.t7")
            for cp in [cp1, cp2]:
                with open(cp, 'w') as f:
                    f.write("data")

            res = autosample.process_dir(tmpdir, temp=1.0, count=1000, seed=1, ident="out", verbose=True, dry_run=True)
            captured = capsys.readouterr()

            assert "Dry Run Summary:" in captured.out
            assert "Directories scanned: 3" in captured.out
            assert "Checkpoints identified: 2" in captured.out
            assert "Target output files: 2" in captured.out
            assert len(res['samples']) == 2

    def test_main_validation_errors(self):
        with pytest.raises(ValueError, match="bad rnndir"):
            autosample.main("/nonexistent_rnn_dir_12345", "/tmp", 1.0, 1000)

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="bad cpdir"):
                autosample.main(tmpdir, "/nonexistent_cp_dir_12345", 1.0, 1000)

    def test_main_dry_run(self, capsys):
        with tempfile.TemporaryDirectory() as rnndir, tempfile.TemporaryDirectory() as cpdir:
            sub = os.path.join(cpdir, "run1")
            os.makedirs(sub)
            cp = os.path.join(sub, "lm_lstm_epoch05.00_0.2200.t7")
            with open(cp, 'w') as f:
                f.write("model")

            res = autosample.main(rnndir, cpdir, temp=0.8, count=5000, seed=99, ident="out", verbose=False, dry_run=True)
            captured = capsys.readouterr()

            assert "Dry Run Summary:" in captured.out
            assert "Checkpoints identified: 1" in captured.out
            assert len(res['samples']) == 1

    def test_cli_dry_run_flags(self, capsys):
        with tempfile.TemporaryDirectory() as rnndir, tempfile.TemporaryDirectory() as cpdir:
            sub = os.path.join(cpdir, "run1")
            os.makedirs(sub)
            cp = os.path.join(sub, "lm_lstm_epoch05.00_0.2200.t7")
            with open(cp, 'w') as f:
                f.write("model")

            for flag in ['-p', '--preview', '--dry-run']:
                test_args = ['scripts/autosample.py', rnndir, cpdir, flag, '-t', '0.7', '-c', '100', '-s', '42', '-i', 'testrun']
                with patch('sys.argv', test_args):
                    with pytest.raises(SystemExit) as exc_info:
                        runpy.run_path('scripts/autosample.py', run_name='__main__')
                    assert exc_info.value.code == 0

                captured = capsys.readouterr()
                assert "Dry Run Summary:" in captured.out
                assert "Checkpoints identified: 1" in captured.out
