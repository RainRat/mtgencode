import re

import utils
from cardlib import Card

# Format a list of rows of data into nice columns.
# Note that it's the columns that are nice, not this code.
def padrows(l):
    # get length for each field
    lens = []
    for ll in l:
        for i, field in enumerate(ll):
            if i < len(lens):
                lens[i] = max(utils.visible_len(str(field)), lens[i])
            else:
                lens += [utils.visible_len(str(field))]
    # now pad out to that length
    padded = []
    for ll in l:
        padded += ['']
        for i, field in enumerate(ll):
            s = str(field)
            pad = ' ' * (lens[i] - utils.visible_len(s))
            padded[-1] += (s + pad + '  ')
    return padded
def printrows(l, indent=0):
    pad = ' ' * indent
    for row in l:
        print(pad + row)

# index management helpers


def inc(d, k, obj):
    if k or k == 0:
        if k in d:
            d[k] += obj
        else:
            d[k] = obj

# thanks gleemax
def plimit(s, mlen = 1000):
    if len(s) > mlen:
        return s[:mlen] + '[...]'
    else:
        return s

def color_count(count, use_color, color_code=utils.Ansi.BOLD + utils.Ansi.GREEN):
    s = str(count)
    if use_color and count > 0:
        return utils.colorize(s, color_code)
    return s

def color_line(text, use_color, color_code=utils.Ansi.BOLD + utils.Ansi.CYAN):
    if use_color:
        return utils.colorize(text, color_code)
    return text

def _print_breakdown(title, index, total, use_color, vsize=None, sort_key=None, reverse=True, key_formatter=None):
    if not index:
        return
    print()
    print('  ' + color_line(title, use_color))

    if sort_key:
        keys = sorted(index.keys(), key=sort_key, reverse=reverse)
    else:
        # default alphabetical
        keys = sorted(index.keys())

    if vsize:
        keys = keys[:vsize]

    header_row = ['Category', 'Count', 'Percent', 'Distribution']
    if use_color:
        header_row = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header_row]

    rows = [header_row]
    for k in keys:
        count = len(index[k])
        percent = (count / total * 100) if total > 0 else 0

        display_key = key_formatter(k) if key_formatter else str(k)

        # apply content-aware coloring
        display_color = None
        if use_color:
            if 'rarity' in title.lower():
                display_color = utils.Ansi.get_rarity_color(k)
                display_key = utils.colorize(display_key, display_color)
            elif 'color' in title.lower() and not 'number' in title.lower():
                display_color = utils.Ansi.get_color_color(k)
                display_key = utils.colorize(display_key, display_color)
            elif 'mana costs' in title.lower():
                display_key = utils.from_mana(k, ansi_color=True)
            elif 'p/t' in title.lower() or 'loyalty' in title.lower():
                display_color = utils.Ansi.RED
                display_key = utils.colorize(display_key, display_color)

        # Bar chart
        bar_width = 10
        filled = int(round(percent / 100 * bar_width))
        if filled == 0 and percent > 0:
            filled = 1
        bar = '[' + '#' * filled + ' ' * (bar_width - filled) + ']'
        if use_color:
            bar_color = display_color if display_color else (utils.Ansi.BOLD + utils.Ansi.GREEN)
            bar = utils.colorize(bar, bar_color)

        rows.append([
            display_key,
            color_count(count, use_color),
            f"{percent:5.1f}%",
            bar
        ])
    printrows(padrows(rows), indent=4)

def _print_color_pie(pie_groups, pie_mechanics, all_mechanics, use_color, vsize=None):
    if not all_mechanics:
        return
    print()
    print('  ' + color_line('Mechanical Color Pie (Frequency %):', use_color))

    header = ['Mechanic', 'W', 'U', 'B', 'R', 'G', 'A', 'M']
    if use_color:
        header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

    rows = [header]
    # Sort mechanics by total frequency
    sorted_mechanics = sorted(all_mechanics.keys(), key=lambda m: len(all_mechanics[m]), reverse=True)
    if vsize:
        sorted_mechanics = sorted_mechanics[:vsize]

    for m in sorted_mechanics:
        row = [m]
        for group in 'WUBRGAM':
            total = pie_groups[group]
            count = pie_mechanics[group].get(m, 0)
            percent = (count / total * 100) if total > 0 else 0

            val = f"{percent:4.0f}%" if percent > 0 else "  - "
            if use_color and percent > 0:
                color = utils.Ansi.get_color_color(group)
                val = utils.colorize(val, color)
            row.append(val)
        rows.append(row)

    printrows(padrows(rows), indent=4)

class Datamine:
    # build the global indices
    def __init__(self, cards_input):
        # global card pools
        self.unparsed_cards = []
        self.invalid_cards = []
        self.cards = []
        self.allcards = []

        # color pie indices
        self.pie_groups = {c: 0 for c in 'WUBRGAM'}
        self.pie_mechanics = {c: {} for c in 'WUBRGAM'}

        # global indices
        self.by_name = {}
        self.by_type = {}
        self.by_type_inclusive = {}
        self.by_supertype = {}
        self.by_supertype_inclusive = {}
        self.by_subtype = {}
        self.by_subtype_inclusive = {}
        self.by_color = {}
        self.by_color_inclusive = {}
        self.by_color_count = {}
        self.by_cmc = {}
        self.by_cost = {}
        self.by_power = {}
        self.by_toughness = {}
        self.by_pt = {}
        self.by_loyalty = {}
        self.by_rarity = {}
        self.by_textlines = {}
        self.by_textlen = {}
        self.by_mechanic = {}

        self.indices = {
            'by_name' : self.by_name,
            'by_type' : self.by_type,
            'by_type_inclusive' : self.by_type_inclusive,
            'by_supertype' : self.by_supertype,
            'by_supertype_inclusive' : self.by_supertype_inclusive,
            'by_subtype' : self.by_subtype,
            'by_subtype_inclusive' : self.by_subtype_inclusive,
            'by_color' : self.by_color,
            'by_color_inclusive' : self.by_color_inclusive,
            'by_color_count' : self.by_color_count,
            'by_cmc' : self.by_cmc,
            'by_cost' : self.by_cost,
            'by_power' : self.by_power,
            'by_toughness' : self.by_toughness,
            'by_pt' : self.by_pt,
            'by_loyalty' : self.by_loyalty,
            'by_rarity' : self.by_rarity,
            'by_textlines' : self.by_textlines,
            'by_textlen' : self.by_textlen,
            'by_mechanic' : self.by_mechanic,
        }

        for item in cards_input:
            # the empty card is not interesting
            if not item:
                continue

            if hasattr(item, 'fields'):
                card = item
            else:
                card = Card(item)

            if card.valid:
                self.cards += [card]
                self.allcards += [card]
            elif card.parsed:
                self.invalid_cards += [card]
                self.allcards += [card]
            else:
                self.unparsed_cards += [card]

            if card.parsed:
                inc(self.by_name, card.name, [card])

                inc(self.by_type, ' '.join(card.types), [card])
                for t in card.types:
                    inc(self.by_type_inclusive, t, [card])
                inc(self.by_supertype, ' '.join(card.supertypes), [card])
                for t in card.supertypes:
                    inc(self.by_supertype_inclusive, t, [card])
                inc(self.by_subtype, ' '.join(card.subtypes), [card])
                for t in card.subtypes:
                    inc(self.by_subtype_inclusive, t, [card])

                if card.cost.colors:
                    inc(self.by_color, card.cost.colors, [card])
                    for c in card.cost.colors:
                        inc(self.by_color_inclusive, c, [card])
                    inc(self.by_color_count, len(card.cost.colors), [card])
                else:
                    # colorless, still want to include in these tables
                    inc(self.by_color, 'A', [card])
                    inc(self.by_color_inclusive, 'A', [card])
                    inc(self.by_color_count, 0, [card])

                inc(self.by_cmc, card.cost.cmc, [card])
                inc(self.by_cost, card.cost.encode() if card.cost.encode() else 'none', [card])

                inc(self.by_power, card.pt_p, [card])
                inc(self.by_toughness, card.pt_t, [card])
                inc(self.by_pt, card.pt, [card])

                inc(self.by_loyalty, card.loyalty, [card])

                inc(self.by_rarity, card.rarity_name, [card])

                inc(self.by_textlines, len(card.text_lines), [card])
                inc(self.by_textlen, len(card.text.encode()), [card])

                # Mechanical profiling using Card.mechanics
                # Categorize for Color Pie analysis
                group = 'A'
                if len(card.cost.colors) > 1:
                    group = 'M'
                elif len(card.cost.colors) == 1:
                    group = card.cost.colors[0]

                self.pie_groups[group] += 1
                for m in card.mechanics:
                    inc(self.by_mechanic, m, [card])
                    self.pie_mechanics[group][m] = self.pie_mechanics[group].get(m, 0) + 1

        self.avg_cmc = sum(c.cost.cmc for c in self.cards) / len(self.cards) if self.cards else 0

        # Calculate average P/T
        p_vals = [utils.from_unary_single(c.pt_p) for c in self.cards if c.pt_p is not None]
        t_vals = [utils.from_unary_single(c.pt_t) for c in self.cards if c.pt_t is not None]
        self.avg_power = sum(p_vals) / len(p_vals) if p_vals else 0
        self.avg_toughness = sum(t_vals) / len(t_vals) if t_vals else 0

    # summarize the indices
    def summarize(self, hsize = 10, vsize = 10, cmcsize = 20, use_color = False):

        print(color_line('DATASET SUMMARY', use_color, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE))
        print('  ' + color_count(len(self.cards), use_color) + ' valid cards, ' +
              color_count(len(self.invalid_cards), use_color, utils.Ansi.BOLD + utils.Ansi.RED) + ' invalid cards.')
        print('  ' + color_count(len(self.allcards), use_color) + ' cards parsed, ' +
              color_count(len(self.unparsed_cards), use_color, utils.Ansi.BOLD + utils.Ansi.RED) + ' failed to parse')
        print('  ' + color_count(len(self.by_name), use_color) + " unique card names")
        print()

        # Section: Colors & Mana
        print(color_line('COLORS & MANA', use_color, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE))
        print('  ' + color_line(str(len(self.by_color_inclusive)) + ' represented colors (including colorless as \'A\'), '
               + str(len(self.by_color)) + ' combinations', use_color))
        _print_breakdown('Breakdown by color:', self.by_color_inclusive, len(self.allcards), use_color)
        _print_breakdown('Breakdown by number of colors:', self.by_color_count, len(self.allcards), use_color)
        print()

        print('  ' + color_line(str(len(self.by_cmc)) + ' different CMCs, ' +
              str(len(self.by_cost)) + ' unique mana costs', use_color))
        avg_cmc_str = 'Average CMC: {:.2f}'.format(self.avg_cmc)
        if use_color:
            avg_cmc_str = utils.colorize(avg_cmc_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
        print('  ' + avg_cmc_str)
        _print_breakdown('Breakdown by CMC:', self.by_cmc, len(self.allcards), use_color,
                         vsize=cmcsize, reverse=False, sort_key=lambda x: float(x))
        _print_breakdown('Popular mana costs:', self.by_cost, len(self.allcards), use_color,
                         vsize=vsize, sort_key=lambda x: len(self.by_cost[x]), key_formatter=utils.from_mana)
        print()

        # Section: Card Types
        print(color_line('CARD TYPES', use_color, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE))
        print('  ' + color_line(str(len(self.by_type_inclusive)) + ' unique card types, ' +
              str(len(self.by_type)) + ' combinations', use_color))
        _print_breakdown('Breakdown by type:', self.by_type_inclusive, len(self.allcards), use_color,
                         vsize=vsize, sort_key=lambda x: len(self.by_type_inclusive[x]))
        print()

        print('  ' + color_line(str(len(self.by_subtype_inclusive)) + ' unique subtypes, '
               + str(len(self.by_subtype)) + ' combinations', use_color))
        _print_breakdown('Popular subtypes:', self.by_subtype_inclusive, len(self.allcards), use_color,
                         vsize=vsize, sort_key=lambda x: len(self.by_subtype_inclusive[x]))
        _print_breakdown('Top combinations:', self.by_subtype, len(self.allcards), use_color,
                         vsize=vsize, sort_key=lambda x: len(self.by_subtype[x]))
        print()

        print('  ' + color_line(str(len(self.by_supertype_inclusive)) + ' unique supertypes, '
               + str(len(self.by_supertype)) + ' combinations', use_color))
        _print_breakdown('Breakdown by supertype:', self.by_supertype_inclusive, len(self.allcards), use_color,
                         vsize=vsize, sort_key=lambda x: len(self.by_supertype_inclusive[x]))
        print()

        # Section: Stats & Rarity
        print(color_line('STATS & RARITY', use_color, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE))
        print('  ' + color_line(str(len(self.by_rarity)) + ' represented rarities', use_color))
        _print_breakdown('Breakdown by rarity:', self.by_rarity, len(self.allcards), use_color)
        print()

        print('  ' + color_line(str(len(self.by_pt)) + ' unique p/t combinations', use_color))
        if len(self.by_power) > 0 and len(self.by_toughness) > 0:
            print('  ' + ('Largest power: ' + str(max(map(utils.from_unary_single, self.by_power))) +
                   ', largest toughness: ' + str(max(map(utils.from_unary_single, self.by_toughness)))))
            avg_pt_str = f'Average power: {self.avg_power:.2f}, Average toughness: {self.avg_toughness:.2f}'
            if use_color:
                avg_pt_str = utils.colorize(avg_pt_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
            print('  ' + avg_pt_str)
        _print_breakdown('Popular p/t values:', self.by_pt, len(self.allcards), use_color,
                         vsize=vsize, sort_key=lambda x: len(self.by_pt[x]), key_formatter=utils.from_unary)
        print()

        if self.by_loyalty:
            _print_breakdown('Loyalty values:', self.by_loyalty, len(self.allcards), use_color,
                             vsize=vsize, sort_key=lambda x: len(self.by_loyalty[x]), key_formatter=utils.from_unary)
            print()

        # Section: Content & Mechanics
        print(color_line('CONTENT & MECHANICS', use_color, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE))
        if len(self.by_textlen) > 0 and len(self.by_textlines) > 0:
            print('  ' + color_line('Card text ranges from ' + str(min(self.by_textlen)) + ' to '
                   + str(max(self.by_textlen)) + ' characters in length', use_color))
            print('  ' + color_line('Card text ranges from ' + str(min(self.by_textlines)) + ' to '
                   + str(max(self.by_textlines)) + ' lines', use_color))
        _print_breakdown('Line counts by frequency:', self.by_textlines, len(self.allcards), use_color,
                         vsize=vsize, sort_key=lambda x: len(self.by_textlines[x]))
        print()

        print('  ' + color_line(str(len(self.by_mechanic)) + ' distinct mechanical features identified', use_color))
        _print_breakdown('Mechanical Breakdown:', self.by_mechanic, len(self.allcards), use_color,
                         vsize=vsize, sort_key=lambda x: len(self.by_mechanic[x]))
        _print_color_pie(self.pie_groups, self.pie_mechanics, self.by_mechanic, use_color, vsize=vsize)
        print()

    # describe outliers in the indices
    def outliers(self, hsize=10, vsize=10, dump_invalid=False, use_color = False):

        print(color_line('OUTLIER ANALYSIS', use_color, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE))
        print('  ' + color_line('Overview of indices:', use_color))

        header_row = ['  Index Name', 'Keys', 'Total Members']
        if use_color:
            header_row = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header_row]

        rows = [header_row]
        for index in self.indices:
            rows += [[index, color_count(len(self.indices[index]), use_color),
                      color_count(sum(len(v) for v in self.indices[index].values()), use_color)]]
        printrows(padrows(rows), indent=4)
        print()

        if len(self.by_name) > 0:
            scardname = sorted(self.by_name,
                               key=len,
                               reverse=False)[0]
            print('  ' + color_line('Shortest Cardname: (' + str(len(scardname)) + ')', use_color))
            print('    ' + scardname)
            lcardname = sorted(self.by_name,
                               key=len,
                               reverse=True)[0]
            print('  ' + color_line('Longest Cardname: (' + str(len(lcardname)) + ')', use_color))
            print('    ' + lcardname)
            d = sorted(self.by_name,
                       key=lambda x: len(self.by_name[x]),
                       reverse = True)
            rows = []
            for k in d[0:vsize]:
                if len(self.by_name[k]) > 1:
                    rows += [[k, color_count(len(self.by_name[k]), use_color)]]
            if rows == []:
                print('  No duplicated cardnames')
            else:
                print('  ' + color_line('Most duplicated names:', use_color))
                printrows(padrows(rows), indent=4)
        else:
            print('  No cards indexed by name?')
        print()

        if len(self.by_type) > 0:
            ltypes = sorted(self.by_type,
                            key=len,
                            reverse=True)[0]
            print('  ' + color_line('Longest card type: (' + str(len(ltypes)) + ')', use_color))
            print('    ' + ltypes)
        else:
            print('  No cards indexed by type?')
        if len(self.by_subtype) > 0:
            lsubtypes = sorted(self.by_subtype,
                               key=len,
                               reverse=True)[0]
            print('  ' + color_line('Longest subtype: (' + str(len(lsubtypes)) + ')', use_color))
            print('    ' + lsubtypes)
        else:
            print('  No cards indexed by subtype?')
        if len(self.by_supertype) > 0:
            lsupertypes = sorted(self.by_supertype,
                                 key=len,
                                 reverse=True)[0]
            print('  ' + color_line('Longest supertype: (' + str(len(lsupertypes)) + ')', use_color))
            print('    ' + lsupertypes)
        else:
            print('  No cards indexed by supertype?')
        print()

        if len(self.by_cost) > 0:
            lcost = sorted(self.by_cost,
                           key=len,
                           reverse=True)[0]
            print('  ' + color_line('Longest mana cost: (' + str(len(lcost)) + ')', use_color))
            print('    ' + utils.from_mana(lcost))
            print('\n    ' + plimit(self.by_cost[lcost][0].encode()).replace('\n', '\n    ') + '\n')
        else:
            print('  No cards indexed by cost?')
        if len(self.by_cmc) > 0:
            lcmc = sorted(self.by_cmc, reverse=True)[0]
            print('  ' + color_line('Largest cmc: (' + str(lcmc) + ')', use_color))
            print('    ' + str(self.by_cmc[lcmc][0].cost))
            print('\n    ' + plimit(self.by_cmc[lcmc][0].encode()).replace('\n', '\n    '))
        else:
            print('  No cards indexed by cmc?')
        print()

        if len(self.by_power) > 0:
            lpower = sorted(self.by_power,
                            key=utils.from_unary_single,
                            reverse=True)[0]
            print('  ' + color_line('Largest creature power: ' + utils.from_unary(lpower), use_color))
            print('\n    ' + plimit(self.by_power[lpower][0].encode()).replace('\n', '\n    ') + '\n')
        else:
            print('  No cards indexed by power?')
        if len(self.by_toughness) > 0:
            ltoughness = sorted(self.by_toughness,
                                key=utils.from_unary_single,
                                reverse=True)[0]
            print('  ' + color_line('Largest creature toughness: ' +
                  utils.from_unary(ltoughness), use_color))
            print('\n    ' + plimit(self.by_toughness[ltoughness][0].encode()).replace('\n', '\n    '))
        else:
            print('  No cards indexed by toughness?')
        print()

        if len(self.by_textlines) > 0:
            llines = sorted(self.by_textlines, reverse=True)[0]
            print('  ' + color_line('Most lines of text in a card: ' + str(llines), use_color))
            print('\n    ' + plimit(self.by_textlines[llines][0].encode()).replace('\n', '\n    ') + '\n')
        else:
            print('  No cards indexed by line count?')
        if len(self.by_textlen) > 0:
            ltext = sorted(self.by_textlen, reverse=True)[0]
            print('  ' + color_line('Most chars in a card text: ' + str(ltext), use_color))
            print('\n    ' + plimit(self.by_textlen[ltext][0].encode()).replace('\n', '\n    '))
        else:
            print('  No cards indexed by char count?')
        print()

        print('  ' + color_line('There were ' + color_count(len(self.invalid_cards), use_color, utils.Ansi.BOLD + utils.Ansi.RED) + ' invalid cards.', use_color))
        if dump_invalid:
            for card in self.invalid_cards:
                print('\n    ' + repr(card.fields).replace('\n', '\n    '))
        elif len(self.invalid_cards) > 0:
            print('  Not summarizing.')
        print()

        print('  ' + color_line('There were ' + color_count(len(self.unparsed_cards), use_color, utils.Ansi.BOLD + utils.Ansi.RED) + ' unparsed cards.', use_color))
        if dump_invalid:
            for card in self.unparsed_cards:
                print('\n    ' + repr(card.fields).replace('\n', '\n    '))
        elif len(self.unparsed_cards) > 0:
            print('  Not summarizing.')
        print()

    def to_dict(self):
        """Returns a dictionary representation of the collected statistics."""
        result = {
            'counts': {
                'valid': len(self.cards),
                'invalid': len(self.invalid_cards),
                'parsed': len(self.allcards),
                'unparsed': len(self.unparsed_cards),
            },
            'indices': {}
        }
        for name, index in self.indices.items():
            result['indices'][name] = {str(k): len(v) for k, v in index.items()}

        result['color_pie'] = {
            'groups': self.pie_groups,
            'mechanics': self.pie_mechanics
        }

        if self.by_textlen:
            result['stats'] = {
                'textlen_min': min(self.by_textlen),
                'textlen_max': max(self.by_textlen),
                'textlines_min': min(self.by_textlines),
                'textlines_max': max(self.by_textlines),
                'avg_cmc': self.avg_cmc,
                'avg_power': self.avg_power,
                'avg_toughness': self.avg_toughness,
            }
        return result
