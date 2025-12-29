import unittest
from lib import transforms
from lib import utils

class TestTransforms(unittest.TestCase):

    def test_name_pass_1_sanitize(self):
        self.assertEqual(transforms.name_pass_1_sanitize("Hello!"), "Hello")
        self.assertEqual(transforms.name_pass_1_sanitize("What?"), "What")
        self.assertEqual(transforms.name_pass_1_sanitize("Face-to-Face"), "Face" + utils.dash_marker + "to" + utils.dash_marker + "Face")
        self.assertEqual(transforms.name_pass_1_sanitize("100,000"), "one hundred thousand")
        self.assertEqual(transforms.name_pass_1_sanitize("1,000"), "one thousand")
        self.assertEqual(transforms.name_pass_1_sanitize("1996"), "nineteen ninety-six")

    def test_name_unpass_1_dashes(self):
        s = "Face" + utils.dash_marker + "to" + utils.dash_marker + "Face"
        self.assertEqual(transforms.name_unpass_1_dashes(s), "Face-to-Face")

    def test_text_pass_2_cardname(self):
        name = "dark confidant"
        text = "at the beginning of your upkeep, reveal the top card of your library and put that card into your hand. you lose life equal to its mana value. dark confidant is a 2/1 creature."
        expected = "at the beginning of your upkeep, reveal the top card of your library and put that card into your hand. you lose life equal to its mana value. " + utils.this_marker + " is a 2/1 creature."
        self.assertEqual(transforms.text_pass_2_cardname(text, name), expected)

    def test_text_pass_2_cardname_edge_cases(self):
        # 'sacrifice' is a keyword, shouldn't be replaced unless it's the card name
        # transforms and cardlib expect lowercase inputs

        # Test 'sacrifice' card name
        text = "sacrifice a creature."
        expected = utils.this_marker + " a creature."
        self.assertEqual(transforms.text_pass_2_cardname(text, "sacrifice"), expected)

        # Test 'fear' card name - explicit skip
        text = "fear cannot be blocked except by artifact creatures and black creatures."
        self.assertEqual(transforms.text_pass_2_cardname(text, "fear"), text)

        # Test legend nicknames
        name = "skithiryx, the blight dragon"
        text = "flying, infect, haste. regenerate skithiryx."
        expected = "flying, infect, haste. regenerate " + utils.this_marker + "."
        self.assertEqual(transforms.text_pass_2_cardname(text, name), expected)

        # Test overrides
        name = "crovax the cursed"
        text = "crovax enters the battlefield with four +1/+1 counters on it."
        expected = utils.this_marker + " enters the battlefield with four +1/+1 counters on it."
        self.assertEqual(transforms.text_pass_2_cardname(text, name), expected)

        # Test planeswalker pronouns
        name = "jace beleren"
        text = "prevent all damage that would be dealt to him this turn."
        expected = "prevent all damage that would be dealt to " + utils.this_marker + " this turn."
        self.assertEqual(transforms.text_pass_2_cardname(text, name), expected)

    def test_text_pass_7_choice(self):
        # This function runs AFTER dash fix (text_pass_4a_dashes) but BEFORE newlines (text_pass_9_newlines)
        # It expects \n and \u2022 (bullet)
        # cardlib passes lowercased text with unicode characters preserved (except those replaced by earlier passes)

        bullet = "\u2022"
        prefix = "choose one \u2014" # Em dash
        text = prefix + "\n" + bullet + " mode a\n" + bullet + " mode b"

        # The choice pass replaces this structure with [1 mode a mode b] (formatted)

        res = transforms.text_pass_7_choice(text)

        # It should contain the choice delimiters.
        self.assertIn(utils.choice_open_delimiter, res)
        self.assertIn(utils.choice_close_delimiter, res)

        # Verify unary count for 1
        unary_1 = utils.unary_marker + utils.unary_counter
        self.assertIn(unary_1, res)

    def test_text_pass_5_counters(self):
        # Expects "time counter" etc.
        text = "put a time counter on it."
        # It replaces whole words.
        res = transforms.text_pass_5_counters(text)

        # It replaces the counter name with `counter_marker + ' counter'`
        # And prepends `countertype % time\n`

        self.assertIn("countertype " + utils.counter_marker + " time", res)
        self.assertIn("put a " + utils.counter_marker + " counter on it.", res)

    def test_text_pass_6_uncast(self):
        text = "counter target spell."
        expected = utils.counter_rename + " target spell."
        self.assertEqual(transforms.text_pass_6_uncast(text), expected)

        text = "put a +1/+1 counter on target creature." # Should NOT replace this 'counter'
        self.assertEqual(transforms.text_pass_6_uncast(text), text)

    def test_text_pass_4c_abilitywords(self):
        # "Landfall — Whenever a land enters..."
        # abilitywords list includes 'landfall'.
        # Expects: "Whenever a land enters..."
        dash = "\u2014"
        text = "landfall " + dash + " whenever a land enters the battlefield under your control, +1/+1."
        expected = "whenever a land enters the battlefield under your control, +1/+1."
        self.assertEqual(transforms.text_pass_4c_abilitywords(text), expected)

    def test_text_pass_8_equip(self):
        # Moves equip to top.
        # "Equipped creature gets +1/+1.\nEquip {1}"
        # transforms expect lowercase usually?
        # let's try lowercase.
        # utils.mana_json_regex handles {1}.

        text = "equipped creature gets +1/+1.\nequip {1}"
        expected = "equip {1}\nequipped creature gets +1/+1."
        self.assertEqual(transforms.text_pass_8_equip(text), expected)

    def test_text_pass_11_linetrans(self):
        # Reorders:
        # prelines: equip, enchant
        # keylines: keywords (no period)
        # mainlines: sentences (period)
        # postlines: countertype, kicker

        # Input mixed:
        # "deal 2 damage.\nflying\nequip {1}\nkicker {R}"

        # Expected order:
        # equip {1} (pre)
        # flying (key)
        # deal 2 damage. (main)
        # kicker {R} (post)

        text = "deal 2 damage." + utils.newline + "flying" + utils.newline + "equip {1}" + utils.newline + "kicker {r}"
        # text_pass_11_linetrans uses utils.newline (\n usually).
        # Note: text_pass_8_equip might have already moved equip?
        # But here we test linetrans in isolation.

        res = transforms.text_pass_11_linetrans(text)
        lines = res.split(utils.newline)
        self.assertEqual(lines[0], "equip {1}")
        self.assertEqual(lines[1], "flying")
        self.assertEqual(lines[2], "deal 2 damage.")
        self.assertEqual(lines[3], "kicker {r}")

    def test_text_pass_1_strip_rt_bug(self):
        # The previous bug was greedy regex re.sub(r'\(.*\)', '', s) which stripped everything between first ( and last )
        # Current logic is non-greedy re.sub(r'\(.*?\)', '', s)
        text = "target creature (this effect lasts until end of turn) gets +1/+1 (counters)."
        # Expected behavior: intermediate text is preserved
        expected = "target creature  gets +1/+1 ."
        self.assertEqual(transforms.text_pass_1_strip_rt(text), expected)

    def test_text_pass_4b_x(self):
        # Tests standardizing 'X'
        # x_marker is 'X', dash_marker is '~'

        # ~x -> -X
        self.assertEqual(transforms.text_pass_4b_x(utils.dash_marker + "x"), "-" + utils.x_marker)
        # +x -> +X
        self.assertEqual(transforms.text_pass_4b_x("+x"), "+" + utils.x_marker)
        # " x " -> " X "
        self.assertEqual(transforms.text_pass_4b_x(" x "), " " + utils.x_marker + " ")
        # x: -> X:
        self.assertEqual(transforms.text_pass_4b_x("x:"), utils.x_marker + ":")
        # x~ -> X~
        self.assertEqual(transforms.text_pass_4b_x("x" + utils.dash_marker), utils.x_marker + utils.dash_marker)
        # x\u2014 -> X\u2014
        self.assertEqual(transforms.text_pass_4b_x("x\u2014"), utils.x_marker + "\u2014")
        # x. -> X.
        self.assertEqual(transforms.text_pass_4b_x("x."), utils.x_marker + ".")
        # x, -> X,
        self.assertEqual(transforms.text_pass_4b_x("x,"), utils.x_marker + ",")
        # x is -> X is
        self.assertEqual(transforms.text_pass_4b_x("x is"), utils.x_marker + " is")
        # x can't -> X can't
        self.assertEqual(transforms.text_pass_4b_x("x can't"), utils.x_marker + " can't")
        # x/x -> X/X
        self.assertEqual(transforms.text_pass_4b_x("x/x"), utils.x_marker + "/" + utils.x_marker)
        # x target -> X target
        self.assertEqual(transforms.text_pass_4b_x("x target"), utils.x_marker + " target")
        # six target -> six target (regression test)
        self.assertEqual(transforms.text_pass_4b_x("six target"), "six target")
        # avaraX -> avarax (regression test)
        self.assertEqual(transforms.text_pass_4b_x("avara" + utils.x_marker), "avarax")

    def test_text_unpass_1_choice(self):
        # Input: "[&^=Option A=Option B]" (encoded choice)
        # Expected: "choose one ~\n= Option A\n= Option B"
        # markers: ~ is dash_marker, = is bullet_marker

        # Construct encoded string manually to avoid dependency on pass logic
        # Count 1: &^
        encoded = (utils.choice_open_delimiter +
                   utils.unary_marker + utils.unary_counter +
                   utils.bullet_marker + "Option A" +
                   utils.bullet_marker + "Option B" +
                   utils.choice_close_delimiter)

        expected = ("choose one " + utils.dash_marker +
                    utils.newline + utils.bullet_marker + " Option A" +
                    utils.newline + utils.bullet_marker + " Option B")

        self.assertEqual(transforms.text_unpass_1_choice(encoded), expected)

        # Test "choose two" (Count 2: &^^)
        encoded_2 = (utils.choice_open_delimiter +
                   utils.unary_marker + utils.unary_counter + utils.unary_counter +
                   utils.bullet_marker + "Opt1" +
                   utils.bullet_marker + "Opt2" +
                   utils.choice_close_delimiter)

        expected_2 = ("choose two " + utils.dash_marker +
                    utils.newline + utils.bullet_marker + " Opt1" +
                    utils.newline + utils.bullet_marker + " Opt2")

        self.assertEqual(transforms.text_unpass_1_choice(encoded_2), expected_2)

if __name__ == '__main__':
    unittest.main()
