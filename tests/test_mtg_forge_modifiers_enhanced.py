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

from scripts.mtg_forge import (
    main, apply_modifiers, parse_replace_arg, run_replace, adjust_generic_mana
)

class TestMtgForgeModifiersEnhanced(unittest.TestCase):

    def test_parse_replace_arg(self):
        # Test simple slash split
        p, r = parse_replace_arg("Bear/Beast")
        self.assertEqual(p, "Bear")
        self.assertEqual(r, "Beast")

        # Test sed-style slash
        p, r = parse_replace_arg("/Bear/Beast/")
        self.assertEqual(p, "Bear")
        self.assertEqual(r, "Beast")

        # Test sed-style other delimiter
        p, r = parse_replace_arg("|Bear|Beast|")
        self.assertEqual(p, "Bear")
        self.assertEqual(r, "Beast")

        p, r = parse_replace_arg("s/Bear/Beast/")
        self.assertEqual(p, "Bear")
        self.assertEqual(r, "Beast")

        p, r = parse_replace_arg("s~Bear~Beast~")
        self.assertEqual(p, "Bear")
        self.assertEqual(r, "Beast")

        # Empty/invalid
        p, r = parse_replace_arg("")
        self.assertIsNone(p)
        self.assertIsNone(r)

    def test_run_replace(self):
        # Literal replace
        res = run_replace("Grizzly Bear", "Bear/Beast")
        self.assertEqual(res, "Grizzly Beast")

        # Regex replace
        res = run_replace("Bear 123 Bear", r"\d+/ABC")
        self.assertEqual(res, "Bear ABC Bear")

        # Fallback to literal replace for invalid regex
        res = run_replace("Bear [ Bear", "[/ABC")
        self.assertEqual(res, "Bear ABC Bear")

    def test_adjust_generic_mana(self):
        # Generic mana reduction
        self.assertEqual(adjust_generic_mana("{3}{W}{U}", -1), "{2}{W}{U}")
        self.assertEqual(adjust_generic_mana("{3}{W}{U}", -3), "{W}{U}")
        self.assertEqual(adjust_generic_mana("{3}{W}{U}", -4), "{W}{U}")

        # Generic mana addition
        self.assertEqual(adjust_generic_mana("{W}{U}", 2), "{2}{W}{U}")
        self.assertEqual(adjust_generic_mana("{1}{G}", 1), "{2}{G}")

        # No mana cost
        self.assertEqual(adjust_generic_mana("", 2), "{2}")
        self.assertEqual(adjust_generic_mana("", -1), "")

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_cli_replacements_and_mana(self, mock_stdout):
        test_args = [
            'mtg_forge.py',
            '--name', 'Grizzly Bears',
            '--type', 'Creature - Bear',
            '--cost', '{1}{G}',
            '--text', 'A simple Bear.',
            '--replace-name', 'Bears/Pandas',
            '--replace-type', 'Bear/Panda',
            '--replace', 'Bear/Panda',
            '--mana-adjust', '2'
        ]
        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Grizzly Pandas')
        self.assertEqual(output['manaCost'], '{3}{G}')
        # 'Panda' becomes 'panda' here because Card constructor lowercases incoming JSON
        # rules text before re-applying sentence-case tokenization.
        self.assertEqual(output['text'], 'A simple panda.')
        self.assertIn('Panda', output['subtypes'])

if __name__ == '__main__':
    unittest.main()
