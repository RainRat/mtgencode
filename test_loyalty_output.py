from lib import utils
from lib import cardlib

jcard = {
    "name": "Jace",
    "manaCost": "{1}{U}{U}",
    "types": ["Planeswalker"],
    "subtypes": ["Jace"],
    "text": "+1: Draw a card.\n-2: Target player mills three cards.",
    "loyalty": "3",
    "rarity": "Mythic"
}

card = cardlib.Card(jcard)
print("Summary:")
print(card.summary())
print("\nFormat:")
print(card.format())
