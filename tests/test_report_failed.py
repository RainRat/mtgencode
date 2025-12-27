import os
import tempfile
import utils
from jdecode import mtg_open_file
import cardlib

def test_mtg_open_file_report_failed_encoded():
    # Construct a card using a known valid encoding that is guaranteed to parse.
    valid_card = "Sorcery|||||||Common|TestCard"

    invalid_card = "INVALID_CARD_DATA"
    content = valid_card + utils.cardsep + invalid_card + utils.cardsep

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        input_filename = f.name

    report_filename = input_filename + ".report"

    try:
        cards = mtg_open_file(input_filename, verbose=False, report_file=report_filename)

        assert len(cards) == 2, f"Expected 2 cards, got {len(cards)}"
        assert cards[0].valid, f"First card should be valid, but got: {cards[0].__dict__}"
        assert not cards[1].valid

        assert os.path.exists(report_filename)
        with open(report_filename, 'r', encoding='utf-8') as rf:
            report_content = rf.read()
            assert invalid_card in report_content
            assert valid_card not in report_content

    finally:
        if os.path.exists(input_filename):
            os.remove(input_filename)
        if os.path.exists(report_filename):
            os.remove(report_filename)
