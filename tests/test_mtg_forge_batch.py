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

class TestMtgForgeBatch(unittest.TestCase):

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_explicit_batch(self, mock_stdout, mock_open):
        # Mocking cards loaded from mtg_open_file
        card1 = MagicMock()
        card1.name = "Grizzly Bears"
        card1.to_dict.return_value = {
            'name': 'Grizzly Bears',
            'manaCost': '{1}{G}',
            'type': 'Creature - Bear',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'power': '2',
            'toughness': '2',
            'rarity': 'common'
        }
        card2 = MagicMock()
        card2.name = "Balduvian Bears"
        card2.to_dict.return_value = {
            'name': 'Balduvian Bears',
            'manaCost': '{1}{G}',
            'type': 'Creature - Bear',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'power': '2',
            'toughness': '2',
            'rarity': 'common'
        }
        mock_open.return_value = [card1, card2]

        test_args = [
            'mtg_forge.py',
            '--batch',
            '--pt', '3/3'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertIsInstance(output, list)
        self.assertEqual(len(output), 2)
        self.assertEqual(output[0]['name'], 'Grizzly Bears')
        self.assertEqual(output[0]['power'], '3')
        self.assertEqual(output[1]['name'], 'Balduvian Bears')
        self.assertEqual(output[1]['power'], '3')

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_auto_batch_on_no_base_or_name(self, mock_stdout, mock_open):
        # Mocking cards loaded from mtg_open_file
        card1 = MagicMock()
        card1.name = "Grizzly Bears"
        card1.to_dict.return_value = {
            'name': 'Grizzly Bears',
            'manaCost': '{1}{G}',
            'type': 'Creature - Bear',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'power': '2',
            'toughness': '2',
            'rarity': 'common'
        }
        mock_open.return_value = [card1]

        # Since neither --base nor --name are provided, it should auto-detect batch mode
        test_args = [
            'mtg_forge.py',
            '--buff', '1'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertIsInstance(output, list)
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['name'], 'Grizzly Bears')
        self.assertEqual(output[0]['power'], '3')

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_batch_encoded_output(self, mock_stdout, mock_open):
        # Mock cards
        card1 = MagicMock()
        card1.name = "Grizzly Bears"
        card1.to_dict.return_value = {
            'name': 'Grizzly Bears',
            'manaCost': '{1}{G}',
            'type': 'Creature - Bear',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'power': '2',
            'toughness': '2',
            'rarity': 'common'
        }
        # Card encoder output mock
        fc_mock = MagicMock()
        fc_mock.encode.return_value = "|5creature|4|6bear|7|8&^^/&^^|9|3{^G}|0O|1grizzly bears|"

        # Override the Card class inside scripts.mtg_forge to return our encoder mock
        with patch('scripts.mtg_forge.cardlib.Card', return_value=fc_mock):
            mock_open.return_value = [card1]

            test_args = [
                'mtg_forge.py',
                '--batch',
                '--encoded'
            ]

            with patch('sys.argv', test_args):
                main()

        output = mock_stdout.getvalue()
        self.assertIn("|5creature|", output)
        self.assertIn("|1grizzly bears|", output)

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_batch_summary_output(self, mock_stdout, mock_open):
        # Mock cards
        card1 = MagicMock()
        card1.name = "Grizzly Bears"
        card1.to_dict.return_value = {
            'name': 'Grizzly Bears',
            'manaCost': '{1}{G}',
            'type': 'Creature - Bear',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'power': '2',
            'toughness': '2',
            'rarity': 'common'
        }
        # Card summary output mock
        fc_mock = MagicMock()
        fc_mock.summary.return_value = "[O] Grizzly Bears {1}{G} • Creature — Bear • (2/2)"

        with patch('scripts.mtg_forge.cardlib.Card', return_value=fc_mock):
            mock_open.return_value = [card1]

            test_args = [
                'mtg_forge.py',
                '--batch',
                '--summary'
            ]

            with patch('sys.argv', test_args):
                main()

        output = mock_stdout.getvalue()
        self.assertIn("Grizzly Bears", output)
        self.assertIn("(2/2)", output)

if __name__ == '__main__':
    unittest.main()
