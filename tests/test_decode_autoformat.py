import os
import subprocess
import json
import pytest

# Helper to run decode.py
def run_decode(infile, outfile, extra_args=None):
    cmd = ['python3', 'decode.py', infile, outfile]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True)

@pytest.fixture
def encoded_file(tmp_path):
    f = tmp_path / "test_card.txt"
    # Correct format for std with labels: |5types|1name|
    f.write_text("|5Creature|1Test Card|")
    return str(f)

def test_auto_format_json(encoded_file, tmp_path):
    outfile = tmp_path / "output.json"
    run_decode(encoded_file, str(outfile))

    assert outfile.exists()
    with open(outfile, 'r') as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert data[0]['name'] == 'Test Card'

def test_auto_format_html(encoded_file, tmp_path):
    outfile = tmp_path / "output.html"
    run_decode(encoded_file, str(outfile))

    assert outfile.exists()
    content = outfile.read_text()
    assert '<html>' in content or '<div class="card-text">' in content

def test_auto_format_csv(encoded_file, tmp_path):
    outfile = tmp_path / "output.csv"
    run_decode(encoded_file, str(outfile))

    assert outfile.exists()
    content = outfile.read_text()
    assert 'name,mana_cost,type' in content

def test_auto_format_summary(encoded_file, tmp_path):
    outfile = tmp_path / "output.sum"
    run_decode(encoded_file, str(outfile))

    assert outfile.exists()
    content = outfile.read_text()
    # Summary format: [?] Test Card - Creature
    assert 'Test Card' in content
    assert '-' in content

def test_explicit_flag_overrides_extension(encoded_file, tmp_path):
    # Extension is .json but we force --text
    outfile = tmp_path / "output.json"
    run_decode(encoded_file, str(outfile), extra_args=['--text'])

    assert outfile.exists()
    content = outfile.read_text()
    # If it's text, it won't be valid JSON
    with pytest.raises(json.JSONDecodeError):
        json.loads(content)
    assert 'Test Card' in content

def test_unknown_extension_defaults_to_text(encoded_file, tmp_path):
    outfile = tmp_path / "output.xyz"
    run_decode(encoded_file, str(outfile))

    assert outfile.exists()
    content = outfile.read_text()
    # Default text format output
    assert 'Test Card' in content
    assert not content.startswith('[') # Not JSON
