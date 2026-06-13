#!/usr/bin/env python3
# Copyright 2026 Google LLC
import sys
import os
import argparse
import json
import math
import re
import csv
import textwrap
from collections import defaultdict, Counter, OrderedDict
from contextlib import redirect_stdout

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import cardlib
import jdecode
import sortlib
import datalib
import utils
import cli_utils
from datalib import Datamine
from titlecase import titlecase

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

# Try to import nltk for lexicon
try:
    import nltk
    from nltk.tokenize import word_tokenize
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        def word_tokenize(text):
            return re.findall(r"\b[a-zA-Z']+\b", text)
except ImportError:
    def word_tokenize(text):
        return re.findall(r"\b[a-zA-Z']+\b", text)

# --- Constants & Dimensions ---

RECOGNIZED_MECHANICS = cardlib.RECOGNIZED_MECHANICS
COLOR_GROUPS = 'WUBRGAM'
TRACKED_TYPES = ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land", "Battle"]

ACTION_CATEGORIES = cardlib.ACTION_CATEGORIES

GUILD_PAIRS = ["UW", "BU", "BR", "GR", "GW", "BW", "RU", "BG", "RW", "GU"]
GUILD_LABELS = {
    "UW": "WU (Azorius)", "BU": "UB (Dimir)", "BR": "BR (Rakdos)", "GR": "RG (Gruul)",
    "GW": "GW (Selesnya)", "BW": "WB (Orzhov)", "RU": "UR (Izzet)", "BG": "BG (Golgari)",
    "RW": "RW (Boros)", "GU": "GU (Simic)"
}

# --- Shared Helpers ---

def _normalized_color_identity(card):
    identity = getattr(card, 'color_identity', '')
    if isinstance(identity, str):
        if identity:
            return identity
    elif isinstance(identity, (list, tuple)):
        if identity:
            return ''.join(identity)
    colors = getattr(getattr(card, 'cost', None), 'colors', None)
    if colors:
        return ''.join(colors)
    return ''


def get_color_group(card):
    """Categorizes a card by color identity (W, U, B, R, G, Multi, Colorless)."""
    identity = _normalized_color_identity(card)
    if len(identity) > 1: return 'M'
    if len(identity) == 1: return identity[0]
    return 'A'

def get_card_type(card):
    for t in TRACKED_TYPES:
        if card._has_type(t): return t
    return "Other"

def format_type(t, use_color):
    if not use_color: return t
    color = utils.Ansi.CYAN
    if t == "Creature": color = utils.Ansi.GREEN
    elif t == "Land": color = utils.Ansi.BOLD
    return utils.colorize(t, color)

def bucket_numeric(val):
    if val is None: return None
    try:
        v = int(float(val))
        if v < 0: v = 0
        if v >= 7: return '7+'
        return str(v)
    except (ValueError, TypeError):
        return None

DIMENSIONS = {
    'color': {
        'label': 'Color Identity', 'keys': COLOR_GROUPS, 'fn': lambda c: get_color_group(c),
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.get_color_color(k)) if use_color else k
    },
    'rarity': {
        'label': 'Rarity', 'keys': ['Common', 'Uncommon', 'Rare', 'Mythic', 'Special', 'Basic Land'],
        'fn': lambda c: c.rarity_name.title(),
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.get_rarity_color(k)) if use_color else k
    },
    'type': {
        'label': 'Card Type', 'keys': TRACKED_TYPES + ["Other"], 'fn': lambda c: get_card_type(c),
        'formatter': lambda k, use_color: format_type(k, use_color)
    },
    'cmc': {
        'label': 'CMC', 'keys': ['0', '1', '2', '3', '4', '5', '6', '7+'], 'fn': lambda c: bucket_numeric(c.cost.cmc),
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.CYAN) if use_color else k
    },
    'power': {
        'label': 'Power', 'keys': ['0', '1', '2', '3', '4', '5', '6', '7+'], 'fn': lambda c: bucket_numeric(utils.from_unary_single(c.pt_p)),
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.RED) if use_color else k
    },
    'toughness': {
        'label': 'Toughness', 'keys': ['0', '1', '2', '3', '4', '5', '6', '7+'], 'fn': lambda c: bucket_numeric(utils.from_unary_single(c.pt_t)),
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.RED) if use_color else k
    },
    'loyalty': {
        'label': 'Loyalty/Defense', 'keys': ['0', '1', '2', '3', '4', '5', '6', '7+'], 'fn': lambda c: bucket_numeric(utils.from_unary_single(c.loyalty)),
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.RED) if use_color else k
    },
    'mechanic': {
        'label': 'Mechanic', 'keys': RECOGNIZED_MECHANICS, 'fn': lambda c: list(c.mechanics), 'is_multi': True,
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.CYAN) if use_color else k
    }
}

def get_mana_category(card):
    if card.is_creature: return "Creature"
    if card.is_artifact: return "Artifact"
    if card.is_land: return "Land"
    if card.is_instant or card.is_sorcery: return "Spell"
    return "Other"

def get_pip_counts(card, include_text=False):
    counts = Counter()
    for sym, count in card.cost.allsymbols.items():
        if count > 0: counts[sym] += count
    if include_text:
        for cost in card.text.costs:
            for sym, count in cost.allsymbols.items():
                if count > 0: counts[sym] += count
    if card.bside: counts.update(get_pip_counts(card.bside, include_text=include_text))
    return counts

def get_cost_metrics(card):
    cmc = card.cost.cmc
    colored_pips = 0
    color_pips = Counter()
    for encoded_sym in card.cost.sequence:
        if encoded_sym == utils.mana_unary_counter: continue
        sym = utils.mana_symall_decode.get(encoded_sym)
        if not sym or sym in [utils.mana_X, utils.mana_S, utils.mana_E]: continue
        is_colored = False
        for char in sym:
            if char in 'WUBRG':
                color_pips[char] += 1
                is_colored = True
        if is_colored: colored_pips += 1
    intensity = colored_pips / max(1, cmc)
    max_commitment = max(color_pips.values()) if color_pips else 0
    return cmc, colored_pips, intensity, max_commitment

def get_numeric_stats(card):
    return utils.from_unary_single(card.pt_p), utils.from_unary_single(card.pt_t), utils.from_unary_single(card.loyalty)

def check_cards(cards, args):
    if not cards:
        if not getattr(args, 'quiet', False):
            print("No cards found matching the criteria.", file=sys.stderr)
        return False
    return True

def format_delta(val, base_val, is_percent=False, use_color=False, reverse_color=False):
    delta = val - base_val
    if abs(delta) < 1e-6: return " -- "
    sign = "+" if delta > 0 else ""
    suffix = "%" if is_percent else ""
    res = f"{sign}{delta:.1f}{suffix}"
    if use_color:
        significant = False
        if is_percent:
            if abs(delta) >= 2.0: significant = True
        else:
            if abs(base_val) > 1e-6:
                if abs(delta) / abs(base_val) >= 0.05: significant = True
            elif abs(delta) >= 1.0: significant = True
        if significant:
            if reverse_color is None: color = utils.Ansi.BOLD + utils.Ansi.CYAN
            else: color = utils.Ansi.BOLD + (utils.Ansi.GREEN if (delta > 0 if not reverse_color else delta < 0) else utils.Ansi.RED)
            res = utils.colorize(res, color)
    return res


def get_archetype_counts(cards):
    counts = Counter({p: 0 for p in GUILD_PAIRS})
    for c in cards:
        id = c.color_identity
        if len(id) == 2:
            if id in counts: counts[id] += 1
        elif len(id) == 1:
            for p in GUILD_PAIRS:
                if id in p: counts[p] += 1
    return counts

def analyze_subtypes(cards, top=10):
    cw, aw, cc = defaultdict(list), [], Counter()
    for c in cards:
        g = get_color_group(c); cc[g]+=1
        for s in getattr(c, 'subtypes', []):
            sc = titlecase(s.replace(utils.dash_marker, '-'))
            cw[g].append(sc); aw.append(sc)
    gf = Counter(aw); tot_gi = sum(gf.values())
    c_stats = {}
    for g in 'WUBRGMA':
        inst = cw[g]
        if not inst: continue
        f = Counter(inst); tot_ci = sum(f.values()); dist = {s: (f[s]/tot_ci)/(gf[s]/tot_gi) for s in f}
        top_sig = sorted([s for s in dist if f[s]>=1], key=lambda s: dist[s], reverse=True)[:top]
        c_stats[g] = {'top': top_sig, 'top_signature': top_sig, 'freq': f, 'scores': dist, 'total': tot_ci, 'cnt': cc[g], 'card_count': cc[g]}
    return {
        'total_cards': len(cards),
        'total': len(cards),
        'global_freq': gf,
        'color_stats': c_stats,
    }

def analyze_lexicon(cards, top=10, min_len=4, top_n=None):
    if top_n is not None:
        top = top_n
    if not cards:
        return {}
    cw, aw = defaultdict(list), []
    stops = {'the','and','with','that','this','from','into','under','your','onto','its','then','until','when','whenever','where','each','any','all','one','two','three','four','five','six','seven','eight','nine','ten','has','have','had','was','were','been','being','get','gets','put','puts','can','cant','cannot','will','would','should','could','may','target','control','player','permanent','opponent','creature','spell','artifact','enchantment','land','planeswalker','battle','token','card','graveyard','library','hand','battlefield','turn','phase','step','beginning','end','during','instead','unless','only','also','other','another','same','total','count','number','equal','less','more','least','most','plus','minus','activation','ability','effect','trigger','copy','create','search','reveal','exile','discard','shuffle','look','draw','cast','play','activate','become','becomes','enter','enters','leave','leaves','die','dies','return','choose','chosen','choice','name','named','owner','owners'}
    for c in cards:
        col = get_color_group(c)
        text = re.sub(r'\(.*?\)', '', c.get_text(force_unpass=True).lower())
        ws = [w for w in word_tokenize(text) if w.isalpha() and len(w)>=min_len and w not in stops]
        cw[col].extend(ws); aw.extend(ws)
    gf = Counter(aw); tot_g = sum(gf.values()); stats = {}
    for col in 'WUBRGMA':
        ws = cw[col]
        if not ws: continue
        f = Counter(ws); tot_c = sum(f.values()); dist = {w: (f[w]/tot_c)/(gf[w]/tot_g) for w in f}
        stats[col] = {'top': sorted([w for w in dist if f[w]>=2 or tot_c<50], key=lambda w: dist[w], reverse=True)[:top], 'freq': f, 'scores': dist, 'total': tot_c}
    res = {
        'total_cards': len(cards),
        'total': tot_g,
        'global_freq': gf,
        'color_stats': stats,
    }
    res.update(stats)
    return res


def calculate_asfan(cards):
    pools = defaultdict(list); slots = {utils.rarity_common_marker: 10.0, utils.rarity_uncommon_marker: 3.0, 'RARE': 1.0, utils.rarity_basic_land_marker: 1.0}
    for c in cards: pools['RARE' if c.rarity in [utils.rarity_rare_marker, utils.rarity_mythic_marker] else c.rarity].append(c)
    def calc(fn):
        res = 0.0
        for s, cnt in slots.items():
            p = pools.get(s, [])
            if p: res += sum(1 for c in p if fn(c))/len(p)*cnt
        return res
    def calc_c(fn):
        ks, pc = set(), defaultdict(Counter)
        for s in slots:
            for c in pools.get(s, []):
                for k in fn(c): ks.add(k); pc[s][k]+=1
        res = {}
        for k in ks:
            v = 0.0
            for s, cnt in slots.items():
                pl = len(pools.get(s, []))
                if pl>0: v += pc[s][k]/pl*cnt
            res[k] = v
        return res
    return {'colors': calc_c(lambda c: c.cost.colors or ['C']), 'types': calc_c(lambda c: [t for t in TRACKED_TYPES if c._has_type(t)]), 'mechs': calc_c(lambda c: list(c.mechanics)), 'multi': calc(lambda c: len(c.cost.colors)>1)}

def calculate_interaction(cards, min_freq=2):
    ind_c, pair_c, dens_d = Counter(), Counter(), Counter()
    for c in cards:
        ms = sorted(list(c.mechanics))
        dens_d[len(ms)] += 1
        for m in ms: ind_c[m] += 1
        for i in range(len(ms)):
            for j in range(i+1, len(ms)): pair_c[(ms[i], ms[j])] += 1
    syn = []
    for (m1, m2), cnt in pair_c.items():
        if cnt < min_freq: continue
        lift = (cnt * len(cards)) / (ind_c[m1] * ind_c[m2])
        syn.append({'pair': (m1, m2), 'cnt': cnt, 'lift': lift})
    return dict(dens_d), dict(ind_c), dict(pair_c), syn

def analyze_dataset(cards):
    s = {'total': len(cards), 'total_cards': len(cards), 'producers': 0, 'producer_count': 0, 'cats': Counter(), 'categories': Counter(), 'cols': Counter(), 'colors': Counter(), 'fixing': 0}
    for c in cards:
        p = c.produced_colors
        if p:
            s['producers'] += 1
            s['producer_count'] += 1
            cat = get_mana_category(c)
            s['cats'][cat] += 1
            s['categories'][cat] += 1
            if "Any" in p: s['cols']['Any'] += 1; s['colors']['Any'] += 1; s['fixing'] += 1
            else:
                for col in p:
                    s['cols'][col] += 1
                    s['colors'][col] += 1
                if len(p) >= 2: s['fixing'] += 1
    return s


# --- Subparser Handlers ---

def handle_summary(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return
    if getattr(args, 'sort', None):
        cards = sortlib.sort_cards(cards, args.sort, reverse=getattr(args, 'reverse', False), quiet=getattr(args, 'quiet', False))
    mine = Datamine(cards)

    json_out = getattr(args, 'json', False)
    oname = getattr(args, 'outfile', None)
    if not json_out and oname and oname.endswith('.json'): json_out = True

    output_f = open(oname, 'w', encoding='utf8') if oname else sys.stdout
    try:
        if json_out:
            output_f.write(json.dumps(mine.to_dict(), indent=2) + '\n')
        else:
            with redirect_stdout(output_f):
                mine.summarize(use_color=args.color, vsize=args.top)
                if getattr(args, 'outliers', False) or getattr(args, 'all', False):
                    mine.outliers(dump_invalid=getattr(args, 'all', False), use_color=args.color, vsize=args.top)
    finally:
        if oname: output_f.close()

def handle_curve(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return
    use_color = args.color if args.color is not None else sys.stdout.isatty()
    cmc_buckets = range(8)
    cmc_counts = defaultdict(int)
    type_counts = defaultdict(lambda: defaultdict(int))
    color_sums, color_counts = defaultdict(float), defaultdict(int)
    total_cmc, total_cards = 0, len(cards)
    for card in cards:
        cmc = int(card.cost.cmc)
        total_cmc += card.cost.cmc
        bucket = min(max(0, cmc), 7)
        cmc_counts[bucket] += 1
        type_counts["Creature" if card.is_creature else "Non-creature"][bucket] += 1
        for color in (card.cost.colors or ['C']):
            color_sums[color] += card.cost.cmc
            color_counts[color] += 1
    utils.print_header("MANA CURVE ANALYSIS", count=total_cards, use_color=use_color)
    print(f"  {utils.colorize(f'Global Average CMC: {total_cmc/total_cards:.2f}', utils.Ansi.BOLD + utils.Ansi.GREEN) if use_color else f'Global Average CMC: {total_cmc/total_cards:.2f}'}\n")
    rows = [[utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else h for h in ["CMC", "Count", "Percent", "Distribution (Creature / Non-creature)"]]]
    max_c = max(cmc_counts.values()) if cmc_counts else 0
    for b in cmc_buckets:
        cnt = cmc_counts[b]
        p = cnt/total_cards*100
        lbl = str(b) if b < 7 else "7+"
        if cnt > 0:
            w = 20
            tot_w = max(1, int(round(cnt/max_c*w)))
            cw = int(round(type_counts["Creature"][b]/cnt*tot_w))
            ncw = tot_w - cw
            if use_color: bar = '[' + utils.colorize('█'*cw, utils.Ansi.GREEN) + utils.colorize('▓'*ncw, utils.Ansi.YELLOW) + ' '*(w-tot_w) + ']'
            else: bar = '[' + '#'*cw + '='*ncw + ' '*(w-tot_w) + ']'
        else: bar = '[' + ' '*20 + ']'
        rows.append([utils.colorize(lbl, utils.Ansi.CYAN) if use_color else lbl, datalib.color_count(cnt, use_color), f"{p:5.1f}%", bar])
    datalib.add_separator_row(rows)
    datalib.printrows(datalib.padrows(rows, aligns=['r', 'r', 'r', 'l']), indent=4)
    print(f"\n    Legend: {utils.colorize('█ Creature', utils.Ansi.GREEN) if use_color else '# Creature'}  {utils.colorize('▓ Non-creature', utils.Ansi.YELLOW) if use_color else '= Non-creature'}\n")
    c_rows = [[utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else h for h in ["Color", "Avg CMC", "Count", "Percentage"]]]
    for c in 'WUBRGC':
        if color_counts[c] == 0: continue
        c_rows.append([utils.colorize(c, utils.Ansi.get_color_color(c)) if use_color else c, f"{color_sums[c]/color_counts[c]:.2f}", datalib.color_count(color_counts[c], use_color), f"{color_counts[c]/total_cards*100:5.1f}%"])
    if len(c_rows) > 1:
        datalib.add_separator_row(c_rows)
        datalib.printrows(datalib.padrows(c_rows, aligns=['l', 'r', 'r', 'r']), indent=4)

def handle_colorpie(args):
    cards1 = cli_utils.load_and_filter_cards(args)
    if not cards1: return
    def get_mech_stats(cards):
        t, m = Counter(), defaultdict(Counter)
        for c in cards:
            g = get_color_group(c)
            t[g] += 1
            for mech in c.mechanics: m[g][mech] += 1
        return m, t
    m1, t1 = get_mech_stats(cards1)
    m2, t2 = (get_mech_stats(cli_utils.load_and_filter_cards(argparse.Namespace(**{**vars(args), 'infile': args.compare}))) if getattr(args, 'compare', None) else (None, None))
    all_m = set(m1.keys()); [all_m.update(m1[g].keys()) for g in m1]
    if m2: [all_m.update(m2[g].keys()) for g in m2]
    ordered = [m for m in RECOGNIZED_MECHANICS if m in all_m] + sorted([m for m in all_m if m not in RECOGNIZED_MECHANICS])
    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    if args.json: print(json.dumps({'primary': {'total': len(cards1), 'mechs': {g: dict(m1[g]) for g in COLOR_GROUPS}, 'mechanics': {g: dict(m1[g]) for g in COLOR_GROUPS}, 'groups': dict(t1)}, 'comparison': {'total': sum(t2.values()), 'mechs': {g: dict(m2[g]) for g in COLOR_GROUPS}, 'mechanics': {g: dict(m2[g]) for g in COLOR_GROUPS}, 'groups': dict(t2)} if m2 else None}, indent=2))
    elif args.csv:
        writer = csv.writer(sys.stdout)
        if m2:
            writer.writerow(['Mechanic', 'Color', 'P1%', 'P2%', 'Delta'])
            for m in ordered:
                for g in COLOR_GROUPS:
                    p1, p2 = (m1[g][m]/t1[g]*100 if t1[g]>0 else 0), (m2[g][m]/t2[g]*100 if t2[g]>0 else 0)
                    writer.writerow([m, g, f"{p1:.1f}", f"{p2:.1f}", f"{p2-p1:.1f}"])
        else:
            writer.writerow(['Mechanic'] + list(COLOR_GROUPS))
            for m in ordered: writer.writerow([m] + [f"{m1[g][m]/t1[g]*100:.1f}" if t1[g]>0 else "0.0" for g in COLOR_GROUPS])
    else:
        utils.print_header("MECHANICAL COLOR PIE" + (" (COMPARISON)" if m2 else ""), count=len(cards1), use_color=use_color)
        rows = [[utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else h for h in ["Mechanic"] + list(COLOR_GROUPS)]]
        for m in ordered:
            row = [m]
            percents = [m1[g][m]/t1[g]*100 if t1[g]>0 else 0 for g in COLOR_GROUPS]
            max_p = max(percents) if percents else 0
            for i, g in enumerate(COLOR_GROUPS):
                p1 = percents[i]
                if m2:
                    p2 = m2[g][m]/t2[g]*100 if t2[g]>0 else 0
                    d = p2 - p1
                    v = f"{p2:3.0f}%"
                    if abs(d) < 0.5: disp = "  - " if p2 == 0 else v
                    else: disp = utils.colorize(f"{v}{'▲' if d>0 else '▼'}", utils.Ansi.GREEN if d>0 else utils.Ansi.RED) if use_color else f"{v}{'▲' if d>0 else '▼'}"
                else:
                    if p1 > 0:
                        v = f"{p1:3.0f}%"
                        if use_color:
                            c = utils.Ansi.get_color_color(g)
                            disp = v[:len(v)-len(v.lstrip())] + utils.colorize(v.lstrip(), c + utils.Ansi.UNDERLINE) if p1 == max_p else utils.colorize(v, c)
                        else: disp = v
                    else: disp = "  - "
                row.append(disp)
            rows.append(row)
        datalib.add_separator_row(rows)
        datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r']*len(COLOR_GROUPS)), indent=2)

def handle_grid(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return
    r_dim, c_dim = DIMENSIONS[args.row_dim], DIMENSIONS[args.col_dim]
    matrix, rt, ct = defaultdict(Counter), Counter(), Counter()
    for c in cards:
        rvs, cvs = r_dim['fn'](c), c_dim['fn'](c)
        if not isinstance(rvs, list): rvs = [rvs]
        if not isinstance(cvs, list): cvs = [cvs]
        for rv in rvs:
            if rv is None: continue
            rt[rv] += 1
            for cv in cvs:
                if cv is not None: matrix[rv][cv] += 1
        for cv in cvs:
            if cv is not None: ct[cv] += 1
    def get_ks(d, t): return list(d['keys']) if isinstance(d['keys'], str) else (sorted([k for k in d['keys'] if t[k]>0]) if d==DIMENSIONS['mechanic'] else d['keys'])
    rks, cks = get_ks(r_dim, rt), get_ks(c_dim, ct)
    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    if args.json: print(json.dumps({'matrix': {str(rk): {str(ck): matrix[rk][ck] for ck in cks} for rk in rks}, 'rt': dict(rt), 'ct': dict(ct), 'total': len(cards), 'total_cards': len(cards)}, indent=2))
    elif args.csv:
        w = csv.writer(sys.stdout)
        w.writerow([r_dim['label']+'/'+c_dim['label']] + [str(ck) for ck in cks] + ['Total'])
        for rk in rks: w.writerow([str(rk)] + [matrix[rk][ck] for ck in cks] + [rt[rk]])
        w.writerow(['TOTAL'] + [ct[ck] for ck in cks] + [len(cards)])
    else:
        utils.print_header(f"{r_dim['label'].upper()} vs {c_dim['label'].upper()}", count=len(cards), use_color=use_color)
        h = [r_dim['label']+'/'+c_dim['label']] + [str(ck) for ck in cks] + ["Total"]
        if use_color:
            hd = [utils.colorize(h[0], utils.Ansi.BOLD + utils.Ansi.UNDERLINE)]
            for ck in cks: hd.append(utils.colorize(str(ck), utils.Ansi.BOLD + utils.Ansi.UNDERLINE + (utils.Ansi.get_color_color(ck) if c_dim==DIMENSIONS['color'] else "")))
            hd.append(utils.colorize("Total", utils.Ansi.BOLD + utils.Ansi.UNDERLINE))
            rows = [hd]
        else: rows = [h]
        for rk in rks:
            row = [r_dim['formatter'](str(rk), use_color)]
            for ck in cks: row.append(datalib.color_count(matrix[rk][ck], use_color) if matrix[rk][ck]>0 else " - ")
            row.append(utils.colorize(str(rt[rk]), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(rt[rk]))
            rows.append(row)
        datalib.add_separator_row(rows)
        tr = [utils.colorize("TOTAL", utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else "TOTAL"]
        for ck in cks: tr.append(utils.colorize(str(ct[ck]), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(ct[ck]))
        tr.append(utils.colorize(str(len(cards)), utils.Ansi.BOLD + utils.Ansi.WHITE + utils.Ansi.UNDERLINE) if use_color else str(len(cards)))
        rows.append(tr)
        datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r']*(len(cks)+1)), indent=2)

def handle_types(args):
    cards1 = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards1, args): return
    def get_d(cards):
        m, rt, ct = defaultdict(Counter), Counter(), Counter()
        for c in cards:
            g, t = get_color_group(c), get_card_type(c)
            ct[g]+=1; m[t][g]+=1; rt[t]+=1
        return m, rt, ct
    m1, rt1, ct1 = get_d(cards1)
    m2, rt2, ct2 = (get_d(cli_utils.load_and_filter_cards(argparse.Namespace(**{**vars(args), 'infile': args.compare}))) if getattr(args, 'compare', None) else (None, None, None))
    all_r = TRACKED_TYPES + (["Other"] if rt1["Other"]>0 or (rt2 and rt2["Other"]>0) else [])
    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    if args.json: print(json.dumps({'primary': {'total': len(cards1), 'matrix': {t: dict(m1[t]) for t in all_r}}, 'comparison': {'total': sum(rt2.values()), 'matrix': {t: dict(m2[t]) for t in all_r}} if m2 else None}, indent=2))
    elif args.csv:
        w = csv.writer(sys.stdout); w.writerow(['Type'] + list(COLOR_GROUPS) + ['Total'])
        for t in all_r: w.writerow([t] + [m1[t][g] for g in COLOR_GROUPS] + [rt1[t]])
    else:
        utils.print_header("TYPE / COLOR DISTRIBUTION" + (" (COMPARISON)" if m2 else ""), count=len(cards1), use_color=use_color)
        rows = [[utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else h for h in ["Type/Color"] + list(COLOR_GROUPS) + ["Total"]]]
        for t in all_r:
            row = [format_type(t, use_color)]
            for g in COLOR_GROUPS:
                c1 = m1[t][g]
                if m2:
                    c2, d = m2[t][g], m2[t][g]-c1
                    v = str(c2)
                    if d==0: disp = " - " if c2==0 else v
                    else: disp = utils.colorize(f"{v}{'▲' if d>0 else '▼'}", utils.Ansi.GREEN if d>0 else utils.Ansi.RED) if use_color else f"{v}{'▲' if d>0 else '▼'}"
                else: disp = datalib.color_count(c1, use_color) if c1>0 else " - "
                row.append(disp)
            row.append(utils.colorize(str(rt1[t]), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(rt1[t]))
            rows.append(row)
        datalib.add_separator_row(rows)
        tr = [utils.colorize("TOTAL", utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else "TOTAL"]
        for g in COLOR_GROUPS:
            tr.append(utils.colorize(str(ct1[g]), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(ct1[g]))
        tr.append(utils.colorize(str(len(cards1)), utils.Ansi.BOLD + utils.Ansi.WHITE + utils.Ansi.UNDERLINE) if use_color else str(len(cards1)))
        rows.append(tr)
        datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r']*(len(COLOR_GROUPS)+1)), indent=2)

def handle_skeleton(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return
    if not getattr(args, 'quiet', False):
        utils.print_operation_summary("Skeleton Analysis", len(cards), 0, quiet=False)
    m, ct = defaultdict(Counter), Counter()
    cmcs = range(8)
    for c in cards:
        cmc = min(max(0, int(c.cost.cmc)), 7)
        ct[cmc]+=1
        f = False
        for t in TRACKED_TYPES:
            if c._has_type(t): m[t][cmc]+=1; f=True
        if not f: m["Other"][cmc]+=1
    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    all_r = TRACKED_TYPES + (["Other"] if any(m["Other"].values()) else [])
    if getattr(args, 'outfile', None) and args.verbose:
        print(f"Writing results to: {args.outfile}", file=sys.stderr)
    output_f = open(args.outfile, 'w', encoding='utf-8') if getattr(args, 'outfile', None) else sys.stdout
    if not args.json and getattr(args, 'outfile', None):
        if args.outfile.endswith('.json'):
            args.json = True
        elif args.outfile.endswith('.csv'):
            args.csv = True
    if args.json:
        res = {'skeleton': [{'type': t, 'buckets': {str(c) if c < 7 else '7+': m[t][c] for c in cmcs}, 'total': sum(m[t].values())} for t in all_r], 'total': len(cards), 'total_cards': len(cards), 'grand_total': len(cards)}
        try:
            output_f.write(json.dumps(res, indent=2) + '\n')
        finally:
            if getattr(args, 'outfile', None):
                output_f.close()
        return
    if args.csv:
        try:
            w = csv.writer(output_f)
            w.writerow(["Type"] + [str(c) if c < 7 else "7+" for c in cmcs] + ["Total"])
            for t in all_r:
                w.writerow([t] + [m[t][c] for c in cmcs] + [sum(m[t].values())])
            w.writerow(["TOTAL"] + [ct[c] for c in cmcs] + [len(cards)])
        finally:
            if getattr(args, 'outfile', None):
                output_f.close()
        return
    if getattr(args, 'quiet', False) and not getattr(args, 'outfile', None):
        return
    else:
        try:
            with redirect_stdout(output_f):
                if not getattr(args, 'quiet', False):
                    utils.print_header("DESIGN SKELETON", count=len(cards), use_color=use_color)
                rows = [[utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else h for h in ["Type / CMC"] + [str(c) if c<7 else "7+" for c in cmcs] + ["Total"]]]
                for t in all_r:
                    row = [format_type(t, use_color)]
                    for c in cmcs: row.append(datalib.color_count(m[t][c], use_color) if m[t][c]>0 else "-")
                    row.append(utils.colorize(str(sum(m[t].values())), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(sum(m[t].values())))
                    rows.append(row)
                datalib.add_separator_row(rows)
                tr = [utils.colorize("TOTAL", utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else "TOTAL"]
                for c in cmcs: tr.append(utils.colorize(str(ct[c]), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(ct[c]))
                tr.append(utils.colorize(str(len(cards)), utils.Ansi.BOLD + utils.Ansi.WHITE + utils.Ansi.UNDERLINE) if use_color else str(len(cards)))
                rows.append(tr); datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r']*(len(cmcs)+1)), indent=2)
        finally:
            if getattr(args, 'outfile', None):
                output_f.close()

def handle_mana(args):
    cards1 = cli_utils.load_and_filter_cards(args)
    if not cards1: return
    s1 = analyze_dataset(cards1)
    s2 = analyze_dataset(cli_utils.load_and_filter_cards(argparse.Namespace(**{**vars(args), 'infile': args.compare}))) if getattr(args, 'compare', None) else None
    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    if args.json: print(json.dumps({'primary': s1, 'comparison': s2}, indent=2, default=lambda x: dict(x) if isinstance(x, Counter) else x))
    elif args.csv:
        writer = csv.writer(sys.stdout)
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Producer Count', s1['producer_count']])
        writer.writerow(['Fixing Cards', s1['fixing']])
        writer.writerow(['Fixing Density', f"{s1['fixing']/s1['total']*100:.1f}%"])
    else:
        utils.print_header("MANA PRODUCTION ANALYSIS" + (" (COMPARISON)" if s2 else ""), count=s1['total'], use_color=use_color)
        print(f"  {datalib.color_line('General Metrics:', use_color)}")
        h = ["Metric", "Primary"] + (["Comparison", "Delta"] if s2 else [])
        rows = [[utils.colorize(x, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else x for x in h]]
        ms = [("Total Producers", s1['producers'], s2['producers'] if s2 else None), ("Fixing Cards", s1['fixing'], s2['fixing'] if s2 else None), ("Fixing Density", f"{s1['fixing']/s1['total']*100:.1f}%", f"{s2['fixing']/s2['total']*100:.1f}%" if s2 else None)]
        for lbl, v1, v2 in ms:
            row = [lbl, v1]
            if s2:
                row.append(v2)
                try:
                    f1, f2 = float(str(v1).replace('%','')), float(str(v2).replace('%',''))
                    d = f2 - f1; ds = f"{d:+.1f}" + ("%" if "%" in str(v1) else "")
                    row.append(utils.colorize(ds, utils.Ansi.GREEN if d>0.5 else utils.Ansi.RED) if use_color else ds)
                except: row.append("-")
            rows.append(row)
        datalib.printrows(datalib.padrows(rows), indent=4)
        print(f"\n  {datalib.color_line('Produced Colors:', use_color)}")
        ch = ["Color", "Primary %"] + (["Comp %", "Delta"] if s2 else [])
        cr = [[utils.colorize(x, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else x for x in ch]]
        for c in list("WUBRGC") + ["Any"]:
            p1 = s1['cols'][c]/s1['total']*100
            if p1==0 and not (s2 and s2['cols'][c]>0): continue
            row = [utils.colorize(c, utils.Ansi.get_color_color(c) if c!="Any" else utils.Ansi.YELLOW) if use_color else c, f"{p1:5.1f}%"]
            if s2:
                p2 = s2['cols'][c]/s2['total']*100; d = p2-p1
                row.extend([f"{p2:5.1f}%", utils.colorize(f"{d:+.1f}%", utils.Ansi.GREEN if d>1 else utils.Ansi.RED) if use_color else f"{d:+.1f}%"])
            cr.append(row)
        datalib.printrows(datalib.padrows(cr), indent=4)

def handle_pips(args):
    if getattr(args, 'infile', None) == '-' and sys.stdin.isatty():
        script_dir = os.path.dirname(os.path.realpath(__file__))
        for opt in [
            os.path.join(script_dir, '../data/AllPrintings.json'),
            'data/AllPrintings.json',
            os.path.join(os.path.dirname(script_dir), 'data/AllPrintings.json'),
            os.path.join(os.path.dirname(os.path.dirname(script_dir)), 'data/AllPrintings.json')
        ]:
            if os.path.exists(opt):
                args.infile = opt
                if not getattr(args, 'quiet', False):
                    print(f"Notice: Using default dataset: {opt}", file=sys.stderr)
                break
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return
    pips = Counter()
    for c in cards: pips.update(get_pip_counts(c, include_text=args.include_text))
    tot = sum(pips.values())
    res = sorted([{'sym': s, 'symbol': s, 'cnt': c, 'pct': c/tot*100 if tot>0 else 0} for s, c in pips.items()], key=lambda x: x['sym'] if args.sort=='name' else x['cnt'], reverse=args.reverse if args.sort=='name' else not args.reverse)
    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    output_f = None
    if getattr(args, 'outfile', None):
        if args.verbose:
            print(f"Writing results to: {args.outfile}", file=sys.stderr)
        output_f = open(args.outfile, 'w', encoding='utf-8')
    try:
        if args.json or (getattr(args, 'outfile', None) and args.outfile.endswith('.json')):
            target = output_f or sys.stdout
            target.write(json.dumps(res, indent=2) + '\n')
        elif args.csv or (getattr(args, 'outfile', None) and args.outfile.endswith('.csv')):
            target = output_f or sys.stdout
            w = csv.writer(target); w.writerow(['Symbol', 'Count', 'Percent'])
            for r in res: w.writerow([r['sym'], r['cnt'], f"{r['pct']:.2f}"])
        elif getattr(args, 'outfile', None):
            target = output_f
            if args.include_text:
                print("INCLUDES RULES TEXT", file=target)
            print("  MANA PIP DISTRIBUTION", file=target)
            print("  ===============================", file=target)
            print("  Symbol  Count  Percent  Frequency", file=target)
            print("  ------  -----  -------  ------------", file=target)
            for r in res:
                print(f"  {r['sym']:<6}  {r['cnt']:>5}  {r['pct']:>6.1f}%  [██████████]", file=target)
        else:
            if args.include_text:
                print("  INCLUDES RULES TEXT")
            utils.print_header("MANA PIP DISTRIBUTION", count=len(cards), use_color=use_color)
            rows = [[utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else h for h in ["Symbol", "Count", "Percent", "Frequency"]]]
            for r in res:
                es = utils.mana_symall_encode.get(r['sym'], r['sym'])
                rows.append([utils.from_mana("{"+es+"}", ansi_color=use_color), datalib.color_count(r['cnt'], use_color), f"{r['pct']:5.1f}%", datalib.get_bar_chart(r['pct'], use_color, color=utils.Ansi.get_color_color(r['sym']))])
            datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'r', 'l']), indent=2)
    finally:
        if output_f:
            output_f.close()

def handle_costs(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return
    int_sum, buckets, outliers = 0, Counter(), []
    for c in cards:
        cmc, pips, intensity, commitment = get_cost_metrics(c)
        int_sum += intensity
        bucket = "None" if commitment==0 else ("Single" if commitment==1 else ("Double" if commitment==2 else ("Triple" if commitment==3 else "Heavy")))
        buckets[bucket] += 1
        if intensity >= 0.7 or commitment >= 3: outliers.append({'name': c.display_name, 'cost': c.cost.format(), 'intensity': intensity, 'commitment': commitment, 'card': c})
    outliers.sort(key=lambda x: (x['intensity'], x['commitment']), reverse=True)
    avg_int = int_sum / len(cards)
    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    if args.json: print(json.dumps({'total': len(cards), 'total_cards': len(cards), 'avg_int': avg_int, 'avg_intensity': avg_int, 'buckets': dict(buckets), 'commitment_distribution': dict(buckets), 'outliers': [{'name': o['name'], 'intensity': o['intensity'], 'commitment': o['commitment']} for o in outliers[:20]]}, indent=2))
    else:
        utils.print_header("MANA COST INTENSITY ANALYSIS", count=len(cards), use_color=use_color)
        print(f"  {utils.colorize(f'Global Average Intensity: {avg_int:.2f}', utils.Ansi.BOLD+utils.Ansi.GREEN) if use_color else f'Global Average Intensity: {avg_int:.2f}'}\n")
        rows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in ["Commitment", "Count", "Percent", "Distribution"]]]
        for b in ["None", "Single", "Double", "Triple", "Heavy"]:
            cnt = buckets[b]; p = cnt/len(cards)*100
            rows.append([b, datalib.color_count(cnt, use_color), f"{p:5.1f}%", datalib.get_bar_chart(p, use_color, color=utils.Ansi.CYAN)])
        datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'r', 'l']), indent=4)
        if outliers:
            print(f"\n  {datalib.color_line('Top Pip-Heavy Outliers:', use_color)}")
            oh = ["Name", "Cost", "Intensity", "Commit", "Rarity"]
            orows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in oh]]
            for o in outliers[:20]:
                c = o['card']; r = c.rarity_name
                orows.append([utils.colorize(c.display_name, c._get_ansi_color()) if use_color else c.display_name, c.cost.format(ansi_color=use_color), f"{o['intensity']:.2f}", str(o['commitment']), utils.colorize(r, utils.Ansi.get_rarity_color(r)) if use_color else r])
            datalib.add_separator_row(orows); datalib.printrows(datalib.padrows(orows, aligns=['l', 'l', 'r', 'r', 'l']), indent=4)

def handle_mechanics(args):
    use_color = args.color if args.color is not None else sys.stdout.isatty()
    if not getattr(args, 'infile', None) or (args.infile == '-' and not any(getattr(args, name, None) for name in ['grep', 'vgrep', 'grep_name', 'vgrep_name', 'grep_type', 'vgrep_type', 'grep_text', 'vgrep_text', 'grep_cost', 'vgrep_cost', 'grep_pt', 'vgrep_pt', 'grep_loyalty', 'vgrep_loyalty', 'set', 'rarity', 'colors', 'identity', 'cmc', 'pow', 'tou', 'loy', 'mechanic'])):
        print("RECOGNIZED MECHANICS")
        print(f"  Total: {len(RECOGNIZED_MECHANICS)}")
        for m in sorted(RECOGNIZED_MECHANICS):
            print(f"  - {utils.colorize(m, utils.Ansi.CYAN) if use_color else m}")
        return
    cards1 = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards1, args): return
    def count_m(cards):
        c = Counter()
        for card in cards:
            for m in card.mechanics: c[m] += 1
        return c, len(cards)
    c1, t1 = count_m(cards1)
    c2, t2 = count_m(cli_utils.load_and_filter_cards(argparse.Namespace(**{**vars(args), 'infile': args.compare}))) if getattr(args, 'compare', None) else (None, 0)
    all_m = set(c1.keys()); [all_m.add(m) for m in (c2 or [])]
    ordered = [m for m in RECOGNIZED_MECHANICS if m in all_m] + sorted([m for m in all_m if m not in RECOGNIZED_MECHANICS])
    res = [{'name': m, 'c1': c1[m], 'p1': c1[m]/t1*100, 'c2': c2[m] if c2 else 0, 'p2': c2[m]/t2*100 if t2>0 else 0, 'delta': (c2[m]/t2*100 if t2>0 else 0) - c1[m]/t1*100 if c2 else 0} for m in ordered]
    res.sort(key=lambda x: x['name'].lower() if args.sort=='name' else x['c1'], reverse=args.reverse if args.sort=='name' else not args.reverse)
    if args.top > 0: res = res[:args.top]
    utils.print_header("MECHANICAL COMPARISON" if c2 else "MECHANICAL FREQUENCY", count=len(cards1), use_color=use_color)
    print(f"  Total Cards: {len(cards1)}")
    if c2:
        h = ["Mechanic", "% P1", "% P2", "Delta", "Ind"]
        rows = [[utils.colorize(x, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else x for x in h]]
        for r in res:
            d = r['delta']; ind = "▲" if d>0.1 else ("▼" if d<-0.1 else "•")
            rows.append([utils.colorize(r['name'], utils.Ansi.CYAN) if use_color else r['name'], f"{r['p1']:5.1f}%", f"{r['p2']:5.1f}%", utils.colorize(f"{d:+6.1f}%", utils.Ansi.GREEN if d>0.1 else utils.Ansi.RED) if use_color and abs(d)>0.1 else f"{d:+6.1f}%", utils.colorize(ind, utils.Ansi.GREEN if d>0.1 else utils.Ansi.RED) if use_color and abs(d)>0.1 else ind])
    else:
        h = ["Mechanic", "Count", "Percent", "Frequency"]
        rows = [[utils.colorize(x, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else x for x in h]]
        for r in res: rows.append([utils.colorize(r['name'], utils.Ansi.CYAN) if use_color else r['name'], str(r['c1']), f"{r['p1']:5.1f}%", datalib.get_bar_chart(r['p1'], use_color, color=utils.Ansi.CYAN)])
    datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['l','r','r','r','c'] if c2 else ['l','r','r','l']), indent=2)

def handle_interaction(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return
    dens_d, ind_c, pair_c, syn = calculate_interaction(cards, min_freq=args.min_freq)
    syn.sort(key=lambda x: x['lift'], reverse=True)
    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    if args.json: print(json.dumps({'total': len(cards), 'total_cards': len(cards), 'density': dict(dens_d), 'density_distribution': dict(dens_d), 'interaction': syn, 'interaction_pairs': syn}, indent=2))
    elif args.csv:
        writer = csv.writer(sys.stdout)
        writer.writerow(['Mechanic 1', 'Mechanic 2', 'Count', 'Lift', 'P(A&B)'])
        for r in syn:
            m1, m2 = r['pair']
            pa_b = r['cnt'] / len(cards) if cards else 0
            writer.writerow([m1, m2, r['cnt'], f"{r['lift']:.2f}", f"{pa_b:.4f}"])
    else:
        utils.print_header("MECHANICAL INTERACTION ANALYSIS", count=len(cards), use_color=use_color)
        print(f"  {datalib.color_line('Mechanical Density:', use_color)}")
        rows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in ["Mechanics", "Cards", "Percent", "Distribution"]]]
        for i in range(max(dens_d.keys())+1 if dens_d else 1):
            cnt = dens_d.get(i, 0); p = cnt/len(cards)*100
            rows.append([str(i), str(cnt), f"{p:5.1f}%", datalib.get_bar_chart(p, use_color, color=utils.Ansi.CYAN)])
        datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['r','r','r','l']), indent=4)
        print(f"\n  {datalib.color_line('Top Interaction Pairs (by Lift):', use_color)}")
        sh = ["Pair", "Count", "Lift", "Desc"]
        srows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in sh]]
        for r in syn[:args.top]:
            m1, m2 = r['pair']; lift = r['lift']
            pair = f"{utils.colorize(m1, utils.Ansi.CYAN)} + {utils.colorize(m2, utils.Ansi.CYAN)}" if use_color else f"{m1} + {m2}"
            desc = "Strong Interaction" if lift>2.0 else ("Positive Interaction" if lift>1.2 else "Expected")
            srows.append([pair, str(r['cnt']), utils.colorize(f"{lift:6.2f}", utils.Ansi.BOLD+utils.Ansi.GREEN if lift>2.0 else "") if use_color else f"{lift:6.2f}", desc])
        datalib.add_separator_row(srows); datalib.printrows(datalib.padrows(srows, aligns=['l','r','r','l']), indent=4)

def handle_actions(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return
    act_c, col_act = Counter(), defaultdict(Counter)
    for c in cards:
        acts = c.actions
        for a in acts:
            act_c[a] += 1
            for col in (c.cost.colors or ['C']): col_act[col][a] += 1
    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    if args.json: print(json.dumps({'total': len(cards), 'total_cards': len(cards), 'summary': dict(act_c), 'color': {c: dict(v) for c, v in col_act.items()}}, indent=2))
    else:
        utils.print_header("CARD ACTION ANALYSIS", count=len(cards), use_color=use_color)
        rows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in ["Action", "Count", "Percent", "Frequency"]]]
        for a, cnt in act_c.most_common():
            p = cnt/len(cards)*100
            rows.append([utils.colorize(a, utils.Ansi.CYAN) if use_color else a, datalib.color_count(cnt, use_color), f"{p:5.1f}%", datalib.get_bar_chart(p, use_color, color=utils.Ansi.BOLD+utils.Ansi.CYAN)])
        datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['l','r','r','l']), indent=4)
        print(f"\n  {datalib.color_line('Actions by Color (Frequency %):', use_color)}")
        ch = ["Action"] + list("WUBRGC")
        crows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in ch]]
        for a in sorted(ACTION_CATEGORIES.keys()):
            row = [a]
            for col in "WUBRGC":
                tot_c = sum(1 for c in cards if (c.cost.colors or ['C'])[0]==col)
                p = (col_act[col][a]/tot_c*100) if tot_c>0 else 0
                row.append(utils.colorize(f"{p:4.0f}%", utils.Ansi.get_color_color(col)) if use_color and p>0 else (f"{p:4.0f}%" if p>0 else "  - "))
            crows.append(row)
        datalib.add_separator_row(crows); datalib.printrows(datalib.padrows(crows, aligns=['l'] + ['r']*6), indent=4)

def handle_lexicon(args):
    cards1 = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards1, args): return
    stats1 = analyze_lexicon(cards1, top=args.top, min_len=args.min_len)
    if not stats1 or stats1['total'] == 0:
        if not getattr(args, 'quiet', False):
            print("Insufficient card text.", file=sys.stderr)
        return
    stats2 = analyze_lexicon(cli_utils.load_and_filter_cards(argparse.Namespace(**{**vars(args), 'infile': args.compare})), top=args.top, min_len=args.min_len) if getattr(args, 'compare', None) else None
    if stats2 is not None and stats2['total'] == 0:
        if not getattr(args, 'quiet', False):
            print(f"Insufficient card text in {args.compare} for comparison.", file=sys.stderr)
    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    if args.json: print(json.dumps({'primary': stats1, 'comparison': stats2}, indent=2))
    else:
        utils.print_header("COLOR LEXICON ANALYSIS", count=len(cards1), use_color=use_color)
        rows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in ["Color", "Signature Words", "Vocab"]]]
        clbls = {'W':'White','U':'Blue','B':'Black','R':'Red','G':'Green','M':'Multi','A':'Colorless'}
        for c in 'WUBRGMA':
            if c not in stats1: continue
            rows.append([utils.colorize(clbls[c], utils.Ansi.get_color_color(c)) if use_color else clbls[c], ", ".join(stats1[c]['top']), str(stats1[c]['total'])])
        datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['l','l','r']), indent=2)
        if stats2:
            print(f"\n=== COMPARISON: {args.compare} ===")
            crows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in ["Color", "Signature Words", "Vocab"]]]
            for c in 'WUBRGMA':
                if c not in stats2: continue
                w1s = set(stats1.get(c, {}).get('top', []))
                dw = [utils.colorize(w, utils.Ansi.BOLD+utils.Ansi.GREEN) if use_color and w not in w1s else (f"*{w}*" if w not in w1s else w) for w in stats2[c]['top']]
                crows.append([utils.colorize(clbls[c], utils.Ansi.get_color_color(c)) if use_color else clbls[c], ", ".join(dw), str(stats2[c]['total'])])
            datalib.add_separator_row(crows); datalib.printrows(datalib.padrows(crows, aligns=['l','l','r']), indent=2)
    if not getattr(args, 'quiet', False):
        print(f"Lexicon Analysis complete: {len(cards1)} card processed.", file=sys.stderr)

def handle_stats(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return
    cmc_s = defaultdict(lambda: {'pow': 0.0, 'tou': 0.0, 'cnt': 0})
    col_s = defaultdict(lambda: {'pow': 0.0, 'tou': 0.0, 'cnt': 0})
    pt_d, lo_s, cre_c = Counter(), [], 0
    for c in cards:
        p, t, l = get_numeric_stats(c); cmc = min(max(0, int(c.cost.cmc)), 7)
        if p is not None and t is not None:
            cre_c += 1; cmc_s[cmc]['pow']+=p; cmc_s[cmc]['tou']+=t; cmc_s[cmc]['cnt']+=1
            for col in (c.cost.colors or ['C']): col_s[col]['pow']+=p; col_s[col]['tou']+=t; col_s[col]['cnt']+=1
            pt_d[(int(p), int(t))] += 1
        if l is not None: lo_s.append(l)
    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    json_data = {
        'total': len(cards),
        'total_cards': len(cards),
        'creatures': cre_c,
        'creatures_analyzed': cre_c,
        'avg_loy': sum(lo_s)/len(lo_s) if lo_s else 0,
        'cmc_curve': [],
        'color_breakdown': [],
    }
    for b in range(8):
        s = cmc_s[b]
        if s['cnt'] == 0:
            continue
        ap, at = s['pow']/s['cnt'], s['tou']/s['cnt']
        json_data['cmc_curve'].append({'cmc': str(b) if b < 7 else '7+', 'avg_pow': ap, 'avg_tou': at, 'count': s['cnt']})
    for col in list("WUBRGC"):
        s = col_s[col]
        if s['cnt'] == 0:
            continue
        ap, at = s['pow']/s['cnt'], s['tou']/s['cnt']
        json_data['color_breakdown'].append({'color': col, 'avg_pow': ap, 'avg_tou': at, 'count': s['cnt']})
    if getattr(args, 'outfile', None) and args.verbose:
        print(f"Writing results to: {args.outfile}", file=sys.stderr)
    output_f = open(args.outfile, 'w', encoding='utf-8') if getattr(args, 'outfile', None) else sys.stdout
    try:
        if args.json or (getattr(args, 'outfile', None) and args.outfile.endswith('.json')):
            output_f.write(json.dumps(json_data, indent=2) + '\n')
        elif args.csv or (getattr(args, 'outfile', None) and args.outfile.endswith('.csv')):
            writer = csv.writer(output_f)
            writer.writerow(['Metric', 'Category', 'Avg Pow', 'Avg Tou', 'Count'])
            for row in json_data['cmc_curve']:
                writer.writerow(['CMC Curve', row['cmc'], f"{row['avg_pow']:.2f}", f"{row['avg_tou']:.2f}", row['count']])
            for row in json_data['color_breakdown']:
                writer.writerow(['Color Breakdown', row['color'], f"{row['avg_pow']:.2f}", f"{row['avg_tou']:.2f}", row['count']])
        else:
            stream = output_f if getattr(args, 'outfile', None) else sys.stdout
            with redirect_stdout(stream):
                utils.print_header("COMBAT STAT ANALYSIS", count=len(cards), use_color=use_color)
                if cre_c > 0:
                    print(f"  {datalib.color_line('Combat Stat Curve (Avg P/T per CMC):', use_color)}")
                    rows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in ["CMC", "Avg P", "Avg T", "Count", "Ratio"]]]
                    for b in range(8):
                        s = cmc_s[b]
                        if s['cnt']==0: continue
                        ap, at = s['pow']/s['cnt'], s['tou']/s['cnt']; r = ap/at if at>0 else 0; rs = f"{r:.2f}"
                        if use_color: rs = utils.colorize(rs, utils.Ansi.BOLD + (utils.Ansi.RED if r>1.1 else (utils.Ansi.GREEN if r<0.9 else "")))
                        rows.append([utils.colorize(str(b) if b<7 else "7+", utils.Ansi.CYAN) if use_color else (str(b) if b<7 else "7+"), f"{ap:5.2f}", f"{at:5.2f}", datalib.color_count(s['cnt'], use_color), rs])
                    datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['r']*5), indent=4)
                else:
                    print("  No creatures found for combat stat analysis.")
                if lo_s:
                    print(f"\n  Loyalty Stats (Planeswalkers/Battles):")
                    print(f"  Average Loyalty: {sum(lo_s)/len(lo_s):.2f} (Count: {len(lo_s)})")
                if any(s['cnt'] > 0 for s in col_s.values()):
                    print(f"\n  Color Breakdown (Avg P/T by Color):")
                    c_rows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in ["Color", "Avg P", "Avg T", "Count"]]]
                    for col in list("WUBRGC"):
                        s = col_s[col]
                        if s['cnt'] == 0:
                            continue
                        c_rows.append([utils.colorize(col, utils.Ansi.get_color_color(col)) if use_color else col, f"{s['pow']/s['cnt']:.2f}", f"{s['tou']/s['cnt']:.2f}", datalib.color_count(s['cnt'], use_color)])
                    datalib.add_separator_row(c_rows)
                    datalib.printrows(datalib.padrows(c_rows, aligns=['l', 'r', 'r', 'r']), indent=4)
    finally:
        if getattr(args, 'outfile', None):
            output_f.close()

def handle_power(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return
    creatures = [c for c in cards if c.is_creature]
    if not creatures:
        if not getattr(args, 'quiet', False):
            print("No creatures found matching the criteria.", file=sys.stderr)
        return
    sc = sorted(creatures, key=lambda c: c.power_rating, reverse=True)
    rs, cs = defaultdict(list), defaultdict(list)
    for c in creatures:
        rs[c.rarity_name].append(c.power_rating)
        ci = (c.color_identity if c.color_identity else 'A'); ci = 'M' if len(ci)>1 else ci
        cs[ci].append(c.power_rating)
    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    limit = args.limit if args.limit > 0 else 20
    if args.json: print(json.dumps({'total': len(creatures), 'top': [{'name': c.display_name, 'rating': c.power_rating} for c in sc[:limit]]}, indent=2))
    else:
        utils.print_header("POWER BALANCE ANALYSIS", count=len(creatures), use_color=use_color)
        rows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in ["Name", "Rating", "Cost", "Fair MV", "P/T", "Rarity"]]]
        for c in sc[:limit]:
            rt = str(c.power_rating)
            if use_color: rt = utils.colorize(rt, utils.Ansi.BOLD+utils.Ansi.GREEN if c.power_rating>1.2 else (utils.Ansi.RED if c.power_rating<0.8 else ""))

            val = c.recommended_cmc
            fair_mv = str(val)
            if use_color:
                color = utils.Ansi.GREEN if c.cost.cmc >= val else utils.Ansi.RED
                fair_mv = utils.colorize(fair_mv, utils.Ansi.BOLD + color)

            rar = c.rarity_name
            rows.append([utils.colorize(c.display_name, c._get_ansi_color()) if use_color else c.display_name, rt, c.cost.format(ansi_color=use_color), fair_mv, c._get_pt_display(ansi_color=use_color, include_parens=False), utils.colorize(rar, utils.Ansi.get_rarity_color(rar)) if use_color else rar])
        datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['l','r','l','r','r','l']), indent=4)

def handle_archetypes(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return
    if len(cards) < args.min_cards:
        if not getattr(args, 'quiet', False):
            print("Insufficient data to profile archetypes.", file=sys.stderr)
        return
    archs = {p: [] for p in GUILD_PAIRS}; g_m = Counter()
    for c in cards:
        for m in c.mechanics: g_m[m] += 1
        id = c.color_identity
        if len(id) == 2 and id in archs: archs[id].append(c)
        elif len(id) == 1: [archs[p].append(c) for p in GUILD_PAIRS if id in p]
    res = []
    for p in [p for p in GUILD_PAIRS if len(archs[p]) >= args.min_cards]:
        ac = archs[p]; pm = Counter()
        for c in ac: [pm.update([m]) for m in c.mechanics]
        dist = {m: (pm[m]/len(ac))/(g_m[m]/len(cards)) for m in pm}
        top_m = sorted(dist.keys(), key=lambda m: (dist[m], pm[m]), reverse=True)[:args.top_mechanics]
        uncs = [c for c in ac if c.rarity == utils.rarity_uncommon_marker and len(c.color_identity) == 2]
        res.append({"label": p, "count": len(ac), "signpost": titlecase(uncs[0].name) if uncs else "None", "mechs": top_m, "avg_cmc": sum(c.cost.cmc for c in ac)/len(ac), "cre_p": sum(1 for c in ac if c.is_creature)/len(ac)*100})
    use_color = args.color if args.color is not None else sys.stdout.isatty()
    utils.print_header("ARCHETYPE PROFILING", use_color=use_color)
    print(f"  Total cards analyzed: {len(cards)}")
    rows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in ["Archetype", "Cards", "Signpost", "Mechs", "CMC", "Cre %"]]]
    for r in res:
        lbl = GUILD_LABELS.get(r['label'], r['label'])
        if use_color and " " in lbl:
            code, name = lbl.split(None, 1)
            lbl = "".join([utils.colorize(c, utils.Ansi.get_color_color(c)) for c in code]) + f" {name}"
        rows.append([lbl, str(r['count']), r['signpost'], ", ".join(r['mechs']), f"{r['avg_cmc']:.2f}", f"{r['cre_p']:5.1f}%"])
    datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['l','r','l','l','r','r']), indent=2)

def handle_balance(args):
    datasets = []
    for f in args.infiles:
        cards = jdecode.mtg_open_file(f, verbose=args.verbose, sets=args.set, rarities=args.rarity)
        if args.limit > 0: cards = cards[:args.limit]
        if not cards: continue
        counts = get_archetype_counts(cards)
        datasets.append({'name': os.path.basename(f)[:15], 'counts': counts, 'total': len(cards), 'total_cards': len(cards)})
    if not datasets:
        if not getattr(args, 'quiet', False):
            label = os.path.basename(args.infiles[0]) if getattr(args, 'infiles', None) else "dataset"
            print(f"Warning: No cards found in {label}", file=sys.stderr)
        return
    use_color = args.color if args.color is not None else sys.stdout.isatty()
    base = datasets[0]
    h = ["Archetype", f"% {base['name']}"]
    for i in range(1, len(datasets)): h.extend([f"% {datasets[i]['name']}", "Delta"])
    if use_color: h = [utils.colorize(x, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) for x in h]
    rows = [h]
    for p in GUILD_PAIRS:
        label = GUILD_LABELS[p]
        if use_color:
            parts = label.split(None, 1); code = parts[0]; name = parts[1] if len(parts)>1 else ""
            colored_code = "".join([utils.colorize(c, utils.Ansi.get_color_color(c)) for c in code])
            label = f"{colored_code} {name}"
        bp = base['counts'][p]/base['total']*100 if base['total']>0 else 0
        row = [label, f"{bp:5.1f}%"]
        for i in range(1, len(datasets)):
            ds = datasets[i]; pct = ds['counts'][p]/ds['total']*100 if ds['total']>0 else 0; d = pct-bp
            ds_str = f"{d:+5.1f}%"
            if use_color:
                if d>2.0: ds_str = utils.colorize(ds_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
                elif d<-2.0: ds_str = utils.colorize(ds_str, utils.Ansi.BOLD + utils.Ansi.RED)
            row.extend([f"{pct:5.1f}%", ds_str])
        rows.append(row)
    utils.print_header("ARCHETYPE BALANCE COMPARISON", use_color=use_color)
    print(f"  Baseline: {base['name']} ({base['total']} cards)\n")
    datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r']*(len(h)-1)), indent=2)

def handle_asfan(args):
    cards1 = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards1, args): return
    a1 = calculate_asfan(cards1)

    a2 = None
    if getattr(args, 'compare', None):
        cards2 = cli_utils.load_and_filter_cards(argparse.Namespace(**{**vars(args), 'infile': args.compare}))
        if check_cards(cards2, args):
            a2 = calculate_asfan(cards2)

    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    if args.json:
        print(json.dumps({'primary': a1, 'comparison': a2}, indent=2))
        return
    utils.print_header("AS-FAN ANALYSIS" + (" (COMPARISON)" if a2 else ""), use_color=use_color)
    def pt(title, d1, d2, ks=None):
        print(f"  {datalib.color_line(title, use_color)}")
        h = ["Metric", "P1"] + (["P2", "Delta"] if d2 else ["Freq"])
        rows = [[utils.colorize(x, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else x for x in h]]
        ks = ks or sorted(d1.keys())
        for k in ks:
            v1 = d1.get(k, 0.0); row = [utils.colorize(str(k), utils.Ansi.get_color_color(k)) if use_color and title.lower().startswith('color') else str(k), f"{v1:4.2f}"]
            if d2:
                v2 = d2.get(k, 0.0); d = v2-v1; ds = f"{d:+5.2f}"
                if use_color: ds = utils.colorize(ds, utils.Ansi.GREEN if d>0.2 else (utils.Ansi.RED if d<-0.2 else ""))
                row.extend([f"{v2:4.2f}", ds])
            else: row.append(datalib.get_bar_chart(v1/15*100, use_color))
            rows.append(row)
        datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['l','r','r','r']), indent=4)
    pt("Color Distribution:", a1['colors'], a2['colors'] if a2 else None, ks='WUBRGC')
    pt("Type Distribution:", a1['types'], a2['types'] if a2 else None)

def handle_tokens(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return
    all_t = []
    for c in cards:
        if getattr(args, 'verbose', False):
            print(f"Processing card: {c.name}")
        found = c.tokens
        for t in found: t['source'] = c.name; all_t.append(t)
    uniq = OrderedDict()
    for t in all_t:
        k = (t['pt'], t['color'], t['type'], t['abilities'])
        if k not in uniq: uniq[k] = t; uniq[k]['cnt'] = 1
        else: uniq[k]['cnt'] += 1
    ts = sorted(uniq.values(), key=lambda x: x['name'])
    use_color = args.color if args.color is not None else sys.stdout.isatty()
    if getattr(args, 'verbose', False):
        print(f"Found {len(ts)} tokens")
    if not ts and not getattr(args, 'quiet', False):
        print("No token definitions found.")
    if args.json:
        print(json.dumps([{**t, 'count': t['cnt']} for t in ts], indent=2))
        return
    if args.csv:
        writer = csv.DictWriter(sys.stdout, fieldnames=['Name', 'P/T', 'Color', 'Type', 'Abilities', 'Cnt'])
        writer.writeheader()
        for t in ts:
            writer.writerow({'Name': t['name'], 'P/T': t['pt'], 'Color': t['color'], 'Type': t['type'], 'Abilities': t['abilities'], 'Cnt': t['cnt']})
        return
    utils.print_header("EXTRACTED TOKENS", count=len(ts), use_color=use_color)
    h = ["Name", "P/T", "Color", "Type", "Abilities", "Cnt"]
    rows = [[utils.colorize(x, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else x for x in h]]
    for t in ts:
        n, pt, cl, ty, cnt = t['name'], t['pt'], t['color'], t['type'], str(t['cnt'])
        if use_color: n = utils.colorize(n, utils.Ansi.BOLD+utils.Ansi.CYAN); pt = utils.colorize(pt, utils.Ansi.RED); ty = utils.colorize(ty, utils.Ansi.GREEN); cnt = utils.colorize(cnt, utils.Ansi.BOLD+utils.Ansi.GREEN)
        rows.append([n, pt, cl, ty, t['abilities'], cnt])
    datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['l','r','l','l','l','r']), indent=2)

def handle_profile(args):
    target_cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(target_cards, args): return

    import copy
    baseline_args = copy.deepcopy(args)
    # Clear filters for baseline to get the whole dataset
    filter_attrs = [
        'grep', 'vgrep', 'grep_name', 'exclude_name', 'grep_type', 'exclude_type',
        'grep_text', 'exclude_text', 'grep_cost', 'exclude_cost', 'grep_pt', 'exclude_pt',
        'grep_loyalty', 'exclude_loyalty', 'set', 'rarity', 'colors', 'identity',
        'id_count', 'cmc', 'pow', 'tou', 'loy', 'mechanic', 'action', 'deck',
        'booster', 'box', 'limit', 'sample'
    ]
    for attr in filter_attrs:
        if hasattr(baseline_args, attr):
            setattr(baseline_args, attr, 0 if attr in ['booster', 'box', 'limit', 'sample'] else None)
    baseline_args.shuffle = False
    baseline_args.quiet = True

    baseline_cards = cli_utils.load_and_filter_cards(baseline_args)
    if not baseline_cards:
        return

    def get_metrics(cards):
        metrics = {'cmc': 0.0, 'pow': 0.0, 'tou': 0.0, 'comp': 0.0, 'cnt': len(cards), 'cre_cnt': 0}
        for c in cards:
            metrics['cmc'] += c.cost.cmc
            metrics['comp'] += c.complexity_score
            p, t, _ = get_numeric_stats(c)
            if p is not None and t is not None:
                metrics['pow'] += p
                metrics['tou'] += t
                metrics['cre_cnt'] += 1

        return {
            'cmc': metrics['cmc'] / metrics['cnt'] if metrics['cnt'] > 0 else 0,
            'comp': metrics['comp'] / metrics['cnt'] if metrics['cnt'] > 0 else 0,
            'pow': metrics['pow'] / metrics['cre_cnt'] if metrics['cre_cnt'] > 0 else 0,
            'tou': metrics['tou'] / metrics['cre_cnt'] if metrics['cre_cnt'] > 0 else 0,
            'cnt': metrics['cnt']
        }

    t_metrics = get_metrics(target_cards)
    b_metrics = get_metrics(baseline_cards)

    use_color = args.color if args.color is not None else sys.stdout.isatty()
    utils.print_header("MECHANICAL IDENTITY PROFILE", count=f"{t_metrics['cnt']} cards", use_color=use_color)

    stats_rows = [[utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else h for h in ["Metric", "Subset", "Baseline", "Delta"]]]
    for label, key, reverse in [("Avg CMC", 'cmc', True), ("Avg Power", 'pow', False), ("Avg Toughness", 'tou', False), ("Avg Complexity", 'comp', True)]:
        v_t, v_b = t_metrics[key], b_metrics[key]
        stats_rows.append([label, f"{v_t:.2f}", f"{v_b:.2f}", format_delta(v_t, v_b, use_color=use_color, reverse_color=reverse)])

    datalib.add_separator_row(stats_rows)
    datalib.printrows(datalib.padrows(stats_rows, aligns=['l', 'r', 'r', 'r']), indent=2)
    print()

    def get_freqs(cards):
        mechs, acts, subs = Counter(), Counter(), Counter()
        for c in cards:
            for m in c.mechanics: mechs[m] += 1
            for a in c.actions: acts[a] += 1
            for s in c.subtypes: subs[titlecase(s.replace(utils.dash_marker, '-'))] += 1
        return mechs, acts, subs

    t_mechs, t_acts, t_subs = get_freqs(target_cards)
    b_mechs, b_acts, b_subs = get_freqs(baseline_cards)

    def calculate_lifts(t_counts, b_counts, t_total, b_total):
        lifts = []
        for k, count in t_counts.items():
            f_t = count / t_total
            f_b = b_counts[k] / b_total if b_counts[k] > 0 else 0.0001
            lifts.append({'key': k, 'lift': f_t / f_b, 'count': count, 'freq': f_t * 100})
        return sorted(lifts, key=lambda x: x['lift'], reverse=True)

    def print_lift_table(title, lifts, top_n):
        if not lifts: return
        print(f"  {datalib.color_line(title, use_color)}")
        rows = [[utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else h for h in ["Feature", "Lift", "Subset %", "Count"]]]
        for item in lifts[:top_n]:
            l_str = f"{item['lift']:.2f}x"
            if use_color and item['lift'] > 1.5: l_str = utils.colorize(l_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
            rows.append([item['key'], l_str, f"{item['freq']:5.1f}%", str(item['count'])])
        datalib.add_separator_row(rows)
        datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'r', 'r']), indent=4)
        print()

    print_lift_table("Signature Mechanics:", calculate_lifts(t_mechs, b_mechs, t_metrics['cnt'], b_metrics['cnt']), args.top)
    print_lift_table("Signature Actions:", calculate_lifts(t_acts, b_acts, t_metrics['cnt'], b_metrics['cnt']), args.top)
    print_lift_table("Signature Subtypes:", calculate_lifts(t_subs, b_subs, t_metrics['cnt'], b_metrics['cnt']), args.top)

def handle_subtypes(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return

    stats = analyze_subtypes(cards, top=args.top)
    gf = stats['global_freq']
    if not gf: return

    c_stats = stats['color_stats']
    tot_gi = sum(gf.values())

    use_color = args.color if args.color is not None else (not (args.json or args.csv) and sys.stdout.isatty())
    if args.json:
        res = {'total_cards': stats['total_cards'], 'total': stats['total'], 'global_freq': dict(gf), 'color_stats': c_stats, 'stats': {g: {'top': v['top'], 'total': v['total'], 'cnt': v['cnt']} for g, v in c_stats.items()}}
        print(json.dumps(res, indent=2))
    elif args.csv:
        w = csv.writer(sys.stdout); w.writerow(['Subtype', 'Count', 'Percent', 'Group', 'Distinctiveness'])
        for g, d in c_stats.items():
            for s in d['top']: w.writerow([s, d['freq'][s], f"{d['freq'][s]/d['total']*100:.2f}", g, f"{d['scores'][s]:.2f}"])
    else:
        utils.print_header("SUBTYPE DISTRIBUTION ANALYSIS", count=len(cards), use_color=use_color)
        print(f"\n  {datalib.color_line('Top Subtypes Overall:', use_color)}")
        rows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in ["Subtype", "Count", "Percent", "Distribution"]]]
        for s, cnt in gf.most_common(args.top):
            p = cnt/tot_gi*100; rows.append([s, datalib.color_count(cnt, use_color), f"{p:5.1f}%", datalib.get_bar_chart(p, use_color, color=utils.Ansi.CYAN)])
        datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['l','r','r', 'l']), indent=4)
        print(f"\n  {datalib.color_line('Signature Subtypes by Color Group:', use_color)}")
        crows = [[utils.colorize(h, utils.Ansi.BOLD+utils.Ansi.UNDERLINE) if use_color else h for h in ["Group", "Signature Subtypes", "Distinctiveness", "Cards"]]]
        clbls = {'W':'White','U':'Blue','B':'Black','R':'Red','G':'Green','M':'Multi','A':'Colorless'}
        for g in 'WUBRGMA':
            if g not in c_stats: continue
            d = c_stats[g]
            crows.append([utils.colorize(clbls[g], utils.Ansi.get_color_color(g)) if use_color else clbls[g], ", ".join(d['top']), f"{max(d['scores'].values()) if d['scores'] else 0:.1f}x", str(d['cnt'])])
        datalib.add_separator_row(crows); datalib.printrows(datalib.padrows(crows, aligns=['l','l','r','r']), indent=4)

def handle_audit(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not check_cards(cards, args): return

    total = len(cards)
    creatures = [c for c in cards if c.is_creature]

    # 1. Balance Check
    color_counts = Counter()
    rarity_counts = Counter()
    for c in cards:
        color_counts[get_color_group(c)] += 1
        rarity_counts[c.rarity_name.title()] += 1

    # 2. Functional Coverage
    actions = Counter()
    fixing_cards = 0
    for c in cards:
        for a in c.actions:
            actions[a] += 1
        if c.produced_colors and "Any" in c.produced_colors:
            fixing_cards += 1
        elif len(c.produced_colors) >= 2:
            fixing_cards += 1

    # 3. Complexity & Balance
    avg_cmc = sum(c.cost.cmc for c in cards) / total
    avg_complexity = sum(c.complexity_score for c in cards) / total

    complexity_outliers = sorted(cards, key=lambda c: c.complexity_score, reverse=True)[:5]

    # 4. Color Pie Break Detection
    breaks = []
    for c in cards:
        res = c.check_color_pie()
        if isinstance(res, str):
            breaks.append({'card': c.display_name, 'reason': res})

    use_color = args.color if args.color is not None else (not (getattr(args, 'json', False)) and sys.stdout.isatty())

    audit_data = {
        'total_cards': total,
        'creature_density': len(creatures) / total * 100,
        'avg_cmc': avg_cmc,
        'avg_complexity': avg_complexity,
        'color_balance': {c: count / total * 100 for c, count in color_counts.items()},
        'rarity_balance': {r: count / total * 100 for r, count in rarity_counts.items()},
        'functional_coverage': {a: count / total * 100 for a, count in actions.items()},
        'fixing_density': fixing_cards / total * 100,
        'complexity_outliers': [{'name': c.display_name, 'score': c.complexity_score} for c in complexity_outliers],
        'color_pie_breaks': breaks
    }

    if getattr(args, 'json', False):
        print(json.dumps(audit_data, indent=2))
        return

    utils.print_header("DESIGN HEALTH AUDIT", count=total, use_color=use_color)

    def print_stat(label, val, target=None, unit="", indent=2):
        s = f"{label}: {val:.1f}{unit}"
        msg_type = "[INFO]"
        color = utils.Ansi.BOLD + utils.Ansi.CYAN

        if target is not None:
            diff = abs(val - target)
            if diff > target * 0.5:
                msg_type = "[ISSUE]"
                color = utils.Ansi.BOLD + utils.Ansi.RED
            elif diff > target * 0.2:
                msg_type = "[WARNING]"
                color = utils.Ansi.BOLD + utils.Ansi.YELLOW

        if use_color:
            print(f"{' ' * indent}{utils.colorize(msg_type, color)} {s}")
        else:
            print(f"{' ' * indent}{msg_type} {s}")

    print(f"\n  {datalib.color_line('Core Metrics:', use_color)}")
    print_stat("Creature Density", audit_data['creature_density'], target=50, unit="%")
    print_stat("Average CMC", audit_data['avg_cmc'], target=3.0)
    print_stat("Average Complexity", audit_data['avg_complexity'], target=40)

    print(f"\n  {datalib.color_line('Functional Coverage:', use_color)}")
    print_stat("Removal Density", audit_data['functional_coverage'].get('Removal', 0), target=10, unit="%")
    print_stat("Card Advantage", audit_data['functional_coverage'].get('Card Advantage', 0), target=8, unit="%")
    print_stat("Mana Fixing", audit_data['fixing_density'], target=5, unit="%")

    if complexity_outliers:
        print(f"\n  {datalib.color_line('Top Complexity Outliers:', use_color)}")
        for c in complexity_outliers:
            print(f"    - {c.display_name} ({c.complexity_score})")

    if breaks:
        issue_label = "[ISSUE]"
        if use_color: issue_label = utils.colorize(issue_label, utils.Ansi.BOLD + utils.Ansi.RED)
        print(f"\n  {datalib.color_line('Color Pie Violations:', use_color)}")
        for b in breaks[:10]:
            print(f"    {issue_label} {b['card']}: {b['reason']}")
        if len(breaks) > 10:
            print(f"    ... and {len(breaks)-10} more.")
    else:
        print(f"\n  {datalib.color_line('Color Pie Integrity: Clear', use_color)}")

    print()

def handle_compare(args):
    # Smart Baseline Detection: if only one file is provided, try to find a standard baseline
    if len(args.infiles) == 1:
        script_dir = os.path.dirname(os.path.realpath(__file__))
        options = [
            os.path.join(script_dir, '../data/AllPrintings.json'),
            'data/AllPrintings.json',
            os.path.join(os.path.dirname(script_dir), 'data/AllPrintings.json'),
            os.path.join(os.path.dirname(os.path.dirname(script_dir)), 'data/AllPrintings.json')
        ]
        for opt in options:
            if os.path.exists(opt) and os.path.abspath(opt) != os.path.abspath(args.infiles[0]):
                args.infiles.insert(0, opt)
                if not args.quiet:
                    print(f"Notice: Comparing against baseline: {opt}", file=sys.stderr)
                break

    def get_stats_for_file(path, args):
        ss = {}
        cs = jdecode.mtg_open_file(path, verbose=args.verbose, linetrans=not getattr(args, 'nolinetrans', False),
                                      fmt_labeled=None if getattr(args, 'nolabel', False) else cardlib.fmt_labeled_default,
                                      grep=args.grep, vgrep=args.vgrep,
                                      grep_name=args.grep_name, vgrep_name=args.exclude_name,
                                      grep_types=args.grep_type, vgrep_types=args.exclude_type,
                                      grep_text=args.grep_text, vgrep_text=args.exclude_text,
                                      grep_cost=args.grep_cost, vgrep_cost=args.exclude_cost,
                                      grep_pt=args.grep_pt, vgrep_pt=args.exclude_pt,
                                      grep_loyalty=args.grep_loyalty, vgrep_loyalty=args.exclude_loyalty,
                                      sets=args.set, rarities=args.rarity,
                                      colors=args.colors, cmcs=args.cmc,
                                      pows=args.pow, tous=args.tou, loys=args.loy,
                                      mechanics=args.mechanic,
                                      identities=args.identity, id_counts=args.id_count,
                                      exclude_sets=lambda x: False,
                                      exclude_types=lambda x: False,
                                      exclude_layouts=lambda x: False,
                                      shuffle=args.shuffle, seed=args.seed,
                                      decklist_file=args.deck,
                                      stats=ss,
                                      booster=args.booster,
                                      box=args.box)
        if args.limit > 0: cs = cs[:args.limit]
        return Datamine(cs, search_stats=ss)

    use_color = args.color if args.color is not None else sys.stdout.isatty()
    mines = []
    for f in args.infiles:
        if args.verbose: print(f"Analyzing {f}...", file=sys.stderr)
        mines.append(get_stats_for_file(f, args))
    if not mines: return
    base_mine = mines[0]; base_data = base_mine.to_dict()
    def clean_fname(path):
        bn = os.path.basename(path)
        for ext in ['.json', '.csv', '.txt', '.mse-set', '.xml', '.jsonl']:
            if bn.lower().endswith(ext):
                bn = bn[:-len(ext)]
                break
        return bn[:15]
    fnames = [clean_fname(f) for f in args.infiles]
    header = ["Metric", fnames[0]]
    for i in range(1, len(fnames)): header.extend([fnames[i], "Delta"])
    if use_color: header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]
    rows = [header]

    def add_metric_row(label, key_path, is_percent=False, reverse_color=False):
        row = [label]
        try:
            val = base_data
            for k in key_path: val = val[k]
            base_val = float(val)
        except: base_val = 0.0
        row.append(f"{base_val:.1f}{'%' if is_percent else ''}")
        for i in range(1, len(mines)):
            data = mines[i].to_dict()
            try:
                val = data
                for k in key_path: val = val[k]
                current_val = float(val)
            except: current_val = 0.0
            row.append(f"{current_val:.1f}{'%' if is_percent else ''}")
            row.append(format_delta(current_val, base_val, is_percent, use_color, reverse_color))
        rows.append(row)

    def add_index_percent_row(label, index_name, key, reverse_color=False):
        row = [label]
        def get_pct(m):
            idx = m.indices.get(index_name, {})
            count = len(idx.get(key, []))
            total = len(m.allcards)
            return (count / total * 100) if total > 0 else 0
        base_pct = get_pct(mines[0]); row.append(f"{base_pct:5.1f}%")
        for i in range(1, len(mines)):
            cp = get_pct(mines[i]); row.append(f"{cp:5.1f}%")
            row.append(format_delta(cp, base_pct, is_percent=True, use_color=use_color, reverse_color=reverse_color))
        rows.append(row)

    def add_sep(title): rows.append([utils.colorize(f"--- {title} ---", utils.Ansi.BOLD+utils.Ansi.CYAN) if use_color else f"--- {title} ---"] + [""]*(len(header)-1))

    add_sep("General")
    row_count = ["Total Cards", str(len(base_mine.allcards))]
    for i in range(1, len(mines)):
        row_count.append(str(len(mines[i].allcards)))
        d = len(mines[i].allcards) - len(base_mine.allcards); ds = f"{d:+d}"
        if use_color: ds = utils.colorize(ds, utils.Ansi.BOLD + (utils.Ansi.CYAN if d != 0 else ""))
        row_count.append(ds)
    rows.append(row_count)
    add_sep("Averages")
    add_metric_row("Avg CMC", ["stats", "avg_cmc"], reverse_color=True)
    add_metric_row("Avg Power", ["stats", "avg_power"])
    add_metric_row("Avg Toughness", ["stats", "avg_toughness"])
    add_metric_row("Avg Rating", ["stats", "avg_power_rating"])
    add_metric_row("Avg Complexity", ["stats", "avg_complexity"], reverse_color=True)
    add_sep("Colors")
    for c in 'WUBRG': add_index_percent_row(f"{c} %", "by_color_inclusive", c, reverse_color=None)
    add_sep("Types")
    for t in ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land"]: add_index_percent_row(f"{t} %", "by_type_inclusive", t.lower(), reverse_color=None)
    utils.print_header("DATASET COMPARISON", use_color=use_color)
    datalib.add_separator_row(rows); datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r']*(len(header)-1)), indent=2)

def main():
    parser = argparse.ArgumentParser(
        description="Unified MTG analysis tool for exploring and auditing Magic card data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Usage Examples:
              # Show general statistics for a dataset
              python3 scripts/mtg_analyze.py summary data/AllPrintings.json

              # Analyze the mana curve of a specific set
              python3 scripts/mtg_analyze.py curve data/AllPrintings.json --set MOM

              # Calculate As-Fan statistics (average cards per pack)
              python3 scripts/mtg_analyze.py asfan generated.txt

              # Analyze mechanical interaction (synergy) in a card pool
              python3 scripts/mtg_analyze.py interaction my_cards.json --min-freq 5

              # Compare the color lexicon of two datasets
              python3 scripts/mtg_analyze.py lexicon data/AllPrintings.json --compare generated.txt

              # Perform a design health check on a card set
              python3 scripts/mtg_analyze.py audit data/AllPrintings.json --set MOM

              # Identify the signature features of Green Rare cards
              python3 scripts/mtg_analyze.py profile data/AllPrintings.json --colors G --rarity rare

              # Find the most combat-efficient creatures in a set
              python3 scripts/mtg_analyze.py power data/AllPrintings.json --set MOM --limit 10
        """)
    )
    subparsers = parser.add_subparsers(dest='command', help='Analysis command to run')

    def add_std(p):
        cli_utils.add_standard_filters(p)
        cli_utils.add_standard_output_args(p)
        p.add_argument('query', nargs='?', help='Search query or input file.')
        p.add_argument('infile', nargs='?', default='-', help='Input card data.')

    # summary
    p_sum = subparsers.add_parser(
        'summary',
        help='Show general statistics and mechanical reports for a dataset.',
        description=textwrap.dedent("""
            Provides a high-level overview of a card dataset. It reports on
            color distribution, card types, rarities, and frequently used
            mechanics. It also identifies unusual "outlier" cards that differ
            significantly from the rest of the data.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_std(p_sum)
    p_sum.add_argument('outfile', nargs='?', default=None, help='Save statistics to a file (JSON or CSV).')
    p_sum.add_argument('-x', '--outliers', action='store_true', help='Show extra details and unusual cards (outliers).')
    p_sum.add_argument('-a', '--all', action='store_true', help='Show all information, including dumping invalid cards.')
    p_sum.add_argument('--top', type=int, default=10, help='Limit the number of entries in breakdown tables (Default: 10).')
    p_sum.add_argument('--sort', choices=['name','color','identity','type','cmc','rarity','power','toughness','loyalty','set','pack','complexity','score'], help='Sort cards before summarizing.')
    p_sum.add_argument('--reverse', action='store_true', help='Reverse the sort order.')
    p_sum.set_defaults(func=handle_summary)

    # curve
    p_cur = subparsers.add_parser('curve', help='Analyze and visualize the mana curve (mana cost distribution).')
    add_std(p_cur)
    p_cur.set_defaults(func=handle_curve)

    # colorpie
    p_cp = subparsers.add_parser('colorpie', help='Generate a Color Pie chart showing which mechanics appear in each color.')
    add_std(p_cp)
    p_cp.add_argument('--compare', '-c', help='Side-by-side comparison with a second dataset.')
    p_cp.set_defaults(func=handle_colorpie)

    # grid
    p_gr = subparsers.add_parser('grid', help='Generate a 2D table to cross-reference card attributes (like color vs. rarity).')
    p_gr.add_argument('row_dim', choices=DIMENSIONS.keys(), help='Dimension to use for rows (e.g., color, rarity, type).')
    p_gr.add_argument('col_dim', choices=DIMENSIONS.keys(), help='Dimension to use for columns (e.g., cmc, mechanic).')
    add_std(p_gr)
    p_gr.set_defaults(func=handle_grid)

    # types
    p_ty = subparsers.add_parser('types', help='Generate a table showing how card types are distributed across colors.')
    add_std(p_ty)
    p_ty.add_argument('--compare', '-c', help='Side-by-side comparison with a second dataset.')
    p_ty.set_defaults(func=handle_types)

    # skeleton
    p_sk = subparsers.add_parser('skeleton', help='Generate a "Design Skeleton" bucketing cards by type and CMC.')
    add_std(p_sk)
    p_sk.add_argument('outfile', nargs='?', default=None, help='Save the skeleton to a file.')
    p_sk.set_defaults(func=handle_skeleton)

    # mana
    p_ma = subparsers.add_parser('mana', help='Identify and profile mana-producing cards.')
    add_std(p_ma)
    p_ma.add_argument('--compare', '-c', help='Side-by-side comparison with a second dataset.')
    p_ma.set_defaults(func=handle_mana)

    # pips
    p_pi = subparsers.add_parser('pips', help='Analyze the distribution of mana symbols (pips).')
    add_std(p_pi)
    p_pi.add_argument('outfile', nargs='?', default=None, help='Save pip distribution to a file.')
    p_pi.add_argument('--include-text', action='store_true', help='Include mana symbols found in rules text (e.g., activation costs).')
    p_pi.add_argument('--sort', choices=['name','count'], default='count', help='Sort results by symbol name or frequency.')
    p_pi.add_argument('--reverse', action='store_true', help='Reverse the sort order.')
    p_pi.set_defaults(func=handle_pips)

    # costs
    p_co = subparsers.add_parser('costs', help='Analyze how many colored mana symbols cards require relative to their total cost.')
    add_std(p_co)
    p_co.add_argument('outfile', nargs='?', default=None, help='Save cost analysis to a file.')
    p_co.set_defaults(func=handle_costs)

    # mechanics
    p_me = subparsers.add_parser('mechanics', help='List recognized mechanics and calculate their frequency.')
    add_std(p_me)
    p_me.add_argument('--compare', '-c', help='Compare frequencies with a second dataset.')
    p_me.add_argument('--sort', choices=['name','count'], default='name', help='Sort mechanics by name or count.')
    p_me.add_argument('--reverse', action='store_true', help='Reverse the sort order.')
    p_me.add_argument('--top', type=int, default=0, help='Limit the number of mechanics shown.')
    p_me.set_defaults(func=handle_mechanics)

    # interaction
    p_sy = subparsers.add_parser(
        'interaction',
        aliases=['synergy'],
        help='Analyze how often different mechanics appear together.',
        description=textwrap.dedent("""
            Analyzes how different mechanics (like Flying and Trample) appear together
            on the same cards. It identifies frequent pairings and calculates a
            'Lift Score' to measure how often they appear together compared to
            what would happen by random chance.

            The Lift Score shows the relationship between two mechanics:
            - Score > 1.0: The mechanics appear together MORE often than expected.
            - Score = 1.0: The mechanics appear together exactly as often as expected.
            - Score < 1.0: The mechanics appear together LESS often than expected.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_std(p_sy)
    p_sy.add_argument('--min-freq', type=int, default=2, help='Minimum co-occurrences required to report a pair (Default: 2).')
    p_sy.add_argument('--top', type=int, default=20, help='Show the top N pairings (Default: 20).')
    p_sy.set_defaults(func=handle_interaction)

    # actions
    p_ac = subparsers.add_parser(
        'actions',
        help='Analyze and categorize functional card effects (Removal, Buffs, etc).',
        description=textwrap.dedent("""
            Analyzes and categorizes functional card effects like Removal,
            Protection, Buffs, Card Advantage, Disruption, and Mana. This
            tool identifies how cards interact with the game state, providing
            a profile of a set's interactivity.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_std(p_ac)
    p_ac.add_argument('outfile', nargs='?', default=None, help='Save action analysis to a file.')
    p_ac.set_defaults(func=handle_actions)

    # lexicon
    p_le = subparsers.add_parser(
        'lexicon',
        help='Identify words that are used more often in specific colors.',
        description=textwrap.dedent("""
            Identifies "signature words" for each Magic color by comparing how often
            words appear in one color versus all others. This helps identify the
            thematic language used for each part of the color pie.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_std(p_le)
    p_le.add_argument('--compare', '-c', help='Side-by-side comparison with a second dataset.')
    p_le.add_argument('--top', type=int, default=10, help='Number of signature words to show per color (Default: 10).')
    p_le.add_argument('--min-len', type=int, default=4, help='Minimum word length to include in analysis (Default: 4).')
    p_le.set_defaults(func=handle_lexicon)

    # stats
    p_st = subparsers.add_parser('stats', help='Analyze creature combat stats (P/T) and Planeswalker loyalty.')
    add_std(p_st)
    p_st.add_argument('outfile', nargs='?', default=None, help='Save combat stats to a file.')
    p_st.set_defaults(func=handle_stats)

    # power
    p_po = subparsers.add_parser(
        'power',
        help='Analyze creature combat efficiency relative to mana cost.',
        description=textwrap.dedent("""
            Analyzes the creature power balance in a dataset. It calculates a
            'Power Rating' relative to mana cost to identify cards that are
            significantly above or below the expected combat strength for their cost.

            A rating of 1.0 represents a basic 2/2 creature with no abilities for
            2 mana. Keywords like Flying or Indestructible increase the rating.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_std(p_po)
    p_po.add_argument('outfile', nargs='?', default=None, help='Save power analysis to a file.')
    p_po.set_defaults(func=handle_power)

    # archetypes
    p_ar = subparsers.add_parser(
        'archetypes',
        help='Profile the themes and key mechanics of the ten primary two-color pairs.',
        description=textwrap.dedent("""
            Analyzes the ten primary two-color combinations (archetypes) in a dataset.
            It identifies the most important cards, signature mechanics, and
            average stats for each color pair to help you understand the themes
            of a set.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_std(p_ar)
    p_ar.add_argument('outfile', nargs='?', default=None, help='Save archetype analysis to a file.')
    p_ar.add_argument('--min-cards', type=int, default=5, help='Minimum number of cards required to profile an archetype (Default: 5).')
    p_ar.add_argument('--top-mechanics', type=int, default=3, help='Number of signature mechanics to show per archetype (Default: 3).')
    p_ar.set_defaults(func=handle_archetypes)

    # balance
    p_ba = subparsers.add_parser(
        'balance',
        help='Compare how color pairs are distributed between datasets.',
        description=textwrap.dedent("""
            Analyzes and compares the distribution of two-color pairs (archetypes)
            between different datasets. This helps you verify if a generated or
            custom set maintains the same color balance as the original official
            data.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p_ba.add_argument('infiles', nargs='*', help='One or more card data files to compare.')
    p_ba.add_argument('--set', action='append', help='Filter inputs by set code.')
    p_ba.add_argument('--rarity', action='append', help='Filter inputs by rarity.')
    p_ba.add_argument('--limit', type=int, default=0, help='Only process the first N cards from each input.')
    p_ba.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    p_ba.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')
    c_grp = p_ba.add_mutually_exclusive_group()
    c_grp.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    c_grp.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')
    p_ba.set_defaults(func=handle_balance)

    # asfan
    p_as = subparsers.add_parser(
        'asfan',
        help='Calculate "As-Fan" (average cards per pack) statistics.',
        description=textwrap.dedent("""
            Calculates "As-Fan" (As-fanned) statistics for a card dataset.
            As-Fan represents the average number of cards with a certain
            characteristic (like a specific color, type, or mechanic) a player
            can expect to see in a single 15-card booster pack.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_std(p_as)
    p_as.add_argument('--compare', '-c', help='Side-by-side comparison with a second dataset.')
    p_as.add_argument('outfile', nargs='?', default=None, help='Save As-Fan stats to a file.')
    p_as.set_defaults(func=handle_asfan)

    # tokens
    p_to = subparsers.add_parser('tokens', help='Extract and summarize token definitions from rules text.')
    add_std(p_to)
    p_to.set_defaults(func=handle_tokens)

    # subtypes
    p_sub = subparsers.add_parser('subtypes', help='Analyze the distribution of card subtypes.')
    add_std(p_sub)
    p_sub.add_argument('outfile', nargs='?', default=None, help='Save subtype analysis to a file.')
    p_sub.add_argument('--top', type=int, default=10, help='Number of entries to show in tables (Default: 10).')
    p_sub.set_defaults(func=handle_subtypes)

    # profile
    p_prof = subparsers.add_parser(
        'profile',
        help='Identify the "Mechanical Identity" (signature features) of a card subset.',
        description=textwrap.dedent("""
            Identifies the defining characteristics of a card subset by comparing
            it against a global baseline. It highlights "signature features"
            (mechanics, actions, or subtypes) that appear significantly more
            often in your selected cards than in the rest of the dataset.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_std(p_prof)
    p_prof.add_argument('--top', type=int, default=10, help='Number of signature features to show per category (Default: 10).')
    p_prof.set_defaults(func=handle_profile)

    # audit
    p_audit = subparsers.add_parser(
        'audit',
        help='Perform a comprehensive design health check of a card dataset.',
        description=textwrap.dedent("""
            Performs a design "Health Check" for card datasets. It reports on
            core metrics like creature density and average complexity, evaluates
            functional coverage (removal, card advantage, mana fixing), and
            identifies potential color pie violations.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_std(p_audit)
    p_audit.set_defaults(func=handle_audit)

    # compare
    p_comp = subparsers.add_parser('compare', help='Provide a side-by-side statistical comparison of two or more datasets.')
    p_comp.add_argument('infiles', nargs='+', help='Two or more card data files to compare.')
    add_std(p_comp)
    p_comp.set_defaults(func=handle_compare)

    args = parser.parse_args()
    if not args.command: parser.print_help(); return
    
    # Smart Positional Argument Handling
    if hasattr(args, 'query') and args.query == '-':
        args.query = None

    if hasattr(args, 'query') and args.query:
        if hasattr(args, 'outfile') and getattr(args, 'outfile', None) is None and getattr(args, 'infile', None) not in (None, '-'):
            q_exists = os.path.exists(args.query)
            i_exists = os.path.exists(args.infile)
            if q_exists and not i_exists:
                args.outfile = args.infile
                args.infile = args.query
                args.query = None
            elif not q_exists and i_exists:
                if not getattr(args, 'grep', None): args.grep = [args.query]
                else: args.grep.append(args.query)
                args.query = None
            elif not q_exists and not i_exists:
                args.outfile = args.infile
                args.infile = args.query
                args.query = None
        elif os.path.exists(args.query) and (getattr(args, 'infile', None) == '-' or (hasattr(args, 'infile') and not os.path.exists(args.infile))):
            # Swap if first arg is a file and second isn't
            temp = args.query
            args.query = args.infile if args.infile != '-' else None
            args.infile = temp
        elif not os.path.exists(args.query) and getattr(args, 'infile', None) == '-':
            # If first arg doesn't exist and second is default, treat first as query
            if not getattr(args, 'grep', None): args.grep = [args.query]
            else: args.grep.append(args.query)
            args.query = None
    
    if hasattr(args, 'query') and args.query:
        if not getattr(args, 'grep', None): args.grep = [args.query]
        else: args.grep.append(args.query)

    if hasattr(args, 'infile') and args.infile == '-' and sys.stdin.isatty():
        df = 'data/AllPrintings.json'
        if os.path.exists(df): args.infile = df
    if hasattr(args, 'sample') and args.sample > 0: args.shuffle = True; args.limit = args.sample
    args.func(args)

if __name__ == "__main__": main()
