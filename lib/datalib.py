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
            padded[-1] += (s + pad + ' ')
    return padded
def printrows(l):
    for row in l:
        print(row)

# index management helpers


def index_size(d):
    return sum([len(d[k]) for k in d])

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

def color_header(text, use_color):
    if use_color:
        return utils.colorize(text, utils.Ansi.BOLD + utils.Ansi.CYAN)
    return text

def color_line(text, use_color, color_code=utils.Ansi.BOLD + utils.Ansi.CYAN):
    if use_color:
        return utils.colorize(text, color_code)
    return text

class Datamine:
    # build the global indices
    def __init__(self, card_srcs):
        # global card pools
        self.unparsed_cards = []
        self.invalid_cards = []
        self.cards = []
        self.allcards = []
        
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
        }

        for card_src in card_srcs:
            # the empty card is not interesting
            if not card_src:
                continue
            card = Card(card_src)
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

                # normalize rarity
                rarity = card.rarity
                if rarity in utils.json_rarity_unmap:
                    rarity = utils.json_rarity_unmap[rarity]
                inc(self.by_rarity, rarity, [card])

                inc(self.by_textlines, len(card.text_lines), [card])
                inc(self.by_textlen, len(card.text.encode()), [card])

    # summarize the indices
    def summarize(self, hsize = 10, vsize = 10, cmcsize = 20, use_color = False):

        print(color_line('========================================', use_color))
        print(color_header('             DATASET SUMMARY            ', use_color))
        print(color_line('========================================', use_color))
        print(color_count(len(self.cards), use_color) + ' valid cards, ' +
              color_count(len(self.invalid_cards), use_color, utils.Ansi.BOLD + utils.Ansi.RED) + ' invalid cards.')
        print(color_count(len(self.allcards), use_color) + ' cards parsed, ' +
              color_count(len(self.unparsed_cards), use_color, utils.Ansi.BOLD + utils.Ansi.RED) + ' failed to parse')
        print()

        print(color_header(str(len(self.by_name)) + ' unique card names', use_color))
        print()

        print(color_header(str(len(self.by_color_inclusive)) + ' represented colors (including colorless as \'A\'), '
               + str(len(self.by_color)) + ' combinations', use_color))
        print(color_header('Breakdown by color:', use_color))
        rows = []
        for k in sorted(self.by_color_inclusive.keys()):
            rows += [[k, color_count(len(self.by_color_inclusive[k]), use_color)]]
        printrows(padrows(rows))
        print(color_header('Breakdown by number of colors:', use_color))
        rows = []
        for k in sorted(self.by_color_count.keys()):
            rows += [[str(k), color_count(len(self.by_color_count[k]), use_color)]]
        printrows(padrows(rows))
        print()

        print(color_header(str(len(self.by_type_inclusive)) + ' unique card types, ' +
              str(len(self.by_type)) + ' combinations', use_color))
        print(color_header('Breakdown by type:', use_color))
        d = sorted(self.by_type_inclusive,
                   key=lambda x: len(self.by_type_inclusive[x]),
                   reverse=True)
        rows = []
        for k in d[:vsize]:
            rows += [[k, color_count(len(self.by_type_inclusive[k]), use_color)]]
        printrows(padrows(rows))
        print()

        print(color_header(str(len(self.by_subtype_inclusive)) + ' unique subtypes, '
               + str(len(self.by_subtype)) + ' combinations', use_color))
        print(color_header('Popular subtypes:', use_color))
        d = sorted(self.by_subtype_inclusive,
                   key=lambda x: len(self.by_subtype_inclusive[x]),
                   reverse=True)
        rows = []
        for k in d[0:vsize]:
            rows += [[k, color_count(len(self.by_subtype_inclusive[k]), use_color)]]
        printrows(padrows(rows))
        print(color_header('Top combinations:', use_color))
        d = sorted(self.by_subtype,
                   key=lambda x: len(self.by_subtype[x]),
                   reverse = True)
        rows = []
        for k in d[0:vsize]:
            rows += [[k, color_count(len(self.by_subtype[k]), use_color)]]
        printrows(padrows(rows))
        print()

        print(color_header(str(len(self.by_supertype_inclusive)) + ' unique supertypes, '
               + str(len(self.by_supertype)) + ' combinations', use_color))
        print(color_header('Breakdown by supertype:', use_color))
        d = sorted(self.by_supertype_inclusive,
                   key=lambda x: len(self.by_supertype_inclusive[x]),
                   reverse=True)
        rows = []
        for k in d[:vsize]:
            rows += [[k, color_count(len(self.by_supertype_inclusive[k]), use_color)]]
        printrows(padrows(rows))
        print()

        print(color_header(str(len(self.by_cmc)) + ' different CMCs, ' +
              str(len(self.by_cost)) + ' unique mana costs', use_color))
        avg_cmc = sum(c.cost.cmc for c in self.cards) / len(self.cards) if self.cards else 0
        print('Average CMC: {:.2f}'.format(avg_cmc))
        print(color_header('Breakdown by CMC:', use_color))
        d = sorted(self.by_cmc, reverse=False)
        rows = []
        for k in d[:vsize]:
            rows += [[str(k), color_count(len(self.by_cmc[k]), use_color)]]
        printrows(padrows(rows))
        print(color_header('Popular mana costs:', use_color))
        d = sorted(self.by_cost,
                   key=lambda x: len(self.by_cost[x]),
                   reverse = True)
        rows = []
        for k in d[0:vsize]:
            rows += [[utils.from_mana(k), color_count(len(self.by_cost[k]), use_color)]]
        printrows(padrows(rows))
        print()

        print(color_header(str(len(self.by_rarity)) + ' represented rarities', use_color))
        print(color_header('Breakdown by rarity:', use_color))
        rows = []
        for k in sorted(self.by_rarity.keys()):
            rows += [[k, color_count(len(self.by_rarity[k]), use_color)]]
        printrows(padrows(rows))
        print()

        print(color_header(str(len(self.by_pt)) + ' unique p/t combinations', use_color))
        if len(self.by_power) > 0 and len(self.by_toughness) > 0:
            print(('Largest power: ' + str(max(list(map(len, self.by_power))) - 1) +
                   ', largest toughness: ' + str(max(list(map(len, self.by_toughness))) - 1)))
        print(color_header('Popular p/t values:', use_color))
        d = sorted(self.by_pt,
                   key=lambda x: len(self.by_pt[x]),
                   reverse = True)
        rows = []
        for k in d[0:vsize]:
            rows += [[utils.from_unary(k), color_count(len(self.by_pt[k]), use_color)]]
        printrows(padrows(rows))
        print()

        print(color_header('Loyalty values:', use_color))
        d = sorted(self.by_loyalty,
                   key=lambda x: len(self.by_loyalty[x]),
                   reverse = True)
        rows = []
        for k in d[0:vsize]:
            rows += [[utils.from_unary(k), color_count(len(self.by_loyalty[k]), use_color)]]
        printrows(padrows(rows))
        print()

        if len(self.by_textlen) > 0 and len(self.by_textlines) > 0:
            print(color_header('Card text ranges from ' + str(min(self.by_textlen)) + ' to '
                   + str(max(self.by_textlen)) + ' characters in length', use_color))
            print(color_header('Card text ranges from ' + str(min(self.by_textlines)) + ' to '
                   + str(max(self.by_textlines)) + ' lines', use_color))
        print(color_header('Line counts by frequency:', use_color))
        d = sorted(self.by_textlines,
                   key=lambda x: len(self.by_textlines[x]),
                   reverse = True)
        rows = []
        for k in d[0:vsize]:
            rows += [[k, color_count(len(self.by_textlines[k]), use_color)]]
        printrows(padrows(rows))
        print(color_line('========================================', use_color))

    # describe outliers in the indices
    def outliers(self, hsize=10, vsize=10, dump_invalid=False, use_color = False):

        print(color_line('========================================', use_color))
        print(color_header('            OUTLIER ANALYSIS            ', use_color))
        print(color_line('========================================', use_color))
        print(color_header('Overview of indices:', use_color))
        rows = [['Index Name', 'Keys', 'Total Members']]
        for index in self.indices:
            rows += [[index, color_count(len(self.indices[index]), use_color),
                      color_count(index_size(self.indices[index]), use_color)]]
        printrows(padrows(rows))
        print()

        if len(self.by_name) > 0:
            scardname = sorted(self.by_name,
                               key=len,
                               reverse=False)[0]
            print(color_header('Shortest Cardname: (' + str(len(scardname)) + ')', use_color))
            print('  ' + scardname)
            lcardname = sorted(self.by_name,
                               key=len,
                               reverse=True)[0]
            print(color_header('Longest Cardname: (' + str(len(lcardname)) + ')', use_color))
            print('  ' + lcardname)
            d = sorted(self.by_name,
                       key=lambda x: len(self.by_name[x]),
                       reverse = True)
            rows = []
            for k in d[0:vsize]:
                if len(self.by_name[k]) > 1:
                    rows += [[k, color_count(len(self.by_name[k]), use_color)]]
            if rows == []:
                print('No duplicated cardnames')
            else:
                print(color_header('Most duplicated names:', use_color))
                printrows(padrows(rows))
        else:
            print('No cards indexed by name?')
        print()

        if len(self.by_type) > 0:
            ltypes = sorted(self.by_type,
                            key=len,
                            reverse=True)[0]
            print(color_header('Longest card type: (' + str(len(ltypes)) + ')', use_color))
            print('  ' + ltypes)
        else:
            print('No cards indexed by type?')
        if len(self.by_subtype) > 0:
            lsubtypes = sorted(self.by_subtype,
                               key=len,
                               reverse=True)[0]
            print(color_header('Longest subtype: (' + str(len(lsubtypes)) + ')', use_color))
            print('  ' + lsubtypes)
        else:
            print('No cards indexed by subtype?')
        if len(self.by_supertype) > 0:
            lsupertypes = sorted(self.by_supertype,
                                 key=len,
                                 reverse=True)[0]
            print(color_header('Longest supertype: (' + str(len(lsupertypes)) + ')', use_color))
            print('  ' + lsupertypes)
        else:
            print('No cards indexed by supertype?')
        print()

        if len(self.by_cost) > 0:
            lcost = sorted(self.by_cost,
                           key=len,
                           reverse=True)[0]
            print(color_header('Longest mana cost: (' + str(len(lcost)) + ')', use_color))
            print('  ' + utils.from_mana(lcost))
            print('\n' + plimit(self.by_cost[lcost][0].encode()) + '\n')
        else:
            print('No cards indexed by cost?')
        if len(self.by_cmc) > 0:
            lcmc = sorted(self.by_cmc, reverse=True)[0]
            print(color_header('Largest cmc: (' + str(lcmc) + ')', use_color))
            print('  ' + str(self.by_cmc[lcmc][0].cost))
            print('\n' + plimit(self.by_cmc[lcmc][0].encode()))
        else:
            print('No cards indexed by cmc?')
        print()

        if len(self.by_power) > 0:
            lpower = sorted(self.by_power,
                            key=len,
                            reverse=True)[0]
            print(color_header('Largest creature power: ' + utils.from_unary(lpower), use_color))
            print('\n' + plimit(self.by_power[lpower][0].encode()) + '\n')
        else:
            print('No cards indexed by power?')
        if len(self.by_toughness) > 0:
            ltoughness = sorted(self.by_toughness,
                                key=len,
                                reverse=True)[0]
            print(color_header('Largest creature toughness: ' +
                  utils.from_unary(ltoughness), use_color))
            print('\n' + plimit(self.by_toughness[ltoughness][0].encode()))
        else:
            print('No cards indexed by toughness?')
        print()

        if len(self.by_textlines) > 0:
            llines = sorted(self.by_textlines, reverse=True)[0]
            print(color_header('Most lines of text in a card: ' + str(llines), use_color))
            print('\n' + plimit(self.by_textlines[llines][0].encode()) + '\n')
        else:
            print('No cards indexed by line count?')
        if len(self.by_textlen) > 0:
            ltext = sorted(self.by_textlen, reverse=True)[0]
            print(color_header('Most chars in a card text: ' + str(ltext), use_color))
            print('\n' + plimit(self.by_textlen[ltext][0].encode()))
        else:
            print('No cards indexed by char count?')
        print()

        print(color_header('There were ' + color_count(len(self.invalid_cards), use_color, utils.Ansi.BOLD + utils.Ansi.RED) + ' invalid cards.', use_color))
        if dump_invalid:
            for card in self.invalid_cards:
                print('\n' + repr(card.fields))
        elif len(self.invalid_cards) > 0:
            print('Not summarizing.')
        print()

        print(color_header('There were ' + color_count(len(self.unparsed_cards), use_color, utils.Ansi.BOLD + utils.Ansi.RED) + ' unparsed cards.', use_color))
        if dump_invalid:
            for card in self.unparsed_cards:
                print('\n' + repr(card.fields))
        elif len(self.unparsed_cards) > 0:
            print('Not summarizing.')
        print(color_line('========================================', use_color))

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

        if self.by_textlen:
            result['stats'] = {
                'textlen_min': min(self.by_textlen),
                'textlen_max': max(self.by_textlen),
                'textlines_min': min(self.by_textlines),
                'textlines_max': max(self.by_textlines),
                'avg_cmc': sum(c.cost.cmc for c in self.cards) / len(self.cards) if self.cards else 0,
            }
        return result
