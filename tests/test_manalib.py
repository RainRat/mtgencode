import pytest
from lib.manalib import Manacost, Manatext
from lib import utils

class TestManaTranslation:
    def test_mana_translate(self):
        assert utils.mana_translate("{W}{U}{B}{R}{G}") == "{WWUUBBRRGG}"
        assert utils.mana_translate("{10}") == "{^^^^^^^^^^}"
        assert utils.mana_translate("") == "{}"

        # Test hybrid
        assert utils.mana_translate("{W/U}") == "{WU}"
        assert utils.mana_translate("{2/W}") == "{2W}"

        # Test phyrexian
        assert utils.mana_translate("{W/P}") == "{WP}"

    def test_mana_untranslate(self):
        assert utils.mana_untranslate("{WWUUBBRRGG}") == "{W}{U}{B}{R}{G}"
        assert utils.mana_untranslate("{^^^^^^^^^^}") == "{10}"
        assert utils.mana_untranslate("{}") == "{0}"

        # Test hybrid
        assert utils.mana_untranslate("{WU}") == "{W/U}"
        assert utils.mana_untranslate("{2W}") == "{2/W}"

        # Test phyrexian
        assert utils.mana_untranslate("{WP}") == "{W/P}"

    def test_mana_untranslate_formatting(self):
        # Forum formatting
        assert utils.mana_untranslate("{WW}", for_forum=True) == "[mana]W[/mana]"
        # Hybrid uses {WU} format in forum output
        assert utils.mana_untranslate("{WU}", for_forum=True) == "[mana]{WU}[/mana]"

        # HTML formatting
        html_w = utils.mana_untranslate("{WW}", for_html=True)
        assert "<img class='mana-W'>" in html_w


class TestManacost:
    def test_initialization_encoded(self):
        # Default initialization uses encoded string
        m = Manacost("{WWUUBBRRGG}")
        assert m.cmc == 5
        assert m.colors == "BGRUW"
        assert m.valid
        assert not m.none
        assert m.parsed

    def test_initialization_json(self):
        # Initialization from JSON string (e.g. "{1}{W}")
        m = Manacost("{1}{W}", fmt='json')
        assert m.cmc == 2
        assert m.colors == "W"
        assert m.valid
        assert m.sequence == ['^', 'WW'] # sequence stores encoded symbols

    def test_initialization_empty(self):
        m = Manacost("")
        assert m.none
        assert m.cmc == 0
        assert m.colors == ""

    def test_initialization_invalid(self):
        m = Manacost("Invalid")
        assert not m.valid
        assert not m.parsed

    def test_cmc_calculation(self):
        # X is 0
        assert Manacost("{XX}").cmc == 0
        # 2/W is 2
        assert Manacost("{2W}").cmc == 2
        # WP is 1
        assert Manacost("{WP}").cmc == 1
        # Unary
        assert Manacost("{^^^}").cmc == 3

    def test_colors_calculation(self):
        # Order should be alphabetical
        assert Manacost("{WWUU}").colors == "UW"
        assert Manacost("{RRGGBB}").colors == "BGR"

        # Colorless/Generic/X do not add colors
        assert Manacost("{XX}").colors == ""
        assert Manacost("{^^}").colors == "" # Generic
        assert Manacost("{CC}").colors == "" # Colorless mana is not a color

        # Hybrid
        assert Manacost("{WU}").colors == "UW"
        assert Manacost("{2W}").colors == "W"
        assert Manacost("{WP}").colors == "W"

    def test_check_colors(self):
        m = Manacost("{WWUUBBRRGG}") # WUBRG
        assert m.check_colors("W")
        assert m.check_colors("U")
        assert m.check_colors("WU")
        assert m.check_colors("BGRUW")

        # Not subset
        m2 = Manacost("{WW}") # W
        assert m2.check_colors("W")
        assert not m2.check_colors("U")

    def test_format(self):
        m = Manacost("{WWUUBBRRGG}")
        assert m.format() == "{W}{U}{B}{R}{G}"

        # Forum
        assert m.format(for_forum=True) == "[mana]WUBRG[/mana]"

        # ANSI Color
        colored = m.format(ansi_color=True)
        assert colored == utils.colorize("{W}{U}{B}{R}{G}", utils.Ansi.CYAN)

        # None
        assert Manacost("").format() == "_NOCOST_"

    def test_encode(self):
        m = Manacost("{WWUUBBRRGG}")
        assert m.encode() == "{WWUUBBRRGG}"

        # Randomize
        encoded = m.encode(randomize=True)
        assert len(encoded) == len("{WWUUBBRRGG}")
        assert encoded.startswith("{")
        assert encoded.endswith("}")
        assert sorted(encoded[1:-1]) == sorted("WWUUBBRRGG")

    def test_vectorize(self):
        m = Manacost("{WWUUBBRRGG}")
        # Sorted sequence of symbols
        # sequence: WW, UU, BB, RR, GG (order from initialization loop depends on string)
        # vectorize sorts the sequence: BB GG RR UU WW
        assert m.vectorize() == "BB GG RR UU WW"

        # With delimiters
        assert m.vectorize(delimit=True) == "(BB) (GG) (RR) (UU) (WW)"


class TestManatext:
    def test_initialization_json_needs_preprocessing(self):
        # Manatext expects {T} to be handled before initialization if it's not a mana symbol
        # because leftovers cause invalidity
        src = "Pay {1}{W}, {T}: Destroy target creature."

        # Without preprocessing: invalid
        mt = Manatext(src, fmt='json')
        assert not mt.valid

        # With preprocessing
        processed_src = utils.to_symbols(src) # converts {T} to T marker
        mt_processed = Manatext(processed_src, fmt='json')
        assert mt_processed.valid
        assert len(mt_processed.costs) == 1 # {1}{W} is a single cost block

    def test_simple_manatext(self):
        # {U} is in charset.
        mt = Manatext("Counter target spell unless its controller pays {1}.", fmt='json')
        assert mt.valid
        assert len(mt.costs) == 1
        assert mt.costs[0].cmc == 1

        # Text should replace cost with marker
        assert utils.reserved_mana_marker in mt.text
        assert "{1}" not in mt.text

    def test_format(self):
        src = "Pay {X}."
        mt = Manatext(src, fmt='json')
        assert mt.format() == "Pay {X}."

        # Forum
        assert mt.format(for_forum=True) == "Pay [mana]X[/mana]."

        # ANSI Color
        # {X} -> {XX} -> format() -> {X}
        # In Manatext, cost.format(ansi_color=True) is called
        colored = mt.format(ansi_color=True)
        expected_cost = utils.colorize("{X}", utils.Ansi.CYAN)
        assert colored == f"Pay {expected_cost}."

    def test_encode(self):
        src = "Pay {X}."
        mt = Manatext(src, fmt='json')
        # 'X' is length 1, so it is encoded as 'XX'
        assert mt.encode() == "Pay {XX}."

    def test_vectorize(self):
        src = "Pay {W}."
        mt = Manatext(src, fmt='json')
        # vectorize puts spaces around special chars and costs
        # {W} -> {WW} -> vectorize -> WW
        # Pay -> Pay
        # . -> . (special char padded)
        vec = mt.vectorize()
        tokens = vec.split()
        assert "WW" in tokens
        assert "Pay" in tokens
        assert "." in tokens
        # Verify order
        assert tokens == ["Pay", "WW", "."]

    def test_invalid_manatext(self):
        # Leftover delimiters make it invalid
        mt = Manatext("Open { brace", fmt='json')
        assert not mt.valid
