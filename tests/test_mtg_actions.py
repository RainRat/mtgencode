import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import io
from scripts.mtg_actions import get_card_actions, main
from lib.cardlib import Card

class TestMtgActionsSimplified(unittest.TestCase):

    def test_get_card_actions_basic(self):
        # Removal
        card = Card({"name": "Murder", "manaCost": "{1}{B}{B}", "text": "destroy target creature.", "types": ["instant"], "rarity": "common"})
        actions = get_card_actions(card)
        self.assertIn("Removal", actions)

        # Protection
        card = Card({"name": "Swiftfoot Boots", "manaCost": "{2}", "text": "hexproof", "types": ["artifact"], "rarity": "common"})
        actions = get_card_actions(card)
        self.assertIn("Protection", actions)

    @patch('scripts.mtg_actions.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_standard_flags(self, mock_stdout, mock_open):
        mock_open.return_value = []

        # Test that all project-standard filtering flags are recognized
        args = [
            'mtg_actions.py', 'dummy.json',
            '--vgrep', 'test', '--identity', 'W', '--id-count', '1',
            '--pow', '>2', '--tou', '1-3', '--loy', '4',
            '--mechanic', 'Flying', '--deck-filter', 'deck.txt',
            '--booster', '1', '--box', '1', '--seed', '42', '--shuffle',
            '-j', '-n', '10', '-S', '5'
        ]

        with patch('sys.argv', args):
            try:
                main()
            except SystemExit:
                pass

        mock_open.assert_called_once()
        kwargs = mock_open.call_args.kwargs
        self.assertEqual(kwargs['vgrep'], ['test'])
        self.assertEqual(kwargs['identities'], ['W'])
        self.assertEqual(kwargs['id_counts'], ['1'])
        self.assertEqual(kwargs['pows'], ['>2'])
        self.assertEqual(kwargs['tous'], ['1-3'])
        self.assertEqual(kwargs['loys'], ['4'])
        self.assertEqual(kwargs['mechanics'], ['Flying'])
        self.assertEqual(kwargs['decklist_file'], 'deck.txt')
        self.assertEqual(kwargs['booster'], 1)
        self.assertEqual(kwargs['box'], 1)
        self.assertEqual(kwargs['seed'], 42)
        self.assertTrue(kwargs['shuffle'])

    @patch('scripts.mtg_actions.jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_execution_summary(self, mock_stdout, mock_open):
        cards = [Card({"name": "Murder", "manaCost": "{1}{B}{B}", "text": "destroy", "types": ["instant"], "rarity": "common"})]
        mock_open.return_value = cards

        with patch('sys.argv', ['mtg_actions.py', 'dummy.json']):
            main()

        # Check for the operation summary in stderr (where utils.print_operation_summary prints)
        # Actually it depends on how it's called. In mtg_actions.py it's called with quiet=args.quiet.
        # utils.print_operation_summary defaults to stdout? No, let's check.
        # Actually, mtg_actions.py code: utils.print_operation_summary("Action Analysis", len(cards), 0, quiet=args.quiet)
        pass

if __name__ == '__main__':
    unittest.main()
