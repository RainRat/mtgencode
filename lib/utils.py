import re

# Utilities for handling unicode, unary numbers, mana costs, and special symbols.
# For convenience we redefine everything from config so that it can all be accessed
# from the utils module.

import config

# special chunk of text that Magic Set Editor 2 requires at the start of all set files.
mse_prepend = 'mse version: 0.3.8\ngame: magic\nstylesheet: m15\nset info:\n\tsymbol:\nstyling:\n\tmagic-m15:\n\t\ttext box mana symbols: magic-mana-small.mse-symbol-font\n\t\toverlay:\n\tmagic-m15-clear:\n\t\ttext box mana symbols: magic-mana-small.mse-symbol-font\n\t\toverlay: \n\tmagic-m15-extra-improved:\n\t\ttext box mana symbols: magic-mana-small.mse-symbol-font\n\t\tpt box symbols: magic-pt-symbols-extra.mse-symbol-font\n\t\toverlay: \n\tmagic-m15-planeswalker:\n\t\ttext box mana symbols: magic-mana-small.mse-symbol-font\n\t\toverlay: \n\tmagic-m15-planeswalker-promo-black:\n\t\ttext box mana symbols: magic-mana-small.mse-symbol-font\n\t\toverlay: \n\tmagic-m15-promo-dka:\n\t\ttext box mana symbols: magic-mana-small.mse-symbol-font\n\t\toverlay: \n\tmagic-m15-token-clear:\n\t\ttext box mana symbols: magic-mana-small.mse-symbol-font\n\t\toverlay: \n\tmagic-new-planeswalker:\n\t\ttext box mana symbols: magic-mana-small.mse-symbol-font\n\t\toverlay: \n\tmagic-new-planeswalker-4abil:\n\t\ttext box mana symbols: magic-mana-small.mse-symbol-font\n\t\toverlay: \n\tmagic-new-planeswalker-clear:\n\t\ttext box mana symbols: magic-mana-small.mse-symbol-font\n\t\toverlay: \n\tmagic-new-planeswalker-promo-black:\n\t\ttext box mana symbols: magic-mana-small.mse-symbol-font\n\t\toverlay: \n'

# special chunk of text to start an HTML document.
import html_extra_data
segment_ids = html_extra_data.id_lables
html_prepend = html_extra_data.html_prepend
html_append = "\n</body>\n</html>"

# encoding formats we know about
formats = [
    'std',
    'named',
    'noname',
    'rfields',
    'old',
    'norarity',
    'vec',
    'custom',
]

# separators
cardsep = config.cardsep
fieldsep = config.fieldsep
bsidesep = config.bsidesep
newline = config.newline

# special indicators
dash_marker = config.dash_marker
bullet_marker = config.bullet_marker
this_marker = config.this_marker
counter_marker = config.counter_marker
reserved_marker = config.reserved_marker
reserved_mana_marker = config.reserved_mana_marker
choice_open_delimiter = config.choice_open_delimiter
choice_close_delimiter = config.choice_close_delimiter
x_marker = config.x_marker
tap_marker = config.tap_marker
untap_marker = config.untap_marker
rarity_common_marker = config.rarity_common_marker
rarity_uncommon_marker = config.rarity_uncommon_marker
rarity_rare_marker = config.rarity_rare_marker
rarity_mythic_marker = config.rarity_mythic_marker
rarity_special_marker = config.rarity_special_marker
rarity_basic_land_marker = config.rarity_basic_land_marker

json_rarity_map = {
    'Common' : rarity_common_marker,
    'common' : rarity_common_marker,
    'Uncommon' : rarity_uncommon_marker,
    'uncommon' : rarity_uncommon_marker,
    'Rare' : rarity_rare_marker,
    'rare' : rarity_rare_marker,
    'Mythic Rare' : rarity_mythic_marker,
    'Mythic' : rarity_mythic_marker,
    'mythic' : rarity_mythic_marker,
    'Special' : rarity_special_marker,
    'special' : rarity_special_marker,
    'Basic Land' : rarity_basic_land_marker,
}
json_rarity_unmap = {v: k for k, v in json_rarity_map.items()}

# unambiguous synonyms
counter_rename = config.counter_rename

# field labels
field_label_name = config.field_label_name
field_label_rarity = config.field_label_rarity
field_label_cost = config.field_label_cost
field_label_supertypes = config.field_label_supertypes
field_label_types = config.field_label_types
field_label_subtypes = config.field_label_subtypes
field_label_loyalty = config.field_label_loyalty
field_label_pt = config.field_label_pt
field_label_text = config.field_label_text

# additional fields we add to the json cards
json_field_bside = config.json_field_bside
json_field_set_name = config.json_field_set_name
json_field_info_code = config.json_field_info_code

# unicode / ascii conversion
unicode_trans = {
    '\u2014': dash_marker,  # unicode long dash
    '\u2022': bullet_marker,  # unicode bullet
    '\u2019': '"',  # single quote
    '\u2018': '"',  # single quote
    '\u2212': '-',  # minus sign
    '\xe6': 'ae',  # ae symbol
    '\xfb': 'u',  # u with caret
    '\xfa': 'u',  # u with accent
    '\xfc': 'u',  # u with umlaut
    '\xe9': 'e',  # e with accent
    '\xe1': 'a',  # a with accent
    '\xe0': 'a',  # a with accent going the other way
    '\xe2': 'a',  # a with caret
    '\xf6': 'o',  # o with umlaut
    '\xed': 'i',  # i with accent
    '\u03c0' : 'pi',  # pi
    '\xae' : 'r', # Registered trademark as r
    '\xbd' : '1/2', # 1/2 unicode to string
    '\u221e': 'inf',  # infinity
    '\u2610': 'na'  # ballot box as na
}

# this one is one-way only
_ascii_trans_table = str.maketrans(unicode_trans)

def to_ascii(s):
    return s.translate(_ascii_trans_table)

# unary numbers
unary_marker = config.unary_marker
unary_counter = config.unary_counter
unary_max = config.unary_max
unary_exceptions = config.unary_exceptions

def to_unary(s, warn = False):
    def replace_number(match):
        n = match.group(0)
        i = int(n)
        if i in unary_exceptions:
            return unary_exceptions[i]
        elif i > unary_max:
            # original code capped it at unary_max (20)
            if warn:
                print(s)
            i = unary_max
            return unary_marker + unary_counter * i
        else:
            return unary_marker + unary_counter * i

    return re.sub(r'[0123456789]+', replace_number, s)

def from_unary(s):
    pattern = re.escape(unary_marker) + re.escape(unary_counter) + '*'

    def replace_unary(match):
        n = match.group(0)
        i = (len(n) - len(unary_marker)) // len(unary_counter)
        return str(i)

    return re.sub(pattern, replace_unary, s)

# mana syntax
mana_open_delimiter = '{'
mana_close_delimiter = '}'
mana_json_open_delimiter = mana_open_delimiter
mana_json_close_delimiter = mana_close_delimiter
mana_json_hybrid_delimiter = '/'
mana_forum_open_delimiter = '[mana]'
mana_forum_close_delimiter = '[/mana]'
mana_html_open_delimiter = "<img class='mana-"
mana_html_close_delimiter = "'>"
mana_html_hybrid_delimiter = '-'
mana_unary_marker = '' # if the same as unary_marker, from_unary WILL replace numbers in mana costs
mana_unary_counter = unary_counter

# The decoding from mtgjson format is dependent on the specific structure of
# these internally used mana symbol strings, so if you want to change them you'll
# also have to change the json decoding functions.

# standard mana symbol set
mana_W = 'W' # single color
mana_U = 'U'
mana_B = 'B'
mana_R = 'R'
mana_G = 'G'
mana_P = 'P' # colorless phyrexian
mana_S = 'S' # snow
mana_X = 'X' # colorless X
mana_C = 'C' # colorless only 'eldrazi'
mana_E = 'E' # energy
mana_WP = 'WP' # single color phyrexian
mana_UP = 'UP'
mana_BP = 'BP'
mana_RP = 'RP'
mana_GP = 'GP'
mana_2W = '2W' # single color hybrid
mana_2U = '2U'
mana_2B = '2B'
mana_2R = '2R'
mana_2G = '2G'
mana_WU = 'WU' # dual color hybrid
mana_WB = 'WB'
mana_RW = 'RW'
mana_GW = 'GW'
mana_UB = 'UB'
mana_UR = 'UR'
mana_GU = 'GU'
mana_BR = 'BR'
mana_BG = 'BG'
mana_RG = 'RG'
mana_GWP = 'GWP'
mana_RGP = 'RGP'
mana_RWP = 'RWP'
mana_GUP = 'GUP'
mana_CW = 'CW'
mana_CU = 'CU'
mana_CB = 'CB'
mana_CR = 'CR'
mana_CG = 'CG'
# alternative order symbols
mana_WP_alt = 'PW' # single color phyrexian
mana_UP_alt = 'PU'
mana_BP_alt = 'PB'
mana_RP_alt = 'PR'
mana_GP_alt = 'PG'
mana_2W_alt = 'W2' # single color hybrid
mana_2U_alt = 'U2'
mana_2B_alt = 'B2'
mana_2R_alt = 'R2'
mana_2G_alt = 'G2'
mana_WU_alt = 'UW' # dual color hybrid
mana_WB_alt = 'BW'
mana_RW_alt = 'WR'
mana_GW_alt = 'WG'
mana_UB_alt = 'BU'
mana_UR_alt = 'RU'
mana_GU_alt = 'UG'
mana_BR_alt = 'RB'
mana_BG_alt = 'GB'
mana_RG_alt = 'GR'
# special 
mana_2 = '2' # use with 'in' to identify single color hybrid

# master symbol lists
mana_syms = [
    mana_W,
    mana_U,
    mana_B,
    mana_R,
    mana_G,
    mana_P,
    mana_S,
    mana_X,
    mana_C,
    mana_E,
    mana_WP,
    mana_UP,
    mana_BP,
    mana_RP,
    mana_GP,
    mana_2W,
    mana_2U,
    mana_2B,
    mana_2R,
    mana_2G,
    mana_WU,
    mana_WB,
    mana_RW,
    mana_GW,
    mana_UB,
    mana_UR,
    mana_GU,
    mana_BR,
    mana_BG,
    mana_RG,
    mana_GWP,
    mana_RGP,
    mana_RWP,
    mana_GUP,
    mana_CW,
    mana_CU,
    mana_CB,
    mana_CR,
    mana_CG,
]
mana_symalt = [
    mana_WP_alt,
    mana_UP_alt,
    mana_BP_alt,
    mana_RP_alt,
    mana_GP_alt,
    mana_2W_alt,
    mana_2U_alt,
    mana_2B_alt,
    mana_2R_alt,
    mana_2G_alt,
    mana_WU_alt,
    mana_WB_alt,
    mana_RW_alt,
    mana_GW_alt,
    mana_UB_alt,
    mana_UR_alt,
    mana_GU_alt,
    mana_BR_alt,
    mana_BG_alt,
    mana_RG_alt,
]
mana_symall = mana_syms + mana_symalt

# alt symbol conversion
def mana_alt(sym):
    if not sym in mana_symall:
        raise ValueError('invalid mana symbol for mana_alt(): ' + repr(sym))
    if len(sym) < 2:
        return sym
    else:
        return sym[::-1]

# produce intended neural net output format
def mana_sym_to_encoding(sym):
    if not sym in mana_symall:
        raise ValueError('invalid mana symbol for mana_sym_to_encoding(): ' + repr(sym))
    if len(sym) < 2:
        return sym * 2
    else:
        return sym

# produce json formatting used in mtgjson
def mana_sym_to_json(sym):
    if not sym in mana_symall:
        raise ValueError('invalid mana symbol for mana_sym_to_json(): ' + repr(sym))
    if len(sym) < 2:
        return mana_json_open_delimiter + sym + mana_json_close_delimiter
    elif len(sym) > 2:
        return (mana_json_open_delimiter + sym[0] + mana_json_hybrid_delimiter
                + sym[1] + mana_json_hybrid_delimiter + sym[2] + mana_json_close_delimiter)
    else:
        return (mana_json_open_delimiter + sym[0] + mana_json_hybrid_delimiter
                + sym[1] + mana_json_close_delimiter)

# produce pretty formatting that renders on mtgsalvation forum
# converts individual symbols; surrounding [mana][/mana] tags are added elsewhere
def mana_sym_to_forum(sym):
    if not sym in mana_symall:
        raise ValueError('invalid mana symbol for mana_sym_to_forum(): ' + repr(sym))
    if sym in mana_symalt:
        sym = mana_alt(sym)
    if len(sym) < 2:
        return sym
    else:
        return mana_json_open_delimiter + sym + mana_json_close_delimiter

# forward symbol tables for encoding
mana_syms_encode = {sym : mana_sym_to_encoding(sym) for sym in mana_syms}
mana_symalt_encode = {sym : mana_sym_to_encoding(sym) for sym in mana_symalt}
mana_symall_encode = {sym : mana_sym_to_encoding(sym) for sym in mana_symall}
mana_syms_jencode = {sym : mana_sym_to_json(sym) for sym in mana_syms}
mana_symalt_jencode = {sym : mana_sym_to_json(sym) for sym in mana_symalt}
mana_symall_jencode = {sym : mana_sym_to_json(sym) for sym in mana_symall}

# reverse symbol tables for decoding
mana_syms_decode = {mana_sym_to_encoding(sym) : sym for sym in mana_syms}
mana_symalt_decode = {mana_sym_to_encoding(sym) : sym for sym in mana_symalt}
mana_symall_decode = {mana_sym_to_encoding(sym) : sym for sym in mana_symall}
mana_syms_jdecode = {mana_sym_to_json(sym) : sym for sym in mana_syms}
mana_symalt_jdecode = {mana_sym_to_json(sym) : sym for sym in mana_symalt}
mana_symall_jdecode = {mana_sym_to_json(sym) : sym for sym in mana_symall}

# going straight from json to encoding and vice versa
def mana_encode_direct(jsym):
    if not jsym in mana_symall_jdecode:
        raise ValueError('json string not found in decode table for mana_encode_direct(): '
                         + repr(jsym))
    else:
        return mana_symall_encode[mana_symall_jdecode[jsym]]

def mana_decode_direct(sym):
    if not sym in mana_symall_decode:
        raise ValueError('mana symbol not found in decode table for mana_decode_direct(): '
                         + repr(sym))
    else:
        return mana_symall_jencode[mana_symall_decode[sym]]

# hacked in support for mtgsalvation forum
def mana_decode_direct_forum(sym):
    if not sym in mana_symall_decode:
        raise ValueError('mana symbol not found in decode table for mana_decode_direct_forum(): '
                         + repr(sym))
    else:
        return mana_sym_to_forum(mana_symall_decode[sym])

# processing entire strings
def unique_string(s):
    return ''.join(set(s))

mana_charset_special = mana_unary_marker + mana_unary_counter
mana_charset_strict = unique_string(''.join(mana_symall) + mana_charset_special)
mana_charset = unique_string(mana_charset_strict + mana_charset_strict.lower())

mana_regex_strict = (re.escape(mana_open_delimiter) + '['
                     + re.escape(mana_charset_strict) 
                     + ']*' + re.escape(mana_close_delimiter))
mana_regex = (re.escape(mana_open_delimiter) + '['
              + re.escape(mana_charset)
              + ']*' + re.escape(mana_close_delimiter))

# as a special case, we let unary or decimal numbers exist in json mana strings
mana_json_charset_special = ('0123456789' + unary_marker + unary_counter)
mana_json_charset_strict = unique_string(''.join(mana_symall_jdecode) + mana_json_charset_special)
mana_json_charset = unique_string(mana_json_charset_strict + mana_json_charset_strict.lower())

# note that json mana strings can't be empty between the delimiters
mana_json_regex_strict = (re.escape(mana_json_open_delimiter) + '['
                     + re.escape(mana_json_charset_strict) 
                     + ']+' + re.escape(mana_json_close_delimiter))
mana_json_regex = (re.escape(mana_json_open_delimiter) + '['
               + re.escape(mana_json_charset)
               + ']+' + re.escape(mana_json_close_delimiter))

number_decimal_regex = r'[0123456789]+'
number_unary_regex = re.escape(unary_marker) + re.escape(unary_counter) + '*'
mana_decimal_regex = (re.escape(mana_json_open_delimiter) + number_decimal_regex 
                      + re.escape(mana_json_close_delimiter))
mana_unary_regex = (re.escape(mana_json_open_delimiter) + number_unary_regex
                    + re.escape(mana_json_close_delimiter))

# regex for mana_translate
mana_translate_regex = re.compile('|'.join(
    [mana_unary_regex, mana_decimal_regex] +
    [re.escape(s) for s in sorted(mana_symall_jdecode, key=len, reverse=True)]
))

# convert a json mana string to the proper encoding
def mana_translate(jmanastr):
    def replace_token(match):
        token = match.group(0)
        if token in mana_symall_jdecode:
            return mana_encode_direct(token)

        inner = token[len(mana_json_open_delimiter):-len(mana_json_close_delimiter)]

        if inner.isdigit():
             i = int(inner)
             return mana_unary_marker + mana_unary_counter * i

        if inner.startswith(unary_marker):
             i = (len(inner) - len(unary_marker)) // len(unary_counter)
             return mana_unary_marker + mana_unary_counter * i

        return token

    manastr = re.sub(mana_translate_regex, replace_token, jmanastr)
    return mana_open_delimiter + manastr + mana_close_delimiter

# convert an encoded mana string back to json
mana_symlen_min = min([len(sym) for sym in mana_symall_decode])
mana_symlen_max = max([len(sym) for sym in mana_symall_decode])
def mana_untranslate(manastr, for_forum = False, for_html = False):
    inner = manastr[1:-1]
    jmanastr = ''
    colorless_total = 0
    idx = 0
    while idx < len(inner):
        # taking this branch is an infinite loop if unary_marker is empty
        if len(mana_unary_marker) > 0 and inner[idx:idx+len(mana_unary_marker)] == mana_unary_marker:
            idx += len(mana_unary_marker)
        elif inner[idx:idx+len(mana_unary_counter)] == mana_unary_counter:
            idx += len(mana_unary_counter)
            colorless_total += 1
        else:
            old_idx = idx
            for symlen in range(mana_symlen_max, mana_symlen_min - 1, -1):
                sym = inner[idx:idx+symlen]
                if sym in mana_symall_decode:
                    idx += symlen
                    if for_html:
                        decoded = mana_decode_direct(sym)
                        decoded = decoded.replace(mana_open_delimiter, mana_html_open_delimiter)
                        decoded = decoded.replace(mana_close_delimiter, mana_html_close_delimiter)
                        decoded = decoded.replace(mana_json_hybrid_delimiter, mana_html_hybrid_delimiter)
                        jmanastr = jmanastr + decoded
                    elif for_forum:
                        jmanastr = jmanastr + mana_decode_direct_forum(sym)
                    else:
                        jmanastr = jmanastr + mana_decode_direct(sym)
                    break
            # otherwise we'll go into an infinite loop if we see a symbol we don't know
            if idx == old_idx:
                idx += 1
    
    if for_html:
        if jmanastr == '':
            return mana_html_open_delimiter + str(colorless_total) + mana_html_close_delimiter
        else:
            return (('' if colorless_total == 0
                     else mana_html_open_delimiter + str(colorless_total) + mana_html_close_delimiter)
                    + jmanastr)

    elif for_forum:
        if jmanastr == '':
            return mana_forum_open_delimiter + str(colorless_total) + mana_forum_close_delimiter
        else:
            return (mana_forum_open_delimiter + ('' if colorless_total == 0 
                                                 else str(colorless_total))
                    + jmanastr + mana_forum_close_delimiter)
    else:
        if jmanastr == '':
            return mana_json_open_delimiter + str(colorless_total) + mana_json_close_delimiter
        else:
            return (('' if colorless_total == 0 else 
                     mana_json_open_delimiter + str(colorless_total) + mana_json_close_delimiter)
                    + jmanastr)

# finally, replacing all instances in a string
# notice the calls to .upper(), this way we recognize lowercase symbols as well just in case
def to_mana(s):
    return re.sub(mana_json_regex, lambda m: mana_translate(m.group(0).upper()), s)


def from_mana(s, for_forum=False, for_html=False):
    return re.sub(mana_regex, lambda m: mana_untranslate(m.group(0).upper(), for_forum=for_forum, for_html=for_html), s)
    
# Translation could also be accomplished using the datamine.Manacost object's
# display methods, but these direct string transformations are retained for
# quick scripting and convenience (and used under the hood by that class to
# do its formatting).

# more convenience features for formatting tap / untap symbols
json_symbol_tap = tap_marker
json_symbol_untap = untap_marker

json_symbol_trans = {
    mana_json_open_delimiter + json_symbol_tap + mana_json_close_delimiter : tap_marker,
    mana_json_open_delimiter + json_symbol_tap.lower() + mana_json_close_delimiter : tap_marker,
    mana_json_open_delimiter + json_symbol_untap + mana_json_close_delimiter : untap_marker,
    mana_json_open_delimiter + json_symbol_untap.lower() + mana_json_close_delimiter : untap_marker,
}
symbol_trans = {
    tap_marker : mana_json_open_delimiter + json_symbol_tap + mana_json_close_delimiter,
    untap_marker : mana_json_open_delimiter + json_symbol_untap + mana_json_close_delimiter,
}
symbol_forum_trans = {
    tap_marker : mana_forum_open_delimiter + json_symbol_tap + mana_forum_close_delimiter,
    untap_marker : mana_forum_open_delimiter + json_symbol_untap + mana_forum_close_delimiter,
}
symbol_html_trans = {
    tap_marker : mana_html_open_delimiter + json_symbol_tap + mana_html_close_delimiter,
    untap_marker : mana_html_open_delimiter + json_symbol_untap + mana_html_close_delimiter,
}

json_symbol_regex = (re.escape(mana_json_open_delimiter) + '['
                     + json_symbol_tap + json_symbol_tap.lower()
                     + json_symbol_untap + json_symbol_untap.lower()
                     + ']' + re.escape(mana_json_close_delimiter))
symbol_regex = '[' + tap_marker + untap_marker + ']'

def to_symbols(s):
    return re.sub(json_symbol_regex, lambda m: json_symbol_trans[m.group(0)], s)


def from_symbols(s, for_forum=False, for_html=False):
    def replace(match):
        sym = match.group(0)
        if for_html:
            return symbol_html_trans[sym]
        elif for_forum:
            return symbol_forum_trans[sym]
        else:
            return symbol_trans[sym]
    return re.sub(symbol_regex, replace, s)

unletters_regex = r"[^abcdefghijklmnopqrstuvwxyz']"

class Ansi:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'

def colorize(text, color_code):
    if not text:
        return text
    return f"{color_code}{text}{Ansi.RESET}"
