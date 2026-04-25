# This module is misleadingly named, as it has other utilities as well
# that are generally necessary when trying to postprocess output by
# comparing it against existing cards.

import difflib
import os
import multiprocessing

import utils
import jdecode
import cardlib

libdir = os.path.dirname(os.path.realpath(__file__))
datadir = os.path.realpath(os.path.join(libdir, '../data'))

# multithreading control parameters
cores = multiprocessing.cpu_count()

# split a list into n pieces; return a list of these lists
# has slightly interesting behavior, in that if n is large, it can
# run out of elements early and return less than n lists
def list_split(l, n):
    if not l:
        return []
    if n <= 0:
        return [l]
    split_size = len(l) // n
    if len(l) % n > 0:
        split_size += 1
    return [l[i:i+split_size] for i in range(0, len(l), int(split_size))]

# flatten a list of lists into a single list of all their contents, in order
def list_flatten(l):
    return [item for sublist in l for item in sublist]


# isolated logic for multiprocessing
def f_nearest(source, matchers_with_labels, n, exact_shortcut=False):
    if not matchers_with_labels:
        return []
    ratios = []
    for label, m in matchers_with_labels:
        m.set_seq1(source)
        ratios.append((m.ratio(), label))
    ratios.sort(reverse=True)
    if exact_shortcut and ratios[0][0] >= 1.0:
        return ratios[:1]
    return ratios[:n]

def f_nearest_per_thread(workitem):
    (work_sources, target_items, n, exact_shortcut) = workitem
    # target_items is [(label, string), ...]
    matchers_with_labels = [(label, difflib.SequenceMatcher(b=string, autojunk=False))
                            for label, string in target_items]
    return [f_nearest(src, matchers_with_labels, n, exact_shortcut) for src in work_sources]

class Namediff:
    def __init__(self, verbose = True,
                 json_fname = os.path.join(datadir, 'AllSets.json'),
                 cards = None):
        self.verbose = verbose
        self.names = {}
        self.codes = {}
        self.cardstrings = {}

        if self.verbose:
            print('Setting up namediff...')

        if cards:
            if self.verbose:
                print('  Initializing from provided card list.')

            def process_card_obj(card):
                name = card.name
                if name not in self.names:
                    self.names[name] = cardlib.titlecase(cardlib.transforms.name_unpass_1_dashes(name))
                    self.cardstrings[name] = card.encode()
                    jcode = getattr(card, 'set_code', '')
                    jnum = getattr(card, 'number', '')
                    if jcode and jnum:
                        self.codes[name] = str(jcode) + '/' + str(jnum) + '.jpg'
                    else:
                        self.codes[name] = ''

                if card.bside:
                    process_card_obj(card.bside)

            for card in cards:
                process_card_obj(card)

            namecount = len(self.names)

        else:
            if self.verbose:
                print('  Reading names from: ' + json_fname)
            json_srcs, _ = jdecode.mtg_open_json(json_fname, verbose)
            namecount = 0

            def process_card(card, jcard):
                nonlocal namecount
                name = card.name
                if name in self.names:
                    if self.verbose:
                        print('  Duplicate name ' + name + ', ignoring.')
                else:
                    self.names[name] = jcard['name']
                    self.cardstrings[name] = card.encode()
                    jcode = jcard.get(utils.json_field_info_code)
                    jnum = jcard.get('number', '')
                    if jcode and jnum:
                        self.codes[name] = jcode + '/' + jnum + '.jpg'
                    else:
                        self.codes[name] = ''
                    namecount += 1

                if card.bside:
                    # For bsides in MTGJSON, they are often nested.
                    # card.bside is a Card object.
                    # We need the jcard for the bside too.
                    jbside = jcard.get(utils.json_field_bside)
                    if jbside:
                        process_card(card.bside, jbside)

            for json_cardname in sorted(json_srcs.keys()):
                if len(json_srcs[json_cardname]) > 0:
                    jcards = json_srcs[json_cardname]
                    # just use the first one
                    idx = 0
                    card = cardlib.Card(jcards[idx])
                    process_card(card, jcards[idx])

        if self.verbose:
            print('  Read ' + str(namecount) + ' unique cardnames')
            print('  Building SequenceMatcher objects.')

        self.matchers = [(n, difflib.SequenceMatcher(
            b=n, autojunk=False)) for n in self.names]
        self.card_matchers = [(n, difflib.SequenceMatcher(
            b=self.cardstrings[n], autojunk=False)) for n in self.cardstrings]

        if self.verbose:
            print('... Done.')
    
    def nearest(self, name, n=3):
        return f_nearest(name, self.matchers, n, exact_shortcut=True)

    def nearest_par(self, names, n=3, threads=cores, quiet=False):
        with multiprocessing.Pool(threads) as workpool:
            proto_worklist = list_split(names, threads)
            # Pass (label, string) pairs for matcher construction in thread
            target_items = [(n, n) for n in self.names]
            worklist = [(x, target_items, n, True) for x in proto_worklist]

            try:
                from tqdm import tqdm
                iterator = tqdm(workpool.imap(f_nearest_per_thread, worklist),
                              total=len(worklist),
                              disable=quiet,
                              desc="Matching names",
                              unit="chunk")
            except ImportError:
                iterator = workpool.imap(f_nearest_per_thread, worklist)

            donelist = list(iterator)
        return list_flatten(donelist)

    def nearest_card(self, card, n=5):
        return f_nearest(card.encode(), self.card_matchers, n, exact_shortcut=False)

    def nearest_card_par(self, cards, n=5, threads=cores, quiet=False):
        with multiprocessing.Pool(threads) as workpool:
            proto_worklist = list_split(cards, threads)
            # Pass (label, string) pairs for card strings
            target_items = [(n, self.cardstrings[n]) for n in self.cardstrings]
            worklist = [([c.encode() for c in x], target_items, n, False) for x in proto_worklist]

            try:
                from tqdm import tqdm
                iterator = tqdm(workpool.imap(f_nearest_per_thread, worklist),
                              total=len(worklist),
                              disable=quiet,
                              desc="Matching cards",
                              unit="chunk")
            except ImportError:
                iterator = workpool.imap(f_nearest_per_thread, worklist)

            donelist = list(iterator)
        return list_flatten(donelist)
