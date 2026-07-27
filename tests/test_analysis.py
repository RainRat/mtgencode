from unittest.mock import patch
import sys
import os

# Add scripts directory to sys.path so we can import analysis and ngrams
scripts_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), '../scripts'))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

import analysis
import cardlib
import ngrams

def test_get_statistics_sep_false():
    # Mock jdecode.mtg_open_file to return a list of cardlib.Card objects
    mock_cards = [
        cardlib.Card({
            'name': 'Giant Growth',
            'manaCost': '{G}',
            'text': 'Target creature gets +3/+3 until end of turn.',
            'type': 'Instant',
            'rarity': 'Common',
            'types': ['Instant']
        })
    ]

    lm = ngrams.build_ngram_model(mock_cards, 3, separate_lines=False)

    with patch('jdecode.mtg_open_file', return_value=mock_cards):
        # We call get_statistics with sep=False (which triggers the else block where NameError was raised)
        stats = analysis.get_statistics("dummy_path.txt", lm=lm, sep=False)

        # Verify that we got statistics and no NameError was raised!
        assert 'ngram' in stats
        assert 'perp' in stats['ngram']
        assert len(stats['ngram']['perp']) == 1
        assert len(stats['ngram']['perp_per_max']) == 1

def test_get_statistics_sep_true():
    mock_cards = [
        cardlib.Card({
            'name': 'Giant Growth',
            'manaCost': '{G}',
            'text': 'Target creature gets +3/+3 until end of turn.',
            'type': 'Instant',
            'rarity': 'Common',
            'types': ['Instant']
        })
    ]

    lm = ngrams.build_ngram_model(mock_cards, 3, separate_lines=True)

    with patch('jdecode.mtg_open_file', return_value=mock_cards):
        stats = analysis.get_statistics("dummy_path.txt", lm=lm, sep=True)
        assert 'ngram' in stats
        assert 'perp' in stats['ngram']
        assert len(stats['ngram']['perp']) == 1
