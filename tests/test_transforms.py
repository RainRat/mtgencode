import pytest
import re
from lib import transforms, utils, config

# Tests for text_pass_1_strip_rt
def test_text_pass_1_strip_rt_simple():
    input_text = "Destroy target creature. (It can't be regenerated.)"
    expected = "Destroy target creature. "
    assert transforms.text_pass_1_strip_rt(input_text) == expected

def test_text_pass_1_strip_rt_multiple():
    input_text = "Flying (This creature has flying.) Trample (This creature can deal excess damage.)"
    expected = "Flying  Trample "
    assert transforms.text_pass_1_strip_rt(input_text) == expected

def test_text_pass_1_strip_rt_no_parens():
    input_text = "Destroy target creature."
    expected = "Destroy target creature."
    assert transforms.text_pass_1_strip_rt(input_text) == expected

# Tests for text_pass_4c_abilitywords
def test_text_pass_4c_abilitywords_simple():
    # Input should be lowercase as per pipeline
    input_text = "landfall \u2014 whenever a land enters the battlefield..."
    expected = "whenever a land enters the battlefield..."
    assert transforms.text_pass_4c_abilitywords(input_text) == expected

def test_text_pass_4c_abilitywords_boundary():
    # This verifies the fix for the "islandfall" bug (should match whole words only)
    input_text = "islandfall \u2014 effect"
    expected = "islandfall \u2014 effect"
    assert transforms.text_pass_4c_abilitywords(input_text) == expected

def test_text_pass_4c_abilitywords_multiple():
    input_text = "landfall \u2014 effect. metalcraft \u2014 effect."
    expected = "effect. effect."
    assert transforms.text_pass_4c_abilitywords(input_text) == expected

# Tests for text_pass_4b_x
def test_text_pass_4b_x_basic():
    input_text = "~x costs more."
    expected = "-X costs more."
    assert transforms.text_pass_4b_x(input_text) == expected

def test_text_pass_4b_x_replacements():
    assert transforms.text_pass_4b_x("+x") == "+X"
    assert transforms.text_pass_4b_x(" x ") == " X "
    assert transforms.text_pass_4b_x("x:") == "X:"
    assert transforms.text_pass_4b_x("x\u2014") == "X\u2014"

def test_text_pass_4b_x_exclusions():
    # "six target" should remain "six target"
    assert transforms.text_pass_4b_x("six target") == "six target"
    # "avarax" should remain "avarax"
    assert transforms.text_pass_4b_x("avarax") == "avarax"

# Tests for text_pass_5_counters
def test_text_pass_5_counters_time():
    input_text = "remove a time counter from it."
    # Expect: "countertype % time\n" + body with % replacement
    # Note: text_pass_5_counters adds the countertype line at the start.
    # It does not perform newline replacement (that's pass 9).
    expected_start = "countertype % time\n"
    expected_body = "remove a % counter from it."
    result = transforms.text_pass_5_counters(input_text)
    assert result == expected_start + expected_body

def test_text_pass_5_counters_multiple_same():
    input_text = "put a charge counter on it. remove a charge counter."
    expected_start = "countertype % charge\n"
    expected_body = "put a % counter on it. remove a % counter."
    result = transforms.text_pass_5_counters(input_text)
    assert result == expected_start + expected_body

# Tests for text_pass_6_uncast
def test_text_pass_6_uncast_basics():
    assert transforms.text_pass_6_uncast("counter target spell.") == "uncast target spell."
    assert transforms.text_pass_6_uncast("counter all spells.") == "uncast all spells."
    assert transforms.text_pass_6_uncast("can't be countered.") == "can't be uncasted."

# Tests for text_pass_7_choice
def test_text_pass_7_choice_choose_one():
    # Input uses unicode bullets and dash
    input_text = "choose one \u2014\n\u2022 option 1\n\u2022 option 2"

    # Expected:
    # It seems to flatten the choice into one line with spaces instead of newlines.
    expected = "[&^ \u2022 option 1 \u2022 option 2]"
    assert transforms.text_pass_7_choice(input_text) == expected

# Tests for text_pass_8_equip
def test_text_pass_8_equip_move_to_top():
    # equip {3}
    input_text = "Do stuff.\nequip {3}"
    expected = "equip {3}\nDo stuff."
    assert transforms.text_pass_8_equip(input_text) == expected

# Tests for text_pass_11_linetrans
def test_text_pass_11_linetrans_reorder():
    # Separator is utils.newline ('\')
    # Order: prelines (equip/enchant), keylines (no dot), mainlines (dot), postlines (countertype/kicker)

    lines = [
        "destroy target creature.", # mainline
        "flying", # keyline
        "equip {1}", # preline
        "countertype % time", # postline
    ]
    input_text = utils.newline.join(lines)

    expected_lines = [
        "equip {1}", # pre
        "flying", # key
        "destroy target creature.", # main
        "countertype % time", # post
    ]
    expected = utils.newline.join(expected_lines)

    assert transforms.text_pass_11_linetrans(input_text) == expected

def test_text_pass_11_linetrans_levelup_ignore():
    input_text = "level up {1}\nsomething."
    # If "level up" is in text, it returns as is.
    assert transforms.text_pass_11_linetrans(input_text) == input_text

# Tests for Unpasses
def test_text_unpass_1_choice():
    # Unpass functions are used in Card.format(), which happens AFTER unpassing newlines?
    # No, let's check format() in cardlib.py:
    # mtext = transforms.text_unpass_1_choice(mtext, delimit=True)
    # ...
    # mtext = transforms.text_unpass_7_newlines(mtext)

    # So text_unpass_1_choice runs on text with INTERNAL newlines (`\`).

    input_text = "[&^=opt 1=opt 2]" # bullet_marker is '='

    # text_unpass_1_choice constructs new string using `newline` (from utils/config which is `\`).
    # "choose one " + dash_marker
    # + newline + bullet_marker + ' ' + option

    expected = r"choose one ~\= opt 1\= opt 2"
    assert transforms.text_unpass_1_choice(input_text) == expected

def test_text_unpass_2_counters():
    # "countertype % time\n... % ..." -> replace % with time, remove header
    # But unpasses run on internal representation.
    # However, text_pass_5_counters uses ACTUAL newlines ('\n') because it runs BEFORE text_pass_9_newlines.
    # text_unpass_2_counters is called in format(), BEFORE text_unpass_7_newlines.
    # Wait, `format()` calls:
    # mtext = transforms.text_unpass_2_counters(mtext)
    # ...
    # mtext = transforms.text_unpass_7_newlines(mtext)

    # So at the time unpass_2 runs, newlines are still `\` (internal representation).
    # But `text_pass_5_counters` inserts `\n`?
    # No, `text_pass_5_counters` inserts `\n`.
    # Then `text_pass_9_newlines` converts `\n` to `\`.
    # So the encoded text has `\` (backslash).

    # So the input to unpass_2 must use `\`.
    input_text = "countertype % time\\remove a % counter."
    expected = "remove a time counter."
    assert transforms.text_unpass_2_counters(input_text) == expected

def test_text_unpass_3_uncast():
    # "uncast" -> "counter"
    assert transforms.text_unpass_3_uncast("uncast target.") == "counter target."
