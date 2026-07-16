from lib.cardlib import Card

def test_extract_tokens_predefined_extended_counts():
    # 'six' is currently NOT supported for predefined tokens
    c6 = Card("|Creature|Legendary||||Create six Treasure tokens.|||Test|")
    tokens6 = c6.tokens
    assert len(tokens6) == 1, "Should identify Treasure tokens when count is 'six'"
    assert tokens6[0]['name'] == "Treasure Token"

    # 'ten' is currently NOT supported for predefined tokens
    c10 = Card("|Creature|Legendary||||Create ten Food tokens.|||Test|")
    tokens10 = c10.tokens
    assert len(tokens10) == 1, "Should identify Food tokens when count is 'ten'"
    assert tokens10[0]['name'] == "Food Token"

def test_extract_tokens_predefined_existing_counts():
    # 'five' IS currently supported
    c5 = Card("|Creature|Legendary||||Create five Clue tokens.|||Test|")
    tokens5 = c5.tokens
    assert len(tokens5) == 1
    assert tokens5[0]['name'] == "Clue Token"
