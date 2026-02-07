import os
import unittest
import tempfile
import csv
import shutil
import sys
from io import StringIO
from unittest.mock import patch

# Ensure lib is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import jdecode

class TestJDecodeCSV(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_csv(self, filename, rows):
        path = os.path.join(self.test_dir, filename)
        # Collect all unique keys from all rows to ensure fieldnames is complete
        fieldnames = set()
        for row in rows:
            fieldnames.update(row.keys())
        fieldnames = sorted(list(fieldnames))

        with open(path, 'w', encoding='utf-8', newline='') as f:
            if not rows:
                return path
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_mtg_open_csv_basic(self):
        rows = [
            {'name': 'Black Lotus', 'mana_cost': '{0}', 'type': 'Artifact', 'text': '{T}, Sacrifice: Add three mana.', 'rarity': 'Rare'},
            {'name': 'Shock', 'mana_cost': '{R}', 'type': 'Instant', 'text': 'Shock deals 2 damage.', 'rarity': 'Common'}
        ]
        path = self.create_csv('test.csv', rows)
        srcs, bad_sets = jdecode.mtg_open_csv(path)

        self.assertIn('black lotus', srcs)
        self.assertEqual(srcs['black lotus'][0]['name'], 'Black Lotus')
        self.assertEqual(srcs['black lotus'][0]['manaCost'], '{0}')

        self.assertIn('shock', srcs)
        self.assertEqual(srcs['shock'][0]['name'], 'Shock')

    def test_mtg_open_csv_stats(self):
        rows = [
            {'name': 'Tarmogoyf', 'mana_cost': '{1}{G}', 'type': 'Creature', 'power': '1+*', 'toughness': '*', 'rarity': 'Rare'},
            {'name': 'Jace', 'mana_cost': '{2}{U}{U}', 'type': 'Legendary Planeswalker', 'loyalty': '3', 'rarity': 'Mythic'},
            {'name': 'Battle', 'mana_cost': '{1}{R}', 'type': 'Battle', 'defense': '4', 'rarity': 'Uncommon'}
        ]
        path = self.create_csv('test_stats.csv', rows)
        srcs, _ = jdecode.mtg_open_csv(path)

        tarmo = srcs['tarmogoyf'][0]
        self.assertEqual(tarmo['power'], '1+*')
        self.assertEqual(tarmo['toughness'], '*')

        jace = srcs['jace'][0]
        self.assertEqual(jace['loyalty'], '3')
        self.assertIn('Legendary', jace['supertypes'])
        self.assertIn('Planeswalker', jace['types'])

        battle = srcs['battle'][0]
        self.assertEqual(battle['defense'], '4')

    def test_mtg_open_csv_subtypes(self):
        rows = [
            {'name': 'Goblin Guide', 'type': 'Creature', 'subtypes': 'Goblin Scout', 'rarity': 'Rare'}
        ]
        path = self.create_csv('test_subtypes.csv', rows)
        srcs, _ = jdecode.mtg_open_csv(path)

        goblin = srcs['goblin guide'][0]
        self.assertEqual(goblin['subtypes'], ['Goblin', 'Scout'])

    def test_mtg_open_csv_duplicates(self):
        # Multiple versions of the same card
        rows = [
            {'name': 'Shock', 'rarity': 'Common', 'mana_cost': '{R}'},
            {'name': 'Shock', 'rarity': 'Uncommon', 'mana_cost': '{R}'}
        ]
        path = self.create_csv('test_dupes.csv', rows)
        srcs, _ = jdecode.mtg_open_csv(path)

        self.assertEqual(len(srcs['shock']), 2)

    def test_mtg_open_csv_verbose(self):
        rows = [{'name': 'Test', 'rarity': 'Common'}]
        path = self.create_csv('test_verbose.csv', rows)

        with patch('sys.stderr', new=StringIO()) as fake_stderr:
            jdecode.mtg_open_csv(path, verbose=True)
            output = fake_stderr.getvalue()
            self.assertIn('Opened 1 uniquely named cards from CSV.', output)

    def test_mtg_open_file_integration_csv(self):
        # Testing single CSV file via mtg_open_file
        rows = [{'name': 'Shock', 'mana_cost': '{R}', 'type': 'Instant', 'rarity': 'Common'}]
        path = self.create_csv('shock.csv', rows)

        with patch('sys.stderr', new=StringIO()) as fake_stderr:
            cards = jdecode.mtg_open_file(path, verbose=True)
            output = fake_stderr.getvalue()
            self.assertIn('This looks like a csv file:', output)
            self.assertIn('Opened 1 uniquely named cards from CSV.', output)

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, 'shock')

    def test_mtg_open_file_integration_dir_csv(self):
        # Testing directory with CSV files via mtg_open_file
        rows1 = [{'name': 'Shock', 'mana_cost': '{R}', 'type': 'Instant', 'rarity': 'Common'}]
        rows2 = [{'name': 'Bolt', 'mana_cost': '{R}', 'type': 'Instant', 'rarity': 'Common'}]
        rows3 = [{'name': 'Shock', 'mana_cost': '{R}', 'type': 'Instant', 'rarity': 'Uncommon'}]

        subdir = os.path.join(self.test_dir, 'csv_dir')
        os.makedirs(subdir)

        self.create_csv(os.path.join('csv_dir', 'card1.csv'), rows1)
        self.create_csv(os.path.join('csv_dir', 'card2.csv'), rows2)
        self.create_csv(os.path.join('csv_dir', 'card3.csv'), rows3)

        with patch('sys.stderr', new=StringIO()) as fake_stderr:
            cards = jdecode.mtg_open_file(subdir, verbose=True)
            output = fake_stderr.getvalue()
            self.assertIn('Scanning directory', output)
            self.assertIn('Loading card1.csv...', output)
            self.assertIn('Loading card2.csv...', output)
            self.assertIn('Loading card3.csv...', output)
            # Should have 2 unique names: bolt and shock
            self.assertIn('Opened 2 uniquely named cards from directory.', output)

        card_names = sorted([c.name for c in cards])
        self.assertEqual(card_names, ['bolt', 'shock'])

    def test_mtg_open_file_exclusions(self):
        rows = [
            {'name': 'Shock', 'type': 'Instant', 'rarity': 'Common'},
            {'name': 'Plains', 'type': 'Land', 'rarity': 'Common'}
        ]
        path = self.create_csv('exclusions.csv', rows)

        # Exclude Land type
        def exclude_lands(cardtype):
            return cardtype == 'land'

        cards = jdecode.mtg_open_file(path, exclude_types=exclude_lands)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, 'shock')

if __name__ == '__main__':
    unittest.main()
