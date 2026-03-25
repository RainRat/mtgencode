# card representation
import re
import random
import sys

import utils
import transforms
from xml.sax.saxutils import escape
from manalib import Manacost, Manatext
import nltk.data

from titlecase import titlecase

sent_tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
# This could be made smarter - MSE will capitalize for us after :,
# but we still need to capitalize the first english component of an activation
# cost that starts with symbols, such as {2U}, *R*emove a +1/+1 counter from @: etc.
def cap(s):
    # Find the first letter and capitalize it
    for i, char in enumerate(s):
        if char.isalpha():
            return s[:i] + char.upper() + s[i+1:]
        if char in [utils.this_marker, utils.reserved_marker]:
            return s
    return s
# This function is used during decoding to apply sentence-style capitalization
# while newline markers are still present.
def sentencecase(s):
    s = s.replace(utils.x_marker, utils.reserved_marker)
    lines = s.split(utils.newline)
    clines = []
    for line in lines:
        if line:
            # Split by ": " to handle activated abilities
            # and by " =" to handle choice options
            parts = re.split(r'(: | =)', line)
            cparts = []
            for part in parts:
                if part in [': ', ' =']:
                    cparts += [part]
                else:
                    sentences = sent_tokenizer.tokenize(part)
                    cparts += [' '.join([cap(sent) for sent in sentences])]
            clines += [''.join(cparts)]
        else:
            clines += ['']
    return utils.newline.join(clines).replace(utils.reserved_marker, utils.x_marker)

# These are used later to determine what the fields of the Card object are called.
# Define them here because they have nothing to do with the actual format.
field_name = 'name'
field_rarity = 'rarity'
field_cost = 'cost'
field_supertypes = 'supertypes'
field_types = 'types'
field_subtypes = 'subtypes'
field_loyalty = 'loyalty'
field_pt = 'pt'
field_text = 'text'
field_other = 'other' # it's kind of a pseudo-field

# Import the labels, because these do appear in the encoded text.
field_label_name = utils.field_label_name
field_label_rarity = utils.field_label_rarity
field_label_cost = utils.field_label_cost
field_label_supertypes = utils.field_label_supertypes
field_label_types = utils.field_label_types
field_label_subtypes = utils.field_label_subtypes
field_label_loyalty = utils.field_label_loyalty
field_label_pt = utils.field_label_pt
field_label_text = utils.field_label_text

fieldnames = [
    field_name,
    field_rarity,
    field_cost,
    field_supertypes,
    field_types,
    field_subtypes,
    field_loyalty,
    field_pt,
    field_text,
]

# Use shorthand: C, U, R, M, S, L
RARITY_MAP = {
    'common': 'C',
    'uncommon': 'U',
    'rare': 'R',
    'mythic rare': 'M',
    'mythic': 'M',
    'special': 'S',
    'basic land': 'L',
    utils.rarity_common_marker: 'C',
    utils.rarity_uncommon_marker: 'U',
    utils.rarity_rare_marker: 'R',
    utils.rarity_mythic_marker: 'M',
    utils.rarity_special_marker: 'S',
    utils.rarity_basic_land_marker: 'L',
}

# legacy
fmt_ordered_old = [
    field_name,
    field_supertypes,
    field_types,
    field_loyalty,
    field_subtypes,
    field_rarity,
    field_pt,
    field_cost,
    field_text,
]
fmt_ordered_norarity = [
    field_name,
    field_supertypes,
    field_types,
    field_loyalty,
    field_subtypes,
    field_pt,
    field_cost,
    field_text,
]

# minor variations
fmt_ordered_noname = [
    field_types,
    field_supertypes,
    field_subtypes,
    field_loyalty,
    field_pt,
    field_text,
    field_cost,
    field_rarity,
]
# standard
fmt_ordered_default = fmt_ordered_noname + [field_name]
fmt_ordered_named = [field_name] + fmt_ordered_noname

fmt_labeled_default = {
    field_name : field_label_name,
    field_rarity : field_label_rarity,
    field_cost : field_label_cost,
    field_supertypes : field_label_supertypes,
    field_types : field_label_types,
    field_subtypes : field_label_subtypes,
    field_loyalty : field_label_loyalty,
    field_pt : field_label_pt,
    field_text : field_label_text,
}

# Verify that the card's fields are consistent (e.g., creatures must have power and toughness).
def fields_check_valid(fields):
    # all cards must have a name and a type
    if field_name not in fields:
        return False
    if field_types not in fields:
        return False

    iscreature = False
    isartifact = False
    isplaneswalker = False
    isbattle = False
    for idx, value in fields[field_types]:
        if 'creature' in value:
            iscreature = True
        if 'artifact' in value:
            isartifact = True
        if 'planeswalker' in value:
            isplaneswalker = True
        if 'battle' in value:
            isbattle = True

    if field_subtypes in fields:
        for idx, value in fields[field_subtypes]:
            if 'vehicle' in value:
                iscreature = True

    text = ''
    if field_text in fields:
        for idx, value in fields[field_text]:
            text += value.text

    # P/T requirements
    if iscreature:
        if field_pt not in fields:
            return False
    # Station cards can become creatures, so they are allowed to NOT have P/T.
    # We also allow them to HAVE P/T if they want.
    elif isartifact and 'station' in text:
        pass
    else:
        if field_pt in fields:
            return False

    # Loyalty / Defense requirements
    if isplaneswalker or isbattle:
        if field_loyalty not in fields:
            return False
    else:
        if field_loyalty in fields:
            return False

    return True


# These functions take a bunch of source data in some format and turn
# it into nicely labeled fields that we know how to initialize a card from.
# Both return a dict that maps field names to lists of possible values,
# paired with the index that we read that particular field value from.
# So, {fieldname : [(idx, value), (idx, value)...].
# Usually we want these lists to be length 1, but you never know.

# The dictionary is the third element of the returned tuple
# of a triple that reports parsing success and valid success as its 
# first two elements.

# This whole things assumes the json format of mtgjson.com.

# Here's a brief list of relevant fields:
# name - string
# names - list (used for split, flip, and double-faced)
# manaCost - string
# cmc - number
# colors - list
# type - string (the whole big long damn thing)
# supertypes - list
# types - list
# subtypes - list
# text - string
# power - string
# toughness - string
# loyalty - number

# And some less useful ones, in case they're wanted for something:
# layout - string
# rarity - string
# flavor - string
# artist - string
# number - string
# multiverseid - number
# variations - list
# imageName - string
# watermark - string
# border - string
# timeshifted - boolean
# hand - number
# life - number
# reserved - boolean
# releaseDate - string
# starter - boolean

def fields_from_json(src_json, linetrans = True):
    parsed = True
    valid = True
    fields = {}

    if 'name' in src_json:
        name_val = src_json['name'].lower()
        name_orig = name_val
        name_val = transforms.name_pass_1_sanitize(name_val)
        name_val = utils.to_ascii(name_val)
        fields[field_name] = [(-1, name_val)]
    else:
        name_orig = ''
        parsed = False

    # return the actual Manacost object
    if 'manaCost' in src_json:
        cost =  Manacost(src_json['manaCost'], fmt = 'json')
        valid = valid and cost.valid
        parsed = parsed and cost.parsed
        fields[field_cost] = [(-1, cost)]

    if 'supertypes' in src_json:
        fields[field_supertypes] = [
            (-1, list(map(lambda s: utils.to_ascii(s.lower()), src_json['supertypes'])))]

    if 'types' in src_json:
        fields[field_types] = [(-1, [utils.to_ascii(s.lower())
                                     for s in src_json['types']])]
    else:
        parsed = False

    if 'subtypes' in src_json:
        fields[field_subtypes] = [(-1, [utils.to_ascii(s.lower())
                                        # urza's lands...
                                        .replace('"', "'").replace('-', utils.dash_marker) for s in src_json['subtypes']])]
        

    if 'rarity' in src_json:
        # Use lowercase for robust rarity lookup
        rarity_key = src_json['rarity'].lower() if hasattr(src_json['rarity'], 'lower') else src_json['rarity']
        # Also try direct match if lowercase lookup fails (just in case)
        if rarity_key in utils.json_rarity_map:
            fields[field_rarity] = [(-1, utils.json_rarity_map[rarity_key])]
        elif src_json['rarity'] in utils.json_rarity_map:
            fields[field_rarity] = [(-1, utils.json_rarity_map[src_json['rarity']])]
        else:
            fields[field_rarity] = [(-1, src_json['rarity'])]
            parsed = False
    else:
        parsed = False

    loyalty_val = src_json.get('loyalty')
    if loyalty_val is None:
        loyalty_val = src_json.get('defense')
    if loyalty_val is not None:
        fields[field_loyalty] = [(-1, utils.to_unary(str(loyalty_val)))]

    p_t = ''
    parsed_pt = True
    if 'pt' in src_json:
        p_t = src_json['pt']
    elif 'power' in src_json:
        p_t = utils.to_ascii(utils.to_unary(src_json['power'])) + '/' # hardcoded
        parsed_pt = False
        if 'toughness' in src_json:
            p_t = p_t + utils.to_ascii(utils.to_unary(src_json['toughness']))
            parsed_pt = True
    elif 'toughness' in src_json:
        p_t = '/' + utils.to_ascii(utils.to_unary(src_json['toughness'])) # hardcoded
        parsed_pt = False
    if p_t:
        fields[field_pt] = [(-1, p_t)]
    parsed = parsed and parsed_pt
        
    # similarly, return the actual Manatext object
    if 'text' in src_json:
        text_val = src_json['text'].lower()
        # if 'station' in text_val:
        #    text_val = re.sub(r'station\s*\d+\+*', 'station', text_val)
        text_val = transforms.text_pass_1_strip_rt(text_val)
        text_val = transforms.text_pass_2_cardname(text_val, name_orig)
        text_val = utils.to_unary(text_val)
        text_val = transforms.text_pass_4a_dashes(text_val)
        text_val = transforms.text_pass_4b_x(text_val)
        text_val = transforms.text_pass_4c_abilitywords(text_val)
        text_val = transforms.text_pass_5_counters(text_val)
        text_val = transforms.text_pass_6_uncast(text_val)
        text_val = transforms.text_pass_7_choice(text_val)
        text_val = transforms.text_pass_8_equip(text_val)
        text_val = transforms.text_pass_9_newlines(text_val)
        text_val = utils.to_symbols(text_val)
        if linetrans:
            text_val = transforms.text_pass_11_linetrans(text_val)
        text_val = utils.to_ascii(text_val)
        text_val = text_val.strip()
        mtext = Manatext(text_val, fmt = 'json')
        valid = valid and mtext.valid
        fields[field_text] = [(-1, mtext)]
    
    # we don't need to worry about bsides because we handle that in the constructor
    return parsed, valid and fields_check_valid(fields), fields


def fields_from_format(src_text, fmt_ordered, fmt_labeled, fieldsep, linetrans = False):
    parsed = True
    valid = True
    fields = {}

    if fmt_labeled:
        labels = {fmt_labeled[k] : k for k in fmt_labeled}
        # Sort labels by length descending to match longest first, if we ever have multi-char labels
        sorted_labels = sorted(labels.keys(), key=len, reverse=True)
    def addf(fields, fkey, fval):
        # make sure you pass a pair
        if fval and fval[1]:
            if fkey in fields:
                fields[fkey] += [fval]
            else:
                fields[fkey] = [fval]

    textfields = src_text.split(fieldsep)
    idx = 0
    true_idx = 0
    for textfield in textfields:
        # ignore leading or trailing empty fields due to seps
        if textfield == '':
            if true_idx == 0 or true_idx == len(textfields) - 1:
                true_idx += 1
                continue
            # count the field index for other empty fields but don't add them
            else:
                idx += 1
                true_idx += 1
                continue

        lab = None
        if fmt_labeled:
            for l in sorted_labels:
                if textfield.startswith(l):
                    lab = l
                    textfield = textfield[len(l):]
                    break
        # try to use the field label if we got one
        if lab and lab in labels:
            fname = labels[lab]
        # fall back to the field order specified
        elif idx < len(fmt_ordered):
            fname = fmt_ordered[idx]
        # we don't know what to do with this field: call it other
        else:
            fname = field_other
            parsed = False
            valid = False

        # specialized handling
        if fname in [field_cost]:
            fval = Manacost(textfield)
            parsed = parsed and fval.parsed
            valid = valid and fval.valid
            addf(fields, fname, (idx, fval))
        elif fname in [field_text]:
            if linetrans:
                textfield = transforms.text_pass_11_linetrans(textfield)
            fval = Manatext(textfield)
            valid = valid and fval.valid
            addf(fields, fname, (idx, fval))
        elif fname in [field_supertypes, field_types, field_subtypes]:
            addf(fields, fname, (idx, textfield.split()))
        else:
            addf(fields, fname, (idx, textfield))

        idx += 1
        true_idx += 1
        
    # again, bsides are handled by the constructor
    return parsed, valid and fields_check_valid(fields), fields

# Here's the actual Card class that other files should use.

class Card:
    '''Represents a Magic: The Gathering card. It can be created from JSON data or encoded text.'''

    def __init__(self, src, fmt_ordered=None, fmt_labeled=None,
                 fieldsep=utils.fieldsep, linetrans=True,
                 verbose=False):
        if fmt_ordered is None:
            fmt_ordered = fmt_ordered_default
        if fmt_labeled is None:
            fmt_labeled = fmt_labeled_default

        # source fields, exactly one will be set
        self.json = None
        self.raw = None
        # flags
        self.parsed = True
        self.valid = True # doesn't record that much
        self.verbose = verbose
        # placeholders to fill in with expensive distance metrics
        self.nearest_names = []
        self.nearest_cards = []
        self._init_defaults()
        self.bside = None
        # format-independent view of processed input
        self.fields = None # will be reset later

        # looks like a json object
        if isinstance(src, dict):
            self.json = src
            self.set_code = src.get('setCode')
            self.number = src.get('number')
            if utils.json_field_bside in src:
                self.bside = Card(src[utils.json_field_bside],
                                  fmt_ordered = fmt_ordered,
                                  fmt_labeled = fmt_labeled,
                                  fieldsep = fieldsep,
                                  linetrans = linetrans)
            p_success, v_success, parsed_fields = fields_from_json(src, linetrans = linetrans)
            self.parsed = p_success
            self.valid = v_success
            self.fields = parsed_fields
        # otherwise assume text encoding
        else:
            self.raw = src
            sides = src.split(utils.bsidesep)
            if len(sides) > 1:
                self.bside = Card(utils.bsidesep.join(sides[1:]), 
                                  fmt_ordered = fmt_ordered,
                                  fmt_labeled = fmt_labeled,
                                  fieldsep = fieldsep,
                                  linetrans = linetrans)
            p_success, v_success, parsed_fields = fields_from_format(sides[0], fmt_ordered, 
                                                                     fmt_labeled,  fieldsep,
                                                                     linetrans = linetrans)
            self.parsed = p_success
            self.valid = v_success
            self.fields = parsed_fields
        # Both encoding methods support recursive nesting of b-sides.

        # Automatically assign field values based on their names.
        if self.fields:
            for field in self.fields:
                # look for a specialized set function
                if hasattr(self, '_set_' + field):
                    getattr(self, '_set_' + field)(self.fields[field])
                # otherwise use the default one
                elif field in self.__dict__:
                    self.set_field_default(field, self.fields[field])
                # If we don't recognize the field, fail. This is a totally artificial
                # limitation; if we just used the default handler for the else case,
                # we could set arbitrarily named fields.
                else:
                    raise ValueError('Unknown field for Card object: '
                                     + field)
        else:
            # valid but not parsed indicates that the card was apparently empty
            self.parsed = False

    @property
    def is_artifact(self):
        """Returns True if the card is an artifact."""
        return 'artifact' in self.types

    @property
    def is_creature(self):
        """Returns True if the card is a creature or a vehicle."""
        return 'creature' in self.types or 'vehicle' in self.subtypes

    @property
    def is_planeswalker(self):
        """Returns True if the card is a planeswalker."""
        return 'planeswalker' in self.types

    @property
    def is_battle(self):
        """Returns True if the card is a battle."""
        return 'battle' in self.types

    @property
    def is_land(self):
        """Returns True if the card is a land."""
        return 'land' in self.types

    @property
    def is_enchantment(self):
        """Returns True if the card is an enchantment."""
        return 'enchantment' in self.types

    @property
    def is_instant(self):
        """Returns True if the card is an instant."""
        return 'instant' in self.types

    @property
    def is_sorcery(self):
        """Returns True if the card is a sorcery."""
        return 'sorcery' in self.types

    def get_type_line(self, separator='\u2014'):
        """Returns a formatted type line string (e.g., 'Legendary Creature — Human Warrior')."""
        supertypes = [titlecase(s) for s in self.__dict__[field_supertypes]]
        types = [titlecase(t) for t in self.__dict__[field_types]]
        res = ' '.join(supertypes + types)
        if self.__dict__[field_subtypes]:
            res += f' {separator} ' + ' '.join([titlecase(s) for s in self.__dict__[field_subtypes]])
        return res

    def _get_single_face_display_data(self, ansi_color=False, include_text=False):
        """Helper to get standardized display fields for a single face of the card."""
        # Name
        name = titlecase(self.name)
        if ansi_color:
            name = utils.colorize(name, self._get_ansi_color())

        # Cost
        cost = self.cost.format(ansi_color=ansi_color)

        # CMC
        cmc = str(int(self.cost.cmc)) if self.cost.cmc == int(self.cost.cmc) else f"{self.cost.cmc:.1f}"
        if ansi_color:
            cmc = utils.colorize(cmc, utils.Ansi.BOLD + utils.Ansi.GREEN)

        # Type
        typeline = self.get_type_line()
        if ansi_color:
            typeline = utils.colorize(typeline, utils.Ansi.GREEN)

        # Stats (P/T or Loyalty/Defense)
        stats = self._get_pt_display(ansi_color=ansi_color, include_parens=False)
        if not stats:
            stats = self._get_loyalty_display(ansi_color=ansi_color, include_parens=False)

        # Text
        text = ""
        if include_text:
            text = self.get_text(force_unpass=True).replace('\n', '<br>')

        # Rarity
        rarity = self.rarity_name
        if ansi_color and rarity:
            rarity = utils.colorize(rarity, utils.Ansi.get_rarity_color(rarity))

        # Mechanics
        mech_list = sorted(list(self.get_face_mechanics()))
        mechanics = ', '.join(mech_list)
        if ansi_color and mechanics:
            mechanics = utils.colorize(mechanics, utils.Ansi.CYAN)

        return name, cost, cmc, typeline, stats, text, rarity, mechanics

    def _get_display_data(self, ansi_color=False, include_text=False):
        """Helper to get standardized display fields for the card, merging b-sides."""
        name, cost, cmc, typeline, stats, text, rarity, mechanics = self._get_single_face_display_data(ansi_color=ansi_color, include_text=include_text)

        if self.bside:
            b_name, b_cost, b_cmc, b_typeline, b_stats, b_text, b_rarity, b_mechanics = self.bside._get_display_data(ansi_color=ansi_color, include_text=include_text)
            name = f"{name} // {b_name}"
            cost = f"{cost} // {b_cost}"
            cmc = f"{cmc} // {b_cmc}"
            typeline = f"{typeline} // {b_typeline}"
            stats = f"{stats} // {b_stats}" if stats and b_stats else (stats or b_stats)
            if include_text:
                text = f"{text}<br>---<br>{b_text}"
            if b_rarity and b_rarity != rarity:
                rarity = f"{rarity} // {b_rarity}"
            if b_mechanics:
                mechanics = f"{mechanics} // {b_mechanics}" if mechanics else b_mechanics

        return name, cost, cmc, typeline, stats, text, rarity, mechanics

    def get_face_mechanics(self):
        """Returns a set of mechanical features and keyword abilities identified on this card face."""
        text_raw = self.text.text.lower()
        # To handle cards named after keywords (e.g., card "Exile" with rule text "@ target..."),
        # we create a search string where @ is replaced by the card name.
        # We replace spaces with underscores to avoid false positives from names like "Trample Bear".
        safe_name = self.name.lower().replace(' ', '_')
        text_search = text_raw.replace(utils.this_marker, safe_name)

        text_enc = self.text.encode().lower()
        cost_enc = self.cost.encode()

        m = set()

        # 1. Structural / Complex Mechanics
        if ':' in text_raw:
            m.add('Activated')

        # Triggered: check start of lines
        for mt in self.text_lines:
            line = mt.text.lower().strip().replace(utils.this_marker, safe_name)
            if line.startswith('when') or line.startswith('whenever') or line.startswith('at '):
                m.add('Triggered')
                break

        if 'enters the battlefield' in text_search or 'enters,' in text_search or 'enters.' in text_search:
            m.add('ETB Effect')

        if utils.choice_open_delimiter in text_enc or utils.choice_close_delimiter in text_enc or '=' in text_enc:
            m.add('Modal/Choice')

        if 'X' in cost_enc or re.search(r'\bx+\b', text_enc):
            m.add('X-Cost/Effect')

        if 'kick' in text_raw:
            m.add('Kicker')

        if 'uncast' in text_raw:
            m.add('Uncast')

        if 'equipment' in [t.lower() for t in self.subtypes] or 'equip' in text_raw:
            m.add('Equipment')

        if 'level up' in text_raw or 'level &' in text_enc:
            m.add('Leveler')

        if '%' in text_enc or '#' in text_enc or 'counter' in text_raw:
            m.add('Counters')

        # 2. Common Keyword Abilities
        keywords = [
            ('flying', 'Flying'), ('trample', 'Trample'), ('lifelink', 'Lifelink'),
            ('haste', 'Haste'), ('deathtouch', 'Deathtouch'), ('vigilance', 'Vigilance'),
            ('ward', 'Ward'), ('prowess', 'Prowess'), ('menace', 'Menace'),
            ('reach', 'Reach'), ('flash', 'Flash'), ('indestructible', 'Indestructible'),
            ('defender', 'Defender'), ('scry', 'Scry'), ('draw a card', 'Draw A Card'),
            ('mill', 'Mill'), ('exile', 'Exile'), (r'tokens?', 'Token'),
            ('discard', 'Discard'), ('cycling', 'Cycling')
        ]

        for pattern, label in keywords:
            # Use word boundaries for keywords to avoid partial matches
            if re.search(r'\b' + pattern + r'\b', text_search):
                m.add(label)

        return m

    @property
    def mechanics(self):
        """Returns a set of mechanical features and keyword abilities identified on the card (including b-side)."""
        m = self.get_face_mechanics()

        # Recursive profiling for split/double-faced cards
        if self.bside:
            m.update(self.bside.mechanics)

        return m

    @property
    def rarity_name(self):
        """Returns the human-readable rarity name (e.g., 'rare' for 'A')."""
        if not self.rarity:
            return ''
        if self.rarity in utils.json_rarity_unmap:
            return utils.json_rarity_unmap[self.rarity]
        return self.rarity

    def _get_pt_display(self, ansi_color=False, include_parens=True, unary=False):
        """Helper to format Power/Toughness for display."""
        if not self.pt:
            return ""
        val = self.pt if unary else utils.from_unary(self.pt)
        res = f"({val})" if include_parens else val
        if ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
        return res

    def _get_loyalty_display(self, ansi_color=False, double_paren=False, include_parens=True, unary=False):
        """Helper to format Loyalty or Defense for display."""
        if not self.loyalty:
            return ""
        val = self.loyalty if unary else utils.from_unary(self.loyalty)
        if self.is_battle:
            res = f"[[{val}]]" if include_parens else val
        elif include_parens:
            res = f"(({val}))" if double_paren else f"({val})"
        else:
            res = val
        if ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
        return res

    def _init_defaults(self):
        # default values for all fields
        setattr(self, field_name, '')
        setattr(self, field_rarity, '')
        setattr(self, field_cost, Manacost(''))
        setattr(self, field_supertypes, [])
        setattr(self, field_types, [])
        setattr(self, field_subtypes, [])
        setattr(self, field_loyalty, '')
        setattr(self, field_pt, '')
        setattr(self, field_pt + '_p', None)
        setattr(self, field_pt + '_t', None)
        setattr(self, field_text, Manatext(''))
        setattr(self, field_text + '_lines', [])
        setattr(self, field_text + '_words', [])
        setattr(self, field_text + '_lines_words', [])
        setattr(self, field_other, [])
        # metadata for interoperability
        self.set_code = None
        self.number = None

    def _get_ansi_color(self):
        """Returns the ANSI color code for the card based on its colors and types."""
        card_colors = self.cost.colors
        if len(card_colors) > 1:
            return utils.Ansi.get_color_color('WUBRG')
        elif len(card_colors) == 1:
            return utils.Ansi.get_color_color(card_colors[0])
        else:
            # Colorless / Artifacts
            # Lands are typically just BOLD, non-land colorless are CYAN
            if 'land' not in [t.lower() for t in self.types]:
                return utils.Ansi.get_color_color('A')
            return utils.Ansi.BOLD

    # These setters are invoked via name mangling, so they have to match 
    # the field names specified above to be used. Otherwise we just
    # always fall back to the (uninteresting) default handler.

    # Also note that all fields come wrapped in pairs, with the first member
    # specifying the index the field was found at when parsing the card. These will
    # all be -1 if the card was parsed from (unordered) json.

    def set_field_default(self, field, values):
        first = True
        for idx, value in values:
            if first:
                first = False
                self.__dict__[field] = value
            else:
                # stick it in other so we'll be know about it when we format the card
                self.valid = False
                self.__dict__[field_other] += [(idx, '<' + field + '> ' + str(value))]

    def _set_loyalty(self, values):
        first = True
        for idx, value in values:
            if first:
                first = False
                self.__dict__[field_loyalty] = value
            else:
                self.valid = False
                if self.verbose:
                    sys.stderr.write("Multiple loyalty values for card '" + self.name + "': " + str(value) + "\n")
                self.__dict__[field_other] += [(idx, '<loyalty> ' + str(value))]

    def _set_pt(self, values):
        first = True
        for idx, value in values:
            if first:
                first = False
                self.__dict__[field_pt] = value
                # Tolerant P/T parsing
                match = re.match(r'^\s*([^\s/]+)\s*/\s*([^\s/]+)\s*$', value)
                if match:
                    p, t = match.groups()
                    self.__dict__[field_pt + '_p'] = p
                    self.__dict__[field_pt + '_t'] = t
                else:
                    self.valid = False
                    if self.verbose:
                        sys.stderr.write("Invalid P/T value for card '" + self.name + "': " + str(value) + "\n")
            else:
                self.valid = False
                if self.verbose:
                    sys.stderr.write("Multiple P/T values for card '" + self.name + "': " + str(value) + "\n")
                self.__dict__[field_other] += [(idx, '<pt> ' + str(value))]
    
    def _set_text(self, values):
        first = True
        for idx, value in values:
            if first:
                first = False
                mtext = value
                self.__dict__[field_text] = mtext
                fulltext = mtext.encode()
                if fulltext:
                    self.__dict__[field_text + '_lines'] = list(map(Manatext,
                                                                    fulltext.split(utils.newline)))
                    self.__dict__[field_text + '_words'] = re.sub(utils.unletters_regex,
                                                                  ' ',
                                                                  fulltext).split()
                    self.__dict__[field_text + '_lines_words'] = [re.sub(
                        utils.unletters_regex, ' ', line).split() for line in fulltext.split(utils.newline)]
            else:
                self.valid = False
                self.__dict__[field_other] += [(idx, '<text> ' + str(value))]
        
    def _set_other(self, values):
        # just record these, we could do something unset valid if we really wanted
        for idx, value in values:
            self.__dict__[field_other] += [(idx, value)]

    def get_text(self, text_obj=None, name_obj=None, gatherer=False, for_forum=False, for_html=False, mse=False, ansi_color=False, force_unpass=False):
        """Centralizes rules text unpassing logic.

        Args:
            text_obj (Manatext): The rules text object to process. Defaults to self.text.
            name_obj (str): The card name to use for replacements. Defaults to self.name.
            gatherer (bool): Whether to use Gatherer-style formatting.
            for_forum (bool): Whether to use forum-style mana formatting.
            for_html (bool): Whether to use HTML-style mana formatting.
            mse (bool): Whether to use Magic Set Editor style formatting.
            ansi_color (bool): Whether to use ANSI color codes.
            force_unpass (bool): Whether to force unpassing of counters and self-references
                                even if gatherer is False. Used by to_dict().

        Returns:
            str: The unpassed and formatted rules text.
        """
        if text_obj is None:
            text_obj = self.text
        if name_obj is None:
            name_obj = self.name

        if not text_obj.text:
            return ''

        mtext = text_obj.text
        if gatherer or mse:
            cardname = titlecase(transforms.name_unpass_1_dashes(name_obj))
        else:
            cardname = titlecase(name_obj)

        # 1. Choice unpass
        delimit_choice = not (gatherer or mse)
        mtext = transforms.text_unpass_1_choice(mtext, delimit=delimit_choice)

        # 2. Counters unpass
        if gatherer or mse or force_unpass:
            mtext = transforms.text_unpass_2_counters(mtext)

        # 3. Uncast unpass
        mtext = transforms.text_unpass_3_uncast(mtext)

        # 4. Unary unpass
        mtext = utils.from_unary(mtext)

        # 6. Sentencecase
        mtext = sentencecase(mtext)

        # 7. Self-references (this_marker)
        if mse:
            mtext = mtext.replace(utils.this_marker, '<atom-cardname><nospellcheck>'
                                  + utils.this_marker + '</nospellcheck></atom-cardname>')
            mtext = transforms.text_unpass_6_cardname(mtext, cardname)
        elif gatherer or force_unpass:
            mtext = transforms.text_unpass_6_cardname(mtext, cardname)

        # 8. Newlines
        mtext = transforms.text_unpass_7_newlines(mtext)

        # 9. Unicode (MSE or Gatherer)
        if mse or gatherer:
            mtext = transforms.text_unpass_8_unicode(mtext)

        # 9.5. Symbols unpass (called AFTER sentencecase to avoid color corruption)
        mtext = utils.from_symbols(mtext, for_forum, for_html, ansi_color=ansi_color)

        if mse:
            # Handle the +X / -X loyalty cost case where X becomes + / - during unary unpass
            # if X was misinterpreted as 0 by Manacost/Manatext.
            # Ensures loyalty costs are correctly formatted for Magic Set Editor.
            mtext = re.sub(r'^\+\s*:', '+X:', mtext, flags=re.MULTILINE)
            mtext = re.sub(r'^−\s*:', '−X:', mtext, flags=re.MULTILINE)
            mtext = re.sub(r'^-\s*:', '-X:', mtext, flags=re.MULTILINE)

        # 10. Final formatting via Manatext
        newtext = Manatext('')
        newtext.text = mtext
        newtext.costs = text_obj.costs
        res = newtext.format(for_forum=for_forum, for_html=for_html, ansi_color=ansi_color)

        # 11. MSE symbol tagging
        if mse:
            res = res.replace('{', '<sym-auto>').replace('}', '</sym-auto>')

        return res

    # Output functions that produce various formats. encode() is specific to
    # the NN representation, use str() or format() for output intended for human
    # readers.

    def encode(self, fmt_ordered = fmt_ordered_default, fmt_labeled = fmt_labeled_default, 
               fieldsep = utils.fieldsep, initial_sep = True, final_sep = True,
               randomize_fields = False, randomize_mana = False, randomize_lines = False):
        """Encodes the card data into a string format suitable for machine learning.

        Args:
            fmt_ordered (list, optional): The order of fields in the output string.
                Defaults to fmt_ordered_default.
            fmt_labeled (dict, optional): A dictionary mapping field names to labels.
                Defaults to fmt_labeled_default.
            fieldsep (str, optional): The separator to use between fields.
                Defaults to utils.fieldsep.
            initial_sep (bool, optional): Whether to add a separator at the beginning of the string.
                Defaults to True.
            final_sep (bool, optional): Whether to add a separator at the end of the string.
                Defaults to True.
            randomize_fields (bool, optional): Whether to randomize the order of fields.
                Defaults to False.
            randomize_mana (bool, optional): Whether to randomize the order of mana symbols.
                Defaults to False.
            randomize_lines (bool, optional): Whether to randomize the order of lines in the text.
                Defaults to False.

        Returns:
            str: The encoded card data.
        """
        outfields = []

        for field in fmt_ordered:
            if field in self.__dict__:
                outfield = self.__dict__[field]
                if outfield:
                    # specialized field handling for the ones that aren't strings (sigh)
                    if isinstance(outfield, list):
                        outfield_str = ' '.join(outfield)
                    elif isinstance(outfield, Manacost):
                        outfield_str = outfield.encode(randomize = randomize_mana)
                    elif isinstance(outfield, Manatext):
                        outfield_str = outfield.encode(randomize = randomize_mana)
                        if randomize_lines:
                            outfield_str = transforms.randomize_lines(outfield_str)
                    else:
                        outfield_str = outfield
                else:
                    outfield_str = ''

                if fmt_labeled and field in fmt_labeled:
                        outfield_str = fmt_labeled[field] + outfield_str

                outfields += [outfield_str]

            else:
                raise ValueError('unknown field for Card.encode(): ' + str(field))

        if randomize_fields:
            random.shuffle(outfields)
        if initial_sep:
            outfields = [''] + outfields
        if final_sep:
            outfields = outfields + ['']

        outstr = fieldsep.join(outfields)

        if self.bside:
            outstr = (outstr + utils.bsidesep 
                      + self.bside.encode(fmt_ordered = fmt_ordered,
                                          fmt_labeled = fmt_labeled,
                                          fieldsep = fieldsep,
                                          randomize_fields = randomize_fields, 
                                          randomize_mana = randomize_mana,
                                          randomize_lines = randomize_lines,
                                          initial_sep = initial_sep, final_sep = final_sep))

        return outstr

    def search(self, pattern):
        """Returns True if the pattern matches any of the card's fields."""
        if self.search_name(pattern):
            return True
        if self.search_types(pattern):
            return True
        if self.search_text(pattern):
            return True
        if self.search_cost(pattern):
            return True
        if self.search_pt(pattern):
            return True
        if self.search_loyalty(pattern):
            return True
        return False

    def search_name(self, pattern):
        """Returns True if the pattern matches the card's name."""
        if pattern.search(self.name):
            return True
        if self.bside:
            return self.bside.search_name(pattern)
        return False

    def search_types(self, pattern):
        """Returns True if the pattern matches any of the card's types (supertypes, types, or subtypes)."""
        if any(pattern.search(t) for t in self.supertypes):
            return True
        if any(pattern.search(t) for t in self.types):
            return True
        if any(pattern.search(t) for t in self.subtypes):
            return True
        if self.bside:
            return self.bside.search_types(pattern)
        return False

    def search_text(self, pattern):
        """Returns True if the pattern matches the card's rules text."""
        if pattern.search(self.text.text):
            return True
        if self.bside:
            return self.bside.search_text(pattern)
        return False

    def search_cost(self, pattern):
        """Returns True if the pattern matches the card's mana cost."""
        if pattern.search(self.cost.format()):
            return True
        if self.bside:
            return self.bside.search_cost(pattern)
        return False

    def search_pt(self, pattern):
        """Returns True if the pattern matches the card's power and toughness."""
        if self.pt and pattern.search(utils.from_unary(self.pt)):
            return True
        if self.bside:
            return self.bside.search_pt(pattern)
        return False

    def search_loyalty(self, pattern):
        """Returns True if the pattern matches the card's loyalty or defense."""
        if self.loyalty and pattern.search(utils.from_unary(self.loyalty)):
            return True
        if self.bside:
            return self.bside.search_loyalty(pattern)
        return False

    def summary(self, ansi_color=False):
        """Returns a compact, one-line summary of the card."""
        # Status indicator
        status = ''
        if not self.parsed:
            status = '[!] '
            if ansi_color:
                status = utils.colorize(status, utils.Ansi.BOLD + utils.Ansi.RED)
        elif not self.valid:
            status = '[?] '
            if ansi_color:
                status = utils.colorize(status, utils.Ansi.YELLOW)

        # Rarity indicator
        rarity_indicator = ''
        if self.rarity:
            r = self.rarity_name
            indicator = RARITY_MAP.get(r.lower() if hasattr(r, 'lower') else r, r[0].upper() if r else '?')

            indicator = f'[{indicator}]'
            if ansi_color:
                color = utils.Ansi.get_rarity_color(r)
                indicator = utils.colorize(indicator, color)

            rarity_indicator = f'{indicator} '

        # Name
        cardname = titlecase(self.name)
        if ansi_color:
            color = self._get_ansi_color()
            cardname = utils.colorize(cardname, color)

        # Cost
        coststr = self.cost.format(ansi_color=ansi_color)
        if coststr:
            coststr = f' {coststr}'

        # Type Line
        typeline = self.get_type_line()
        if ansi_color:
            typeline = utils.colorize(typeline, utils.Ansi.GREEN)

        # P/T or Loyalty
        stats = self._get_pt_display(ansi_color=ansi_color)
        if not stats:
            stats = self._get_loyalty_display(ansi_color=ansi_color)

        # Mechanics
        mech_list = sorted(list(self.get_face_mechanics()))
        mech_str = ', '.join(mech_list)
        if ansi_color and mech_str:
            mech_str = utils.colorize(mech_str, utils.Ansi.CYAN)

        # Construct final summary string with consistent bullet separators
        res = f'{status}{rarity_indicator}{cardname}{coststr} \u2022 {typeline}'
        if stats:
            res += f' \u2022 {stats}'
        if mech_str:
            res += f' \u2022 {mech_str}'

        if self.bside:
            res += ' // ' + self.bside.summary(ansi_color=ansi_color)

        return res

    def format(self, gatherer=False, for_forum=False, vdump=False, for_html=False, ansi_color=False, for_md=False):
        """Formats the card data into a human-readable string.

        Args:
            gatherer (bool, optional): Whether to emulate the Gatherer visual spoiler.
                Defaults to False.
            for_forum (bool, optional): Whether to use pretty mana encoding for mtgsalvation forum.
                Defaults to False.
            vdump (bool, optional): Whether to dump out lots of information about invalid cards.
                Defaults to False.
            for_html (bool, optional): Whether to create a .html file with pretty forum formatting.
                Defaults to False.
            ansi_color (bool, optional): Whether to use ANSI color codes for terminal output.
                Defaults to False.
            for_md (bool, optional): Whether to use Markdown formatting.
                Defaults to False.

        Returns:
            str: The formatted card data.
        """
        linebreak = '\n'
        if for_html:
            linebreak = '<hr>' + linebreak

        outstr = ''
        if for_html:
            outstr += '<div class="card-text">\n'

        if gatherer:
            cardname = titlecase(transforms.name_unpass_1_dashes(self.__dict__[field_name]))
        else:
            cardname = titlecase(self.__dict__[field_name])

        if vdump and not cardname:
            cardname = '_NONAME_'

        if ansi_color:
            color = self._get_ansi_color()
            cardname = utils.colorize(cardname, color)

        coststr = self.__dict__[field_cost].format(for_forum=for_forum, for_html=for_html, ansi_color=ansi_color)
        rarity = self.rarity_name

        formatted_mtext = self.get_text(gatherer=gatherer, for_forum=for_forum,
                                        for_html=for_html, ansi_color=ansi_color)

        if for_html:
            image_url = utils.get_scryfall_image_url(getattr(self, 'set_code', None), getattr(self, 'number', None))
            if image_url:
                outstr += (f'<div class="hover_img"><a href="#"><b>{cardname}</b>'
                           + '<span><img style="background: url(' + image_url
                           + ');" alt=""/></span></a></div>')
            else:
                outstr += '<b>' + cardname + '</b>'
        elif for_forum:
            outstr += '[b]' + cardname + '[/b]'
        elif for_md:
            scry_url = utils.get_scryfall_url(getattr(self, 'set_code', None), getattr(self, 'number', None))
            if scry_url:
                outstr += f"[**{cardname}**]({scry_url})"
            else:
                outstr += '**' + cardname + '**'
        else:
            outstr += cardname

        if vdump or coststr:
            outstr += ' ' + coststr

        if for_html and for_forum:
            outstr += ('<div class="hover_img"><a href="#">[F]</a> <span><p>'
                       + self.format(gatherer=gatherer, for_forum=True, for_html=False, vdump=vdump, ansi_color=False).replace('\n', '<br>')
                       + '</p></span></div><a href="#top" style="float: right;">back to top</a>')

        rarity_display = rarity
        if ansi_color and rarity:
            color = utils.Ansi.get_rarity_color(rarity)
            rarity_display = utils.colorize(rarity, color)

        if rarity and gatherer:
            outstr += ' (' + rarity_display + ')'

        if vdump:
            if not self.parsed:
                outstr += ' _UNPARSED_'
            if not self.valid:
                outstr += ' _INVALID_'

        outstr += linebreak

        typeline = ''
        if gatherer:
            basetypes = list(map(str.capitalize, self.__dict__[field_types]))
            if vdump and len(basetypes) < 1:
                basetypes = ['_NOTYPE_']
            typeline += ' '.join(list(map(str.capitalize, self.__dict__[field_supertypes])) + basetypes)
            if self.__dict__[field_subtypes]:
                typeline += ' \u2014'
                for subtype in self.__dict__[field_subtypes]:
                    typeline += ' ' + titlecase(subtype)
        else:
            typeline = self.get_type_line(separator=utils.dash_marker)

        if ansi_color:
            typeline = utils.colorize(typeline, utils.Ansi.GREEN)

        outstr += typeline

        if rarity and not gatherer:
            outstr += ' (' + rarity_display.lower() + ')'

        if gatherer:
            stats = self._get_pt_display(ansi_color=ansi_color)
            if stats:
                outstr += ' ' + stats

            stats = self._get_loyalty_display(ansi_color=ansi_color, double_paren=True)
            if stats:
                outstr += ' ' + stats

        if formatted_mtext:
            # Add a blank line before the rules text for better readability
            # in plain text, color, and markdown formats.
            if not for_html and not for_forum:
                outstr += linebreak
            outstr += linebreak + formatted_mtext

        if not gatherer:
            stats = self._get_pt_display(ansi_color=ansi_color)
            if stats:
                outstr += linebreak + stats

            stats = self._get_loyalty_display(ansi_color=ansi_color, double_paren=True)
            if stats:
                outstr += linebreak + stats

        if vdump and self.__dict__[field_other]:
            outstr += linebreak
            if for_html:
                outstr += '<i>'
            elif for_forum:
                outstr += '[i]'
            elif for_md:
                outstr += '_'
            else:
                outstr += utils.dash_marker * 2

            for i, (idx, value) in enumerate(self.__dict__[field_other]):
                if for_html and i > 0:
                    outstr += '<br>\n'
                elif for_html:
                    outstr += '<br>'
                elif for_md and i > 0:
                    outstr += '  \n'
                else:
                    outstr += linebreak
                outstr += '(' + str(idx) + ') ' + str(value)

            if for_html:
                outstr += '</i>'
            elif for_forum:
                outstr += '[/i]'
            elif for_md:
                outstr += '_'

        if self.bside:
            outstr += linebreak
            if not for_html and not for_forum and not for_md:
                divider = "~~~~ (B-Side) " + "~" * 21
                if ansi_color:
                    divider = utils.colorize(divider, utils.Ansi.BOLD + utils.Ansi.CYAN)
                outstr += divider + linebreak
            elif not for_html:
                outstr += utils.dash_marker * 8 + linebreak
            outstr += self.bside.format(gatherer=gatherer, for_forum=for_forum and not for_html, for_html=for_html, vdump=vdump, ansi_color=ansi_color, for_md=for_md)

        if for_html:
            outstr += "</div>"

        return outstr

    def to_dict(self):
        """Returns a dictionary representation of the card, compatible with MTGJSON."""
        d = {}

        # Name
        cardname = titlecase(self.name)
        d['name'] = cardname

        # Mana Cost
        if not self.cost.none:
            d['manaCost'] = self.cost.format()

        # Rarity
        if self.rarity:
            d['rarity'] = self.rarity_name

        # Types
        d['supertypes'] = [titlecase(s) for s in self.supertypes]
        d['types'] = [titlecase(t) for t in self.types]
        if self.subtypes:
            d['subtypes'] = [titlecase(s) for s in self.subtypes]

        # Power / Toughness
        pt_str = self._get_pt_display(include_parens=False)
        if pt_str:
            if '/' in pt_str:
                p, t = pt_str.split('/', 1)
                d['power'] = p
                d['toughness'] = t
            else:
                d['pt'] = pt_str

        # Loyalty / Defense
        loyalty_val = self._get_loyalty_display(include_parens=False)
        if loyalty_val:
            if self.is_battle:
                d['defense'] = loyalty_val
            else:
                d['loyalty'] = loyalty_val

        # Text
        if self.text.text:
            d['text'] = self.get_text(force_unpass=True)

        # Metadata
        if self.set_code:
            d['setCode'] = self.set_code
        if self.number:
            d['number'] = self.number

        if hasattr(self, 'box_id'):
            d['box_id'] = self.box_id
        if hasattr(self, 'pack_id'):
            d['pack_id'] = self.pack_id

        # B-Side (Recursive)
        if self.bside:
            d['bside'] = self.bside.to_dict()

        return d
    
    def to_mse(self, print_raw = False, vdump = False):
        """Formats the card data into a string suitable for Magic Set Editor.

        Args:
            print_raw (bool, optional): Whether to print the raw card data.
                Defaults to False.
            vdump (bool, optional): Whether to dump out lots of information about invalid cards.
                Defaults to False.

        Returns:
            str: The formatted card data.
        """
        outstr = ''

        outstr += 'card:\n'

        cardname = titlecase(transforms.name_unpass_1_dashes(self.__dict__[field_name]))
        outstr += '\tname: ' + cardname + '\n'

        if self.rarity:
            outstr += '\trarity: ' + self.rarity_name.lower() + '\n'

        if not self.__dict__[field_cost].none:            
            outstr += ('\tcasting cost: ' 
                       + self.__dict__[field_cost].format().replace('{','').replace('}','') 
                       + '\n')

        outstr += '\tsuper type: ' + ' '.join(self.__dict__[field_supertypes] 
                                              + self.__dict__[field_types]).title() + '\n'
        if self.__dict__[field_subtypes]:
            outstr += ('\tsub type:')
            for subtype in self.__dict__[field_subtypes]:
                outstr += ' ' + titlecase(subtype)
            outstr += '\n'

        if self.__dict__[field_pt]:
            ptstring = utils.from_unary(self.__dict__[field_pt]).split('/')
            if (len(ptstring) > 1): # really don't want to be accessing anything nonexistent.
                outstr += '\tpower: ' + ptstring[0] + '\n'
                outstr += '\ttoughness: ' + ptstring[1] + '\n'

        newtext = self.get_text(mse=True)

        # Annoying special case for bsides;
        # This could be improved by having an intermediate function that returned
        # all of the formatted fields in a data structure and a separate wrapper
        # that actually packed them into the MSE format.
        if self.bside:
            newtext = newtext.replace('\n','\n\t\t')
            outstr += '\trule text:\n\t\t' + newtext + '\n'

            outstr += '\tstylesheet: new-split\n'

            cardname2 = titlecase(transforms.name_unpass_1_dashes(
                self.bside.__dict__[field_name]))

            outstr += '\tname 2: ' + cardname2 + '\n'
            if self.bside.rarity:
                outstr += '\trarity 2: ' + self.bside.rarity_name.lower() + '\n'

            if not self.bside.__dict__[field_cost].none:            
                outstr += ('\tcasting cost 2: ' 
                           + self.bside.__dict__[field_cost].format()
                           .replace('{','').replace('}','')
                           + '\n')

            outstr += ('\tsuper type 2: ' 
                       + ' '.join(self.bside.__dict__[field_supertypes] 
                                  + self.bside.__dict__[field_types]).title() + '\n')

            if self.bside.__dict__[field_subtypes]:
                outstr += ('\tsub type 2: ' 
                           + ' '.join(self.bside.__dict__[field_subtypes]).title() + '\n')

            if self.bside.__dict__[field_pt]:
                ptstring2 = utils.from_unary(self.bside.__dict__[field_pt]).split('/')
                if (len(ptstring2) > 1): # really don't want to be accessing anything nonexistent.
                    outstr += '\tpower 2: ' + ptstring2[0] + '\n'
                    outstr += '\ttoughness 2: ' + ptstring2[1] + '\n'

            newtext2 = self.bside.get_text(mse=True)
            if newtext2:
                newtext2 = newtext2.replace('\n', '\n\t\t')
                outstr += '\trule text 2:\n\t\t' + newtext2 + '\n'

        # Apply specific formatting for planeswalker cards.
        elif self.is_planeswalker:
            outstr += '\tstylesheet: m15-planeswalker\n'

            # set up the loyalty cost fields using regex to find how many there are.
            i = 0
            lcost_regex = r'([-−+−]?[\dxX]+): (.*)' # 1+ figures or X, might be 0.

            abilities = []
            for line in newtext.split('\n'):
                # Handle leading spaces that might be present in text_unpass_7_newlines result
                match = re.match(r'\s*' + lcost_regex, line)
                if match:
                    i += 1
                    outstr += '\tloyalty cost ' + str(i) + ': ' + match.group(1) + '\n'
                    abilities.append(match.group(2))
                elif line:
                    abilities.append(line.strip())

            # We need to uppercase again, because MSE won't magically capitalize for us
            # like it does after semicolons.
            # Re-apply line formatting and sentence casing for consistency.
            newtext = '\n'.join(abilities)
            newtext = transforms.text_pass_9_newlines(newtext)
            newtext = sentencecase(newtext)
            newtext = transforms.text_unpass_7_newlines(newtext)

            if self.__dict__[field_loyalty]:
                outstr += '\tloyalty: ' + utils.from_unary(self.__dict__[field_loyalty]) + '\n'

            newtext = newtext.replace('\n','\n\t\t')
            outstr += '\trule text:\n\t\t' + newtext + '\n'

        else:
            newtext = newtext.replace('\n','\n\t\t')
            outstr += '\trule text:\n\t\t' + newtext + '\n'

        # Append the remaining metadata fields required by the set file.
        outstr += '\thas styling: false\n\ttime created:2015-07-20 22:53:07\n\ttime modified:2015-07-20 22:53:08\n\textra data:\n\timage:\n\tcard code text:\n\tcopyright:\n\timage 2:\n\tcopyright 2:\n\tnotes:'

        return outstr

    def to_markdown_row(self):
        """Returns a Markdown table row representation of the card."""
        name, cost, cmc, typeline, stats, text, rarity, mechanics = self._get_display_data(include_text=True)

        # Escape pipe characters and ensure no actual newlines break the row
        fields = [name, cost, cmc, typeline, stats, text, rarity, mechanics]
        fields = [f.replace('|', '\\|').replace('\n', ' ') for f in fields]

        return f"| {' | '.join(fields)} |"

    def to_table_row(self, ansi_color=False):
        """Returns a list of strings representing the card's fields for a terminal table."""
        import datalib
        name, cost, cmc, typeline, stats, _, rarity, mechanics = self._get_display_data(ansi_color=ansi_color)

        # Limit mechanics list width to prevent table overflow
        mechanics = datalib.plimit(mechanics, 30)

        return [name, cost, cmc, typeline, stats, rarity, mechanics]

    def vectorize(self):
        """Vectorizes the card data into a string format suitable for machine learning.

        Returns:
            str: The vectorized card data.
        """
        ld = '('
        rd = ')'
        outstr = ''

        if self.__dict__[field_rarity]:
            outstr += ld + self.__dict__[field_rarity] + rd + ' '

        coststr = self.__dict__[field_cost].vectorize(delimit = True)
        if coststr:
            outstr += coststr + ' '

        typestr = ' '.join(
            ['(' + s + ')' for s in self.__dict__[field_supertypes] + self.__dict__[field_types]])
        if typestr:
            outstr += typestr + ' '

        if self.__dict__[field_subtypes]:
            outstr += ' '.join(self.__dict__[field_subtypes]) + ' '

        if self.pt:
            outstr += ' '.join(['(' + s + ')' for s in self.pt.replace('/', '/ /').split()])
            outstr += ' '

        if self.loyalty:
            outstr += self._get_loyalty_display(double_paren=True, unary=True) + ' '
            
        outstr += self.__dict__[field_text].vectorize()

        if self.bside:
            outstr = '_ASIDE_ ' + outstr + '\n\n_BSIDE_ ' + self.bside.vectorize()

        return outstr

    def to_cockatrice_xml(self):
        """Returns a Cockatrice XML <card> block representation of the card."""

        def get_fields(card):
            name = titlecase(card.name)
            mana_cost = card.cost.format().replace('{', '').replace('}', '')

            typeline = card.get_type_line()

            # Cockatrice <color> is the color letters
            color = ''.join(card.cost.colors)

            text = card.get_text(force_unpass=True)

            pt = ""
            if card.pt:
                pt = utils.from_unary(card.pt)
            elif card.loyalty:
                pt = utils.from_unary(card.loyalty)

            return name, mana_cost, typeline, color, text, pt

        name, cost, typeline, color, text, pt = get_fields(self)

        if self.bside:
            b_name, b_cost, b_typeline, b_color, b_text, b_pt = get_fields(self.bside)
            name = f"{name} // {b_name}"
            # Combined typeline and text for splits
            typeline = f"{typeline} // {b_typeline}"
            text = f"{text}\n\n---\n\n{b_text}"
            # Combined colors
            color = "".join(sorted(list(set(color + b_color))))

        # Determine tablerow
        # 0: Land, 1: Other, 2: Creature, 3: Spells
        tablerow = 1
        types_lower = [t.lower() for t in self.types]
        if 'land' in types_lower:
            tablerow = 0
        elif 'creature' in types_lower:
            tablerow = 2
        elif 'instant' in types_lower or 'sorcery' in types_lower:
            tablerow = 3

        xml_out = "    <card>\n"
        xml_out += f"      <name>{escape(name)}</name>\n"
        if self.set_code:
            xml_out += f"      <set>{escape(self.set_code.upper())}</set>\n"
        xml_out += f"      <color>{escape(color)}</color>\n"
        if cost:
            xml_out += f"      <manacost>{escape(cost)}</manacost>\n"
        xml_out += f"      <type>{escape(typeline)}</type>\n"
        if pt:
            xml_out += f"      <pt>{escape(pt)}</pt>\n"
        xml_out += f"      <tablerow>{tablerow}</tablerow>\n"
        xml_out += f"      <text>{escape(text)}</text>\n"
        xml_out += "    </card>"

        return xml_out
            
