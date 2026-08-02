import unittest
from unittest.mock import patch
import sys
import os
import json
import io

# Add lib and scripts directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
scriptsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../scripts')
sys.path.append(libdir)
sys.path.append(scriptsdir)

from scripts.mtg_forge import main, apply_replacement, adjust_mana_cost, apply_text_replacements, apply_mana_adjust

class TestMtgForgeModifiersEnhanced(unittest.TestCase):

    def test_apply_replacement_simple(self):
        # Substring replacement (old->new)
        text = "When @ enters the battlefield, draw a card."
        res = apply_replacement(text, "draw->discard")
        self.assertEqual(res, "When @ enters the battlefield, discard a card.")

    def test_apply_replacement_sed_regex(self):
        # sed-like pattern (s/pattern/replacement/flags)
        text = "When @ enters the battlefield, draw a card. Draw two cards."
        # No 'g' flag -> only replace first match
        res1 = apply_replacement(text, "s/draw/discard/")
        self.assertEqual(res1, "When @ enters the battlefield, discard a card. Draw two cards.")

        # With 'g' and 'i' (ignorecase) flags
        res2 = apply_replacement(text, "s/draw/discard/gi")
        self.assertEqual(res2, "When @ enters the battlefield, discard a card. discard two cards.")

    def test_adjust_mana_cost(self):
        # Test adjustment with existing generic mana
        self.assertEqual(adjust_mana_cost("{2}{U}{R}", 2), "{4}{U}{R}")
        self.assertEqual(adjust_mana_cost("{2}{U}{R}", -2), "{U}{R}")
        self.assertEqual(adjust_mana_cost("{2}{U}{R}", -5), "{U}{R}") # shouldn't go below 0

        # Test adjustment with no existing generic mana
        self.assertEqual(adjust_mana_cost("{G}{W}", 1), "{1}{G}{W}")
        self.assertEqual(adjust_mana_cost("{G}{W}", -1), "{G}{W}")

        # Test adjustment on empty mana cost
        self.assertEqual(adjust_mana_cost("", 3), "{3}")
        self.assertEqual(adjust_mana_cost("", -3), "")

    def test_apply_text_replacements_and_bside(self):
        card = {
            'name': 'Grizzly Bears',
            'type': 'Creature - Bear',
            'text': 'A simple bear.',
            'bside': {
                'name': 'Bside Bear',
                'type': 'Creature - Bear Spirit',
                'text': 'A spectral bear.'
            }
        }

        # Mock args
        class Args:
            replace_name = "Bear->Beast"
            replace_type = "s/Creature - (\\w+)/Creature - \\1 Spirit/g"
            replace = "simple->mighty"

        res = apply_text_replacements(card, Args())

        # Verify front
        self.assertEqual(res['name'], 'Grizzly Beasts')
        self.assertEqual(res['type'], 'Creature - Bear Spirit')
        self.assertEqual(res['text'], 'A mighty bear.')

        # Verify B-side recursive behavior
        self.assertEqual(res['bside']['name'], 'Bside Beast')
        self.assertEqual(res['bside']['type'], 'Creature - Bear Spirit Spirit') # since \1 was Bear, and we replaced regex with Bear Spirit Spirit
        self.assertEqual(res['bside']['text'], 'A spectral bear.')

    def test_apply_mana_adjust_and_bside(self):
        card = {
            'manaCost': '{2}{G}',
            'bside': {
                'manaCost': '{1}{R}'
            }
        }
        res = apply_mana_adjust(card, 2)
        self.assertEqual(res['manaCost'], '{4}{G}')
        self.assertEqual(res['bside']['manaCost'], '{3}{R}')

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_cli_integration_replace_and_mana_adjust(self, mock_stdout):
        test_args = [
            'mtg_forge.py',
            '--name', 'Jules, Chrono-Mage',
            '--type', 'Legendary Creature - Wizard',
            '--cost', '{1}{U}{R}',
            '--text', 'T: Draw a card.',
            '--replace-name', 'Chrono->Temporal',
            '--replace-type', 'Wizard->Human Wizard',
            '--replace', 'Draw->Discard',
            '--mana-adjust', '3'
        ]
        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Jules, Temporal-Mage')
        self.assertEqual(output['supertypes'], ['Legendary'])
        self.assertEqual(output['types'], ['Creature'])
        self.assertEqual(output['subtypes'], ['Human', 'Wizard'])
        self.assertEqual(output['manaCost'], '{4}{U}{R}')
        self.assertEqual(output['text'], '{T}: Discard a card.')

if __name__ == '__main__':
    unittest.main()
