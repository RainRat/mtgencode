import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import io
import json
import csv

# Add lib and scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

import mtg_deckgen
import cardlib

class TestMtgDeckgen(unittest.TestCase):

    def test_get_color_identity_set(self):
        card = MagicMock()
        card.color_identity = "WU"
        self.assertEqual(mtg_deckgen.get_color_identity_set(card), {'W', 'U'})

        card.color_identity = ""
        self.assertEqual(mtg_deckgen.get_color_identity_set(card), set())

        card = object() # No color_identity attribute
        self.assertEqual(mtg_deckgen.get_color_identity_set(card), set())

    def test_pick_cards_with_curve_basic(self):
        pool = [MagicMock() for _ in range(10)]
        picked = mtg_deckgen.pick_cards_with_curve(pool, 5)
        self.assertEqual(len(picked), 5)
        for p in picked:
            self.assertIn(p, pool)

    def test_pick_cards_with_curve_empty_pool(self):
        self.assertEqual(mtg_deckgen.pick_cards_with_curve([], 5), [])

    def test_pick_cards_with_curve_with_curve(self):
        # Use real Card objects for better property handling
        c1 = cardlib.Card({'name': 'C1', 'manaCost': '{G}', 'types': ['Creature'], 'rarity': 'common'})
        c2 = cardlib.Card({'name': 'C2', 'manaCost': '{1}{G}', 'types': ['Creature'], 'rarity': 'common'})
        c6 = cardlib.Card({'name': 'C6', 'manaCost': '{5}{G}', 'types': ['Creature'], 'rarity': 'common'})

        pool = [c1, c2, c6]
        curve = {1: 1, 2: 1, 6: 1}
        picked = mtg_deckgen.pick_cards_with_curve(pool, 3, curve=curve)
        self.assertEqual(len(picked), 3)
        self.assertIn(c1, picked)
        self.assertIn(c2, picked)
        self.assertIn(c6, picked)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_commander(self, mock_stderr, mock_stdout, mock_open):
        # Create a pool with a legendary creature and some other cards
        commander = cardlib.Card({
            'name': 'Galia',
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'manaCost': '{R}{G}',
            'rarity': 'rare',
            'text': ''
        })

        card1 = cardlib.Card({
            'name': 'Goblin',
            'types': ['Creature'],
            'manaCost': '{1}{R}',
            'rarity': 'common',
            'text': ''
        })

        mock_open.return_value = [commander, card1]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'commander', '--commander', 'Galia']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        self.assertIn("Galia", output)
        self.assertIn("Goblin", output)
        # Should also include some lands
        self.assertTrue("Mountain" in output or "Forest" in output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_standard(self, mock_stderr, mock_stdout, mock_open):
        c1 = cardlib.Card({
            'name': 'Soldier',
            'types': ['Creature'],
            'manaCost': '{W}',
            'rarity': 'common',
            'text': ''
        })

        s1 = cardlib.Card({
            'name': 'Shock',
            'types': ['Instant'],
            'manaCost': '{R}',
            'rarity': 'common',
            'text': ''
        })

        mock_open.return_value = [c1, s1]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'standard']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        self.assertIn("Soldier", output)
        self.assertIn("Shock", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_no_legendary(self, mock_stderr, mock_open):
        # Pool with no legendary creatures
        c1 = cardlib.Card({'name': 'Soldier', 'types': ['Creature'], 'manaCost': '{W}', 'rarity': 'common'})
        mock_open.return_value = [c1]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json']), self.assertRaises(SystemExit):
            mtg_deckgen.main()
        self.assertIn("Error: No legendary", mock_stderr.getvalue())

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_standard_empty_pool(self, mock_stderr, mock_stdout, mock_open):
        # We need at least one card to avoid the early exit
        c1 = cardlib.Card({'name': 'Soldier', 'types': ['Creature'], 'manaCost': '{W}', 'rarity': 'common'})
        mock_open.return_value = [c1]

        # Test standard with only creatures (empty spells)
        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'standard']):
            mtg_deckgen.main()
        self.assertIn("Warning: No non-creature spells found", mock_stderr.getvalue())

    @patch('sys.stdin.isatty', return_value=True)
    @patch('os.path.exists', return_value=False)
    @patch('sys.stderr', new_callable=io.StringIO)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_interactive_missing_dataset(self, mock_stdout, mock_stderr, mock_exists, mock_isatty):
        with patch('sys.argv', ['mtg_deckgen.py']), self.assertRaises(SystemExit) as cm:
            mtg_deckgen.main()
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error: Deck generation requires an input dataset or card pool.", mock_stderr.getvalue())

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_dry_run_commander(self, mock_stderr, mock_stdout, mock_open):
        commander = cardlib.Card({
            'name': 'Galia',
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'manaCost': '{R}{G}',
            'rarity': 'rare',
            'text': ''
        })
        card1 = cardlib.Card({
            'name': 'Goblin',
            'types': ['Creature'],
            'manaCost': '{1}{R}',
            'rarity': 'common',
            'text': ''
        })
        mock_open.return_value = [commander, card1]

        outfile_path = 'test_dry_run_output.txt'
        if os.path.exists(outfile_path):
            os.remove(outfile_path)

        try:
            with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'commander', '--commander', 'Galia', '--dry-run', '--outfile', outfile_path]):
                mtg_deckgen.main()

            output = mock_stdout.getvalue()
            self.assertIn("Dry Run Summary:", output)
            self.assertIn("Commander: Galia", output)
            self.assertIn("Composition Breakdown:", output)
            self.assertIn("Sample Preview (up to 10 entries):", output)
            self.assertFalse(os.path.exists(outfile_path))
        finally:
            if os.path.exists(outfile_path):
                os.remove(outfile_path)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_dry_run_standard(self, mock_stderr, mock_stdout, mock_open):
        c1 = cardlib.Card({'name': 'Soldier', 'types': ['Creature'], 'manaCost': '{W}', 'rarity': 'common'})
        s1 = cardlib.Card({'name': 'Shock', 'types': ['Instant'], 'manaCost': '{R}', 'rarity': 'common'})
        mock_open.return_value = [c1, s1]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'standard', '-p']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        self.assertIn("Dry Run Summary:", output)
        self.assertIn("Standard format", output)
        self.assertIn("Composition Breakdown:", output)
        self.assertIn("Sample Preview (up to 10 entries):", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_custom_curve_and_invalid_segment(self, mock_stderr, mock_stdout, mock_open):
        commander = cardlib.Card({
            'name': 'Galia',
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'manaCost': '{R}{G}',
            'rarity': 'rare',
            'text': ''
        })
        card1 = cardlib.Card({
            'name': 'Goblin',
            'types': ['Creature'],
            'manaCost': '{1}{R}',
            'rarity': 'common',
            'text': ''
        })
        mock_open.return_value = [commander, card1]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'commander', '--commander', 'Galia', '--curve', '1:2,2:4,6+:2,invalid']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        stderr = mock_stderr.getvalue()
        self.assertIn("Galia", output)
        self.assertIn("Warning: Invalid curve segment 'invalid', skipping.", stderr)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_outfile_writing(self, mock_stderr, mock_stdout, mock_open):
        commander = cardlib.Card({
            'name': 'Galia',
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'manaCost': '{R}{G}',
            'rarity': 'rare',
            'text': ''
        })
        card1 = cardlib.Card({
            'name': 'Goblin',
            'types': ['Creature'],
            'manaCost': '{1}{R}',
            'rarity': 'common',
            'text': ''
        })
        mock_open.return_value = [commander, card1]

        outfile_path = 'test_deckgen_outfile.txt'
        if os.path.exists(outfile_path):
            os.remove(outfile_path)

        try:
            with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'commander', '--commander', 'Galia', '--outfile', outfile_path]):
                mtg_deckgen.main()

            self.assertTrue(os.path.exists(outfile_path))
            with open(outfile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn("1 Galia *CMDR*", content)
            self.assertIn("1 Goblin", content)
        finally:
            if os.path.exists(outfile_path):
                os.remove(outfile_path)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_commander_fallback_warning(self, mock_stderr, mock_stdout, mock_open):
        commander = cardlib.Card({
            'name': 'Galia',
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'manaCost': '{R}{G}',
            'rarity': 'rare',
            'text': ''
        })
        mock_open.return_value = [commander]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'commander', '--commander', 'NonexistentCommander']):
            mtg_deckgen.main()

        stderr = mock_stderr.getvalue()
        self.assertIn("Warning: Commander 'NonexistentCommander' not found. Picking a random one.", stderr)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_commander_partial_matching(self, mock_stderr, mock_stdout, mock_open):
        commander = cardlib.Card({
            'name': "Galia, Bearer of Mischief",
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'manaCost': '{R}{G}',
            'rarity': 'rare',
            'text': ''
        })
        mock_open.return_value = [commander]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'commander', '--commander', 'Galia']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        stderr = mock_stderr.getvalue()
        self.assertIn("1 Galia, Bearer of Mischief *CMDR*", output)
        self.assertIn("Notice: Commander 'Galia' matched: Galia, Bearer of Mischief", stderr)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_commander_fuzzy_matching(self, mock_stderr, mock_stdout, mock_open):
        commander = cardlib.Card({
            'name': "Galia, Bearer of Mischief",
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'manaCost': '{R}{G}',
            'rarity': 'rare',
            'text': ''
        })
        mock_open.return_value = [commander]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'commander', '--commander', 'Galia, Bearer of Mischaef']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        stderr = mock_stderr.getvalue()
        self.assertIn("1 Galia, Bearer of Mischief *CMDR*", output)
        self.assertIn("Notice: Commander 'Galia, Bearer of Mischaef' matched: Galia, Bearer of Mischief", stderr)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_pauper_empty_common_pool(self, mock_stderr, mock_open):
        rare_card = cardlib.Card({
            'name': 'Rare Dragon',
            'types': ['Creature'],
            'manaCost': '{3}{R}{R}',
            'rarity': 'rare',
            'text': ''
        })
        mock_open.return_value = [rare_card]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'pauper']), self.assertRaises(SystemExit):
            mtg_deckgen.main()

        self.assertIn("Error: No common cards found in the card pool for Pauper format.", mock_stderr.getvalue())

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_positional_commander_query(self, mock_stderr, mock_stdout, mock_open):
        commander = cardlib.Card({
            'name': 'Galia',
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'manaCost': '{R}{G}',
            'rarity': 'rare',
            'text': ''
        })
        mock_open.return_value = [commander]

        # Passing "Galia" as first positional argument when Galia file doesn't exist on disk
        with patch('sys.argv', ['mtg_deckgen.py', 'Galia', '--format', 'commander']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        self.assertIn("Galia *CMDR*", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_stream_flushing(self, mock_stderr, mock_stdout, mock_open):
        c1 = cardlib.Card({'name': 'Soldier', 'types': ['Creature'], 'manaCost': '{W}', 'rarity': 'common', 'text': ''})
        s1 = cardlib.Card({'name': 'Shock', 'types': ['Instant'], 'manaCost': '{R}', 'rarity': 'common', 'text': ''})
        mock_open.return_value = [c1, s1]

        mock_stderr.flush = MagicMock()

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'standard']):
            mtg_deckgen.main()

        mock_stderr.flush.assert_called()

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_json_export(self, mock_stderr, mock_stdout, mock_open):
        c1 = cardlib.Card({'name': 'Soldier', 'types': ['Creature'], 'manaCost': '{W}', 'rarity': 'common', 'setCode': 'MOM', 'text': ''})
        s1 = cardlib.Card({'name': 'Shock', 'types': ['Instant'], 'manaCost': '{R}', 'rarity': 'common', 'setCode': 'MOM', 'text': ''})
        mock_open.return_value = [c1, s1]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'standard', '--json']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        data = json.loads(output)
        self.assertEqual(data['format'], 'standard')
        self.assertEqual(data['total_cards'], sum(data['composition'].values()))
        self.assertIn('deck', data)
        self.assertTrue(len(data['deck']) > 0)
        names = [entry['name'] for entry in data['deck']]
        self.assertIn('Soldier', names)
        self.assertIn('Shock', names)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_csv_export(self, mock_stderr, mock_stdout, mock_open):
        c1 = cardlib.Card({'name': 'Soldier', 'types': ['Creature'], 'manaCost': '{W}', 'rarity': 'common', 'setCode': 'MOM', 'text': ''})
        s1 = cardlib.Card({'name': 'Shock', 'types': ['Instant'], 'manaCost': '{R}', 'rarity': 'common', 'setCode': 'MOM', 'text': ''})
        mock_open.return_value = [c1, s1]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'standard', '--csv']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        reader = csv.DictReader(io.StringIO(output))
        rows = list(reader)
        self.assertTrue(len(rows) > 0)
        self.assertIn('count', rows[0])
        self.assertIn('name', rows[0])
        self.assertIn('section', rows[0])
        names = [r['name'] for r in rows]
        self.assertIn('Soldier', names)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_outfile_auto_detect_json_and_csv(self, mock_stderr, mock_stdout, mock_open):
        c1 = cardlib.Card({'name': 'Soldier', 'types': ['Creature'], 'manaCost': '{W}', 'rarity': 'common', 'setCode': 'MOM', 'text': ''})
        s1 = cardlib.Card({'name': 'Shock', 'types': ['Instant'], 'manaCost': '{R}', 'rarity': 'common', 'setCode': 'MOM', 'text': ''})
        mock_open.return_value = [c1, s1]

        json_out = 'test_deck_autodetect.json'
        csv_out = 'test_deck_autodetect.csv'

        try:
            # Auto-detect JSON
            with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'standard', '--outfile', json_out]):
                mtg_deckgen.main()
            self.assertTrue(os.path.exists(json_out))
            with open(json_out, 'r', encoding='utf-8') as f:
                parsed_json = json.load(f)
            self.assertEqual(parsed_json['format'], 'standard')

            # Auto-detect CSV
            with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'standard', '--outfile', csv_out]):
                mtg_deckgen.main()
            self.assertTrue(os.path.exists(csv_out))
            with open(csv_out, 'r', encoding='utf-8') as f:
                parsed_csv = list(csv.DictReader(f))
            self.assertTrue(len(parsed_csv) > 0)
        finally:
            if os.path.exists(json_out): os.remove(json_out)
            if os.path.exists(csv_out): os.remove(csv_out)

    def test_pick_cards_with_curve_pool_smaller_than_target(self):
        pool = [MagicMock() for _ in range(3)]
        picked = mtg_deckgen.pick_cards_with_curve(pool, 10, curve=None)
        self.assertEqual(len(picked), 3)
        self.assertEqual(picked, pool)

    def test_pick_cards_with_curve_backfills_remaining_target(self):
        c1 = cardlib.Card({'name': 'C1', 'manaCost': '{G}', 'types': ['Creature'], 'rarity': 'common'})
        c2 = cardlib.Card({'name': 'C2', 'manaCost': '{1}{G}', 'types': ['Creature'], 'rarity': 'common'})
        c3 = cardlib.Card({'name': 'C3', 'manaCost': '{2}{G}', 'types': ['Creature'], 'rarity': 'common'})
        pool = [c1, c2, c3]
        curve = {1: 1}
        picked = mtg_deckgen.pick_cards_with_curve(pool, 3, curve=curve)
        self.assertEqual(len(picked), 3)
        self.assertIn(c1, picked)
        self.assertIn(c2, picked)
        self.assertIn(c3, picked)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_brawl_planeswalker_commander(self, mock_stderr, mock_stdout, mock_open):
        pw_commander = cardlib.Card({
            'name': 'Ashiok, Wicked Manipulator',
            'supertypes': ['Legendary'],
            'types': ['Planeswalker'],
            'manaCost': '{3}{B}{B}',
            'rarity': 'mythic',
            'text': ''
        })
        spell = cardlib.Card({
            'name': 'Doom Blade',
            'types': ['Instant'],
            'manaCost': '{1}{B}',
            'rarity': 'common',
            'text': ''
        })
        mock_open.return_value = [pw_commander, spell]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'brawl', '--commander', 'Ashiok, Wicked Manipulator']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        self.assertIn("Ashiok, Wicked Manipulator *CMDR*", output)
        self.assertIn("Doom Blade", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_commander_sideboard_generation(self, mock_stderr, mock_stdout, mock_open):
        commander = cardlib.Card({
            'name': 'Galia',
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'manaCost': '{R}{G}',
            'rarity': 'rare',
            'text': ''
        })
        cards = [commander]
        for i in range(25):
            cards.append(cardlib.Card({'name': f'Card_{i}', 'types': ['Creature'], 'manaCost': '{1}{R}', 'rarity': 'common', 'text': ''}))

        mock_open.return_value = cards

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'commander', '--commander', 'Galia', '--sideboard']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        self.assertIn("Sideboard", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_commander_sideboard_small_pool_fallback(self, mock_stderr, mock_stdout, mock_open):
        commander = cardlib.Card({
            'name': 'Galia',
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'manaCost': '{R}{G}',
            'rarity': 'rare',
            'text': ''
        })
        card1 = cardlib.Card({
            'name': 'Goblin',
            'types': ['Creature'],
            'manaCost': '{1}{R}',
            'rarity': 'common',
            'text': ''
        })
        mock_open.return_value = [commander, card1]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'commander', '--commander', 'Galia', '--sideboard-size', '5']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        self.assertIn("Sideboard", output)
        self.assertIn("Goblin", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_standard_sideboard_generation(self, mock_stderr, mock_stdout, mock_open):
        c1 = cardlib.Card({'name': 'Soldier', 'types': ['Creature'], 'manaCost': '{W}', 'rarity': 'common', 'text': ''})
        s1 = cardlib.Card({'name': 'Shock', 'types': ['Instant'], 'manaCost': '{R}', 'rarity': 'common', 'text': ''})
        mock_open.return_value = [c1, s1]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'standard', '--sideboard']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        self.assertIn("Sideboard", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_dry_run_commander_preview(self, mock_stderr, mock_stdout, mock_open):
        commander = cardlib.Card({
            'name': 'Galia',
            'supertypes': ['Legendary'],
            'types': ['Creature'],
            'manaCost': '{R}{G}',
            'rarity': 'rare',
            'text': ''
        })
        mock_open.return_value = [commander]

        with patch('sys.argv', ['mtg_deckgen.py', 'dummy.json', '--format', 'commander', '--commander', 'Galia', '--dry-run']):
            mtg_deckgen.main()

        output = mock_stdout.getvalue()
        self.assertIn("Commander: Galia", output)

if __name__ == '__main__':
    unittest.main()
