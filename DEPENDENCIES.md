# External Tools & Data

This guide covers external data and tools that extend the functionality of `mtgencode`.

## 1. Magic: The Gathering Data (Required)

To encode card data, you need the JSON corpus from [MTGJSON](https://mtgjson.com).

1.  Go to [MTGJSON Downloads](https://mtgjson.com/downloads/all-files/).
2.  Download the **AllPrintings.json** file.
3.  Place it in the `data/` directory of this repository (create the directory if it doesn't exist):
    ```bash
    mkdir -p data
    # Move your downloaded file here
    mv ~/Downloads/AllPrintings.json data/
    ```

## 2. Magic Set Editor (Optional)

[Magic Set Editor (MSE)](https://magicseteditor.boards.net/) is a tool for designing and visualizing custom cards. The `decode.py` script can generate `.mse-set` files (using the `--mse` flag) that you can open in MSE.

### Installation

*   **Windows:** Download the installer from the [official website](https://magicseteditor.boards.net/page/downloads) and run it.
*   **Linux/macOS:** MSE is a Windows application, but it runs well on Linux and macOS using [Wine](https://www.winehq.org/).
    1.  Install Wine (e.g., `sudo apt install wine` on Ubuntu/Debian).
    2.  Download the MSE Windows installer.
    3.  Run the installer with Wine: `wine mse-installer.exe`.

### Fonts
If cards in MSE do not look correct (e.g., missing text or incorrect symbols), you may need to install the specific Magic fonts:
*   **Beleren** (Bold, Small Caps)
*   **Relay** (Medium)
*   **MPlantin**

Search for "Magic The Gathering fonts" online to find these font files, then install them to your system (or `~/.wine/drive_c/windows/Fonts/` for Wine).

### Usage
To generate an MSE set file:
```bash
python3 decode.py encoded_output.txt my_set --mse
```
This creates a file named `my_set.mse-set`. Double-click it or open it from within MSE.

## 3. Creativity Analysis (Advanced)

The `--creativity` flag in `decode.py` calculates how unique your generated cards are by comparing them to existing real cards using vector embeddings. This feature requires a pre-computed vector model (`data/cbow.bin`).

**Note:** This is an advanced feature that requires compiling the legacy C `word2vec` tool.

### Setup Steps

1.  **Install word2vec:**
    You need the original C implementation of `word2vec`. Since the original Google Code repository is archived, you may need to find a mirror on GitHub (e.g., search for "word2vec C").
    Compile the `word2vec` binary and ensure it is executable.

2.  **Generate Vectors:**
    You must generate the binary model from the specific encoding format you are using.

    ```bash
    # 1. Create vector-compatible text from your data
    python3 encode.py -v data/AllPrintings.json data/cbow.txt -s -e vec

    # 2. Compile cbow.bin using word2vec
    # (Example command; adjust flags as needed for your word2vec version)
    ./word2vec -train data/cbow.txt -output data/cbow.bin -cbow 1 -size 200 -window 8 -negative 25 -hs 0 -sample 1e-4 -threads 20 -binary 1 -iter 15
    ```

3.  **Run with Creativity:**
    Once `data/cbow.bin` exists, you can run decoding with creativity analysis:
    ```bash
    python3 decode.py encoded_output.txt decoded.txt --creativity
    ```
