from lib import transforms, utils

def test_unpass_choice_one_or_more_collision():
    # Verify fix for choose one or more vs choose one or both

    # 1. choose one or both
    both_in = "choose one or both \u2014\n\u2022 opt1"
    both_enc = transforms.text_pass_7_choice(both_in)
    both_enc_ascii = utils.to_ascii(both_enc)
    both_out = transforms.text_unpass_1_choice(both_enc_ascii)
    assert "choose one or both" in both_out

    # 2. choose one or more
    more_in = "choose one or more \u2014\n\u2022 opt1"
    more_enc = transforms.text_pass_7_choice(more_in)
    more_enc_ascii = utils.to_ascii(more_enc)
    more_out = transforms.text_unpass_1_choice(more_enc_ascii)

    # Correct behavior: unpasses to "choose one or more"
    assert "choose one or more" in more_out
    assert "choose one or both" not in more_out

def test_unpass_choice_suffix_loss():
    # Verify fix for loss of suffixes during unpassing
    # Input: choose one that hasn't been chosen \u2014\n\u2022 opt1

    input_text = "choose one that hasn't been chosen \u2014\n\u2022 opt1"
    encoded = transforms.text_pass_7_choice(input_text)
    encoded_ascii = utils.to_ascii(encoded)
    decoded = transforms.text_unpass_1_choice(encoded_ascii)

    # Correct behavior: preserves suffix
    assert "choose one" in decoded
    assert "that hasn't been chosen" in decoded

def test_separate_lines_dash_no_spaces():
    # Covers lib/transforms.py:588-597
    # Lines with dash_marker but no spaces
    text = utils.newline.join([
        f"equip{utils.dash_marker}creature.",
        f"cycling{utils.dash_marker}{{2}}.",
        f"cumulative{utils.dash_marker}upkeep."
    ])
    # separate_lines is called by randomize_lines
    # But it returns prelines, keylines, mainlines, costlines, postlines
    pre, key, main, cost, post = transforms.separate_lines(text)

    assert any("equip" in l for l in pre)
    assert any("cycling" in l for l in cost)
    assert any("cumulative" in l for l in key)

def test_separate_lines_monstrosity():
    # Covers lib/transforms.py:598-599
    text = "{3}{R}: monstrosity 3. (If this creature isn't monstrous...)"
    pre, key, main, cost, post = transforms.separate_lines(text)
    assert any("monstrosity" in l for l in cost)

def test_randomize_choice_few_options():
    # Covers lib/transforms.py:615-616
    # Only one option
    line = "[&^ = only one]"
    result = transforms.randomize_choice(line)
    assert result == line

def test_text_pass_4a_dashes_level_up():
    # Covers lib/transforms.py:121-127
    # level 1-2
    # 1 -> &^
    # 2 -> &^^
    s1 = "level &^-&^^"
    res1 = transforms.text_pass_4a_dashes(s1)
    assert f"&^{utils.dash_marker}&" in res1

    # level 1+
    s2 = "level &^+"
    res2 = transforms.text_pass_4a_dashes(s2)
    assert f"&^{utils.dash_marker}" in res2

def test_text_pass_8_equip_nonmana():
    # Covers lib/transforms.py:480-490
    input_text = "equip\u2014Discard a card."
    expected = "equip\u2014Discard a card."
    assert transforms.text_pass_8_equip(input_text) == expected

def test_text_pass_11_linetrans_dash_no_spaces():
    # Covers lib/transforms.py:536-541
    text = "equip\u2014creature.\nkicker\u2014{R}.\nflying\u2014haste."
    # We need to replace \n with newline marker
    text = text.replace('\n', utils.newline)
    res = transforms.text_pass_11_linetrans(text)
    # pre: equip, post: kicker, key: flying
    # order: pre, key, main, post.
    # So: equip, flying, kicker.
    assert res.startswith("equip")
    assert "flying" in res.split(utils.newline)[1]
    assert res.endswith("kicker\u2014{R}.")

def test_randomize_choice_no_choices():
    # Covers lib/transforms.py:611
    line = "No choices here."
    assert transforms.randomize_choice(line) == line

def test_separate_lines_other_dash():
    # Covers lib/transforms.py:597
    text = f"Something.{utils.newline}Other{utils.dash_marker}stuff."
    pre, key, main, cost, post = transforms.separate_lines(text)
    assert any("Other" in l for l in main)
