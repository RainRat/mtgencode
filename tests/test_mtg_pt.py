import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os

# Add the root directory to the path so we can import the scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.mtg_pt import main, get_pt_values

class TestMtgPt(unittest.TestCase):
    def setUp(self):
        # Sample card data for testing
        self.mock_card = MagicMock()
        self.mock_card.name = "Grizzly Bears"
        self.mock_card.is_creature = True
        self.mock_card.pt_p = "&^^" # Unary 2
        self.mock_card.pt_t = "&^^" # Unary 2
        self.mock_card.cost.colors = ['G']
        self.mock_card.cost.cmc = 2
        self.mock_card.bside = None

        self.mock_card2 = MagicMock()
        self.mock_card2.name = "Elite Vanguard"
        self.mock_card2.is_creature = True
        self.mock_card2.pt_p = "&^^" # Unary 2
        self.mock_card2.pt_t = "&^"  # Unary 1
        self.mock_card2.cost.colors = ['W']
        self.mock_card2.cost.cmc = 1
        self.mock_card2.bside = None

    def test_get_pt_values(self):
        """Test extraction of P/T values from single and multi-faced cards."""
        values = get_pt_values(self.mock_card)
        self.assertEqual(values, [(2, 2)])

        # Test multi-faced
        self.mock_card.bside = MagicMock()
        self.mock_card.bside.pt_p = "&^^^"
        self.mock_card.bside.pt_t = "&^^^"
        self.mock_card.bside.bside = None

        values = get_pt_values(self.mock_card)
        self.assertEqual(values, [(2, 2), (3, 3)])

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_basic_output(self, mock_stdout, mock_open):
        """Test the basic CLI output of mtg_pt.py."""
        mock_open.return_value = [self.mock_card, self.mock_card2]

        # We need to mock sys.argv
        with patch('sys.argv', ['mtg_pt.py', 'test.json', '--no-color']):
            main()

        output = mock_stdout.getvalue()

        # Verify headers
        self.assertIn("COMBAT STAT ANALYSIS", output)
        self.assertIn("Combat Grid", output)
        self.assertIn("Combat Orientation", output)
        self.assertIn("Average Stats by Color", output)

        # Verify some data points
        # Grizzly Bears (2/2) -> (2,2)
        # Elite Vanguard (2/1) -> (2,1)
        self.assertIn("Aggressive (P > T)", output)
        self.assertIn("Balanced (P = T)", output)
        self.assertIn("G", output)
        self.assertIn("W", output)

    @patch('jdecode.mtg_open_file')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_no_creatures(self, mock_stdout, mock_open):
        """Test behavior when no creatures are found."""
        non_creature = MagicMock()
        non_creature.is_creature = False
        mock_open.return_value = [non_creature]

        with patch('sys.argv', ['mtg_pt.py', 'test.json']):
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                main()
                self.assertIn("No creatures found", mock_stderr.getvalue())

if __name__ == '__main__':
    unittest.main()
