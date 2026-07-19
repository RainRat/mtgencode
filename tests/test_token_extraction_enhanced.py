from lib.cardlib import extract_tokens_from_text

def test_extract_predefined_tokens_quantities():
    text_six = "Create six Treasure tokens."
    tokens_six = extract_tokens_from_text(text_six)
    assert len(tokens_six) == 1
    assert tokens_six[0]['name'] == "Treasure Token"

    text_ten = "Create ten Food tokens."
    tokens_ten = extract_tokens_from_text(text_ten)
    assert len(tokens_ten) == 1
    assert tokens_ten[0]['name'] == "Food Token"

    text_x = "Create X Clue tokens."
    tokens_x = extract_tokens_from_text(text_x)
    assert len(tokens_x) == 1
    assert tokens_x[0]['name'] == "Clue Token"

def test_extract_gold_tokens():
    text = "Create a Gold token."
    tokens = extract_tokens_from_text(text)
    assert len(tokens) == 1
    assert tokens[0]['name'] == "Gold Token"
    assert tokens[0]['type'] == "Artifact"
    assert "Add one mana of any color" in tokens[0]['abilities']

    text_multi = "Create three Gold tokens."
    tokens_multi = extract_tokens_from_text(text_multi)
    assert len(tokens_multi) == 1
    assert tokens_multi[0]['name'] == "Gold Token"

def test_extract_creature_tokens_complex():
    text = "Create a 2/2 white Knight creature token with vigilance."
    tokens = extract_tokens_from_text(text)
    assert len(tokens) == 1
    assert tokens[0]['name'] == "2/2 White Knight Token"
    assert tokens[0]['pt'] == "2/2"
    assert tokens[0]['color'] == "White"
    assert tokens[0]['type'] == "Knight Creature"
    assert tokens[0]['abilities'] == "vigilance"

    text_multi = "Create a 1/1 blue and red Elemental creature token."
    tokens_multi = extract_tokens_from_text(text_multi)
    assert len(tokens_multi) == 1
    assert "Blue" in tokens_multi[0]['color']
    assert "Red" in tokens_multi[0]['color']
    assert tokens_multi[0]['type'] == "Elemental Creature"

def test_extract_multiple_token_types():
    text = "Create a Treasure token and a 1/1 green Saproling creature token."
    tokens = extract_tokens_from_text(text)
    assert len(tokens) == 2
    names = [t['name'] for t in tokens]
    assert "Treasure Token" in names
    assert "1/1 Green Saproling Token" in names

def test_extract_token_with_hyphenated_type():
    text = "Create a 3/3 colorless Golem-Artifact creature token."
    tokens = extract_tokens_from_text(text)
    assert len(tokens) == 1
    assert "Golem-artifact" in tokens[0]['type'] or "Golem-Artifact" in tokens[0]['type']

def test_extract_non_token_text():
    text = "Destroy all tokens."
    tokens = extract_tokens_from_text(text)
    assert len(tokens) == 0

    text2 = "Sacrifice a Treasure: Draw a card."
    tokens2 = extract_tokens_from_text(text2)
    assert len(tokens2) == 0
