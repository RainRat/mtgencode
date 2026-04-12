
import utils
from cardlib import Card

def get_col_widths(rows):
    """
    Returns a list of maximum visible lengths for each column in the provided rows.
    Accounts for newlines by taking the maximum width of any single line in a cell.
    """
    if not rows:
        return []

    col_widths = []
    for row in rows:
        for i, cell in enumerate(row):
            lines = str(cell).split('\n')
            max_line_len = max(utils.visible_len(line) for line in lines)
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], max_line_len)
            else:
                col_widths.append(max_line_len)
    return col_widths

def add_separator_row(rows, index=1):
    """
    Calculates column widths for the provided rows and inserts a separator
    row of dashes at the specified index.
    """
    if not rows:
        return
    col_widths = get_col_widths(rows)
    separator = ['-' * w for w in col_widths]
    rows.insert(index, separator)

# Format a list of rows of data into nice columns.
# Note that it's the columns that are nice, not this code.
def padrows(rows, aligns=None):
    """
    Formats a list of data rows into aligned columns.
    Supports multi-line cells and ensures proper alignment across columns.
    """
    if not rows:
        return []

    col_widths = get_col_widths(rows)
    padded_output_rows = []

    for row in rows:
        # Split each cell into lines
        cell_lines = [str(cell).split('\n') for cell in row]
        # Determine the maximum number of lines in this row
        max_lines = max(len(lines) for lines in cell_lines) if cell_lines else 0

        # We will generate one or more terminal output lines for this logical row
        for line_idx in range(max_lines):
            padded_cells = []
            for i, lines in enumerate(cell_lines):
                # Get the current line for this cell, or empty string if it's shorter than max_lines
                s = lines[line_idx] if line_idx < len(lines) else ""
                vis_len = utils.visible_len(s)
                diff = col_widths[i] - vis_len

                align = aligns[i] if (aligns and i < len(aligns)) else 'l'
                if align == 'r':
                    cell_str = (' ' * diff) + s
                elif align == 'c':
                    left = diff // 2
                    right = diff - left
                    cell_str = (' ' * left) + s + (' ' * right)
                else: # 'l'
                    cell_str = s + (' ' * diff)

                padded_cells.append(cell_str)

            # Join cells with 2 spaces and add to output
            padded_output_rows.append('  '.join(padded_cells).rstrip())

    return padded_output_rows
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
def plimit(s, mlen=1000):
    vlen = utils.visible_len(s)
    raw_len = len(s)

    if raw_len == vlen:
        if raw_len > mlen:
            return s[:mlen] + '[...]'
        return s

    if vlen <= mlen:
        return s

    res = ""
    visible_count = 0
    last_idx = 0
    ansi_encountered = False

    for match in utils._ansi_escape_re.finditer(s):
        pre_text = s[last_idx:match.start()]
        if visible_count + len(pre_text) > mlen:
            res += pre_text[:mlen - visible_count]
            return res + '[...]' + (utils.Ansi.RESET if ansi_encountered else "")

        res += pre_text
        visible_count += len(pre_text)

        res += match.group()
        ansi_encountered = True
        last_idx = match.end()

    remaining = s[last_idx:]
    if visible_count + len(remaining) > mlen:
        res += remaining[:mlen - visible_count]
        return res + '[...]' + (utils.Ansi.RESET if ansi_encountered else "")

    res += remaining
    return res

def color_count(count, use_color, color_code=utils.Ansi.BOLD + utils.Ansi.GREEN):
    s = str(count)
    if use_color and count > 0:
        return utils.colorize(s, color_code)
    return s

def color_line(text, use_color, color_code=utils.Ansi.BOLD + utils.Ansi.CYAN):
    if use_color:
        return utils.colorize(text, color_code)
    return text

def _colorize_header(header, use_color):
    if use_color:
        return [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]
    return header

def get_bar_chart(percent, use_color, color=None):
    bar_width = 10
    filled = int(round(percent / 100 * bar_width))
    if filled == 0 and percent > 0:
        filled = 1
    bar = '[' + '█' * filled + ' ' * (bar_width - filled) + ']'
    if use_color:
        bar_color = color if color else (utils.Ansi.BOLD + utils.Ansi.GREEN)
        bar = utils.colorize(bar, bar_color)
    return bar

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

    # Determine a context-aware header for the first column
    cat_header = 'Category'
    t_lower = title.lower()
    if 'color' in t_lower:
        cat_header = 'Colors' if 'number' in t_lower else 'Color'
    elif 'cmc' in t_lower:
        cat_header = 'CMC'
    elif 'mana costs' in t_lower:
        cat_header = 'Cost'
    elif 'subtype' in t_lower:
        cat_header = 'Subtype'
    elif 'supertype' in t_lower:
        cat_header = 'Supertype'
    elif 'type' in t_lower:
        cat_header = 'Type'
    elif 'combination' in t_lower:
        cat_header = 'Combination'
    elif 'rarity' in t_lower:
        cat_header = 'Rarity'
    elif 'identity' in t_lower:
        cat_header = 'Identity'
    elif 'p/t' in t_lower:
        cat_header = 'P/T'
    elif 'loyalty' in t_lower:
        cat_header = 'Loyalty'
    elif 'line count' in t_lower:
        cat_header = 'Lines'
    elif 'mechanic' in t_lower:
        cat_header = 'Mechanic'

    header_row = _colorize_header([cat_header, 'Count', 'Percent', 'Distribution'], use_color)

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
            elif ('color' in title.lower() or 'identity' in title.lower()) and 'number' not in title.lower() and 'count' not in title.lower():
                display_color = utils.Ansi.get_color_color(k)
                display_key = utils.colorize(display_key, display_color)
            elif 'mana costs' in title.lower():
                display_key = utils.from_mana(k, ansi_color=True)
            elif 'p/t' in title.lower() or 'loyalty' in title.lower():
                display_color = utils.Ansi.RED
                display_key = utils.colorize(display_key, display_color)

        # Bar chart
        bar = get_bar_chart(percent, use_color, color=display_color)

        rows.append([
            display_key,
            color_count(count, use_color),
            f"{percent:5.1f}%",
            bar
        ])

    # Insert a separator row of dashes
    add_separator_row(rows)

    printrows(padrows(rows, aligns=['l', 'r', 'r', 'l']), indent=4)

def _print_mechanical_profile(mechanical_stats, total, use_color, vsize=None):
    if not mechanical_stats:
        return
    print()
    print('  ' + color_line('Mechanical Profile (Frequency & Budget):', use_color))

    header = _colorize_header(['Mechanic', 'Count', 'Percent', 'Distribution', 'CMC', 'P/T'], use_color)

    rows = [header]
    # Sort by frequency
    sorted_mechanics = sorted(mechanical_stats.keys(), key=lambda m: mechanical_stats[m]['count'], reverse=True)
    if vsize:
        sorted_mechanics = sorted_mechanics[:vsize]

    for m in sorted_mechanics:
        stats = mechanical_stats[m]
        count = stats['count']
        percent = (count / total * 100) if total > 0 else 0
        bar = get_bar_chart(percent, use_color)

        pt_str = "-"
        if stats['avg_power'] is not None and stats['avg_toughness'] is not None:
            pt_str = f"{stats['avg_power']:.1f}/{stats['avg_toughness']:.1f}"
        elif stats['avg_power'] is not None:
             pt_str = f"{stats['avg_power']:.1f}/?"
        elif stats['avg_toughness'] is not None:
             pt_str = f"?/{stats['avg_toughness']:.1f}"

        row = [
            m,
            color_count(count, use_color),
            f"{percent:5.1f}%",
            bar,
            f"{stats['avg_cmc']:.2f}",
            pt_str
        ]

        if use_color:
            row[5] = utils.colorize(row[5], utils.Ansi.RED) if pt_str != "-" else row[5]

        rows.append(row)

    # Insert a separator row of dashes
    add_separator_row(rows)

    printrows(padrows(rows, aligns=['l', 'r', 'r', 'l', 'r', 'r']), indent=4)

def _print_color_pie(pie_groups, pie_mechanics, all_mechanics, use_color, vsize=None):
    if not all_mechanics:
        return
    print()
    print('  ' + color_line('Mechanical Color Pie (Frequency %):', use_color))

    header = _colorize_header(['Mechanic', 'W', 'U', 'B', 'R', 'G', 'A', 'M'], use_color)

    rows = [header]
    # Sort mechanics by total frequency
    sorted_mechanics = sorted(all_mechanics.keys(), key=lambda m: len(all_mechanics[m]), reverse=True)
    if vsize:
        sorted_mechanics = sorted_mechanics[:vsize]

    for m in sorted_mechanics:
        row = [m]
        percents = []
        for group in 'WUBRGAM':
            total = pie_groups[group]
            count = pie_mechanics[group].get(m, 0)
            percents.append((count / total * 100) if total > 0 else 0)

        max_p = max(percents) if percents else 0

        for i, group in enumerate('WUBRGAM'):
            percent = percents[i]
            if percent > 0:
                val_str = f"{percent:4.0f}%"
                if use_color:
                    color = utils.Ansi.get_color_color(group)
                    if percent == max_p and max_p > 0:
                        # Highlight dominant color with underline
                        # Only colorize the non-space part to avoid underlined leading spaces
                        non_space = val_str.lstrip()
                        spaces = val_str[:len(val_str)-len(non_space)]
                        val = spaces + utils.colorize(non_space, color + utils.Ansi.UNDERLINE)
                    else:
                        val = utils.colorize(val_str, color)
                else:
                    val = val_str
            else:
                val = "  - "
            row.append(val)
        rows.append(row)

    # Insert a separator row of dashes
    add_separator_row(rows)

    printrows(padrows(rows, aligns=['l', 'r', 'r', 'r', 'r', 'r', 'r', 'r']), indent=4)

class Datamine:
    # build the global indices
    def __init__(self, cards_input, search_stats=None):
        # global card pools
        self.search_stats = search_stats
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
        self.by_identity = {}
        self.by_identity_inclusive = {}
        self.by_identity_count = {}
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
            'by_identity' : self.by_identity,
            'by_identity_inclusive' : self.by_identity_inclusive,
            'by_identity_count' : self.by_identity_count,
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

                # Color Identity indexing
                identity = card.color_identity
                if identity:
                    inc(self.by_identity, identity, [card])
                    for c in identity:
                        inc(self.by_identity_inclusive, c, [card])
                    inc(self.by_identity_count, len(identity), [card])
                else:
                    inc(self.by_identity, 'A', [card])
                    inc(self.by_identity_inclusive, 'A', [card])
                    inc(self.by_identity_count, 0, [card])

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
        p_vals = [v for v in map(utils.from_unary_single, (c.pt_p for c in self.cards)) if v is not None]
        t_vals = [v for v in map(utils.from_unary_single, (c.pt_t for c in self.cards)) if v is not None]
        self.avg_power = sum(p_vals) / len(p_vals) if p_vals else 0
        self.avg_toughness = sum(t_vals) / len(t_vals) if t_vals else 0

        # Calculate Design Budget / Mechanical Statistics
        self.mechanical_stats = {}
        for m, m_cards in self.by_mechanic.items():
            m_p_vals = [v for v in map(utils.from_unary_single, (c.pt_p for c in m_cards)) if v is not None]
            m_t_vals = [v for v in map(utils.from_unary_single, (c.pt_t for c in m_cards)) if v is not None]
            self.mechanical_stats[m] = {
                'count': len(m_cards),
                'avg_cmc': sum(c.cost.cmc for c in m_cards) / len(m_cards),
                'avg_power': sum(m_p_vals) / len(m_p_vals) if m_p_vals else None,
                'avg_toughness': sum(m_t_vals) / len(m_t_vals) if m_t_vals else None
            }

    # summarize the indices
    def summarize(self, hsize = 10, vsize = 10, cmcsize = 20, use_color = False):

        if self.search_stats:
            print(color_line('SEARCH STATISTICS', use_color, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE))

            total = self.search_stats.get('matched', 0) + self.search_stats.get('filtered', 0)
            matched = self.search_stats.get('matched', 0)
            filtered = self.search_stats.get('filtered', 0)

            rows = []

            for label, count in [('Matched', matched), ('Filtered Out', filtered)]:
                percent = (count / total * 100) if total > 0 else 0
                color = (utils.Ansi.BOLD + utils.Ansi.GREEN if label == 'Matched'
                         else utils.Ansi.BOLD + utils.Ansi.RED)
                bar = get_bar_chart(percent, use_color, color=color)

                rows.append([
                    label,
                    color_count(count, use_color),
                    f"{percent:5.1f}%",
                    bar
                ])

            printrows(padrows(rows, aligns=['l', 'r', 'r', 'l']), indent=4)
            print()

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
        _print_breakdown('Breakdown by color:', self.by_color_inclusive, len(self.allcards), use_color, vsize=vsize)
        _print_breakdown('Breakdown by number of colors:', self.by_color_count, len(self.allcards), use_color, vsize=vsize)
        print()

        print('  ' + color_line(str(len(self.by_identity_inclusive)) + ' represented identity colors, '
               + str(len(self.by_identity)) + ' identity combinations', use_color))
        _print_breakdown('Breakdown by color identity:', self.by_identity, len(self.allcards), use_color, vsize=vsize)
        _print_breakdown('Breakdown by identity count:', self.by_identity_count, len(self.allcards), use_color, vsize=vsize)
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
        rarity_priorities = {
            'mythic': 0, 'rare': 1, 'uncommon': 2, 'common': 3,
            'basic land': 4, 'special': 5
        }
        _print_breakdown('Breakdown by rarity:', self.by_rarity, len(self.allcards), use_color,
                         vsize=vsize, sort_key=lambda x: rarity_priorities.get(x.lower(), 6), reverse=False)
        print()

        print('  ' + color_line(str(len(self.by_pt)) + ' unique p/t combinations', use_color))
        if len(self.by_power) > 0 and len(self.by_toughness) > 0:
            p_max_vals = [v for v in map(utils.from_unary_single, self.by_power) if v is not None]
            t_max_vals = [v for v in map(utils.from_unary_single, self.by_toughness) if v is not None]
            print('  ' + ('Largest power: ' + str(max(p_max_vals) if p_max_vals else 0) +
                   ', largest toughness: ' + str(max(t_max_vals) if t_max_vals else 0)))
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
        _print_mechanical_profile(self.mechanical_stats, len(self.allcards), use_color, vsize=vsize)
        _print_color_pie(self.pie_groups, self.pie_mechanics, self.by_mechanic, use_color, vsize=vsize)
        print()

    # describe outliers in the indices
    def outliers(self, hsize=10, vsize=10, dump_invalid=False, use_color = False):

        print(color_line('OUTLIER ANALYSIS', use_color, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE))
        print('  ' + color_line('Overview of indices:', use_color))

        header_row = _colorize_header(['  Index Name', 'Keys', 'Total Members'], use_color)

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
            for k in d:
                if len(self.by_name[k]) > 1:
                    rows += [[k, color_count(len(self.by_name[k]), use_color)]]
                if len(rows) >= vsize:
                    break
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
                            key=lambda x: utils.from_unary_single(x) or 0,
                            reverse=True)[0]
            print('  ' + color_line('Largest creature power: ' + utils.from_unary(lpower), use_color))
            print('\n    ' + plimit(self.by_power[lpower][0].encode()).replace('\n', '\n    ') + '\n')
        else:
            print('  No cards indexed by power?')
        if len(self.by_toughness) > 0:
            ltoughness = sorted(self.by_toughness,
                                key=lambda x: utils.from_unary_single(x) or 0,
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
            'search_stats': self.search_stats,
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

        result['mechanical_stats'] = self.mechanical_stats

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
