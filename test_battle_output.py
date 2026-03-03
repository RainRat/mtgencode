from lib import utils
from lib import cardlib

jcard = {
    "name": "Invasion of Alara",
    "manaCost": "{W}{U}{B}{R}{G}",
    "types": ["Battle"],
    "subtypes": ["Siege"],
    "text": "When Invasion of Alara enters the battlefield, exile the top five cards of your library. You may cast a nonland card with mana value 4 or less from among them without paying its mana cost. Put the rest on the bottom of your library in a random order.",
    "defense": "7",
    "rarity": "Rare"
}

card = cardlib.Card(jcard)
print("Summary:")
print(card.summary())
print("\nFormat:")
print(card.format())
print("\nVectorize:")
print(card.vectorize())
