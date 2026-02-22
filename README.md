# Magic: The Gathering Card Encoder

This project helps you turn Magic: The Gathering card data into a format that AI models can understand. It can also turn AI-generated text back into readable cards or card images.

**Main features:**
*   **Prepare Data:** Convert official card data for training AI models (like RNNs or Transformers).
*   **View Results:** Decode AI output into readable cards, spreadsheets, or [Magic Set Editor](http://magicseteditor.boards.net) files.

---

## Installation

You can run this project using Docker (easier) or install it directly on your computer.

### Option 1: Docker (Recommended)
This method handles all dependencies for you.

*   **Linux/macOS:** Run `./docker-interactive.sh`
*   **Windows:** Run `./docker-interactive.bat`

### Option 2: Local Installation
If you prefer to run it directly on your machine:

1.  **Check Prerequisites:**
    You need Python 3.9 or newer. If you don't have it, download it from [python.org](https://www.python.org/).
    Check your version by running:
    ```bash
    python3 --version
    ```

2.  **Get the Code:**
    ```bash
    git clone https://github.com/billzorn/mtgencode.git
    cd mtgencode
    ```

3.  **Install Libraries:**
    ```bash
    python3 -m pip install -r requirements.txt
    ```

4.  **Download Language Data:**
    This tool uses the NLTK library for processing text. Run this command to download the required data:
    ```bash
    python3 -m nltk.downloader punkt punkt_tab
    ```

---

## Quick Start Guide

### 0. Verify Installation
Ensure everything is set up correctly by running this quick test. It encodes a sample card and then decodes it back into readable text:

```bash
python3 encode.py testdata/uthros.json | python3 decode.py
```

### 1. Get the Card Data
Download the latest card data from [MTGJSON](https://mtgjson.com/downloads/all-files/). We recommend **AllPrintings.json**, but you can use smaller files (like **Standard.json**) for faster testing.

After downloading, set up your data folder:
1.  Create a folder named `data` in this project.
2.  Place your downloaded JSON file inside the `data` folder.

### 2. Encode Cards (JSON to Text)
Convert the JSON data into a simple text format for AI training.

```bash
# Basic encoding
python3 encode.py data/AllPrintings.json encoded_output.txt --verbose
```
*   **Input:** `data/AllPrintings.json`. You can also provide a folder path or a ZIP file to process all compatible files inside it.
*   **Output:** `encoded_output.txt` (A text file with one card per entry).

### 3. Decode Cards (Text to Readable)
Convert encoded text back into a readable format. You can see the results in your terminal or save them to a file.

```bash
# View decoded cards in your terminal
python3 decode.py encoded_output.txt

# Save to a file (the format is detected from the file extension)
python3 decode.py encoded_output.txt my_cards.html
```

**Want to see card images?**
Generate a file for [Magic Set Editor](https://magicseteditor.boards.net/):
```bash
python3 decode.py encoded_output.txt my_set.mse-set
```
*   **Note:** Open the `.mse-set` file in Magic Set Editor to view and edit your cards.

---

## Usage Details

### `encode.py` (Preparing Data)
Customization options for formatting data:
*   `-e std`: Standard format (Name comes last). Default.
*   `-e named`: Name comes first.
*   `-e noname`: No card names included.
*   `-e rfields`: Randomizes the order of fields (like cost, types, text) for each card.
*   `-e old`: Legacy encoding format.
*   `-e norarity`: Standard format but without rarity labels.
*   `-e vec`: Numerical format for vector-based models.
*   `-e custom`: Use your own user-defined formatting rules (see `lib/cardlib.py`).
*   `-r`, `--randomize`: Randomizes mana symbol order (e.g., `{U}{W}` vs `{W}{U}`) to help the AI learn better.
*   `-s`, `--stable`: Preserve the original order of cards from the input (shuffling is enabled by default).
*   `--sort`: Sorts cards by `name`, `color`, `type`, or `cmc` before encoding. Automatically enables `--stable`.
*   `--limit N`: Only process the first N cards.
*   `--sample N`: Shorthand for `--limit N`. Cards are shuffled by default unless `--stable` is used.

### `decode.py` (Viewing Results)
Options for formatting the output:
*   `--gatherer`: Formats text like the official Gatherer website (Default).
*   `--raw`: Shows raw text without special formatting.
*   `--html`: Creates a webpage with card images.
*   `--deck`: Creates a standard MTG decklist.
*   `--mse`: Creates a file for Magic Set Editor.
*   `--json`: Creates a structured JSON file.
*   `--jsonl`: Creates a JSON Lines file (one card per line).
*   `--csv`: Creates a spreadsheet file.
*   `--md`: Creates a Markdown document.
*   `--summary`: Creates a compact one-line summary for each card.
*   `--color` / `--no-color`: Manually enable or disable ANSI color output in your terminal.
*   `--shuffle`: Randomizes the order of cards (shuffling is off by default for decoding).
*   `--sort`: Sorts cards by `name`, `color`, `type`, or `cmc`.
*   `--limit N`: Only process the first N cards.
*   `--sample N`: Pick N random cards (shorthand for `--shuffle --limit N`).

> **Important:** If you used a specific encoding (like `named`) when running `encode.py`, you **must** use that same encoding flag when running `decode.py`.
>
> ```bash
> # Example: If you encoded with 'named'
> python3 encode.py data/AllPrintings.json output.txt -e named
> # You must decode with 'named'
> python3 decode.py output.txt -e named
> ```

**Automatic Format Detection:**
The tool automatically selects the format based on the file extension of your output file:
*   `.html` -> Webpage
*   `.json` -> JSON data
*   `.jsonl` -> JSON Lines data
*   `.csv`  -> Spreadsheet
*   `.md`   -> Markdown document
*   `.sum`, `.summary` -> One-line summary
*   `.deck`, `.dek` -> MTG Decklist
*   `.mse-set` -> Magic Set Editor file

### Using Pipes
You can chain these tools together using the pipe (`|`) symbol. This lets you process cards in one step without saving temporary files.

```bash
# Encode 10 cards and view them immediately
python3 encode.py data/AllPrintings.json --limit 10 | python3 decode.py

# Encode, sort, and save to a file
python3 encode.py data/AllPrintings.json --limit 100 | python3 sortcards.py - sorted_cards.txt
```
*   **Note:** Use a hyphen (`-`) as the filename to tell a script to read from standard input.

### Advanced Filtering
You can filter which cards are processed using regular expressions (regex). This works for `encode.py`, `decode.py`, and `summarize.py`.

*   `--grep "pattern"`: Only include cards that match the pattern. Patterns are checked against the name, type, and rules text fields individually. Use multiple `--grep` flags for AND logic.
*   `--vgrep "pattern"` (or `--exclude`): Skip cards that match the pattern.

**Examples:**
```bash
# Process only Goblin creatures
python3 encode.py data/AllPrintings.json --grep "Goblin" --grep "Creature"

# Exclude cards with the "Infect" mechanic
python3 encode.py data/AllPrintings.json --vgrep "Infect"

# Find only legendary artifacts
python3 scripts/summarize.py data/AllPrintings.json --grep "Legendary" --grep "Artifact"
```

---

## Training a Neural Network
*Note: This project prepares the data. You will need a separate tool to train the model.*

1.  **Prepare Data:** Use `encode.py` to create a text file (e.g., `input.txt`).
2.  **Train:** Use an AI training tool (like `mtg-rnn` or a Transformer) on your text file.
3.  **Generate:** Use your trained model to create new text.
4.  **Decode:** Use `decode.py` to turn that generated text into readable cards.

---

## Utility Scripts

We provide extra tools in the `scripts/` folder to help you manage your data.

### `sortcards.py`
Organizes encoded cards into categories (like Color or Card Type) and wraps them in `[spoiler]` tags. This is useful for posting generated cards on forums.
```bash
# Basic sorting
python3 sortcards.py encoded_output.txt sorted_output.txt

# Sort with filters and sampling
python3 sortcards.py encoded_output.txt sorted_sample.txt --sample 50 --grep "Elf"
```
*   **Options:** Supports `--encoding`, `--limit`, `--shuffle`, `--sample`, `--grep`, and `--vgrep`.

### `summarize.py`
Shows statistics about your encoded cards, such as the distribution of card types and colors:
```bash
# View statistics in your terminal
python3 scripts/summarize.py encoded_output.txt

# Show extra details and unusual cards (outliers)
python3 scripts/summarize.py encoded_output.txt -x

# Save statistics to a file (JSON format is auto-detected)
python3 scripts/summarize.py encoded_output.txt summary.json
```
*   **Options:**
    *   `-x`, `--outliers`: Show extra details and unusual cards.
    *   `-a`, `--all`: Show all information, including dumping invalid cards.
    *   `--json`: Force JSON output.
    *   Supports filtering flags: `--limit`, `--sample`, `--grep`, `--vgrep`.

### `csv2json.py` & `combinejson.py`
Used for integrating custom cards into your dataset. See [CUSTOM.md](CUSTOM.md) for a full guide.
```bash
# Convert a spreadsheet to JSON
python3 scripts/csv2json.py my_cards.csv my_cards.json

# Merge custom cards with official data
python3 scripts/combinejson.py data/AllPrintings.json my_cards.json AllCards.json
```

### `extract_one.py`
Extracts a single card from the massive `AllPrintings.json` file. This is useful for testing a specific card without loading the entire dataset.
```bash
python3 scripts/extract_one.py data/AllPrintings.json SET_CODE "Card Name"
```

### `splitcards.py`
Splits a card dataset into multiple files, which is essential for creating training and validation sets for AI models.
```bash
python3 scripts/splitcards.py encoded_output.txt --outputs train.txt val.txt --ratios 0.9 0.1
```

---

## Troubleshooting

*   **Missing Data:** If you see an error about `punkt` or `punkt_tab`, run the download command in the Installation section.
*   **File Not Found:** If `encode.py` fails, check that your `data/AllPrintings.json` file is in the correct folder.
*   **Format Mismatch:** If you used a specific encoding flag (like `-e named`) with `encode.py`, you **must** use the same flag with `decode.py`.
*   **Missing Symbols:** If card symbols (like mana) show as squares, you need to install the Magic fonts. See [DEPENDENCIES.md](DEPENDENCIES.md) for help.
*   **Parsing Errors:** Some cards in older JSON formats may not parse correctly. Use the `--report-unparsed` (for `encode.py`) or `--report-failed` (for `decode.py`) flags to identify them.

---

## Documentation & Help
*   [DEPENDENCIES.md](DEPENDENCIES.md): Setup for external tools like Magic Set Editor.
*   [CUSTOM.md](CUSTOM.md): How to use your own custom cards.
*   [AGENTS.md](AGENTS.md): Technical info for AI agents.
*   **Run Tests:** `python3 -m pytest`
