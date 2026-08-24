
import sys
import os

from lib.datalib import plimit
from lib import utils

def test_plimit_ansi_no_truncation():
    s = f"{utils.Ansi.RED}Hello{utils.Ansi.RESET}"
    assert plimit(s, mlen=10) == s

def test_plimit_ansi_truncation_in_pre_text():
    s = f"{utils.Ansi.RED}Hello World{utils.Ansi.RESET}"
    # vlen is 11, mlen is 7. Truncation should happen at 'Hello W'
    expected = f"{utils.Ansi.RED}Hello W[...]{utils.Ansi.RESET}"
    assert plimit(s, mlen=7) == expected

def test_plimit_ansi_truncation_in_remaining():
    s = f"{utils.Ansi.RED}Hello{utils.Ansi.RESET} World"
    # vlen is 11, mlen is 7. 5 chars in 'Hello', 2 more from ' World' -> ' W'
    expected = f"{utils.Ansi.RED}Hello{utils.Ansi.RESET} W[...]{utils.Ansi.RESET}"
    assert plimit(s, mlen=7) == expected

def test_plimit_ansi_truncation_before_any_ansi():
    s = "Hello " + utils.Ansi.RED + "World" + utils.Ansi.RESET
    # mlen = 3, truncation at 'Hel'
    expected = "Hel[...]"
    assert plimit(s, mlen=3) == expected

def test_plimit_ansi_multiple_codes_truncation():
    s = f"{utils.Ansi.BOLD}{utils.Ansi.RED}Color{utils.Ansi.RESET} and {utils.Ansi.GREEN}More{utils.Ansi.RESET}"
    # "Color and More" vlen = 14, mlen = 8 -> "Color an"
    expected = f"{utils.Ansi.BOLD}{utils.Ansi.RED}Color{utils.Ansi.RESET} an[...]{utils.Ansi.RESET}"
    assert plimit(s, mlen=8) == expected

def test_plimit_ansi_truncation_in_remaining_without_ansi():
    s = f"Plain {utils.Ansi.RED}Text{utils.Ansi.RESET} remaining"
    # "Plain Text remaining" vlen = 20, mlen = 12
    # Visible text before last ANSI is "Plain Text" (len 10)
    # Remaining string is " remaining" (len 10)
    # Truncation in remaining at mlen 12 takes " r" (12 - 10 = 2)
    expected = f"Plain {utils.Ansi.RED}Text{utils.Ansi.RESET} r[...]{utils.Ansi.RESET}"
    assert plimit(s, mlen=12) == expected
