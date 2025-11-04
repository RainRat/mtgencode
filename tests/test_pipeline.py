import pytest
import json
from lib.cardlib import Card

@pytest.fixture
def sample_cards():
    with open("tests/sample_cards.json", "r") as f:
        card_samples = json.load(f)
    return card_samples

def test_encode_decode_loop(sample_cards):
    for card_data in sample_cards:
        # 1. Instantiate Card from JSON
        original_card = Card(card_data)
        assert original_card.valid

        # 2. Encode the card
        encoded_string = original_card.encode()
        assert isinstance(encoded_string, str)

        # 3. Instantiate a new Card from the encoded string
        decoded_card = Card(encoded_string)
        assert decoded_card.valid

        # 4. Optional: Verify a basic attribute
        assert original_card.name == decoded_card.name
        assert original_card.cost.cmc == decoded_card.cost.cmc

def test_output_formats(sample_cards):
    for card_data in sample_cards:
        card = Card(card_data)
        assert isinstance(card.format(), str)
        assert isinstance(card.format(gatherer=True), str)
        assert isinstance(card.format(for_forum=True), str)
        assert isinstance(card.to_mse(), str)

def test_html_creativity_output():
    import os
    import shutil
    import subprocess
    infile = "tests/sample_cards.json"
    outfile = "tests/test_output.html"
    data_dir = "data"
    all_sets_file = os.path.join(data_dir, "AllSets.json")
    # The creativity feature requires a data file, so we'll create a temporary one from our sample cards
    shutil.copy(infile, all_sets_file)
    try:
        subprocess.run(["python", "decode.py", infile, outfile, "--html", "--creativity"], check=True)
        assert os.path.exists(outfile)
        with open(outfile, "r") as f:
            content = f.read()
        assert "closest cards" in content
        assert "closest names" in content
    finally:
        if os.path.exists(outfile):
            os.remove(outfile)
        if os.path.exists(all_sets_file):
            os.remove(all_sets_file)
