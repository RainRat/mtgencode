from unittest.mock import patch
import lib.manalib as manalib_mod
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

    def test_initialization_unknown_symbol(self):
        # Test parsing an unknown symbol inside valid cost brackets
        m = Manacost("{WW?UU}")
        assert not m.valid

    def test_initialization_nonempty_mana_unary_marker(self):
        # Test parsing when utils.mana_unary_marker is set to a non-empty string in manalib
        with patch.object(manalib_mod.utils, 'mana_unary_marker', '~'):
            m = Manacost("{~^WW}")
            assert m.valid
            assert '~' in m.sequence

    def test_cmc_calculation(self):
        # X is 0
        assert Manacost("{XX}").cmc == 0
        # 2/W (encoded as 2W) is 2
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

    def test_str_and_format(self):
        m = Manacost("{WWUUBBRRGG}")
        assert str(m) == "{W}{U}{B}{R}{G}"
        assert m.format() == "{W}{U}{B}{R}{G}"

        # Forum
        assert m.format(for_forum=True) == "[mana]WUBRG[/mana]"

        # HTML
        html_out = m.format(for_html=True)
        assert "<img class='mana-W'>" in html_out

        # ANSI Color
        colored = m.format(ansi_color=True)
        expected = (utils.colorize("{W}", utils.Ansi.WHITE) +
                    utils.colorize("{U}", utils.Ansi.CYAN) +
                    utils.colorize("{B}", utils.Ansi.MAGENTA) +
                    utils.colorize("{R}", utils.Ansi.RED) +
                    utils.colorize("{G}", utils.Ansi.GREEN))
        assert colored == expected

        # None
        assert Manacost("").format() == ""

    def test_encode(self):
        m = Manacost("{WWUUBBRRGG}")
        assert m.encode() == "{WWUUBBRRGG}"
        assert Manacost("").encode() == ""

        # Randomize
        encoded = m.encode(randomize=True)
        assert len(encoded) == len("{WWUUBBRRGG}")
        assert encoded.startswith("{")
        assert encoded.endswith("}")
        assert sorted(encoded[1:-1]) == sorted("WWUUBBRRGG")

    def test_vectorize(self):
        assert Manacost("").vectorize() == ""
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

    def test_manatext_raw_format(self):
        mt = Manatext("Pay {WW}.\nDraw a card.")
        assert mt.valid
        assert len(mt.costs) == 1
        assert str(mt) == "Pay {W}.\nDraw a card."

    def test_str_and_format(self):
        src = "Pay {X}."
        mt = Manatext(src, fmt='json')
        assert str(mt) == "Pay {X}."
        assert mt.format() == "Pay {X}."

        # Forum
        assert mt.format(for_forum=True) == "Pay [mana]X[/mana]."

        # HTML
        mt_html = Manatext("Pay {1}{W}.\nDraw a card.", fmt='json')
        html_out = mt_html.format(for_html=True)
        assert "<br>\n" in html_out
        assert "<img class=" in html_out

        # ANSI Color
        # {X} -> {XX} -> format() -> {X}
        # In Manatext, cost.format(ansi_color=True) is called
        colored = mt.format(ansi_color=True)
        expected_cost = utils.colorize("{X}", utils.Ansi.BOLD)
        assert colored == f"Pay {expected_cost}."

    def test_encode(self):
        src = "Pay {X}."
        mt = Manatext(src, fmt='json')
        # 'X' is length 1, so it is encoded as 'XX'
        assert mt.encode() == "Pay {XX}."

        mt_multi = Manatext("Pay {WWUU}.", fmt='')
        randomized = mt_multi.encode(randomize=True)
        assert randomized.startswith("Pay {")
        assert randomized.endswith("}.")

    def test_reserved_mana_marker_escaping(self):
        marker_text = f"Text with {utils.reserved_mana_marker} and {{WW}}"
        mt = Manatext(marker_text, fmt='')
        assert mt.valid
        formatted = mt.format()
        assert formatted == f"Text with {utils.reserved_mana_marker} and {{W}}"
        encoded = mt.encode()
        assert encoded == f"Text with {utils.reserved_mana_marker} and {{WW}}"
        vec = mt.vectorize()
        assert utils.reserved_mana_marker in vec

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

        # Matched cost containing invalid mana symbol sets valid to False
        mt_invalid_cost = Manatext("Pay {WW?UU}.", fmt='')
        assert not mt_invalid_cost.valid

    def test_manatext_empty_cost_formatting_and_encoding(self):
        # Test formatting and encoding when a cost in self.costs has none=True
        mt = Manatext("Pay .", fmt='')
        cost = Manacost("")
        mt.costs = [cost]
        mt.text = f"Pay {utils.reserved_mana_marker}."
        assert mt.format() == "Pay ."
        assert mt.encode() == "Pay ."

    def test_manacost_unary_marker_loop_branch(self):
        # Test loop branch when utils.mana_unary_marker is non-empty
        with patch.object(manalib_mod.utils, 'mana_unary_marker', '~'):
            m = Manacost("{~~}")
            assert m.valid
            assert m.sequence == ['~', '~']
