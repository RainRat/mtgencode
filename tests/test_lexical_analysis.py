import pytest
from lib.datalib import Datamine
from lib.cardlib import Card

def test_lexical_analysis_metrics():
    # Create mock cards with specific text
    # Word count: 1 + 2 + 3 = 6
    # Unique words: {a, bb, ccc, dddd} = 4
    cards = [
        {'name': 'Card A', 'text': 'a bb', 'types': ['Creature'], 'pt': '1/1', 'rarity': 'Common'},
        {'name': 'Card B', 'text': 'ccc dddd bb', 'types': ['Instant'], 'rarity': 'Rare'}
    ]

    mine = Datamine(cards)

    assert mine.total_words == 5
    assert mine.unique_words == 4
    assert mine.ttr == 4/5
    assert mine.avg_words_per_card == 2.5

    # Check top words
    assert mine.global_word_counts['bb'] == 2
    assert mine.global_word_counts['a'] == 1

def test_lexical_analysis_empty():
    mine = Datamine([])
    assert mine.total_words == 0
    assert mine.unique_words == 0
    assert mine.ttr == 0
    assert mine.avg_words_per_card == 0
