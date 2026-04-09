from lib import transforms, utils
import random

def test_name_pass_1_sanitize():
    assert transforms.name_pass_1_sanitize("Wait!") == "Wait"
    assert transforms.name_pass_1_sanitize("Why?") == "Why"
    assert transforms.name_pass_1_sanitize("A-B") == f"A{utils.dash_marker}B"
    assert transforms.name_pass_1_sanitize("100,000") == "one hundred thousand"
    assert transforms.name_pass_1_sanitize("1,000") == "one thousand"
    assert transforms.name_pass_1_sanitize("1996") == "nineteen ninety-six"

def test_name_unpass_1_dashes():
    assert transforms.name_unpass_1_dashes(f"A{utils.dash_marker}B") == "A-B"

def test_text_pass_7_choice_space_ending():
    # To trigger content.endswith(' ') branch at line 402
    input_text = "choose one \u2014\n\u2022 option 1\n"
    res = transforms.text_pass_7_choice(input_text)
    assert res.endswith('\n')
    assert utils.choice_close_delimiter in res

def test_text_pass_8_equip_empty_s():
    # line 447: if equip[-1:] == ' ': equip = equip[0:-1]
    # line 450: if s == '': s = equip
    input_text = "equip {3} "
    res = transforms.text_pass_8_equip(input_text)
    assert res == "equip {3}"

def test_text_pass_8_equip_nonmana_empty_s():
    # line 461: if equip[-1:] == ' ': equip = equip[0:-1]
    # line 464: if s == '': s = equip
    input_text = "equip\u2014creature "
    res = transforms.text_pass_8_equip(input_text)
    assert res == "equip\u2014creature"

    # line 466: else: s = equip.strip() + '\n' + s
    input_text = "Flying\nequip\u2014creature"
    res = transforms.text_pass_8_equip(input_text)
    assert res == "equip\u2014creature\nFlying"

def test_text_pass_9_newlines():
    # line 472
    assert transforms.text_pass_9_newlines("A\nB") == f"A{utils.newline}B"

def test_text_pass_11_linetrans_empty_line():
    # line 494: if line == '': continue
    text = f"flying{utils.newline}{utils.newline}haste"
    res = transforms.text_pass_11_linetrans(text)
    assert res == f"flying{utils.newline}haste"

def test_randomize_lines_triggers_choice():
    # line 611: if line.endswith(utils.choice_close_delimiter): new_mainlines.append(randomize_choice(line))
    # We need it to be in mainlines, so we add a period but it must end with choice_close_delimiter.
    # Wait, if it has a period it goes to mainlines.
    # "Something. [&^= A = B]" ends with ] and has a period.
    line = f"Choose. {utils.choice_open_delimiter}{utils.unary_marker}{utils.unary_counter} {utils.bullet_marker} A {utils.bullet_marker} B{utils.choice_close_delimiter}"
    random.seed(42)
    res = transforms.randomize_lines(line)
    assert utils.choice_open_delimiter in res
    assert "A" in res
    assert "B" in res

def test_text_unpass_1_choice_variants():
    # choicecount 0 (line 653)
    # To reach line 647, we need the overall choice regex to match but number_unary_regex to not match.
    # choice_unpass_regex = [&^.*=.*]
    # number_unary_regex = &^*
    # If we have "&^Something", it matches choice_unpass_regex but not number_unary_regex at the start?
    # Actually number_unary_regex = &^* matches &^.
    # Wait, &^* matches any number of ^.
    # If we have "& Something", it matches choice_unpass_regex and number_unary_regex matches just "&".
    # Then choicecount = from_unary("&") which is 0.

    line0 = f"{utils.choice_open_delimiter}{utils.unary_marker} {utils.bullet_marker} A {utils.bullet_marker} B{utils.choice_close_delimiter}"
    res0 = transforms.text_unpass_1_choice(line0)
    assert "choose one or both" in res0

    # choicecount 2
    line2 = f"{utils.choice_open_delimiter}{utils.unary_marker}{utils.unary_counter}{utils.unary_counter} {utils.bullet_marker} A {utils.bullet_marker} B{utils.choice_close_delimiter}"
    res2 = transforms.text_unpass_1_choice(line2)
    assert "choose two" in res2

    # choicecount 3
    line3 = f"{utils.choice_open_delimiter}{utils.unary_marker}{utils.unary_counter}{utils.unary_counter}{utils.unary_counter} {utils.bullet_marker} A {utils.bullet_marker} B{utils.choice_close_delimiter}"
    res3 = transforms.text_unpass_1_choice(line3)
    assert f"choose {utils.to_unary('3')}" in res3

    # delimit=True
    res_delimit = transforms.text_unpass_1_choice(line2, delimit=True)
    assert res_delimit.startswith(utils.choice_open_delimiter)
    assert res_delimit.endswith(utils.choice_close_delimiter)

def test_text_unpass_2_counters_no_matches():
    # line 689: if not matches: return s
    text = "No counters here."
    assert transforms.text_unpass_2_counters(text) == text

def test_text_unpass_6_cardname():
    assert transforms.text_unpass_6_cardname(f"Cast {utils.this_marker}.", "Shock") == "Cast Shock."

def test_text_unpass_7_newlines():
    assert transforms.text_unpass_7_newlines(f"Line 1{utils.newline}Line 2") == "Line 1\nLine 2"

def test_text_unpass_8_unicode():
    res = transforms.text_unpass_8_unicode(f"A{utils.dash_marker}B{utils.bullet_marker}C")
    assert res == "A\u2014B\u2022C"
