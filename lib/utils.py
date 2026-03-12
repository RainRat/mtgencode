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
    '\u2019': "'",  # single quote
    '\u2018': "'",  # single quote
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
_unary_exceptions_inv = {v: k for k, v in unary_exceptions.items()}

def to_unary(s, warn = False):
    def replace_number(match):
        n = match.group(0)
        i = int(n)
        if i in unary_exceptions:
            return unary_exceptions[i]
        if i > unary_max:
            # original code capped it at unary_max (20)
            if warn:
                print(s)
            i = unary_max
        return unary_marker + unary_counter * i

    return _number_decimal_re.sub(replace_number, s)

def from_unary(s):
    def replace_unary(match):
        n = match.group(0)
        i = (len(n) - len(unary_marker)) // len(unary_counter)
        return str(i)

    return _number_unary_re.sub(replace_unary, s)

def from_unary_single(s):
    """Converts a single unary string (possibly with exceptions) back to a numerical value."""
    if not s:
        return 0
    if s in _unary_exceptions_inv:
        return _unary_exceptions_inv[s]
    try:
        res = from_unary(s)
        if '.' in res:
            return float(res)
        return int(res)
    except (ValueError, TypeError):
        return 0

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
    return (mana_json_open_delimiter +
            mana_json_hybrid_delimiter.join(sym) +
            mana_json_close_delimiter)

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
# Pre-compile for performance
_number_decimal_re = re.compile(number_decimal_regex)
_number_unary_re = re.compile(number_unary_regex)

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
def mana_untranslate(manastr, for_forum = False, for_html = False, ansi_color = False):
    inner = manastr[1:-1]
    jmanastr = ''
    colorless_total = 0

    def get_sym_color(sym):
        # Individual symbol color mapping
        if not ansi_color:
            return None
        # get_color_color always returns BOLD, so we strip it if we want the non-bold version
        # but actually mana symbols look better bolded in summaries.
        # However, the previous code used non-bold for primary colors.
        # Let's see. Original W was Ansi.WHITE.
        sym_upper = sym.upper()
        if len(sym_upper) == 1 and sym_upper in 'WUBRG':
            return getattr(Ansi, {'W':'WHITE', 'U':'CYAN', 'B':'MAGENTA', 'R':'RED', 'G':'GREEN'}[sym_upper])
        return Ansi.get_color_color(sym)

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
                        decoded = mana_decode_direct(sym)
                        if ansi_color:
                            color = get_sym_color(mana_symall_decode[sym])
                            if color:
                                decoded = colorize(decoded, color)
                        jmanastr = jmanastr + decoded
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
        colorless_str = ''
        if colorless_total > 0 or jmanastr == '':
            colorless_str = mana_json_open_delimiter + str(colorless_total) + mana_json_close_delimiter
            if ansi_color:
                colorless_str = colorize(colorless_str, Ansi.BOLD)

        if jmanastr == '':
            return colorless_str
        else:
            # If jmanastr is not empty, we only include colorless if it's > 0
            if colorless_total > 0:
                return colorless_str + jmanastr
            else:
                return jmanastr

# finally, replacing all instances in a string
# notice the calls to .upper(), this way we recognize lowercase symbols as well just in case
def to_mana(s):
    return re.sub(mana_json_regex, lambda m: mana_translate(m.group(0).upper()), s)


def from_mana(s, for_forum=False, for_html=False, ansi_color=False):
    return re.sub(mana_regex, lambda m: mana_untranslate(m.group(0).upper(), for_forum=for_forum, for_html=for_html, ansi_color=ansi_color), s)
    
# Translation could also be accomplished using the datamine.Manacost object's
# display methods, but these direct string transformations are retained for
# quick scripting and convenience (and are used internally by that class to
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
symbol_regex = r'\b[' + tap_marker + untap_marker + r']\b'

def to_symbols(s):
    return re.sub(json_symbol_regex, lambda m: json_symbol_trans[m.group(0)], s)


def from_symbols(s, for_forum=False, for_html=False, ansi_color=False):
    def replace(match):
        sym = match.group(0)
        if for_html:
            return symbol_html_trans[sym]
        elif for_forum:
            return symbol_forum_trans[sym]
        else:
            res = symbol_trans[sym]
            if ansi_color:
                res = colorize(res, Ansi.BOLD + Ansi.YELLOW)
            return res
    return re.sub(symbol_regex, replace, s)

unletters_regex = r"[^abcdefghijklmnopqrstuvwxyz']"

# MTG Constants
known_supertypes = {'Legendary', 'Basic', 'Snow', 'World', 'Ongoing'}
_known_supertypes_lower = {s.lower(): s for s in known_supertypes}

def split_types(full_type):
    """Splits a type line string into supertypes and types."""
    supertypes = []
    types = []

    for t in full_type.split():
        t_lower = t.lower()
        if t_lower in _known_supertypes_lower:
            # Preserve original casing but identify as supertype
            supertypes.append(t)
        else:
            types.append(t)
    return supertypes, types


def parse_type_line(type_line):
    """
    Splits a full type line string into supertypes, types, and subtypes.
    Handles various dash characters used as separators.
    """
    if not type_line:
        return [], [], []

    # Modern MTG and Scryfall use \u2014 (em-dash) to separate types from subtypes.
    # We are lenient and handle en-dash and hyphen as well.
    parts = re.split(r' [\u2014\u2013-] ', type_line)

    front = parts[0]
    subtypes = []
    if len(parts) > 1:
        for part in parts[1:]:
            subtypes.extend(part.split())

    supertypes, types = split_types(front)
    return supertypes, types, subtypes


class Ansi:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def get_rarity_color(rarity):
        """Returns the ANSI color code for a given rarity string or marker."""
        if not rarity:
            return Ansi.BOLD
        r_lower = rarity.lower() if hasattr(rarity, 'lower') else rarity
        if r_lower == 'uncommon' or rarity == rarity_uncommon_marker:
            return Ansi.BOLD + Ansi.CYAN
        if r_lower == 'rare' or rarity == rarity_rare_marker:
            return Ansi.BOLD + Ansi.YELLOW
        if r_lower in ['mythic rare', 'mythic'] or rarity == rarity_mythic_marker:
            return Ansi.BOLD + Ansi.RED
        return Ansi.BOLD

    @staticmethod
    def get_color_color(color_sym):
        """Returns the ANSI color code for a given color symbol or name."""
        if not color_sym:
            return Ansi.BOLD
        c = color_sym.upper()
        if c == 'W':
            return Ansi.BOLD + Ansi.WHITE
        if c == 'U':
            return Ansi.BOLD + Ansi.CYAN
        if c == 'B':
            return Ansi.BOLD + Ansi.MAGENTA
        if c == 'R':
            return Ansi.BOLD + Ansi.RED
        if c == 'G':
            return Ansi.BOLD + Ansi.GREEN
        if c == 'A' or 'COLORLESS' in c or 'LAND' in c:
            return Ansi.BOLD + Ansi.CYAN # Standard for colorless/artifacts in this project
        if any(char in c for char in 'WUBRG'):
            return Ansi.BOLD + Ansi.YELLOW # Multicolored/Hybrid/Phyrexian
        return Ansi.BOLD

def colorize(text, color_code):
    if not text:
        return text
    return f"{color_code}{text}{Ansi.RESET}"

# Regular expression for matching ANSI escape sequences
_ansi_escape_re = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def visible_len(s):
    """Returns the length of a string without ANSI escape sequences."""
    return len(_ansi_escape_re.sub('', s))

def print_operation_summary(op_name, success_count, fail_count, quiet=False):
    """Prints a standardized, colorized summary of a CLI operation to stderr."""
    if quiet:
        return

    import sys

    # Only use color if stderr is a TTY
    use_color = sys.stderr.isatty()

    if fail_count == 0:
        summary = f">> {op_name} complete: {success_count} cards processed."
        if use_color:
            summary = colorize(summary, Ansi.BOLD + Ansi.GREEN)
        print('\n' + summary, file=sys.stderr)
    else:
        header = f"\n>> {op_name} complete:"
        if use_color:
            header = colorize(header, Ansi.BOLD + Ansi.CYAN)

        success_str = f"  - {success_count} cards successfully processed."
        if use_color and success_count > 0:
            success_str = colorize(success_str, Ansi.GREEN)

        fail_str = f"  - {fail_count} cards failed."
        if use_color and fail_count > 0:
            fail_str = colorize(fail_str, Ansi.BOLD + Ansi.RED)

        footer = "----------------------------------------"
        if use_color:
            footer = colorize(footer, Ansi.BOLD + Ansi.CYAN)

        print(header, file=sys.stderr)
        print(success_str, file=sys.stderr)
        print(fail_str, file=sys.stderr)
        print(footer, file=sys.stderr)


class NumericFilter:
    """
    Parses and evaluates numerical filters.
    Supports:
    - Exact values: "5", "2.5"
    - Inequalities: ">5", "<3", ">=2", "<=10", "!=0", "==4"
    - Ranges: "2-4", "0.5-1.5"
    """
    def __init__(self, filter_str):
        self.filter_str = filter_str.strip()
        self.mode = None # 'exact', 'inequality', 'range'
        self.op = None   # '>', '<', '>=', '<=', '!=', '=='
        self.val = None
        self.val2 = None # for range
        self._parse()

    def _parse(self):
        s = self.filter_str
        # Check for range
        range_match = re.match(r'^([-+]?\d*\.?\d+)\s*-\s*([-+]?\d*\.?\d+)$', s)
        if range_match:
            self.mode = 'range'
            self.val = float(range_match.group(1))
            self.val2 = float(range_match.group(2))
            return

        # Check for inequalities
        ineq_match = re.match(r'^([><=!]=|[><])\s*([-+]?\d*\.?\d+)$', s)
        if ineq_match:
            self.mode = 'inequality'
            self.op = ineq_match.group(1)
            self.val = float(ineq_match.group(2))
            return

        # Fallback to exact match (optionally with ==)
        exact_match = re.match(r'^(?:==\s*)?([-+]?\d*\.?\d+)$', s)
        if exact_match:
            self.mode = 'exact'
            self.val = float(exact_match.group(1))
            return

        raise ValueError(f"Invalid numerical filter: {s}")

    def evaluate(self, value):
        """
        Evaluates the filter against a numeric value.
        If value is a string, it attempts to convert it to a float.
        """
        if value is None:
            return False

        try:
            if isinstance(value, str):
                # Handle unary or decimal strings
                if value.startswith(unary_marker):
                    val = float(from_unary_single(value))
                else:
                    val = float(value)
            else:
                val = float(value)
        except (ValueError, TypeError):
            return False

        if self.mode == 'exact':
            return val == self.val
        if self.mode == 'range':
            return self.val <= val <= self.val2
        if self.mode == 'inequality':
            if self.op == '>': return val > self.val
            if self.op == '<': return val < self.val
            if self.op == '>=': return val >= self.val
            if self.op == '<=': return val <= self.val
            if self.op == '!=': return val != self.val
            if self.op == '==': return val == self.val

        return False
