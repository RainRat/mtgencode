import json
import io
import sys
import os
import unittest
import tempfile
from unittest.mock import patch
from scripts.mtg_query import main as query_main
from scripts.mtg_query import get_subtype_forms

class TestMtgQueryTribal(unittest.TestCase):

    def run_main(self, args):
        with patch('sys.argv', ['mtg_query.py', 'tribal'] + args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('sys.stderr', new=io.StringIO()) as fake_err:
                    try:
                        query_main()
                        code = 0
                    except SystemExit as e:
                        code = e.code if isinstance(e.code, int) else 0
                    return code, fake_out.getvalue(), fake_err.getvalue()

    def test_get_subtype_forms(self):
        # Irregular plurals
        self.assertIn("elves", get_subtype_forms("elf"))
        self.assertIn("wolves", get_subtype_forms("wolf"))
        self.assertIn("merfolk", get_subtype_forms("merfolk"))
        self.assertIn("fungi", get_subtype_forms("fungus"))
        self.assertIn("octopuses", get_subtype_forms("octopus"))
        self.assertIn("dwarves", get_subtype_forms("dwarf"))

        # Ending in -y
        self.assertIn("allies", get_subtype_forms("ally"))
        self.assertNotIn("allies", get_subtype_forms("donkey")) # Zombie exception or ay/ey/oy/uy check

        # Ending in sh, ch, s, x, z
        self.assertIn("fishes", get_subtype_forms("fish"))
        self.assertIn("foxes", get_subtype_forms("fox"))

        # Standard s
        self.assertIn("goblins", get_subtype_forms("goblin"))

    def test_tribal_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_tribal.json")
            # Create a deck of cards representing Goblins, Elves, and Wizards
            with open(test_file, "w") as f:
                json.dump([
                    {
                        "name": "Goblin Piker",
                        "manaCost": "{1}{R}",
                        "types": ["Creature"],
                        "subtypes": ["Goblin", "Warrior"],
                        "power": "2",
                        "toughness": "1",
                        "text": "",
                        "rarity": "Common"
                    },
                    {
                        "name": "Goblin King",
                        "manaCost": "{1}{R}{R}",
                        "types": ["Creature"],
                        "subtypes": ["Goblin"],
                        "power": "2",
                        "toughness": "2",
                        "text": "Other Goblins get +1/+1 and have mountainwalk.",
                        "rarity": "Rare"
                    },
                    {
                        "name": "Llanowar Elves",
                        "manaCost": "{G}",
                        "types": ["Creature"],
                        "subtypes": ["Elf", "Druid"],
                        "power": "1",
                        "toughness": "1",
                        "text": "{T}: Add {G}.",
                        "rarity": "Common"
                    },
                    {
                        "name": "Elvish Archdruid",
                        "manaCost": "{1}{G}{G}",
                        "types": ["Creature"],
                        "subtypes": ["Elf", "Druid"],
                        "power": "2",
                        "toughness": "2",
                        "text": "Other Elves you control get +1/+1. {T}: Add {G} for each Elf you control.",
                        "rarity": "Rare"
                    },
                    {
                        "name": "Goblin Grenade",
                        "manaCost": "{R}",
                        "types": ["Sorcery"],
                        "text": "As an additional cost to cast this spell, sacrifice a Goblin.",
                        "rarity": "Uncommon"
                    },
                    {
                        "name": "Divination",
                        "manaCost": "{2}{U}",
                        "types": ["Sorcery"],
                        "text": "Draw two cards.",
                        "rarity": "Common"
                    }
                ], f)

            # 1. Test Goblin Piker -> should find Goblin King (shares Goblin subtype) and Goblin Grenade (mentions Goblin in text)
            # but NOT Divination or Llanowar Elves
            code, out, err = self.run_main(["Goblin Piker", test_file, "--no-color", "--fields", "name"])
            self.assertEqual(code, 0)
            self.assertIn("Goblin King", out)
            self.assertIn("Goblin Grenade", out)
            self.assertNotIn("Llanowar Elves", out)
            self.assertNotIn("Divination", out)
            self.assertNotIn("Goblin Piker", out) # Should not find itself

            # 2. Test Llanowar Elves -> should find Elvish Archdruid (shares Elf, plus text mentions "Elves" which is irregular plural of "Elf")
            code, out, err = self.run_main(["Llanowar Elves", test_file, "--no-color", "--fields", "name"])
            self.assertEqual(code, 0)
            self.assertIn("Elvish Archdruid", out)
            self.assertNotIn("Goblin King", out)

    def test_tribal_no_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_no_tribal.json")
            with open(test_file, "w") as f:
                json.dump([
                    {
                        "name": "Unique Card",
                        "manaCost": "{W}",
                        "types": ["Instant"],
                        "text": "Gain 3 life.",
                        "rarity": "Common"
                    }
                ], f)

            code, out, err = self.run_main(["Unique Card", test_file, "--no-color"])
            self.assertIn("has no subtypes to query.", err)

    def test_shell_tribal_integration(self):
        # Test executing /tribal under mtg_query shell subcommand
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_shell.json")
            with open(test_file, "w") as f:
                json.dump([
                    {
                        "name": "Goblin Piker",
                        "manaCost": "{1}{R}",
                        "types": ["Creature"],
                        "subtypes": ["Goblin"],
                        "power": "2",
                        "toughness": "1",
                        "text": ""
                    },
                    {
                        "name": "Goblin King",
                        "manaCost": "{1}{R}{R}",
                        "types": ["Creature"],
                        "subtypes": ["Goblin"],
                        "power": "2",
                        "toughness": "2",
                        "text": ""
                    }
                ], f)

            # We can mock input for the interactive shell to run `/tribal Goblin Piker` then `exit`
            inputs = ["/tribal Goblin Piker", "exit"]
            with patch('builtins.input', side_effect=inputs):
                with patch('sys.argv', ['mtg_query.py', 'shell', test_file, '--no-color']):
                    with patch('sys.stdout', new=io.StringIO()) as fake_out:
                        with patch('sys.stderr', new=io.StringIO()) as fake_err:
                            try:
                                query_main()
                            except SystemExit:
                                pass
                            out = fake_out.getvalue()
                            # We expect Goblin King to be listed in the output table of the /tribal command
                            self.assertIn("Goblin King", out)

if __name__ == '__main__':
    unittest.main()
