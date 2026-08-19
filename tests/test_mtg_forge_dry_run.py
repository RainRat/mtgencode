import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import io

# Add lib and scripts directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
scriptsdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../scripts')
sys.path.append(libdir)
sys.path.append(scriptsdir)

from scripts.mtg_forge import main

class TestMtgForgeDryRun(unittest.TestCase):

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_single_card_dry_run(self, mock_stdout):
        outfile = 'test_dry_run_single.json'
        if os.path.exists(outfile):
            os.remove(outfile)

        test_args = [
            'mtg_forge.py',
            '--name', 'Jules',
            '--cost', '{U}{R}',
            '--type', 'Legendary Creature - Human Engineer',
            '--pt', '2/3',
            '--text', 'T: Draw a card.',
            '--set', 'MOM',
            '--outfile', outfile,
            '--dry-run'
        ]

        try:
            with patch('sys.argv', test_args):
                main()

            output = mock_stdout.getvalue()
            self.assertIn("Dry Run Summary: 1 card forged/modified.", output)
            self.assertIn("Name: Jules", output)
            self.assertIn("Mana Cost: {U}{R}", output)
            self.assertIn("Type:", output)
            self.assertIn("Legendary Creature", output)
            self.assertIn("Human Engineer", output)
            self.assertIn("Stats: 2/3", output)
            self.assertIn("Text:", output)
            self.assertIn("Draw a card.", output)
            self.assertIn("Set: MOM", output)

            # Assert output file was NOT created due to dry-run
            self.assertFalse(os.path.exists(outfile))
        finally:
            if os.path.exists(outfile):
                os.remove(outfile)

    @patch('scripts.mtg_forge.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_batch_dry_run(self, mock_stdout, mock_open):
        outfile = 'test_dry_run_batch.json'
        if os.path.exists(outfile):
            os.remove(outfile)

        # Mock cards
        card1 = MagicMock()
        card1.name = "Grizzly Bears"
        card1.display_name = "Grizzly Bears"
        card1.set_code = "M10"
        card1.to_dict.return_value = {
            'name': 'Grizzly Bears',
            'manaCost': '{1}{G}',
            'type': 'Creature - Bear',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'power': '2',
            'toughness': '2',
            'rarity': 'common',
            'setCode': 'M10'
        }

        card2 = MagicMock()
        card2.name = "Balduvian Bears"
        card2.display_name = "Balduvian Bears"
        card2.set_code = "ICE"
        card2.to_dict.return_value = {
            'name': 'Balduvian Bears',
            'manaCost': '{1}{G}',
            'type': 'Creature - Bear',
            'types': ['Creature'],
            'subtypes': ['Bear'],
            'power': '2',
            'toughness': '2',
            'rarity': 'common',
            'setCode': 'ICE'
        }

        mock_open.return_value = [card1, card2]

        test_args = [
            'mtg_forge.py',
            '--infile', 'dummy.json',
            '--batch',
            '--pt', '3/3',
            '--outfile', outfile,
            '--preview'
        ]

        try:
            with patch('sys.argv', test_args):
                main()

            output = mock_stdout.getvalue()
            self.assertIn("Dry Run Summary: 2 card(s) forged/modified.", output)
            self.assertIn("Set Code Breakdown:", output)
            self.assertIn("ICE: 1 card(s)", output)
            self.assertIn("M10: 1 card(s)", output)
            self.assertIn("Sample Preview (up to 10): Grizzly Bears, Balduvian Bears", output)

            # Assert output file was NOT created
            self.assertFalse(os.path.exists(outfile))
        finally:
            if os.path.exists(outfile):
                os.remove(outfile)

if __name__ == '__main__':
    unittest.main()
