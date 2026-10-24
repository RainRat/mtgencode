import pytest
import subprocess
import sys

def test_csv2json_version_flags():
    res_short = subprocess.run([sys.executable, 'scripts/csv2json.py', '-V'], capture_output=True, text=True)
    assert res_short.returncode == 0
    assert 'mtgencode 1.0.0' in res_short.stdout or 'mtgencode 1.0.0' in res_short.stderr

    res_long = subprocess.run([sys.executable, 'scripts/csv2json.py', '--version'], capture_output=True, text=True)
    assert res_long.returncode == 0
    assert 'mtgencode 1.0.0' in res_long.stdout or 'mtgencode 1.0.0' in res_long.stderr

def test_json2csv_version_flags():
    res_short = subprocess.run([sys.executable, 'scripts/json2csv.py', '-V'], capture_output=True, text=True)
    assert res_short.returncode == 0
    assert 'mtgencode 1.0.0' in res_short.stdout or 'mtgencode 1.0.0' in res_short.stderr

    res_long = subprocess.run([sys.executable, 'scripts/json2csv.py', '--version'], capture_output=True, text=True)
    assert res_long.returncode == 0
    assert 'mtgencode 1.0.0' in res_long.stdout or 'mtgencode 1.0.0' in res_long.stderr

def test_mtg_csv_json_version_flags():
    res_short = subprocess.run([sys.executable, 'scripts/mtg_csv_json.py', '-V'], capture_output=True, text=True)
    assert res_short.returncode == 0
    assert 'mtgencode 1.0.0' in res_short.stdout or 'mtgencode 1.0.0' in res_short.stderr

    res_long = subprocess.run([sys.executable, 'scripts/mtg_csv_json.py', '--version'], capture_output=True, text=True)
    assert res_long.returncode == 0
    assert 'mtgencode 1.0.0' in res_long.stdout or 'mtgencode 1.0.0' in res_long.stderr
