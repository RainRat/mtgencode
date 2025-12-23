# mtgencode

Utilities to process Magic: The Gathering card data for neural network training and decoding.

This project provides tools to:
1.  **Encode** card data (from [MTGJSON](https://mtgjson.com)) into text formats suitable for training neural networks (RNNs, Transformers, etc.).
2.  **Decode** generated text back into human-readable formats, including visual spoilers and [Magic Set Editor](http://magicseteditor.boards.net) files.

## Installation

### Option 1: Docker (Recommended)

For a consistent environment with all dependencies pre-installed:

**Linux/macOS:**
```bash
./docker-interactive.sh
```

**Windows:**
```bash
./docker-interactive.bat
```

### Option 2: Local Installation

**Prerequisites:**
*   Python 3.9+
*   `pip`

**Steps:**

1.  Clone the repository:
    ```bash
    git clone https://github.com/billzorn/mtgencode.git
    cd mtgencode
    ```

2.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Download required NLTK data:
    ```bash
    python3 -m nltk.downloader punkt punkt_tab
    ```

## Usage

The project consists of two main scripts: `encode.py` and `decode.py`.

### 1. Encode Data
Converts JSON card data into a text format for training.

**Prerequisite:** Download `AllPrintings.json` from [MTGJSON](https://mtgjson.com/downloads/all-files/).

```bash
# Basic encoding
python3 encode.py -v data/AllPrintings.json encoded_output.txt
```

**Options:**
*   `-e {std,named,vec,...}`: Select encoding format (default: `std`).
*   `-r`: Randomize mana symbols for data augmentation.
*   `--nolinetrans`: Keep original text line order.

### 2. Decode Data
Converts encoded text (e.g., neural network output) back into readable cards.

```bash
# Basic decoding to text
python3 decode.py -v encoded_output.txt decoded_output.txt
```

**Options:**
*   `--mse`: Output a Magic Set Editor set file (`.mse-set`).
*   `--html`: Output a styled HTML file.
*   `-g`: Enable "Gatherer" mode for prettier text formatting.

### 3. Training a Neural Network

This tool prepares data for training but does not include the training code itself.
Originally designed for [mtg-rnn](https://github.com/billzorn/mtg-rnn) (Lua/Torch), the `encoded_output.txt` can be used with any modern text generation model (e.g., GPT-2, LSTM).

**Workflow:**
1.  Use `encode.py` to create `input.txt` from MTGJSON.
2.  Train your model on `input.txt`.
3.  Generate text from your model.
4.  Use `decode.py` to convert the generated text into readable cards.

## Development

To run the test suite:

```bash
python3 -m pytest
```

## Documentation

*   [AGENTS.md](AGENTS.md): Instructions for AI agents working on this codebase.
*   [DEPENDENCIES.md](DEPENDENCIES.md): External tools setup (MTGJSON, Magic Set Editor, word2vec).
