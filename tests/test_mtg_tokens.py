import subprocess
import json
import os

def test_mtg_tokens_basic():
    """Test the mtg_tokens.py script with a sample dataset."""
    test_file = "testdata/token_test.json"
    if not os.path.exists(test_file):
        # Create it if it doesn't exist (though it should from previous steps)
        from scripts.mtg_tokens import main
        # This is a bit complex to run main directly due to argparse
        pass

    # Run the script and capture output
    cmd = ["python3", "scripts/mtg_tokens.py", test_file, "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    assert result.returncode == 0
    tokens = json.loads(result.stdout)

    # Verify we found the expected number of unique tokens
    # (1/1 Soldier, 2/2 Drake, 3/3 Beast, Food, Treasure)
    assert len(tokens) == 5

    # Verify specific token properties
    names = [t['name'] for t in tokens]
    assert "1/1 White Soldier Token" in names
    assert "Food Token" in names
    assert "Treasure Token" in names

    # Verify counts
    soldier_token = next(t for t in tokens if "Soldier" in t['name'])
    assert soldier_token['count'] == 2

def test_mtg_tokens_filtering():
    """Test filtering in mtg_tokens.py."""
    test_file = "testdata/token_test.json"

    # Filter for only cards with "Beast" in name
    cmd = ["python3", "scripts/mtg_tokens.py", test_file, "--grep", "Beast", "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    assert result.returncode == 0
    tokens = json.loads(result.stdout)

    assert len(tokens) == 1
    assert tokens[0]['name'] == "3/3 Green Beast Token"
