try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm is not installed
    def tqdm(iterable, **kwargs):
        return iterable

import cardlib

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
            if "land" in card.types:
                colors['lands'].append(card)
            else:
                colors['colorless'].append(card)

    return [colors['W'], colors['U'], colors['B'], colors['R'], colors['G'],
            colors['multi'], colors['colorless'], colors['lands']]

def sort_type(card_set):
    """Sorts cards by their primary card type."""
    sorting = ["creature", "enchantment", "instant", "sorcery", "artifact", "planeswalker"]

    def type_priority(card):
        for i, card_type in enumerate(sorting):
            if card_type in card.types:
                return i
        return len(sorting)

    return sorted(card_set, key=type_priority)

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
    else:
        return cards
