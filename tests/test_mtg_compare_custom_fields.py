import subprocess
import os

def test_compare_custom_fields():
    """Verify that mtg_query.py compare respects the --fields argument."""
    cmd = [
        "python3", "scripts/mtg_query.py", "compare",
        "Uthros", "Invasion of Tarkir", "testdata/",
        "--fields", "name,cost,stats,signature"
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = f".:./lib:./scripts:{env.get('PYTHONPATH', '')}"

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    assert result.returncode == 0
    output = result.stdout

    # Check for requested field headers in the output
    assert "Field" in output
    assert "Name" in output
    assert "Cost" in output
    assert "Stats" in output
    assert "Signature" in output

    # Check that a default field NOT in the list is NOT in the output (e.g., Rarity or CMC)
    assert "Rarity" not in output
    assert "CMC" not in output

def test_compare_signature_alias():
    """Verify that signature field can be accessed via aliases."""
    cmd = [
        "python3", "scripts/mtg_query.py", "compare",
        "Uthros", "Invasion of Tarkir", "testdata/",
        "--fields", "name,unique"
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = f".:./lib:./scripts:{env.get('PYTHONPATH', '')}"

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    assert result.returncode == 0
    output = result.stdout
    assert "Signature" in output
