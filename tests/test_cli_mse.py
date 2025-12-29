import os
import shutil
import subprocess
import pytest

# Ensure we have a valid encoded input file for testing
INPUT_FILE = "tests/test_encoded_input.txt"
OUTPUT_FILE = "tests/test_output_mse"

@pytest.fixture(scope="module")
def setup_input_file():
    # Create a minimal encoded file
    with open(INPUT_FILE, "w") as f:
        f.write("|5artifact|4|6|7|8|9T: add {GG}.|3{}|0A|1mox emerald|\n")
    yield
    # Cleanup
    if os.path.exists(INPUT_FILE):
        os.remove(INPUT_FILE)

def test_mse_generation_crash(setup_input_file):
    """
    Test that running decode.py with --mse and an output file WITHOUT --text
    currently crashes (or passes after the fix).
    """
    # Clean up previous output if any
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    if os.path.exists(OUTPUT_FILE + ".mse-set"):
        os.remove(OUTPUT_FILE + ".mse-set")

    # Run the command: python3 decode.py infile outfile --mse
    # We expect this to fail with exit code 1 (or crash) in the current buggy state,
    # and pass with exit code 0 after the fix.

    cmd = ["python3", "decode.py", INPUT_FILE, OUTPUT_FILE, "--mse"]

    # We use subprocess.run to capture the result
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Check if the process succeeded
    if result.returncode == 0:
        # If it succeeded, verify the files exist
        assert os.path.exists(OUTPUT_FILE), "Text output file was not created"
        assert os.path.exists(OUTPUT_FILE + ".mse-set"), "MSE set file was not created"
    else:
        # If it failed, we expect the specific FileNotFoundError crash in stderr
        # But for the purpose of TDD, we want this test to PASS when the code is fixed.
        # So asserting returncode == 0 is the goal.
        pytest.fail(f"decode.py failed with return code {result.returncode}.\nStderr: {result.stderr}")

def teardown_module(module):
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    if os.path.exists(OUTPUT_FILE + ".mse-set"):
        os.remove(OUTPUT_FILE + ".mse-set")
