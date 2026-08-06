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

class TestMtgForgeValidate(unittest.TestCase):

    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_forge_validate_invalid_bear(self, mock_stderr, mock_stdout):
        # A creature must have power and toughness, otherwise it's invalid.
        test_args = [
            'mtg_forge.py',
            '--name', 'Invalid Bear',
            '--type', 'Creature',
            '--validate'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Invalid Bear')
        self.assertEqual(output['types'], ['Creature'])

        err_output = mock_stderr.getvalue()
        self.assertIn('WARNING', err_output)
        self.assertIn("Card 'Invalid Bear' failed design validation", err_output)
        self.assertIn('pt', err_output)

    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_forge_validate_color_pie_break(self, mock_stderr, mock_stdout):
        # Red counter target spell is a color pie break (Uncast expects UC)
        test_args = [
            'mtg_forge.py',
            '--name', 'Red Counter',
            '--cost', '{R}',
            '--type', 'Instant',
            '--text', 'Counter target spell.',
            '--validate'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Red Counter')

        err_output = mock_stderr.getvalue()
        self.assertIn('WARNING', err_output)
        self.assertIn("Card 'Red Counter' failed design validation", err_output)
        self.assertIn('color_pie', err_output)
        self.assertIn('Color Pie Break: Uncast (Expected UC)', err_output)

    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_forge_validate_valid_card(self, mock_stderr, mock_stdout):
        # A normal, valid creature with P/T and correct color pie keywords
        test_args = [
            'mtg_forge.py',
            '--name', 'Valid Bear',
            '--cost', '{1}{G}',
            '--type', 'Creature - Bear',
            '--pt', '2/2',
            '--text', 'Trample',
            '--validate'
        ]

        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Valid Bear')
        self.assertEqual(output['power'], '2')
        self.assertEqual(output['toughness'], '2')

        err_output = mock_stderr.getvalue()
        # Should not have any warning printed to stderr
        self.assertEqual(err_output.strip(), "")

if __name__ == '__main__':
    unittest.main()
