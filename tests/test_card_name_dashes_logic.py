import sys
import os
libdir = os.path.join(os.getcwd(), 'lib')
sys.path.append(libdir)
import cardlib
import utils
import transforms

def test_card_name_dashes_logic():
    # Card with a dash in its name
    # Internal representation uses '~' for dash
    card_json = {
        "name": "Hate-Twisted",
        "manaCost": "{1}{B}",
        "types": ["Enchantment"],
        "text": "Whenever Hate-Twisted enters, it deals 2 damage.",
        "rarity": "Rare"
    }
    card = cardlib.Card(card_json)

    # Internal name should be lowercase with dash marker
    assert card.name == "hate~twisted"

    # Rules text should have Hate-Twisted correctly capitalized
    # Test with force_unpass=True
    text = card.get_text(force_unpass=True)
    assert "Hate-Twisted" in text
    assert "Hate~twisted" not in text
    assert "hate~twisted" not in text

    # Test with gatherer=True
    text_gatherer = card.get_text(gatherer=True)
    assert "Hate-Twisted" in text_gatherer
    assert "Hate~twisted" not in text_gatherer

    # Test with mse=True
    text_mse = card.get_text(mse=True)
    assert "Hate-Twisted" in text_mse
    assert "Hate~twisted" not in text_mse

    print("Tests passed: Hate-Twisted correctly capitalized in rules text.")

if __name__ == "__main__":
    test_card_name_dashes_logic()
