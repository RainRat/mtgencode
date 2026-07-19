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

from scripts.mtg_forge import main, apply_color_shift, apply_buff_nerf, apply_scale

class TestMtgForgeModifiers(unittest.TestCase):

    def test_apply_color_shift_monocolor_to_monocolor(self):
        card = {
            'name': 'Green Grizzly Bears',
            'manaCost': '{1}{G}',
            'text': 'Forestwalk\nGreen creatures get +1/+1.',
            'colors': ['G'],
            'colorIdentity': ['G']
        }
        res = apply_color_shift(card, 'U')
        self.assertEqual(res['name'], 'Blue Grizzly Bears')
        self.assertEqual(res['manaCost'], '{1}{U}')
        self.assertEqual(res['text'], 'Islandwalk\nBlue creatures get +1/+1.')
        self.assertEqual(res['colors'], ['U'])
        self.assertEqual(res['colorIdentity'], ['U'])

    def test_apply_color_shift_monocolor_to_multicolor(self):
        card = {
            'name': 'Green Bear',
            'manaCost': '{1}{G}',
            'text': 'Forestwalk',
            'colors': ['G'],
            'colorIdentity': ['G']
        }
        res = apply_color_shift(card, 'U,B')
        self.assertEqual(res['name'], 'Blue and Black Bear')
        self.assertEqual(res['manaCost'], '{1}{U}{B}')
        self.assertEqual(res['text'], 'Island and Swampwalk')
        self.assertEqual(res['colors'], ['U', 'B'])
        self.assertEqual(res['colorIdentity'], ['U', 'B'])

    def test_apply_color_shift_multicolor_to_monocolor(self):
        card = {
            'name': 'Selesnya Guildmage',
            'manaCost': '{G/W}',
            'colors': ['G', 'W'],
            'colorIdentity': ['G', 'W']
        }
        res = apply_color_shift(card, 'B')
        self.assertEqual(res['manaCost'], '{B/B}')  # Both G and W map to B
        self.assertEqual(res['colors'], ['B'])
        self.assertEqual(res['colorIdentity'], ['B'])

    def test_apply_buff_nerf_creature(self):
        card = {
            'name': 'Bear',
            'power': '2',
            'toughness': '2',
            'pt': '2/2'
        }
        res = apply_buff_nerf(card, 2)
        self.assertEqual(res['power'], '4')
        self.assertEqual(res['toughness'], '4')
        self.assertEqual(res['pt'], '4/4')

        res2 = apply_buff_nerf(card, -3)
        self.assertEqual(res2['power'], '1')
        self.assertEqual(res2['toughness'], '1')
        self.assertEqual(res2['pt'], '1/1')

    def test_apply_buff_nerf_loyalty_and_defense(self):
        card = {
            'name': 'Hero',
            'loyalty': '3',
            'defense': '5'
        }
        res = apply_buff_nerf(card, 2)
        self.assertEqual(res['loyalty'], '5')
        self.assertEqual(res['defense'], '7')

    def test_apply_scale_up_and_down(self):
        card = {
            'name': 'Giant',
            'manaCost': '{4}{R}',
            'power': '4',
            'toughness': '6'
        }
        # Scale up by 2
        res = apply_scale(card, 2.0, multiply=True)
        self.assertEqual(res['power'], '8')
        self.assertEqual(res['toughness'], '12')
        self.assertEqual(res['manaCost'], '{8}{R}')

        # Scale down by 2
        res2 = apply_scale(res, 2.0, multiply=False)
        self.assertEqual(res2['power'], '4')
        self.assertEqual(res2['toughness'], '6')
        self.assertEqual(res2['manaCost'], '{4}{R}')

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_cli_integration(self, mock_stdout):
        test_args = [
            'mtg_forge.py',
            '--name', 'Green Grizzly Bears',
            '--type', 'Creature',
            '--pt', '2/2',
            '--cost', '{1}{G}',
            '--color-shift', 'R',
            '--buff', '3',
            '--scale-up', '1.5'
        ]
        # Explanation of integration:
        # Original: Green Grizzly Bears, Creature, 2/2, {1}{G}.
        # Color-shifted to R: name -> Red Grizzly Bears, cost -> {1}{R}
        # Buffed by 3: 2/2 + 3/3 -> 5/5
        # Scaled up by 1.5: 5/5 * 1.5 -> 8/8, and {1}{R} -> generic 1 * 1.5 -> 2 -> {2}{R}
        with patch('sys.argv', test_args):
            main()

        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output['name'], 'Red Grizzly Bears')
        self.assertEqual(output['manaCost'], '{2}{R}')
        self.assertEqual(output['power'], '8')
        self.assertEqual(output['toughness'], '8')
        self.assertEqual(output['colorIdentity'], ['R'])

if __name__ == '__main__':
    unittest.main()