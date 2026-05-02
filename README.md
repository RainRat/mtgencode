# Magic: The Gathering Card Encoder

This project helps you turn Magic: The Gathering card data into a format that AI models can understand. It can also turn AI-generated text back into readable cards or card images.

**Main features:**
*   **Prepare Data:** Convert official card data for training AI models.
*   **View Results:** Decode AI output into readable cards, spreadsheets, or [Magic Set Editor](http://magicseteditor.boards.net) files.

---

## Installation

You can run this project using Docker (easier) or install it directly on your computer.

### Option 1: Docker (Recommended)
This method installs all dependencies automatically.

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
Verify your installation by running this quick test. This command encodes a sample card and then decodes it back into readable text:

```bash
python3 encode.py testdata/uthros.json | python3 decode.py
```

### 1. Get the Card Data
Download the latest card data from one of these reliable sources:
*   **[MTGJSON](https://mtgjson.com/downloads/all-files/):** We recommend **AllPrintings.json**, but you can use smaller files (like **Standard.json**) for faster testing.
*   **[Scryfall](https://scryfall.com/docs/api/bulk-data):** Download the **Oracle Cards** bulk data file for the most up-to-date card text and rulings.

After downloading, set up your data folder:
1.  Create a folder named `data` in this project.
2.  Place your downloaded JSON file inside the `data` folder.

### 2. Encode Cards (Data to Text)
Convert card data from various formats into a simple text format for AI training.

```bash
# Basic encoding from JSON
python3 encode.py data/AllPrintings.json encoded_output.txt --verbose

# Convert a Cockatrice XML database to encoded text
python3 encode.py my_database.xml encoded_output.txt
```
*   **Input:** Supports JSON (MTGJSON or Scryfall), CSV, XML, and MSE set files. You can also provide a folder path or a ZIP file to process all compatible files inside it.
*   **Output:** `encoded_output.txt` (A text file with one card per entry).

### 3. Decode Cards (Text to Readable)
Convert AI-generated text back into a readable format. You can see the results in your terminal or save them to a file. While primarily used for AI output, this tool also supports other card data formats (JSON, CSV, etc.) for easy conversion.

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
*   `-e vec`: Numerical format for mathematical models.
*   `-e custom`: Use your own user-defined formatting rules (see `lib/cardlib.py`).
*   `--nolabel`: Removes field labels (e.g., `|cost|`, `|text|`) from the output.
*   `--nolinetrans`: Disables the automatic reordering and normalization of card text lines.
*   `-r`, `--randomize`: Randomizes mana symbol order (e.g., `{U}{W}` vs `{W}{U}`) to help the AI learn better.
*   `-s`, `--stable`: Preserve the original order of cards from the input (the tool shuffles cards by default).
*   `--sort`: Sorts cards by `name`, `color`, `identity`, `type`, `cmc`, `rarity`, `power`, `toughness`, `loyalty`, `set`, `pack`, or `box` before encoding. Automatically enables `--stable`.
*   `--seed N`: Seed for the random number generator (Default: 1371367).
*   `--limit N`: Only process the first N cards.
*   `--sample N`: Shorthand for `--limit N`. The tool shuffles cards by default unless you use `--stable`.
*   `--booster N`: Simulate opening N booster packs. Distribution: 10 Common, 3 Uncommon, 1 Rare/Mythic, 1 Basic Land.
*   `--box N`: Simulate opening N booster boxes (36 packs each).
*   `-q`, `--quiet`: Suppress the progress bar and status messages.
*   `--report-unparsed FILE`: Save the raw JSON of cards that failed to parse into a separate file.

### `decode.py` (Viewing Results)
Options for formatting the output. While primarily used for AI output, this tool also supports other card data formats (**JSON, XML, CSV, etc.**) for easy conversion.

*   `-g`, `--gatherer`: Formats text like the official Gatherer website (Default). This applies modern wording and capitalization.
*   `--raw`: Shows raw text without special formatting.
*   `-t`, `--table`: Creates a formatted table for terminal view.
*   `-H`, `--html`: Creates a webpage with card images.
*   `--deck`: Creates a standard MTG decklist.
*   `--xml`: Creates a Cockatrice-compatible XML card database.
*   `--mse`: Creates a file for Magic Set Editor.
*   `-j`, `--json`: Creates a structured JSON file.
*   `--jsonl`: Creates a JSON Lines file (one card per line).
*   `--csv`: Creates a spreadsheet file.
*   `-M`, `--md`: Creates a Markdown document.
*   `--md-table`: Creates a Markdown table.
*   `-S`, `--summary`: Creates a compact one-line summary for each card.
*   `-f`, `--forum`: Use pretty formatting for mana symbols (compatible with MTG Salvation forums).
*   `-c`, `--creativity`: Calculate how unique these cards are compared to real Magic cards (requires Word2Vec).
*   `-d`, `--dump`: Show detailed debug information for cards that were not processed correctly.
*   `--color` / `--no-color`: Manually enable or disable ANSI color output in your terminal.
*   `--shuffle`: Randomizes the order of cards (the tool does not shuffle cards by default for decoding).
*   `--sort`: Sorts cards by `name`, `color`, `identity`, `type`, `cmc`, `rarity`, `power`, `toughness`, `loyalty`, `set`, `pack`, or `box`.
*   `--seed N`: Seed for the random number generator.
*   `--limit N`: Only process the first N cards.
*   `--sample N`: Pick N random cards (shorthand for `--shuffle --limit N`).
*   `-q`, `--quiet`: Suppress the progress bar and status messages.
*   `--booster N`: Simulate opening N booster packs. Distribution: 10 Common, 3 Uncommon, 1 Rare/Mythic, 1 Basic Land.
*   `--box N`: Simulate opening N booster boxes (36 packs each).
*   `--report-failed FILE`: Save the text of cards that failed to parse or validate into a separate file.

> **Important:** If you used a specific encoding (like `named`) when running `encode.py`, you **must** use that same encoding flag when running `decode.py`.
>
> ```bash
> # Example: If you encoded with 'named'
> python3 encode.py data/AllPrintings.json output.txt -e named
> # You must decode with 'named'
> python3 decode.py output.txt -e named
> ```

**Automatic Format Detection:**
The tool detects the format automatically based on the file extension of your output file:
*   `.html` -> Webpage
*   `.json` -> JSON data
*   `.jsonl` -> JSON Lines data
*   `.csv`  -> Spreadsheet
*   `.md`   -> Markdown document
*   `.mdt`  -> Markdown table
*   `.sum`, `.summary` -> One-line summary
*   `.deck`, `.dek` -> MTG Decklist
*   `.tbl`, `.table` -> Formatted table
*   `.xml` -> Cockatrice XML database
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

---

## Understanding the Encoded Format

When you run `encode.py`, the cards are converted into a specialized text format. This format uses symbols and "unary" numbers to help the AI learn card patterns more easily. AI models often find regular card text confusing, so we simplify it into a language they can better understand.

### Multi-Faced Cards
Multi-faced cards (Splits, Transforms, or Battles) are represented as discrete blocks separated by a single newline character (`\n`).

### Special Markers
| Symbol | Description | Example |
| :--- | :--- | :--- |
| `\|` | Separates card parts (like Name, Cost, or Type). | `\|5creature\|4legendary\|` |
| `@` | Represents the card's own name. | `@ gets +&^/+&^` |
| `\` | Indicates a new line of rules text. | `Flying\Trample` |
| `~` | Replaces a dash (e.g., in type lines). | `Enchantment~Aura` |
| `=` | Separates options in a choice or modal ability. | `[&^ = Option A = Option B]` |
| `%` | Represents a counter (like a +1/+1 or Charge counter). | `Put a % counter on @` |
| `[` `]` | Groups multiple choices or options together. | `[&^ = Option A = Option B]` |
| `{ }` | Mana symbols (symbols are doubled, e.g., `{WW}`). | `{GG}` |
| `T` | The Tap symbol. | `T: Add {GG}` |
| `Q` | The Untap symbol. | `Q: Untap @` |
| `uncast` | Replaces the verb "counter" (to avoid confusion with counters). | `uncast target spell` |

### Unary Numbers
To help the AI learn how to count, numbers are written as a sequence of symbols instead of digits.
*   **The Start (`&`)**: This symbol marks the beginning of a number.
*   **The Count (`^`)**: Each `^` symbol represents 1.
*   **Zero (`&`)**: A start marker by itself represents zero.
*   **Limit**: Standard counts only go up to 20 (`&^^^^^^^^^^^^^^^^^^^^`).
*   **Large Numbers**: Specific large values are written as words to keep the text short:
    *   25 = `twenty~five`
    *   30 = `thirty`
    *   40 = `forty`
    *   50 = `fifty`
    *   100 = `one hundred`
    *   200 = `two hundred`

**Examples**:
| Number | Encoded |
| :--- | :--- |
| 0 | `&` |
| 1 | `&^` |
| 2 | `&^^` |
| 5 | `&^^^^^` |

> **Note for Mana Costs:** Inside mana symbols `{ }`, the start marker `&` is omitted and only the count `^` is used for generic mana. Additionally, single-letter mana symbols are doubled (e.g., `{2}{R}` is encoded as `{^^RR}`).

### Rarity Markers
Rarity is encoded using a single-letter marker. These markers are often the second letter of the rarity name (to avoid collision with mana symbols like `C` for Colorless).

| Marker | Rarity | Mnemonic |
| :--- | :--- | :--- |
| `O` | Common | c**O**mmon |
| `N` | Uncommon | u**N**common |
| `A` | Rare | r**A**re |
| `Y` | Mythic | m**Y**thic |
| `I` | Special | spec**I**al |
| `L` | Basic Land | **L**and |

### Field Labels
If you don't use the `--nolabel` flag, each field is prefixed with a number for easier identification:

| Label | Card Part | Example |
| :--- | :--- | :--- |
| `0` | Rarity | `0O` (Common) |
| `1` | Name | `1grizzly bears` |
| `3` | Mana Cost | `3{GG}` |
| `4` | Supertypes | `4legendary` |
| `5` | Types | `5creature` |
| `6` | Subtypes | `6elf warrior` |
| `7` | Loyalty / Defense | `7&^^^` (3) |
| `8` | Power / Toughness | `8&^^/&^^` (2/2) |
| `9` | Rules Text | `9flying` |

> **Note:** The label `2` is skipped to avoid confusion with mana symbols (like `{2/B}`).

---

### Advanced Filtering
    Filter which cards the tool processes using search patterns, set codes, rarities, or even decklist files. These flags work across `encode.py`, `decode.py`, `sortcards.py`, `splitcards.py`, `scripts/summarize.py`, `scripts/mtg_validate.py`, `scripts/mtg_search.py`, `scripts/mtg_oracle.py`, `scripts/mtg_subset.py`, `scripts/mtg_lexicon.py`, `scripts/mtg_tokens.py`, `scripts/mtg_mechanics.py`, `scripts/mtg_diff.py`, `scripts/mtg_functional.py`, `scripts/mtg_skeleton.py`, `scripts/mtg_pips.py`, `scripts/mtg_complexity.py`, `scripts/mtg_curve.py`, `scripts/mtg_archetypes.py`, `scripts/mtg_balance.py`, `scripts/mtg_mana.py`, `scripts/mtg_stats.py`, and `scripts/mtg_actions.py`.

*   **Global Filters:**
    *   `--grep "pattern"`: Only include cards where the name, typeline, rules text, mana cost, or stats (P/T, loyalty, or defense) match the search pattern. Use multiple `--grep` flags for **AND** logic (all patterns must match).
    *   `--vgrep "pattern"` (or `--exclude`): Skip cards that match the search pattern (checks name, typeline, rules text, mana cost, and stats). Use multiple flags for **OR** logic (matching any pattern excludes the card).
*   **Field-Specific Filters:**
    *   `--grep-name`, `--grep-type`, `--grep-text`: Only include cards where the specific field matches the search pattern.
    *   `--grep-cost`, `--grep-pt`, `--grep-loyalty`: Only include cards whose mana cost, power/toughness, or loyalty/defense matches the search pattern.
    *   `--exclude-name`, `--exclude-type`, `--exclude-text`: Skip cards where the specific field matches the search pattern.
    *   `--exclude-cost`, `--exclude-pt`, `--exclude-loyalty`: Skip cards whose mana cost, power/toughness, or loyalty/defense matches the search pattern.
*   **Metadata Filters:**
    > **Note:** Repeat a flag to include multiple values using **OR** logic (e.g., `--rarity rare --rarity mythic` finds both rares and mythics).
    *   `--set CODE`: Only include cards from specific sets (e.g., `MOM`, `MRD`). Supports multiple sets.
    *   `--rarity NAME`: Only include cards of specific rarities (e.g., `common`, `rare`). Supports full names or shorthands: `O (Common), N (Uncommon), A (Rare), Y (Mythic), I (Special), L (Basic Land). Supports multiple values (OR logic).`
    *   `--colors SYMBOLS`: Only include cards with specific colors (e.g., `W`, `U`, `B`, `R`, `G`). Use `C` or `A` for colorless.
    *   `--identity SYMBOLS`: Only include cards with specific colors in their color identity (e.g., `W`, `U`, `B`, `R`, `G`). Use `C` or `A` for colorless.
    *   **Numerical Filters:** These flags support exact values (`5`), inequalities (`>3`, `<=2`, `!=0`), and ranges (`1-4`).
        *   `--id-count VALUE`: Filter by the number of colors in a card's color identity.
        *   `--cmc VALUE`: Filter by Converted Mana Cost (Mana Value).
        *   `--pow VALUE` (or `--power`): Filter by Power.
        *   `--tou VALUE` (or `--toughness`): Filter by Toughness.
        *   `--loy VALUE` (or `--loyalty`, `--defense`): Filter by Loyalty or Defense.
    *   `--mechanic NAME`: Only include cards with specific mechanical features or keyword abilities (e.g., `Flying`, `Activated`, `ETB Effect`).
    *   `--deck-filter FILE` (or `--decklist-filter`): Filter cards using a standard MTG decklist file. This also multiplies cards in the output based on their counts in the decklist.

> **Tip:** You can use internal shorthand markers with the `--rarity` flag: `O (Common), N (Uncommon), A (Rare), Y (Mythic), I (Special), and L (Basic Land).`

**Examples:**
```bash
# Process only Goblin creatures
python3 encode.py data/AllPrintings.json --grep "Goblin" --grep "Creature"

# Find only legendary artifacts from the MOM set
python3 scripts/summarize.py data/AllPrintings.json --grep "Legendary" --grep "Artifact" --set MOM

# Process only rare cards, excluding those with "Infect" in their name
python3 encode.py data/AllPrintings.json --rarity rare --exclude-name "Infect"

# Encode cards from a specific decklist to create a customized training set
python3 encode.py data/AllPrintings.json --deck-filter my_deck.txt encoded_deck.txt

# Find all creatures with power 5 or greater
python3 scripts/summarize.py data/AllPrintings.json --pow ">=5"

# Find rare cards with CMC between 2 and 4
python3 scripts/mtg_search.py data/AllPrintings.json --rarity rare --cmc "2-4"
```

---

## Training your own AI Model
Use your encoded card data to train a neural network that can design its own Magic cards.

1.  **Prepare the Data:** Create a text file of encoded cards.
    ```bash
    python3 encode.py data/AllPrintings.json data/output.txt
    ```
2.  **Train the Model:** Run the training script.
    ```bash
    python3 train.py --mode train --infile data/output.txt --epochs 10
    ```
3.  **Generate New Cards:** Use your trained model to create new card text.
    ```bash
    python3 train.py --mode sample --checkpoint checkpoint.pt --length 2000 > generated.txt
    ```
4.  **View the Results:** Turn the generated text back into readable cards.
    ```bash
    python3 decode.py generated.txt decoded.txt
    ```

---

## Utility Tools

Use these extra tools to manage and analyze your card data. Most are located in the `scripts/` folder, except for `sortcards.py` which is in the root directory.

### `sortcards.py` (Root Directory)
Organizes cards into categories (like Color or Card Type) and wraps them in `[spoiler]` tags. This is useful for posting cards on forums. It works with any card data (JSON, CSV, etc.) or encoded text.
```bash
# Basic sorting
python3 sortcards.py data/AllPrintings.json sorted_output.txt

# Sort encoded cards with filters and sampling
python3 sortcards.py encoded_output.txt sorted_sample.txt --sample 50 --grep "Elf"
```
*   **Options:** Supports `--encoding`, `--limit`, `--shuffle`, `--sample`, `--booster`, `--box`, and all **Advanced Filtering** flags.
*   `-S`, `--summary`: Output compact card summaries instead of full text.
*   `--md`, `--markdown`: Output in Markdown format with collapsible sections.
*   `--color` / `--no-color`: Enable or disable ANSI color output.

### `summarize.py`
Shows statistics, design budget analysis, mechanical profiling, and lexical diversity for your card data. It works with any card data (JSON, CSV, XML, encoded text, etc.).
```bash
# View statistics for the entire official dataset
python3 scripts/summarize.py data/AllPrintings.json

# View statistics for your encoded output
python3 scripts/summarize.py encoded_output.txt

# Show extra details and unusual cards (outliers)
python3 scripts/summarize.py encoded_output.txt -x

# Save statistics to a file (JSON format is auto-detected)
python3 scripts/summarize.py encoded_output.txt summary.json
```
*   **Options:**
    *   `-x`, `--outliers`: Show extra details and unusual cards.
    *   `-a`, `--all`: Show all information, including dumping invalid cards.
    *   `-t N`, `--top N`: Limit the number of entries in breakdown tables (Default: 10).
    *   `--sort CRITERIA`: Sort cards before summarizing.
    *   `--booster N`: Simulate opening N booster packs and summarize the contents.
    *   `--box N`: Simulate opening N booster boxes (36 packs each) and summarize the contents.
    *   `-j`, `--json`: Force JSON output.
    *   `--color` / `--no-color`: Enable or disable ANSI color output.
    *   Supports all **Advanced Filtering** flags (e.g., `--limit`, `--sample`, `--grep`, `--cmc`, `--mechanic`).

### `mtg_validate.py`
Validates card data for rule and formatting consistency (e.g., checking creature stats or land costs). It works with all supported input formats (JSON, CSV, XML, encoded text, etc.).
```bash
# Basic validation
python3 scripts/mtg_validate.py encoded_output.txt

# Print details for invalid cards
python3 scripts/mtg_validate.py data/AllPrintings.json --dump
```
*   **Options:**
    *   `-d`, `--dump`: Print full details for cards that failed validation.
    *   `-n LIMIT`, `--limit LIMIT`: Only process the first N cards.
    *   `--shuffle`: Randomize the order of cards before validating.
    *   `--sample N`: Pick N random cards (shorthand for `--shuffle --limit N`).
    *   `--sort CRITERIA`: Sort cards before validating.
    *   `--booster N`: Simulate opening N booster packs.
    *   `--box N`: Simulate opening N booster boxes (36 packs each).
    *   `-v`, `--verbose`: Enable detailed status messages.
    *   `-q`, `--quiet`: Suppress the progress bar.
    *   Supports all **Advanced Filtering** flags.

### `mtg_sets.py`
Lists and filters sets in an MTGJSON file. This is useful for seeing which sets are available in a large dataset like `AllPrintings.json`.
```bash
# List all sets in a dataset
python3 scripts/mtg_sets.py data/AllPrintings.json

# Find sets with "Masters" in their name or code
python3 scripts/mtg_sets.py data/AllPrintings.json --grep "Masters"
```
*   **Options:**
    *   `-n LIMIT`, `--limit LIMIT`: Only process the first N sets.
    *   `--shuffle`: Randomize the order of sets before listing.
    *   `--sample N`: Pick N random sets (shorthand for `--shuffle --limit N`).
    *   `--summarize`: Show statistics and mechanical profiling for the cards in the filtered sets.
    *   `--view`: Display a compact list of all cards in the filtered sets.
    *   `-t TOP`, `--top TOP`: Limit the number of entries in breakdown tables (used with `--summarize`).
    *   `--sort {code,name,type,date,count}`: Sort sets by a specific criterion (Default: date).
    *   `--reverse`: Reverse the sort order.
    *   `--grep PATTERN`: Only include sets matching a search pattern (checks name and code). Use multiple times for AND logic.
    *   `--color` / `--no-color`: Enable or disable ANSI color output.

### `mtg_diff.py`
Compares two card datasets and identifies additions, removals, and modifications. It highlights changes in cost, type, stats, text, and rarity.
```bash
# Compare two JSON datasets
python3 scripts/mtg_diff.py data/OldSet.json data/NewSet.json

# Compare encoded text against official data
python3 scripts/mtg_diff.py data/AllPrintings.json generated_cards.txt
```
*   **Options:**
    *   `--summary-only`: Only show count summary, not detailed card diffs.
    *   `--color` / `--no-color`: Enable or disable ANSI color output.
    *   Supports all **Advanced Filtering** flags (e.g., `--grep`, `--set`, `--rarity`).

### `mtg_compare.py`
Provides a side-by-side statistical comparison of two or more card datasets. This is useful for evaluating how well a generated dataset matches the characteristics of official Magic data.
```bash
# Compare official data vs generated cards
python3 scripts/mtg_compare.py data/AllPrintings.json generated.txt

# Compare multiple sets
python3 scripts/mtg_compare.py --set MOM --set ONE data/AllPrintings.json
```
*   **Comparison includes:** Card counts, validity, uniqueness, average stats (CMC, P/T), and percentage distributions for colors, types, and rarities.
*   **Options:**
    *   `--limit N`: Only process the first N cards from each input.
    *   `--shuffle`: Randomize cards before analysis.
    *   `--sample N`: Pick N random cards (shorthand for `--shuffle --limit N`).
    *   `--color` / `--no-color`: Enable or disable ANSI color output.
    *   Supports standard **Advanced Filtering** flags.

### `mtg_functional.py`
Identifies and groups 'functional reprints' (cards with different names but identical mana costs, types, stats, and rules text).
```bash
# List all functional reprints in a dataset
python3 scripts/mtg_functional.py data/AllPrintings.json

# Create a deduplicated dataset (one card per functional group)
python3 scripts/mtg_functional.py data/AllPrintings.json --dedupe unique_cards.json

# Find functional reprints of Goblins
python3 scripts/mtg_functional.py data/AllPrintings.json --grep "Goblin"
```
*   **Options:**
    *   `--table`: Display groups in a formatted table (Default).
    *   `--json`: Output groups as JSON.
    *   `--csv`: Output groups as CSV.
    *   `--dedupe`: Output a JSON file containing the full dataset with functional duplicates removed.
    *   Supports standard **Advanced Filtering** flags.

### `json2csv.py`, `csv2json.py` & `combinejson.py`
Used for integrating custom cards into your dataset. These scripts let you export existing cards to CSV, convert spreadsheets to JSON, and merge them with official data. See [CUSTOM.md](CUSTOM.md) for a full guide.
```bash
# Export existing cards to CSV for editing
python3 scripts/json2csv.py data/AllPrintings.json my_cards.csv --set MOM

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

### `mtg_oracle.py`
Search and display card details in a human-readable format. This tool is optimized for quick lookup with fuzzy name matching and **Smart Dataset Detection**.

**Smart Dataset Detection:**
If you are in a terminal, the tool automatically uses `data/AllPrintings.json` if it exists. You can also skip the file path and just provide the card name—the tool will figure out that the first argument is a query if it doesn't look like a file path.

```bash
# Quick lookup using the default dataset
python3 scripts/mtg_oracle.py "Grizzly Bears"

# Use fuzzy matching for misspelled names
python3 scripts/mtg_oracle.py "Grizly Beers"

# Find cards matching specific filters
python3 scripts/mtg_oracle.py --set MOM --rarity rare --grep "Battle"

# Find cards mechanically similar to a specific card
python3 scripts/mtg_oracle.py "Giant Growth" --similar
```
*   **Options:**
    *   `--similar`: Find and display cards that are mechanically similar to your search results.
    *   `--gatherer`: Use modern Gatherer-style wording and formatting.
    *   `-n`, `--limit`: Only process the first N cards.
    *   `--sample`: Pick N random cards (shorthand for `--shuffle --limit N`).
    *   `--sort`: Sort results by a specific criterion (e.g., `name`, `cmc`, `complexity`).
    *   `--color` / `--no-color`: Enable or disable ANSI color output.
    *   Supports all **Advanced Filtering** flags.

### `mtg_search.py`
Search card data (JSON, encoded text, etc.) and extract specific fields. This is useful for dataset exploration and creating lightweight card listings.
```bash
# List names and costs of all Goblins in a formatted table
python3 scripts/mtg_search.py data/AllPrintings.json -g "Goblin" -f "name,cost" -t

# Find all mythic rares with CMC > 7 and output as JSON
python3 scripts/mtg_search.py data/AllPrintings.json --rarity mythic --cmc ">7" -j
```
*   **Fields:** `name`, `cost`, `cmc`, `colors`, `type`, `stats`, `supertypes`, `types`, `subtypes`, `pt`, `power`, `toughness`, `loyalty`, `text`, `rarity`, `mechanics`, `identity`, `id_count`, `set`, `number`, `pack`, `box`, `summary` (alias `view` - provides a compact one-line string), `complexity` (alias `score`), `encoded`.
*   **Output Formats:** Plain text (default), `-t` (`--table`), `--md-table` (`--mdt`), `-j` (`--json`), `--jsonl`, `--csv`, `-S` (`--summary` - outputs one summary per line).
*   Common operations use shorthands like `-f` (for `--fields`) and `-g` (for `--grep` in this tool) to reduce friction.
*   Supports all **Advanced Filtering** flags, sorting, and booster/box simulation.
*   **Note:** The `box` and `pack` fields are automatically included in the output when simulation flags (`--booster` or `--box`) are used.

### `mtg_subset.py`
Creates a filtered subset of an MTGJSON file while preserving its structure. This is useful for creating specialized training datasets or lightweight card databases without losing set-level metadata.
```bash
# Create a subset of only Legendary cards from a specific set
python3 scripts/mtg_subset.py data/AllPrintings.json output.json --set MOM --grep "Legendary"

# Create a tiny dataset of 100 random rare creatures
python3 scripts/mtg_subset.py data/AllPrintings.json tiny.json --rarity rare --grep-type "Creature" --sample 100
```
*   Supports all **Advanced Filtering** flags and sorting.

### `mtg_mechanics.py`
Lists all mechanical keywords (e.g., Flying, Trample, Ward) recognized by the toolkit and can calculate their frequency in a dataset. This is useful for seeing which keywords are currently tracked or for analyzing the mechanical profile of a set.
```bash
# List all recognized mechanics
python3 scripts/mtg_mechanics.py

# Count frequency of mechanics in a dataset
python3 scripts/mtg_mechanics.py data/AllPrintings.json --set MOM
```
*   **Options:**
    *   `--sort {name,count}`: Sort results by name or frequency.
    *   `--limit N`: Only show the top N mechanics.
    *   Supports standard **Advanced Filtering** flags (e.g., `--grep`, `--set`, `--rarity`).

### `mtg_lexicon.py`
Analyzes the characteristic vocabulary (lexicon) of each Magic color. This identifies "signature words" that appear significantly more often in one color compared to others, helping verify the color-pie integrity of AI designs.
```bash
# Analyze lexicon for a dataset
python3 scripts/mtg_lexicon.py data/AllPrintings.json

# Compare lexicon between official data and AI output
python3 scripts/mtg_lexicon.py data/AllPrintings.json --compare generated.txt
```
*   **Options:**
    *   `-t N`, `--top N`: Number of signature words to show per color (Default: 10).
    *   `--min-len N`: Minimum word length to include in analysis (Default: 4).
    *   `--compare FILE`: Side-by-side comparison with a second dataset.
    *   **Filtering:** Supports `--grep`, `--set`, `--rarity`, and `--mechanic`.

### `mtg_tokens.py`
Extracts and summarizes token definitions from card rules text. This tool identifies the properties of tokens created by cards (like P/T, color, types, and abilities) and de-duplicates them to show a consolidated list.
```bash
# List all unique tokens found in a dataset
python3 scripts/mtg_tokens.py data/AllPrintings.json

# Extract tokens from a specific set and output to JSON
python3 scripts/mtg_tokens.py data/AllPrintings.json --set MOM --json
```
*   **Options:**
    *   `--json`: Output results in structured JSON format.
    *   Supports standard **Advanced Filtering** flags (`--grep`, `--set`, `--rarity`).

### `mtg_skeleton.py`
Generates a "Design Skeleton" (Set Skeleton) for a dataset, bucketing cards by their type and CMC (Converted Mana Cost). This provides a high-level view of the mechanical curve and balance of a set.
```bash
# Generate skeleton for a dataset
python3 scripts/mtg_skeleton.py data/AllPrintings.json --set MOM

# Analyze the curve of a specific color identity
python3 scripts/mtg_skeleton.py data/AllPrintings.json --identity "W"
```
*   Supports all **Advanced Filtering** flags, sorting, and booster/box simulation.

### `mtg_archetypes.py`
Profiles the 10 primary two-color archetypes in a dataset. It identifies "signpost" uncommons, signature mechanical themes, and curve statistics for each color pair.
```bash
# Analyze archetypes in a specific set
python3 scripts/mtg_archetypes.py data/AllPrintings.json --set MOM

# Filter analysis by specific mechanics or rarities
python3 scripts/mtg_archetypes.py data/AllPrintings.json --rarity uncommon --mechanic "Flying"
```
*   **Options:**
    *   `--min-cards N`: Minimum number of cards required to profile an archetype (Default: 5).
    *   `--top-mechanics N`: Number of signature mechanics to show per archetype (Default: 3).
    *   Supports all standard **Advanced Filtering** flags.

### `mtg_balance.py`
Analyzes and compares the archetype balance (color pair distribution) between two or more datasets. This helps verify if a generated dataset maintains the same color identity "gravity" as its training data.
```bash
# Compare the balance of a generated set against an official set
python3 scripts/mtg_balance.py data/AllPrintings.json generated.txt --set MOM

# See which color pairs are over-represented in a card pool
python3 scripts/mtg_balance.py my_cards.json
```
*   **Options:**
    *   `--limit N`: Only process the first N cards from each input.
    *   `--set`, `--rarity`: Filter inputs by set or rarity.
    *   `--color` / `--no-color`: Enable or disable ANSI color output.

### `mtg_complexity.py`
Analyzes the heuristic design complexity of cards in a dataset. It calculates a "Complexity Score" based on word count, line count, mechanical density, and color identity, helping designers identify "wordy" or overly complex cards.
```bash
# Find the most complex cards in a set
python3 scripts/mtg_complexity.py data/AllPrintings.json --set MOM --limit 10

# Compare average complexity between rarities
python3 scripts/mtg_complexity.py data/AllPrintings.json --rarity common --rarity rare
```

*   **Options:**
    *   `-n LIMIT`, `--limit LIMIT`: Number of top complex cards to show in the table (Default: 20).
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports standard **Advanced Filtering** flags (`--grep`, `--set`, `--rarity`, `--colors`, `--cmc`, `--mechanic`).

### `mtg_curve.py`
Analyzes and visualizes the mana curve (CMC distribution) of a card dataset or decklist. It provides a visual distribution chart, global and color-specific average CMC calculations, and a breakdown by card type.
```bash
# Analyze the curve of a specific set
python3 scripts/mtg_curve.py data/AllPrintings.json --set MOM

# Analyze a decklist file
python3 scripts/mtg_curve.py my_deck.txt

# See the curve for only creatures in a dataset
python3 scripts/mtg_curve.py data/AllPrintings.json --grep-type "Creature"
```
*   **Options:**
    *   `-n LIMIT`, `--limit LIMIT`: Only process the first N cards.
    *   `--sample N`: Pick N random cards (shorthand for --shuffle --limit N).
    *   `--booster N`: Simulate opening N booster packs and analyze their curve.
    *   `--box N`: Simulate opening N booster boxes and analyze their curve.
    *   Supports all **Advanced Filtering** flags.

### `mtg_mana.py`
Identifies mana-producing cards using rules text patterns (e.g., 'Add {G}', 'any color') and intrinsic basic land types. It categorizes producers into Dorks (creatures), Rocks (artifacts), Lands, and Rituals (spells), profiles produced colors, and identifies color-fixing density.
```bash
# Analyze mana production for a specific set
python3 scripts/mtg_mana.py data/AllPrintings.json --set MOM

# Compare mana fixing between official data and AI output
python3 scripts/mtg_mana.py data/AllPrintings.json --compare generated.txt
```
*   **Options:**
    *   `--compare FILE`: Side-by-side comparison with a second dataset.
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports all **Advanced Filtering** flags and simulation.

### `mtg_stats.py`
Analyzes creature combat stats (Power/Toughness) and Planeswalker loyalty in a dataset. It provides a "Combat Stat Curve" (average P/T per CMC), a color-based stat breakdown, and a frequency heatmap of P/T combinations.
```bash
# Analyze stats for a specific set
python3 scripts/mtg_stats.py data/AllPrintings.json --set MOM

# Compare stats of rare creatures vs common creatures
python3 scripts/mtg_stats.py data/AllPrintings.json --rarity rare --grep-type "Creature"
```
*   **Options:**
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports standard **Advanced Filtering** flags and simulation.

### `mtg_actions.py`
Analyzes and categorizes functional card effects (Removal, Protection, Buffs, Card Advantage, and Disruption) in a dataset. This tool identifies how cards interact with the game state, providing a profile of a set's interactivity.
```bash
# Analyze actions for a specific set
python3 scripts/mtg_actions.py data/AllPrintings.json --set MOM

# Compare action density of different colors
python3 scripts/mtg_actions.py data/AllPrintings.json --colors R
```
*   **Options:**
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports standard **Advanced Filtering** flags and simulation.

### `mtg_pips.py`
Analyzes the distribution of mana symbols (pips) in a dataset. It counts symbols from casting costs and rules text (optionally via `--include-text`), supports table, JSON, and CSV output formats, and integrates with standard Advanced Filtering and simulation flags.
```bash
# Analyze pip distribution for a set
python3 scripts/mtg_pips.py data/AllPrintings.json --set MOM

# Include pips found in rules text (e.g. activation costs)
python3 scripts/mtg_pips.py data/AllPrintings.json --set MOM --include-text
```
*   **Options:**
    *   `--include-text`: Include mana symbols found in rules text.
    *   `--sort {name,count}`: Sort results by symbol name or frequency.
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports standard **Advanced Filtering** flags and simulation.

### `distances.py` & `sum.py`
These tools allow for bulk creativity analysis of your generated cards. `distances.py` calculates the semantic and name distance between your cards and the official dataset, and `sum.py` provides a statistical summary of the results.

```bash
# Calculate distances for a generated dataset
python3 scripts/distances.py generated_cards.txt distances.txt --parallel

# Summarize the results
python3 scripts/sum.py distances.txt
```
*   **Note:** Like the `--creativity` flag in `decode.py`, these tools require `data/cbow.bin` and `data/output.txt`. See [DEPENDENCIES.md](DEPENDENCIES.md) for setup instructions.

### `splitcards.py`
Splits a card dataset into multiple files. This is essential for creating training and validation sets for AI models. It supports all input formats (JSON, CSV, encoded text, etc.).
```bash
# Split encoded cards into training and validation sets
python3 scripts/splitcards.py encoded_output.txt --outputs train.txt val.txt --ratios 0.9 0.1

# Split a JSON file into multiple parts
python3 scripts/splitcards.py data/AllPrintings.json --outputs part1.json part2.json --ratios 0.5 0.5 -f json

# Create a filtered training set (Red and Black cards only)
python3 scripts/splitcards.py data/AllPrintings.json --outputs rb_train.txt rb_val.txt --ratios 0.9 0.1 --colors RB
```
*   **Options:**
    *   `-f`, `--format`: Output format (`text`, `json`, `jsonl`, `csv`). Default is `text`.
    *   `-v`, `--verbose`: Enable detailed status messages.
    *   `-q`, `--quiet`: Suppress the progress bar.
    *   `--encoding`: Choose the text encoding format (e.g., `std`, `named`, `vec`).
    *   `--shuffle` / `--no-shuffle`: Whether to randomize the order of cards before splitting (Enabled by default).
    *   `--sort CRITERIA`: Sort cards before splitting.
    *   `--booster N`: Simulate opening N booster packs before splitting.
    *   `--box N`: Simulate opening N booster boxes (36 packs each) before splitting.
    *   Supports all **Advanced Filtering** flags (e.g., `--limit`, `--sample`, `--grep`, `--colors`, `--cmc`, `--mechanic`).

---

## Troubleshooting

*   **Missing Data:** If you see an error about `punkt` or `punkt_tab`, run the download command in the Installation section.
*   **File Not Found:** If `encode.py` fails, check that your `data/AllPrintings.json` file is in the correct folder.
*   **Format Mismatch:** If you used a specific encoding flag (like `-e named`) with `encode.py`, you **must** use the same flag with `decode.py`.
*   **Missing Symbols:** If card symbols (like mana) show as squares, you need to install the Magic fonts. See [DEPENDENCIES.md](DEPENDENCIES.md) for help.
*   **Parsing Errors:** Some cards in older JSON formats may not parse correctly. Use the `--report-unparsed` (for `encode.py`) or `--report-failed` (for `decode.py`) flags to identify them.

**Example for importing a Cockatrice XML database:**
```bash
python3 scripts/summarize.py my_custom_set.xml
```

---

## Testing & Development

### Running Tests
To ensure everything is working correctly, you can run the full test suite. We use `pytest` for testing:

```bash
# Run all tests
PYTHONPATH=. python3 -m pytest
```

### Contributing
We welcome contributions! If you are a developer looking to help:
1.  **Read AGENTS.md:** It contains technical guidelines and tips for working with this codebase.
2.  **Verify Changes:** Always run the tests before submitting any pull requests.
3.  **Style:** Keep documentation simple and follow the 'Plain English' principles used throughout this project.

---

## Documentation & Help
*   [DEPENDENCIES.md](DEPENDENCIES.md): Setup for external tools like Magic Set Editor.
*   [CUSTOM.md](CUSTOM.md): How to use your own custom cards.
*   [AGENTS.md](AGENTS.md): Technical info for AI agents.
