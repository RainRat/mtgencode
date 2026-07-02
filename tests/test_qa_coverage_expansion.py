import pytest
import json
from lib.cardlib import Card, fields_from_format, field_text
from lib import jdecode
from lib import transforms

def test_card_supertype_case_insensitivity():
    card_json = {
        "name": "Legendary Golem",
        "supertypes": ["Legendary"],
        "types": ["Artifact", "Creature"]
    }
    card = Card(card_json)
    # Coverage for lib/cardlib.py:741-742, 757
    assert card.is_legendary
    assert card._has_supertype("legendary")
    assert card._has_supertype("LEGENDARY")
    assert not card._has_supertype("Basic")

def test_card_is_permanent_comprehensive():
    # Coverage for lib/cardlib.py:797
    def make_card(types):
        return Card({"name": "Test", "types": types})

    assert make_card(["Artifact"]).is_permanent
    assert make_card(["Creature"]).is_permanent
    assert make_card(["Enchantment"]).is_permanent
    assert make_card(["Land"]).is_permanent
    assert make_card(["Planeswalker"]).is_permanent
    assert make_card(["Battle"]).is_permanent
    assert not make_card(["Instant"]).is_permanent
    assert not make_card(["Sorcery"]).is_permanent

def test_card_tokens_bside_recursion():
    # Coverage for lib/cardlib.py:803-804
    card_json = {
        "name": "Token Maker A",
        "text": "Create a 1/1 white Soldier creature token.",
        "bside": {
            "name": "Token Maker B",
            "text": "Create a 2/2 black Zombie creature token."
        }
    }
    card = Card(card_json)
    tokens = card.tokens
    token_names = [t['name'] for t in tokens]
    # The actual output format is e.g. "1/1 White Soldier Token"
    assert "1/1 White Soldier Token" in token_names
    assert "2/2 Black Zombie Token" in token_names

def test_fields_from_format_ability_words():
    # Coverage for lib/cardlib.py:606, 608
    # Channel is an ability word in transforms.abilitywords
    assert 'channel' in transforms.abilitywords

    src_text = "9Channel — Discard this card: Do something."
    fmt_labeled = {field_text: '9'}
    parsed, valid, fields = fields_from_format(src_text, [], fmt_labeled, '|')

    assert '_ability_words' in fields
    # Ability words are titlecased in the extraction
    assert fields['_ability_words'][0][1] == ['Channel']

def test_jdecode_mtg_open_file_advanced_filters(tmp_path):
    # Coverage for lib/jdecode.py:1413-1419, 1423-1429, 1433-1439
    d = tmp_path / "data"
    d.mkdir()
    p = d / "test.json"

    # We create cards that will clearly fall into different buckets for complexity, rating, and fair_mv
    # Added 'type' and 'code' to set_data to avoid KeyErrors in mtg_open_json_obj
    p.write_text(json.dumps({
        "data": {
            "TEST": {
                "name": "Test Set",
                "code": "TEST",
                "type": "expansion",
                "cards": [
                    {
                        "name": "Simple",
                        "manaCost": "{1}{G}",
                        "types": ["Creature"],
                        "power": "1", "toughness": "1",
                        "text": "Vanilla."
                    },
                    {
                        "name": "ComplexHighRating",
                        "manaCost": "{G}",
                        "types": ["Creature"],
                        "power": "4", "toughness": "4",
                        "text": "Trample\nWhen @ enters the battlefield, create two 1/1 green Saproling creature tokens.\n{2}{G}: Regenerate @."
                    }
                ]
            }
        }
    }))

    # Test complexity filter (Simple is low complexity)
    cards_low_comp = jdecode.mtg_open_file(str(p), complexities=["<20"])
    assert len(cards_low_comp) == 1
    assert cards_low_comp[0].name == "simple"

    # Test rating filter (ComplexHighRating has 4/4 for 1 mana -> rating 4.0)
    cards_high_rate = jdecode.mtg_open_file(str(p), ratings=[">2"])
    assert len(cards_high_rate) == 1
    assert cards_high_rate[0].name == "complexhighrating"

    # Test fair_mv filter (ComplexHighRating has 4/4 -> recommended_cmc 4.0)
    cards_fmv = jdecode.mtg_open_file(str(p), fair_mvs=[">2"])
    assert len(cards_fmv) == 1
    assert cards_fmv[0].name == "complexhighrating"
