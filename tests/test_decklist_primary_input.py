import os
import sys
import unittest
import tempfile
import io
from unittest.mock import patch

# Ensure lib is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
import jdecode

class TestDecklistPrimaryInput(unittest.TestCase):
    def setUp(self):
        self.temp_files = []
        self.real_exists = os.path.exists

    def tearDown(self):
        for f in self.temp_files:
            if os.path.exists(f):
                os.remove(f)

    def create_temp_file(self, content, suffix='.txt'):
        with tempfile.NamedTemporaryFile(mode='w+', suffix=suffix, delete=False, encoding='utf-8') as tmp:
            tmp.write(content)
            self.temp_files.append(tmp.name)
        return tmp.name

    def test_decklist_file_input(self):
        # Create a decklist file. Use "Fire" instead of "Fire // Ice" to match mock data indexing
        decklist_content = "4 Grizzly Bears\n2 Fire\n"
        decklist_path = self.create_temp_file(decklist_content, suffix='.deck')

        # Create a mock AllPrintings.json
        mock_data = {
            "data": {
                "LEA": {
                    "code": "LEA",
                    "name": "Limited Edition Alpha",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Grizzly Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "rarity": "Common",
                            "power": "2",
                            "toughness": "2",
                            "text": "Nom nom nom."
                        }
                    ]
                },
                "APC": {
                    "code": "APC",
                    "name": "Apocalypse",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Fire",
                            "manaCost": "{1}{R}",
                            "types": ["Instant"],
                            "rarity": "Uncommon",
                            "number": "101a",
                            "text": "Fire deals 2 damage."
                        },
                        {
                            "name": "Ice",
                            "manaCost": "{1}{U}",
                            "types": ["Instant"],
                            "rarity": "Uncommon",
                            "number": "101b",
                            "text": "Tap target permanent."
                        }
                    ]
                }
            }
        }

        with patch('os.path.exists') as mock_exists:
            def side_effect(path):
                if 'AllPrintings.json' in path:
                    return True
                return self.real_exists(path)

            mock_exists.side_effect = side_effect

            with patch('jdecode.mtg_open_json') as mock_mtg_json:
                mock_mtg_json.return_value = jdecode.mtg_open_json_obj(mock_data)

                # Now call mtg_open_file with the decklist path
                cards = jdecode.mtg_open_file(decklist_path, verbose=True)

                # Check results
                # 4 Grizzly Bears + 2 Fire = 6 cards
                self.assertEqual(len(cards), 6)

                names = [c.name.lower() for c in cards]
                self.assertEqual(names.count('grizzly bears'), 4)
                self.assertEqual(names.count('fire'), 2)

                # Verify that Fire has Ice as bside
                fire_cards = [c for c in cards if c.name.lower() == 'fire']
                for c in fire_cards:
                    self.assertIsNotNone(c.bside)
                    self.assertEqual(c.bside.name.lower(), 'ice')

    @patch('sys.stdin', new_callable=io.StringIO)
    def test_decklist_stdin_input(self, mock_stdin):
        # Setup mock stdin
        decklist_content = "1 Grizzly Bears\n"
        mock_stdin.write(decklist_content)
        mock_stdin.seek(0)

        # Mock data
        mock_data = {
            "data": {
                "LEA": {
                    "code": "LEA",
                    "name": "Limited Edition Alpha",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Grizzly Bears",
                            "manaCost": "{1}{G}",
                            "types": ["Creature"],
                            "rarity": "Common",
                            "power": "2",
                            "toughness": "2"
                        }
                    ]
                }
            }
        }

        with patch('os.path.exists') as mock_exists:
            mock_exists.side_effect = lambda path: 'AllPrintings.json' in path or self.real_exists(path)

            with patch('jdecode.mtg_open_json') as mock_mtg_json:
                mock_mtg_json.return_value = jdecode.mtg_open_json_obj(mock_data)

                # Call mtg_open_file with '-' for stdin
                cards = jdecode.mtg_open_file('-', verbose=True)

                self.assertEqual(len(cards), 1)
                self.assertEqual(cards[0].name.lower(), 'grizzly bears')

    def test_decklist_no_hydration_file(self):
        # Create a decklist file
        decklist_content = "4 Grizzly Bears\n"
        decklist_path = self.create_temp_file(decklist_content, suffix='.deck')

        # Mock os.path.exists to return False for AllPrintings.json
        with patch('os.path.exists') as mock_exists:
            mock_exists.side_effect = lambda path: False if 'AllPrintings.json' in path else self.real_exists(path)

            # This should fall back to treating it as encoded text
            # Since it doesn't have field separators, it will be one unparsed/invalid card
            cards = jdecode.mtg_open_file(decklist_path, verbose=False)

            # It might return 0 valid cards because it fails to parse as encoded text
            valid_cards = [c for c in cards if c.valid]
            self.assertEqual(len(valid_cards), 0)

if __name__ == '__main__':
    unittest.main()
