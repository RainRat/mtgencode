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

from scripts.mtg_forge import main

class TestMtgForge(unittest.TestCase):

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_scratch(self, mock_stdout, mock_open):
        # Test creating a card from scratch
        test_args = [
            'mtg_forge.py',
            '--name', 'Jules',
            '--cost', '{U}{R}',
            '--type', 'Legendary Creature - Human Engineer',
            '--pt', '2/3',
            '--text', 'T: Draw a card.',
            '--rarity', 'Rare'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Jules')
        self.assertEqual(output['manaCost'], '{U}{R}')
        self.assertEqual(output['types'], ['Creature'])
        self.assertEqual(output['supertypes'], ['Legendary'])
        self.assertEqual(output['subtypes'], ['Human', 'Engineer'])
        self.assertEqual(output['power'], '2')
        self.assertEqual(output['toughness'], '3')
        self.assertEqual(output['rarity'], 'rare')
        self.assertIn('Draw a card', output['text'])

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_reforge(self, mock_stdout, mock_open):
        # Mock base card
        mock_card = MagicMock()
        mock_card.name = "Grizzly Bears"
        mock_card.to_dict.return_value = {
            'name': 'Grizzly Bears',
            'manaCost': '{1}{G}',
            'type': 'Creature - Bear',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'power': '2',
            'toughness': '2',
            'rarity': 'common'
        }
        mock_open.return_value = [mock_card]

        test_args = [
            'mtg_forge.py',
            '--base', 'Grizzly Bears',
            '--pt', '3/3',
            '--name', 'Super Bears'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Super Bears')
        self.assertEqual(output['power'], '3')
        self.assertEqual(output['toughness'], '3')
        self.assertEqual(output['manaCost'], '{1}{G}')
        self.assertEqual(output['subtypes'], ['Bear'])

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_encoded(self, mock_stdout):
        test_args = [
            'mtg_forge.py',
            '--name', 'Test',
            '--type', 'Instant',
            '--encoded'
        ]

        with patch('sys.argv', test_args):
            main()

        output = mock_stdout.getvalue()
        # Check standard encoded format: types|supertypes|subtypes|loyalty|pt|text|cost|rarity|name
        # For Instant, no-name: |5instant|4|6|7|8|9|3|0|1test|
        self.assertIn('|5instant|', output)
        self.assertIn('|1test|', output)

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_summary(self, mock_stdout):
        test_args = [
            'mtg_forge.py',
            '--name', 'Test',
            '--type', 'Creature',
            '--pt', '1/1',
            '--summary'
        ]

        with patch('sys.argv', test_args):
            main()

        output = mock_stdout.getvalue()
        self.assertIn('Test', output)
        self.assertIn('Creature', output)
        self.assertIn('(1/1)', output)

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_view(self, mock_stdout):
        test_args = [
            'mtg_forge.py',
            '--name', 'Jules',
            '--cost', '{U}{R}',
            '--type', 'Legendary Creature',
            '--pt', '2/2',
            '--text', 'T: Draw a card.',
            '--view'
        ]

        with patch('sys.argv', test_args):
            main()

        output = mock_stdout.getvalue()
        self.assertIn('Jules', output)
        self.assertIn('Legendary Creature', output)
        self.assertIn('COMPLEXITY', output)
        self.assertIn('RATING', output)

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_gatherer(self, mock_stdout):
        test_args = [
            'mtg_forge.py',
            '--name', 'Jules',
            '--cost', '{U}{R}',
            '--type', 'Legendary Creature',
            '--pt', '2/2',
            '--text', 'T: Draw a card.',
            '--gatherer'
        ]

        with patch('sys.argv', test_args):
            main()

        output = mock_stdout.getvalue()
        self.assertIn('Jules {U}{R}', output)
        self.assertIn('Legendary Creature (2/2)', output)

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_forge_no_args_interactive_help(self, mock_stdout, mock_isatty):
        test_args = ['mtg_forge.py']

        with patch('sys.argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                main()

        self.assertEqual(cm.exception.code, 0)
        output = mock_stdout.getvalue()
        self.assertIn('usage:', output.lower())
        self.assertIn('--base', output)
        self.assertIn('--infile', output)

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_forge_missing_dataset_interactive_error(self, mock_stderr, mock_isatty):
        # Test 1: Batch mode (default) in TTY with missing dataset
        test_args = ['mtg_forge.py', '--batch']

        with patch('sys.argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                main()

        self.assertEqual(cm.exception.code, 1)
        err_output = mock_stderr.getvalue()
        self.assertIn('error: batch processing requires an input dataset', err_output.lower())

        # Reset stdout/stderr mock and test 2: Single-card template mode with missing dataset
        mock_stderr.truncate(0)
        mock_stderr.seek(0)
        test_args = ['mtg_forge.py', '--base', 'Grizzly Bears']

        with patch('sys.argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                main()

        self.assertEqual(cm.exception.code, 1)
        err_output = mock_stderr.getvalue()
        self.assertIn("error: base card template lookup for 'grizzly bears' requires a dataset", err_output.lower())

if __name__ == '__main__':
    unittest.main()
