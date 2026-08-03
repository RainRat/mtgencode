import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import io

# Add lib and scripts directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
scriptsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../scripts')
sys.path.append(libdir)
sys.path.append(scriptsdir)

from scripts.mtg_forge import (
    main,
    apply_forge_replacements,
    apply_mana_adjust,
    adjust_mana_cost,
    apply_text_replacement,
    parse_sed_replace
)

class TestMtgForgeNewModifiers(unittest.TestCase):

    def test_parse_sed_replace(self):
        # Valid sed-style regex
        pat, repl, flags, is_regex = parse_sed_replace('s/flying/trample/i')
        self.assertTrue(is_regex)
        self.assertEqual(pat, 'flying')
        self.assertEqual(repl, 'trample')
        self.assertEqual(flags, 2)  # re.IGNORECASE

        # No flags
        pat, repl, flags, is_regex = parse_sed_replace('s/flying/trample/')
        self.assertTrue(is_regex)
        self.assertEqual(pat, 'flying')
        self.assertEqual(repl, 'trample')
        self.assertEqual(flags, 0)

        # Non-sed style
        _, _, _, is_regex = parse_sed_replace('flying->trample')
        self.assertFalse(is_regex)

    def test_apply_text_replacement(self):
        # Plain string replace
        res = apply_text_replacement('This creature has flying.', 'flying->trample')
        self.assertEqual(res, 'This creature has trample.')

        # Plain string replace (remove substring)
        res = apply_text_replacement('This creature has flying.', 'flying')
        self.assertEqual(res, 'This creature has .')

        # Sed-style regex replace
        res = apply_text_replacement('This creature has FLYING.', 's/flying/trample/i')
        self.assertEqual(res, 'This creature has trample.')

        # Regex group backreference
        res = apply_text_replacement('Draw 2 cards.', 's/Draw (\\d+)/Discard \\1/i')
        self.assertEqual(res, 'Discard 2 cards.')

    def test_apply_forge_replacements_on_card_fields(self):
        card = {
            'name': 'Grizzly Bears',
            'type': 'Creature - Bear',
            'text': 'This creature has flying.',
            'supertypes': [],
            'types': ['Creature'],
            'subtypes': ['Bear']
        }

        # Mocking arguments
        args = MagicMock()
        args.replace = 'flying->trample'
        args.replace_name = 's/grizzly/Mighty/i'
        args.replace_type = 'Bear->Beast'

        res = apply_forge_replacements(card, args)
        self.assertEqual(res['name'], 'Mighty Bears')
        self.assertEqual(res['type'], 'Creature - Beast')
        self.assertEqual(res['text'], 'This creature has trample.')
        self.assertEqual(res['subtypes'], ['Beast'])

    def test_apply_forge_replacements_recursive_bside(self):
        card = {
            'name': 'Grizzly Bears',
            'type': 'Creature - Bear',
            'text': 'This creature has flying.',
            'bside': {
                'name': 'Polar Bear',
                'type': 'Creature - Bear',
                'text': 'This creature has islandwalk.',
            }
        }

        args = MagicMock()
        args.replace = 'islandwalk->swampwalk'
        args.replace_name = 'Polar->Grizzly'
        args.replace_type = None

        res = apply_forge_replacements(card, args)
        self.assertEqual(res['name'], 'Grizzly Bears')
        self.assertEqual(res['bside']['name'], 'Grizzly Bear')
        self.assertEqual(res['bside']['text'], 'This creature has swampwalk.')

    def test_adjust_mana_cost(self):
        # Increment existing generic cost
        self.assertEqual(adjust_mana_cost('{2}{W}', 1), '{3}{W}')

        # Decrement existing generic cost
        self.assertEqual(adjust_mana_cost('{2}{W}', -1), '{1}{W}')

        # Decrement to zero (removing generic cost entirely)
        self.assertEqual(adjust_mana_cost('{1}{W}', -1), '{W}')
        self.assertEqual(adjust_mana_cost('{2}{W}', -2), '{W}')

        # Adding generic cost when none exists
        self.assertEqual(adjust_mana_cost('{W}', 2), '{2}{W}')

        # Adjusting empty mana cost
        self.assertEqual(adjust_mana_cost('', 3), '{3}')
        self.assertEqual(adjust_mana_cost('', -1), '')

    def test_apply_mana_adjust_recursive_bside(self):
        card = {
            'manaCost': '{2}{W}',
            'bside': {
                'manaCost': '{U}'
            }
        }

        res = apply_mana_adjust(card, 1)
        self.assertEqual(res['manaCost'], '{3}{W}')
        self.assertEqual(res['bside']['manaCost'], '{1}{U}')

        res2 = apply_mana_adjust(res, -2)
        self.assertEqual(res2['manaCost'], '{1}{W}')
        self.assertEqual(res2['bside']['manaCost'], '{U}')

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_cli_integration_new_modifiers(self, mock_stdout):
        # We test with patching argv for mtg_forge.py main entry point
        test_args = [
            'mtg_forge.py',
            '--name', 'Grizzly Bears',
            '--type', 'Creature - Bear',
            '--pt', '2/2',
            '--cost', '{1}{G}',
            '--text', 'This creature has flying.',
            '--replace-name', 'Grizzly->Mighty',
            '--replace-type', 'Bear->Beast',
            '--replace', 'flying->trample',
            '--mana-adjust', '2'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Mighty Bears')
        self.assertEqual(output['manaCost'], '{3}{G}')
        self.assertEqual(output['text'], 'This creature has trample.')
        self.assertEqual(output['subtypes'], ['Beast'])

if __name__ == '__main__':
    unittest.main()
