import re
from lib import transforms
from lib import utils

def test_text_unpass_1_choice_normal():
    # [&^=Option 1] -> choose one ~\= Option 1
    s = "[&^=Option 1]"
    expected = "choose one " + utils.dash_marker + utils.newline + utils.bullet_marker + " Option 1"
    assert transforms.text_unpass_1_choice(s) == expected

def test_text_unpass_1_choice_exception():
    # [twenty~five=Option A] -> choose twenty~five ~\= Option A
    # twenty~five is the unary conversion of 25 in config
    s = "[twenty~five=Option A]"
    expected = "choose twenty" + utils.dash_marker + "five " + utils.dash_marker + utils.newline + utils.bullet_marker + " Option A"
    assert transforms.text_unpass_1_choice(s) == expected

def test_text_unpass_1_choice_empty_count():
    # [=Option B] -> choose one or both ~\= Option B
    s = "[=Option B]"
    expected = "choose one or both " + utils.dash_marker + utils.newline + utils.bullet_marker + " Option B"
    assert transforms.text_unpass_1_choice(s) == expected

def test_text_unpass_1_choice_multiple():
    # [&^=Opt1] and [&^^=Opt2] -> choose one ~\= Opt1 and choose two ~\= Opt2
    s = "[&^=Opt1] and [&^^=Opt2]"
    res = transforms.text_unpass_1_choice(s)
    assert "choose one" in res
    assert "choose two" in res
    assert "and" in res
    assert res.count(utils.dash_marker) == 2

def test_text_unpass_1_choice_or_more():
    # [ or more=Opt] -> choose one or more ~\= Opt
    s = "[ or more=Opt]"
    expected = "choose one or more " + utils.dash_marker + utils.newline + utils.bullet_marker + " Opt"
    assert transforms.text_unpass_1_choice(s) == expected

def test_text_unpass_1_choice_multi_options():
    s = "[&^=Opt 1=Opt 2]"
    expected = ("choose one " + utils.dash_marker +
                utils.newline + utils.bullet_marker + " Opt 1" +
                utils.newline + utils.bullet_marker + " Opt 2")
    assert transforms.text_unpass_1_choice(s) == expected
