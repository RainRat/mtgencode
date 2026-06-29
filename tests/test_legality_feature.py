import unittest
from unittest.mock import patch
import io
import sys
import os
import json
import tempfile

# Add lib and scripts to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'lib'))

from scripts.mtg_query import main as query_main
from scripts.mtg_deckgen import main as deckgen_main

class TestLegalityFeature(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a temporary card dataset with legalities
        cls.test_data = {
            "data": {
                "TEST": {
                    "code": "TEST",
                    "name": "Test Set",
                    "type": "expansion",
                    "releaseDate": "2023-01-01",
                    "cards": [
                        {
                            "name": "Standard Card",
                            "manaCost": "{1}{W}",
                            "type": "Creature - Human",
                            "types": ["creature"],
                            "subtypes": ["human"],
                            "pt": "2/2",
                            "rarity": "common",
                            "legalities": {"standard": "legal", "commander": "legal", "legacy": "legal"}
                        },
                        {
                            "name": "Commander Only",
                            "manaCost": "{1}{U}",
                            "type": "Instant",
                            "types": ["instant"],
                            "rarity": "rare",
                            "legalities": {"standard": "not_legal", "commander": "legal", "legacy": "legal"}
                        },
                        {
                            "name": "Banned Everywhere",
                            "manaCost": "{B}",
                            "type": "Sorcery",
                            "types": ["sorcery"],
                            "rarity": "mythic",
                            "legalities": {"standard": "not_legal", "commander": "not_legal", "legacy": "not_legal"}
                        }
                    ]
                }
            }
        }
        cls.tf = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(cls.test_data, cls.tf)
        cls.tf.close()
        cls.tf_path = cls.tf.name

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.tf_path):
            os.remove(cls.tf_path)

    def test_search_legality_filter(self):
        """Test legality filtering in search subcommand."""
        # Search for cards legal in standard
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_query.py', 'search', self.tf_path, '--legal', 'standard', '--no-color']):
                query_main()
                output = fake_out.getvalue()
                self.assertIn("Standard Card", output)
                self.assertNotIn("Commander Only", output)
                self.assertNotIn("Banned Everywhere", output)

        # Search for cards legal in commander
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_query.py', 'search', self.tf_path, '--legal', 'commander', '--no-color']):
                query_main()
                output = fake_out.getvalue()
                self.assertIn("Standard Card", output)
                self.assertIn("Commander Only", output)
                self.assertNotIn("Banned Everywhere", output)

    def test_oracle_legality_display(self):
        """Test legality display in oracle subcommand."""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with patch('sys.argv', ['mtg_query.py', 'oracle', 'Standard Card', self.tf_path, '--no-color']):
                query_main()
                output = fake_out.getvalue()
                self.assertIn("LEGALITIES:", output)
                self.assertIn("COMMANDER", output)
                self.assertIn("LEGACY", output)
                self.assertIn("STANDARD", output)

    def test_deckgen_legality_filter(self):
        """Test legality filtering in deckgen tool."""
        # Generate a standard deck (should only include standard legal cards)
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            # We use standard format, which will now filter by 'standard' legality
            with patch('sys.argv', ['mtg_deckgen.py', self.tf_path, '--format', 'standard', '--legal', 'standard', '--creatures', '1', '--spells', '0', '--lands', '0', '--no-color']):
                deckgen_main()
                output = fake_out.getvalue()
                self.assertIn("Standard Card", output)
                self.assertNotIn("Commander Only", output)

if __name__ == '__main__':
    unittest.main()
