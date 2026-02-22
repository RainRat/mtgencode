import pytest
from lib.cardlib import Card
from lib import utils

@pytest.fixture
def sample_card_json():
    return {
        "name": "Ornithopter",
        "manaCost": "{0}",
        "cmc": 0,
        "colors": [],
        "type": "Artifact Creature — Thopter",
        "supertypes": [],
        "types": ["Artifact", "Creature"],
        "subtypes": ["Thopter"],
        "rarity": "Uncommon",
        "text": "Flying",
        "power": "0",
        "toughness": "2"
    }

def test_card_initialization_from_json(sample_card_json):
    card = Card(sample_card_json)
    assert card.name == "ornithopter"
    assert card.cost.cmc == 0
    assert card.types == ["artifact", "creature"]
    assert card.subtypes == ["thopter"]
    assert card.pt == "&/&^^"
    assert card.text.text == "flying"
    assert card.valid

def test_verbose_logging(capsys):
    invalid_card_json = {
        "name": "Invalid Card",
        "types": ["Creature"],
        "power": "1",
        "toughness": "1",
        "loyalty": "X"
    }
    card = Card(invalid_card_json, verbose=True)

    # Test multiple P/T values
    card._set_pt([(-1, '1/1'), (-1, '2/2')])
    captured = capsys.readouterr()
    assert "Multiple P/T values for card 'invalid card': 2/2" in captured.err

    # Test invalid loyalty
    card._set_loyalty([(-1, 'X')])
    captured = capsys.readouterr()
    # Note: We removed the check for invalid integer loyalty values because
    # encoded cards use unary strings (e.g. &^^^) which are not valid integers.
    # So this should NOT print an error message anymore.
    assert "Invalid loyalty value for card 'invalid card': X" not in captured.err

def test_planeswalker_negative_loyalty_to_mse():
    planeswalker_json = {
        "name": "Liliana of the Veil",
        "manaCost": "{1}{B}{B}",
        "type": "Legendary Planeswalker — Liliana",
        "supertypes": ["Legendary"],
        "types": ["Planeswalker"],
        "subtypes": ["Liliana"],
        "rarity": "Mythic",
        "text": "+1: Each player discards a card.\n-2: Target player sacrifices a creature.\n-6: Separate all permanents target player controls into two piles. That player sacrifices all permanents in the pile of their choice.",
        "loyalty": 3
    }
    card = Card(planeswalker_json)
    mse_output = card.to_mse()
    assert "\tloyalty cost 2: -2\n" in mse_output

@pytest.mark.parametrize("pt_string, expected_p, expected_t", [
    ("1/2", "1", "2"),
    (" 1 / 2 ", "1", "2"),
    ("*/*", "*", "*"),
    ("*/ *+1", "*", "*+1"),
])
def test_pt_parsing(pt_string, expected_p, expected_t):
    card = Card({"name": "Test Creature", "types": ["Creature"], "pt": pt_string})
    assert card.pt_p == expected_p
    assert card.pt_t == expected_t


def test_card_format(sample_card_json):
    card = Card(sample_card_json)

    # Test with gatherer=True
    gatherer_output = card.format(gatherer=True)
    expected_gatherer_output = (
        "Ornithopter {0} (uncommon)\n"
        "Artifact Creature — Thopter (0/2)\n\n"
        "Flying"
    )
    assert gatherer_output == expected_gatherer_output

    # Test with gatherer=False
    default_output = card.format(gatherer=False)
    expected_default_output = (
        "Ornithopter {0}\n"
        "Artifact Creature ~ Thopter (uncommon)\n\n"
        "Flying\n"
        "(0/2)"
    )
    assert default_output == expected_default_output

    # Test with ansi_color=True
    colored_output = card.format(ansi_color=True)
    # Card name: Bold Cyan (Artifact)
    # Cost: Cyan
    # Typeline: Green
    # P/T: Red
    # Rarity: Cyan (Uncommon)
    expected_name = utils.colorize("Ornithopter", utils.Ansi.BOLD + utils.Ansi.CYAN)
    expected_cost = utils.colorize("{0}", utils.Ansi.CYAN)
    expected_type = utils.colorize("Artifact Creature ~ Thopter", utils.Ansi.GREEN)
    expected_pt = utils.colorize("0/2", utils.Ansi.RED)
    expected_rarity = utils.colorize("uncommon", utils.Ansi.CYAN)

    # Construction of default format with colors
    expected_colored_output = (
        f"{expected_name} {expected_cost}\n"
        f"{expected_type} ({expected_rarity})\n\n"
        "Flying\n"
        f"({expected_pt})"
    )
    assert colored_output == expected_colored_output

def test_card_summary(sample_card_json):
    card = Card(sample_card_json)

    # Test plain summary
    output = card.summary()
    assert output == "[U] Ornithopter {0} - Artifact Creature — Thopter - 0/2"

    # Test colored summary
    colored_output = card.summary(ansi_color=True)
    expected_name = utils.colorize("Ornithopter", utils.Ansi.BOLD + utils.Ansi.CYAN)
    expected_cost = utils.colorize("{0}", utils.Ansi.CYAN)
    expected_type = utils.colorize("Artifact Creature — Thopter", utils.Ansi.GREEN)
    expected_pt = utils.colorize("0/2", utils.Ansi.RED)
    expected_rarity_indicator = utils.colorize("U", utils.Ansi.BOLD + utils.Ansi.CYAN)

    expected_colored_summary = f"[{expected_rarity_indicator}] {expected_name} {expected_cost} - {expected_type} - {expected_pt}"
    assert colored_output == expected_colored_summary

def test_planeswalker_to_mse_formatting():
    planeswalker_json = {
        "name": "Jules, the Wise",
        "manaCost": "{3}{U}{U}",
        "type": "Legendary Planeswalker — Jules",
        "supertypes": ["Legendary"],
        "types": ["Planeswalker"],
        "subtypes": ["Jules"],
        "rarity": "Mythic",
        "text": "You may cast spells from the top of your library.\n+1: Scry 1.\n-8: You get an emblem with \"You have no maximum hand size.\"",
        "loyalty": 4
    }
    card = Card(planeswalker_json)
    mse_output = card.to_mse()
    expected_output = """card:
	name: Jules, the Wise
	rarity: mythic
	casting cost: 3UU
	super type: Legendary Planeswalker
	sub type: Jules
	stylesheet: m15-planeswalker
	loyalty cost 1: +1
	loyalty cost 2: -8
	loyalty: 4
	rule text:
		You may cast spells from the top of your library.
		Scry 1.
		You get an emblem with "you have no maximum hand size."
	has styling: false
	time created:2015-07-20 22:53:07
	time modified:2015-07-20 22:53:08
	extra data:
	image:
	card code text:
	copyright:
	image 2:
	copyright 2:
	notes:"""

    # The timestamps are dynamically generated, so we'll ignore them in the comparison
    assert mse_output.strip().split('has styling')[0] == expected_output.strip().split('has styling')[0]

def test_card_initialization_from_encoded_text():
    encoded_text = "|5artifact creature|4|6thopter|8&/&^^|9flying|3{}|0N|1ornithopter|"
    card = Card(encoded_text, fmt_ordered=[
    "types",
    "supertypes",
    "subtypes",
    "loyalty",
    "pt",
    "text",
    "cost",
    "rarity",
    "name",
])
    assert card.name == "ornithopter"
    assert card.cost.cmc == 0
    assert card.types == ["artifact", "creature"]
    assert card.subtypes == ["thopter"]
    assert card.pt == "&/&^^"
    assert card.text.text == "flying"
    assert card.valid
