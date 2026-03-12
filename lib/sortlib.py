try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm is not installed
    def tqdm(iterable, **kwargs):
        return iterable

import re
import cardlib
import utils

def sort_colors(card_set, quiet=False):
    """Sorts cards by their color identity."""
    colors = {
        'W': [], 'U': [], 'B': [], 'R': [], 'G': [],
        'multi': [], 'colorless': [], 'lands': []
    }

    # Wrap in tqdm if not quiet
    iterator = tqdm(card_set, disable=quiet, desc="Sorting")
    for card in iterator:
        card_colors = card.cost.colors
        if len(card_colors) > 1:
            colors['multi'].append(card)
        elif len(card_colors) == 1:
            colors[card_colors[0]].append(card)
        else:
            if "land" in [t.lower() for t in card.types]:
                colors['lands'].append(card)
            else:
                colors['colorless'].append(card)

    return [colors['W'], colors['U'], colors['B'], colors['R'], colors['G'],
            colors['multi'], colors['colorless'], colors['lands']]

def sort_type(card_set):
    """Sorts cards by their primary card type."""
    # Priority order for primary card types.
    # We maintain the order expected by existing tests for backward compatibility.
    sorting = ["creature", "enchantment", "instant", "sorcery", "artifact", "planeswalker", "battle", "land"]

    def type_priority(card):
        # Convert card types to lowercase for case-insensitive comparison
        card_types_lower = [t.lower() for t in card.types]
        for i, card_type in enumerate(sorting):
            if card_type in card_types_lower:
                return i
        return len(sorting)

    # Use stable sort (Python's sorted is stable)
    return sorted(card_set, key=type_priority)

def _get_numeric_sort_key(val):
    """Helper to generate a sort key for optional numeric fields (P/T, Loyalty)."""
    if val is None or val == '':
        return (1, 0)
    num = utils.from_unary_single(val)
    return (0, -num) if num is not None else (1, 0)

def sort_cards(cards, criterion, quiet=False):
    """Sorts a list of cards based on the specified criterion."""
    if not criterion:
        return cards

    if criterion == 'name':
        return sorted(cards, key=lambda c: c.name.lower())
    elif criterion == 'cmc':
        return sorted(cards, key=lambda c: c.cost.cmc)
    elif criterion == 'color':
        # Flatten the list of lists returned by sort_colors
        segments = sort_colors(cards, quiet=quiet)
        return [card for segment in segments for card in segment]
    elif criterion == 'type':
        return sort_type(cards)
    elif criterion == 'rarity':
        # Priority: Mythic > Rare > Uncommon > Common > Basic Land > Special > Other
        # Markers: Y (Mythic), A (Rare), N (Uncommon), O (Common), L (Basic Land), I (Special)
        rarity_priority = {
            utils.rarity_mythic_marker: 0, 'MYTHIC': 0, 'MYTHIC RARE': 0,
            utils.rarity_rare_marker: 1, 'RARE': 1,
            utils.rarity_uncommon_marker: 2, 'UNCOMMON': 2,
            utils.rarity_common_marker: 3, 'COMMON': 3,
            utils.rarity_basic_land_marker: 4, 'BASIC LAND': 4,
            utils.rarity_special_marker: 5, 'SPECIAL': 5,
        }
        def get_rarity_val(card):
            r = card.rarity.upper() if card.rarity else ''
            return rarity_priority.get(r, 6)
        return sorted(cards, key=get_rarity_val)
    elif criterion == 'power':
        return sorted(cards, key=lambda c: _get_numeric_sort_key(c.pt_p))
    elif criterion == 'toughness':
        return sorted(cards, key=lambda c: _get_numeric_sort_key(c.pt_t))
    elif criterion == 'loyalty':
        return sorted(cards, key=lambda c: _get_numeric_sort_key(c.loyalty))
    elif criterion == 'set':
        def get_set_key(card):
            s = card.set_code.upper() if card.set_code else 'ZZZ'
            n = card.number if card.number else '9999'
            # Try to extract the numeric part for logical sorting of collector numbers
            try:
                n_int = int(re.sub(r'\D', '', n))
            except (ValueError, TypeError):
                n_int = 9999
            return (s, n_int, n)
        return sorted(cards, key=get_set_key)
    else:
        return cards
