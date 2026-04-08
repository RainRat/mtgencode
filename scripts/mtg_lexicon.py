#!/usr/bin/env python3
import sys
import os
import argparse
import re
from collections import Counter, defaultdict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib

# Try to import nltk and handle its specific data requirements
try:
    import nltk
    from nltk.tokenize import word_tokenize
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        # Fallback to regex tokenization if data is missing
        def word_tokenize(text):
            return re.findall(r"\b[a-zA-Z']+\b", text)
except ImportError:
    # Fallback to regex tokenization if nltk is missing
    def word_tokenize(text):
        return re.findall(r"\b[a-zA-Z']+\b", text)

def get_color_group(card):
    """Categorizes a card into one of the 7 primary color buckets."""
    # Ensure we handle cards without costs or colors gracefully
    cost = getattr(card, 'cost', None)
    colors = getattr(cost, 'colors', []) if cost else []

    if len(colors) > 1:
        return 'M' # Multicolored
    elif len(colors) == 1:
        return colors[0] # W, U, B, R, or G
    else:
        return 'A' # Colorless / Artifact

def analyze_lexicon(cards, top_n=10, min_len=4):
    """
    Analyzes the vocabulary used in rules text, grouped by color.
    Returns frequencies and distinctiveness scores.
    """
    color_words = defaultdict(list)
    all_words = []

    # Standard English stop words + MTG specific common words that lack specific color flavor
    stop_words = {
        'the', 'and', 'with', 'that', 'this', 'from', 'into', 'under', 'your', 'onto',
        'its', 'then', 'until', 'when', 'whenever', 'where', 'each', 'any', 'all',
        'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
        'has', 'have', 'had', 'was', 'were', 'been', 'being', 'get', 'gets', 'put',
        'puts', 'can', 'cant', 'cannot', 'will', 'would', 'should', 'could', 'may',
        'target', 'control', 'player', 'permanent', 'opponent', 'creature', 'spell',
        'artifact', 'enchantment', 'land', 'planeswalker', 'battle', 'token', 'card',
        'graveyard', 'library', 'hand', 'battlefield', 'turn', 'phase', 'step',
        'beginning', 'end', 'during', 'instead', 'unless', 'only', 'also', 'other',
        'another', 'same', 'total', 'count', 'number', 'equal', 'less', 'more',
        'least', 'most', 'plus', 'minus', 'activation', 'ability', 'effect',
        'trigger', 'copy', 'create', 'search', 'reveal', 'exile', 'discard',
        'shuffle', 'look', 'draw', 'cast', 'play', 'activate', 'become', 'becomes',
        'enter', 'enters', 'leave', 'leaves', 'die', 'dies', 'return', 'choose',
        'chosen', 'choice', 'name', 'named', 'owner', 'owners'
    }

    # Process each card
    for card in cards:
        color = get_color_group(card)
        # Use force_unpass to get readable text but strip out symbols and punctuation
        text = card.get_text(force_unpass=True).lower()
        # Remove reminder text (text in parentheses)
        text = re.sub(r'\(.*?\)', '', text)
        # Tokenize and filter
        words = [w for w in word_tokenize(text) if w.isalpha() and len(w) >= min_len and w not in stop_words]

        color_words[color].extend(words)
        all_words.extend(words)

    # Calculate frequencies
    global_freq = Counter(all_words)
    total_global = sum(global_freq.values())

    if total_global == 0:
        return {}

    color_stats = {}
    for color in 'WUBRGMA':
        words = color_words[color]
        if not words:
            continue

        freq = Counter(words)
        total_color = sum(freq.values())

        # Calculate Distinctiveness (Significance score)
        # Score = (Freq in Color / Total in Color) / (Freq Global / Total Global)
        # Higher score means the word is more characteristic of this color.
        distinctiveness = {}
        for word, count in freq.items():
            color_prop = count / total_color
            global_prop = global_freq[word] / total_global
            distinctiveness[word] = color_prop / global_prop

        # Sort by distinctiveness but filter out low-frequency noise
        top_distinct = sorted(
            [w for w in distinctiveness if freq[w] >= 2 or total_color < 50],
            key=lambda w: distinctiveness[w],
            reverse=True
        )[:top_n]

        color_stats[color] = {
            'top': top_distinct,
            'freq': freq,
            'scores': distinctiveness,
            'total': total_color
        }

    return color_stats

def main():
    parser = argparse.ArgumentParser(
        description="Analyze the characteristic vocabulary (lexicon) of each Magic color. "
                    "This identifies 'signature words' that appear significantly more often "
                    "in one color compared to the global dataset."
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, encoded text, etc.). Defaults to stdin (-).')
    io_group.add_argument('--compare', '-c',
                        help='Optional second dataset to compare against the primary input.')

    # Group: Content Formatting
    enc_group = parser.add_argument_group('Content Formatting')
    enc_group.add_argument('--nolabel', action='store_true',
                        help="Remove field labels (like '|cost|' or '|text|') from the input.")
    enc_group.add_argument('--nolinetrans', action='store_true',
                        help='Input file does not use automatic line reordering.')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('-t', '--top', type=int, default=10,
                        help='Number of signature words to show per color (Default: 10).')
    proc_group.add_argument('--min-len', type=int, default=4,
                        help='Minimum word length to include in analysis (Default: 4).')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')

    # Group: Filtering Options (Standard)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for AND logic.')
    filter_group.add_argument('--set', action='append',
                        help='Only include cards from specific sets (e.g., MOM, MRD). Supports multiple sets (OR logic).')
    filter_group.add_argument('--rarity', action='append',
                        help="Only include cards of specific rarities. Supports full names (e.g., 'common', 'mythic') or shorthands: O (Common), N (Uncommon), A (Rare), Y (Mythic), I (Special), L (Basic Land). Supports multiple values (OR logic).")
    filter_group.add_argument('--mechanic', action='append',
                        help='Only include cards with specific mechanical features or keyword abilities (e.g., Flying, Activated, ETB Effect). Supports multiple values (OR logic).')

    # Color options
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    debug_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress the progress bar.')

    args = parser.parse_args()

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stdout.isatty():
        use_color = True

    def load_cards(path):
        if not path: return []
        cards = jdecode.mtg_open_file(path, verbose=args.verbose,
                                      linetrans=not args.nolinetrans,
                                      fmt_labeled=None if args.nolabel else cardlib.fmt_labeled_default,
                                      sets=args.set, rarities=args.rarity,
                                      mechanics=args.mechanic, grep=args.grep)
        if args.limit > 0:
            cards = cards[:args.limit]
        return cards

    cards1 = load_cards(args.infile)
    if not cards1:
        print(f"No cards found in {args.infile} matching criteria.", file=sys.stderr)
        return

    stats1 = analyze_lexicon(cards1, top_n=args.top, min_len=args.min_len)
    if not stats1:
        print(f"Insufficient card text in {args.infile} for analysis.", file=sys.stderr)
        return

    title = "COLOR LEXICON ANALYSIS (Signature Words)"
    if use_color:
        title = utils.colorize(title, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE)
    print(f"\n=== {title} ===")
    print("Words ranked by 'Distinctiveness' (Relative frequency vs global average).\n")

    header = ["Color", "Signature Words", "Vocab Size"]
    if use_color:
        header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

    rows = [header]

    color_labels = {
        'W': 'White', 'U': 'Blue', 'B': 'Black', 'R': 'Red', 'G': 'Green',
        'M': 'Multi', 'A': 'Colorless'
    }

    for c in 'WUBRGMA':
        if c not in stats1:
            continue

        label = color_labels[c]
        if use_color:
            label = utils.colorize(label, utils.Ansi.get_color_color(c))

        words = stats1[c]['top']
        word_str = ", ".join(words)
        vocab_size = str(stats1[c]['total'])

        rows.append([label, word_str, vocab_size])

    col_widths = datalib.get_col_widths(rows)
    separator = ['-' * w for w in col_widths]
    rows.insert(1, separator)

    datalib.printrows(datalib.padrows(rows, aligns=['l', 'l', 'r']), indent=2)

    if args.compare:
        cards2 = load_cards(args.compare)
        if cards2:
            stats2 = analyze_lexicon(cards2, top_n=args.top, min_len=args.min_len)
            if not stats2:
                print(f"\nInsufficient card text in {args.compare} for comparison.", file=sys.stderr)
            else:
                print(f"\n=== COMPARISON: {os.path.basename(args.compare)} ===")

                c_rows = [header]
                for c in 'WUBRGMA':
                    if c not in stats2: continue

                    label = color_labels[c]
                    if use_color: label = utils.colorize(label, utils.Ansi.get_color_color(c))

                    # Highlight words present in base but missing in target (or vice-versa)
                    words2 = stats2[c]['top']
                    words1_set = set(stats1.get(c, {}).get('top', []))

                    display_words = []
                    for w in words2:
                        if w in words1_set:
                            display_words.append(w)
                        else:
                            # New word in target!
                            display_words.append(utils.colorize(w, utils.Ansi.BOLD + utils.Ansi.GREEN) if use_color else f"*{w}*")

                    word_str = ", ".join(display_words)
                    vocab_size = str(stats2[c]['total'])
                    c_rows.append([label, word_str, vocab_size])

                c_rows.insert(1, separator)
                datalib.printrows(datalib.padrows(c_rows, aligns=['l', 'l', 'r']), indent=2)

    utils.print_operation_summary("Lexicon Analysis", len(cards1) + (len(cards2) if args.compare else 0), 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
