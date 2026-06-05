
import unittest
import sys
import os
import json
import io
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr

# Add scripts and lib to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))

import mtg_analyze
import utils

class TestMtgAudit(unittest.TestCase):

    def test_audit_json_output(self):
        # Create a tiny mock dataset as a JSON string
        cards_json = {
            "data": {
                "TEST": {
                    "name": "Test Set",
                    "code": "TEST",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "White Weenie",
                            "manaCost": "{W}",
                            "types": ["Creature"],
                            "subtypes": ["Human"],
                            "text": "First strike",
                            "power": "1",
                            "toughness": "1",
                            "rarity": "common"
                        }
                    ]
                }
            }
        }

        with open('test_audit.json', 'w') as f:
            json.dump(cards_json, f)

        try:
            # Run audit with --json flag
            test_argv = ['mtg_analyze.py', 'audit', 'test_audit.json', '--json']
            with patch.object(sys, 'argv', test_argv):
                f = io.StringIO()
                with redirect_stdout(f):
                    mtg_analyze.main()

                output = f.getvalue()
                report = json.loads(output)

                # Check basic structure
                self.assertIn('summary', report)
                self.assertIn('checks', report)
                self.assertIn('suggestions', report)

                # Check for expected imbalances in this 1-card dataset
                labels = [c['label'] for c in report['checks']]
                self.assertTrue(any("Color Balance (U)" in l for l in labels))
                self.assertTrue(any("Functional Coverage (W)" in l for l in labels))

                # Check that Removal was caught as missing for White
                w_coverage = next(c for c in report['checks'] if "Functional Coverage (W)" in c['label'])
                self.assertIn("Removal", w_coverage['message'])

        finally:
            if os.path.exists('test_audit.json'):
                os.remove('test_audit.json')

    def test_audit_human_output(self):
        # Create a skewed dataset: Only Blue cards, no creatures, no removal
        cards_json = {
            "data": {
                "SKEW": {
                    "name": "Skew Set",
                    "code": "SKEW",
                    "type": "expansion",
                    "cards": [
                        {
                            "name": "Deep Research",
                            "manaCost": "{U}{U}",
                            "types": ["Instant"],
                            "text": "Draw two cards.",
                            "rarity": "rare"
                        }
                    ]
                }
            }
        }

        with open('test_skew.json', 'w') as f:
            json.dump(cards_json, f)

        try:
            test_argv = ['mtg_analyze.py', 'audit', 'test_skew.json', '--no-color']
            with patch.object(sys, 'argv', test_argv):
                f = io.StringIO()
                with redirect_stdout(f):
                    mtg_analyze.main()

                output = f.getvalue()

                # Verify key strings appear in the human report
                self.assertIn("DESIGN HEALTH AUDIT", output)
                self.assertIn("[WARNING]  Creature Density: Low creature count", output)
                self.assertIn("[ISSUE]    Functional Coverage (U): Missing core actions: Removal", output)
                self.assertIn("SUGGESTIONS:", output)
                self.assertIn("- Increase the number of creatures", output)

        finally:
            if os.path.exists('test_skew.json'):
                os.remove('test_skew.json')

if __name__ == '__main__':
    unittest.main()
