# Magic: The Gathering Card Encoder

This project helps you turn Magic: The Gathering card data into a format that AI models can understand. It can also turn AI-generated text back into readable cards or card images.

**Main features:**
*   **Prepare Data:** Convert official card data for training AI models.
*   **View Results:** Decode AI output into readable cards, spreadsheets, or [Magic Set Editor](http://magicseteditor.boards.net) files.

---

## Installation

Use Docker for the easiest setup. It installs everything automatically.

### Option 1: Use Docker (Recommended)
*   **Linux/macOS:** Run `./docker-interactive.sh`
*   **Windows:** Run `./docker-interactive.bat`

### Option 2: Install on your computer
Follow these steps if you want to run the tool directly on your machine:

1.  **Install Python:**
    Download Python 3.9 or newer from [python.org](https://www.python.org/).
    Check your version:
    ```bash
    python3 --version
    ```

2.  **Download this project:**
    ```bash
    git clone https://github.com/billzorn/mtgencode.git
    cd mtgencode
    ```

3.  **Install required libraries:**
    ```bash
    python3 -m pip install -r requirements.txt
    ```

4.  **Download text processing data:**
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

The `encode.py` tool converts cards into a specialized text format. This format uses symbols and "counting" numbers to help the AI learn patterns. Regular card text is often too complex for AI models, so we simplify it.

### Multi-Faced Cards
Multi-faced cards (like Split or Transform cards) are written as separate blocks of text.

### Special Markers
| Symbol | Description | Example |
| :--- | :--- | :--- |
| `\|` | Separates parts of a card (like Name, Cost, or Type). | `\|5creature\|4legendary\|` |
| `@` | Replaces the card's name. | `@ gets +&^/+&^` |
| `\` | Starts a new line of text. | `Flying\Trample` |
| `~` | Replaces a dash (used in type lines). | `Enchantment~Aura` |
| `=` | Separates options in a list of choices. | `[&^ = Option A = Option B]` |
| `%` | Replaces the word "counter" (like a +1/+1 counter). | `Put a % counter on @` |
| `[` `]` | Groups multiple choices together. | `[&^ = Option A = Option B]` |
| `{ }` | Mana symbols. Single letters are doubled (e.g., `{WW}`). | `{GG}` |
| `T` | The Tap symbol. | `T: Add {GG}` |
| `Q` | The Untap symbol. | `Q: Untap @` |
| `uncast` | Replaces the word "counter" when it means to cancel a spell. | `uncast target spell` |

### Counting Numbers (Unary)
To help the AI learn how to count, we write numbers as a sequence of symbols instead of using digits.
*   **Start marker (`&`)**: Marks the beginning of a number.
*   **Count marker (`^`)**: Each symbol represents 1.
*   **Zero (`&`)**: A start marker by itself means zero.
*   **Limit**: Numbers only go up to 20 (`&^^^^^^^^^^^^^^^^^^^^`).
*   **Large Numbers**: We write common large numbers as words to keep the text short:
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

> **Note for Mana Costs:** Inside mana symbols `{ }`, we skip the `&` marker. We only use `^` for generic mana.

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
If you don't use the `--nolabel` flag, each field is prefixed with a number. These labels allow the AI (and the decoder) to identify parts of the card regardless of their position in the text.

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

**Default Field Sequence:**
While labels make the order flexible, the standard (`std`) format uses this specific sequence:
1.  **Types** (Label 5)
2.  **Supertypes** (Label 4)
3.  **Subtypes** (Label 6)
4.  **Loyalty / Defense** (Label 7)
5.  **Power / Toughness** (Label 8)
6.  **Rules Text** (Label 9)
7.  **Mana Cost** (Label 3)
8.  **Rarity** (Label 0)
9.  **Name** (Label 1)

> **Note:** The label `2` is skipped to avoid confusion with mana symbols (like `{2/B}`).

---

## Advanced Filtering

Filter cards using search patterns, set codes, rarities, or decklist files. These flags work across most tools in this project.

*   **Global Filters:**
    *   `--grep "pattern"`: Include cards that match the search pattern. The tool checks name, type, rules text, cost, and stats. Use multiple `--grep` flags to require all patterns to match.
    *   `--vgrep "pattern"` (or `--exclude`): Skip cards that match the search pattern. Use multiple flags to skip cards that match any of the patterns.
*   **Field-Specific Filters:**
    *   `--grep-name`, `--grep-type`, `--grep-text`: Include cards where the specific field matches the search pattern.
    *   `--grep-cost`, `--grep-pt`, `--grep-loyalty`: Include cards where the mana cost, power/toughness, or loyalty/defense matches the search pattern.
    *   `--exclude-name`, `--exclude-type`, `--exclude-text`: Skip cards where the specific field matches the search pattern.
    *   `--exclude-cost`, `--exclude-pt`, `--exclude-loyalty`: Skip cards where the mana cost, power/toughness, or loyalty/defense matches the search pattern.
*   **Metadata Filters:**
    > **Note:** Use a flag multiple times to include multiple values (e.g., `--rarity rare --rarity mythic` finds both rares and mythics).
    *   `--set CODE`: Include cards from specific sets (e.g., `MOM`, `MRD`).
    *   `--rarity NAME`: Include cards of specific rarities (e.g., `common`, `rare`). You can use full names or shorthands: `O` (Common), `N` (Uncommon), `A` (Rare), `Y` (Mythic), `I` (Special), or `L` (Basic Land).
    *   `--colors SYMBOLS`: Include cards with specific colors (e.g., `W`, `U`, `B`, `R`, `G`). Use `C` or `A` for colorless.
    *   `--identity SYMBOLS`: Include cards with specific colors in their color identity.
    *   `--produces COLORS`: Include cards that can produce specific colors of mana (W, U, B, R, G, C, or Any).
    *   **Numerical Filters:** These flags support exact values (`5`), inequalities (`>3`, `<=2`, `!=0`), and ranges (`1-4`).
        *   `--id-count VALUE`: Filter by the number of colors in a card's color identity.
        *   `--cmc VALUE`: Filter by mana value (Converted Mana Cost).
        *   `--pow VALUE`: Filter by Power.
        *   `--tou VALUE`: Filter by Toughness.
        *   `--loy VALUE`: Filter by Loyalty or Defense.
    *   `--mechanic NAME`: Include cards with specific keyword abilities or features (e.g., `Flying`, `Activated`, `ETB Effect`).
    *   `--action NAME`: Include cards with specific functional actions (e.g., `Removal`, `Protection`, `Buffs`, `Card Advantage`, `Disruption`, or `Mana`).
    *   `--deck-filter FILE`: Filter cards using a standard MTG decklist file. This also multiplies cards in the output based on their counts in the decklist.

> **Tip:** You can use internal shorthand markers with the `--rarity` flag: `O (Common), N (Uncommon), A (Rare), Y (Mythic), I (Special), and L (Basic Land).`

**Examples:**
```bash
# Process only Goblin creatures
python3 encode.py data/AllPrintings.json --grep "Goblin" --grep "Creature"

# Find only legendary artifacts from the MOM set
python3 scripts/mtg_analyze.py summary data/AllPrintings.json --grep "Legendary" --grep "Artifact" --set MOM

# Process only rare cards, excluding those with "Infect" in their name
python3 encode.py data/AllPrintings.json --rarity rare --exclude-name "Infect"

# Encode cards from a specific decklist to create a customized training set
python3 encode.py data/AllPrintings.json --deck-filter my_deck.txt encoded_deck.txt

# Find all creatures with power 5 or greater
python3 scripts/mtg_analyze.py summary data/AllPrintings.json --pow ">=5"

# Find rare cards with CMC between 2 and 4
python3 scripts/mtg_query.py search data/AllPrintings.json --rarity rare --cmc "2-4"

# Find rare cards from the MOM set that provide Card Advantage
python3 scripts/mtg_query.py search data/AllPrintings.json --set MOM --rarity rare --action "Card Advantage"

# Find all cards that produce Green mana (includes Birds of Paradise and Forests)
python3 scripts/mtg_query.py search --produces G

# Find all cards that can produce any color of mana
python3 scripts/mtg_query.py search --produces Any
```

---

## Smart Input Handling

Most tools in this project feature "smart" logic to make common tasks faster and easier.

### 1. Smart Dataset Detection
If you don't provide an input file (and aren't using a pipe), the tools automatically look for the official dataset at `data/AllPrintings.json`. This means you can often skip typing the filename entirely.

```bash
# Instead of:
python3 scripts/mtg_query.py search data/AllPrintings.json --grep "Grizzly Bears"

# You can just type:
python3 scripts/mtg_query.py search "Grizzly Bears"
```

### 2. Smart Positional Argument Handling
The tools are smart enough to distinguish between a filename and a search query. This allows you to omit the `--grep` flag or even swap the order of arguments.

*   **Automatic Search:** If a positional argument isn't a valid file, the tool automatically treats it as a search query.
*   **Flexible Order:** You can provide the query before or after the filename.

```bash
# Both of these work:
python3 scripts/mtg_analyze.py summary my_cards.json "Elf"
python3 scripts/mtg_analyze.py summary "Elf" my_cards.json

# If my_cards.json doesn't exist, this searches the default dataset for "my_cards.json":
python3 scripts/mtg_analyze.py summary my_cards.json
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

### `mtg_analyze.py profile`
Identifies the "Mechanical Identity" (signature features) of a card subset by comparing it against a global baseline. This highlights what makes a specific group of cards unique.
```bash
# Profile Green Rare cards to see their defining mechanics
python3 scripts/mtg_analyze.py profile data/AllPrintings.json --colors G --rarity rare

# Profile a specific set to see its mechanical themes
python3 scripts/mtg_analyze.py profile data/AllPrintings.json --set MOM

# See the top 20 signature features for a decklist
python3 scripts/mtg_analyze.py profile my_deck.txt --top 20
```
*   **Metrics:** Calculates Avg CMC, Power, Toughness, and Complexity deltas.
*   **Signature Features:** Identifies over-represented Mechanics, Actions, and Subtypes using a 'Lift' score (Relative Frequency vs. Baseline).
*   **Options:** Supports all **Advanced Filtering** flags and the `--top N` argument.

### `mtg_analyze.py summary`
Shows statistics and reports on mechanics and word variety for your card data. It works with any card data (JSON, CSV, XML, encoded text, etc.).
```bash
# View statistics for the entire official dataset
python3 scripts/mtg_analyze.py summary data/AllPrintings.json

# View statistics for your encoded output
python3 scripts/mtg_analyze.py summary encoded_output.txt

# Show extra details and unusual cards (outliers)
python3 scripts/mtg_analyze.py summary encoded_output.txt -x

# Save statistics to a file (JSON format is auto-detected)
python3 scripts/mtg_analyze.py summary encoded_output.txt summary.json
```
*   **Options:**
    *   `-x`, `--outliers`: Show extra details and unusual cards.
    *   `-a`, `--all`: Show all information, including dumping invalid cards.
    *   `--top N`: Limit the number of entries in breakdown tables (Default: 10).
    *   `--sort CRITERIA`: Sort cards by `name`, `color`, `identity`, `type`, `cmc`, `rarity`, `power`, `toughness`, `loyalty`, `set`, `pack`, `complexity`, or `score` before summarizing.
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

# Check for color pie violations (e.g. Blue cards with Deathtouch)
python3 scripts/mtg_validate.py generated.txt --color-pie --dump

# Print details for invalid cards
python3 scripts/mtg_validate.py data/AllPrintings.json --dump
```
*   **Options:**
    *   `--color-pie`: Identify mechanics that don't match the card's color identity.
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

### `mtg_eval.py`
Automates AI model quality assessment by generating a sample of cards and running them through the validation suite. This provides a single 'Mechanical Accuracy Score' for a given model checkpoint.
```bash
# Evaluate a checkpoint by generating 100 cards
python3 scripts/mtg_eval.py --checkpoint checkpoint.pt --count 100

# Evaluate with higher creativity (temperature)
python3 scripts/mtg_eval.py --checkpoint checkpoint.pt --temp 1.0
```
*   **Options:**
    *   `-c`, `--checkpoint`: Path to the model checkpoint file.
    *   `-n`, `--count`: Number of cards to generate and validate.
    *   `-t`, `--temp`: Creativity temperature for generation.
    *   `-d`, `--dump`: Print full text of cards that failed validation.
    *   `-j`, `--json`: Output results in structured JSON format.

### `mtg_llm_validate.py`
Validates the mechanical integrity of cards using a local Large Language Model (LLM). This tool asks the AI to judge if a card's text follows Magic's rules logic and provides a reason for its decision.
```bash
# Validate cards in a file using the default model (TinyLlama)
python3 scripts/mtg_llm_validate.py generated_cards.txt

# Validate specific cards and output valid ones to a JSON file
python3 scripts/mtg_llm_validate.py generated.txt --grep "Grizzly Bears" --only-valid --json > valid.json
```
*   **Requirements:** Requires `transformers`, `torch`, and `accelerate` (installed via `requirements.txt`).
*   **Options:**
    *   `--model MODEL`: The HuggingFace model to use (Default: `TinyLlama/TinyLlama-1.1B-Chat-v1.0`).
    *   `--device DEVICE`: Device to run on (`cuda`, `cpu`, or `mps`).
    *   `--batch-size N`: Number of cards to process at once.
    *   `--only-valid`: Filter output to only include cards the LLM judged as valid.
    *   Supports all **Advanced Filtering** flags and multiple output formats (`--json`, `--csv`, `--table`).


### `mtg_query.py`
A unified tool for searching, extracting, and listing card data. It consolidates several previous scripts into a single interface using subcommands.

#### **Commands:**
*   `search`: Search card data and extract specific fields.
*   `oracle`: Look up a card by name and display its full rules text.
*   `random`: Display one or more random cards matching the filters.
*   `sets`: List and filter sets in an MTGJSON file.
*   `functional`: Identify and group cards with the same mechanics but different names.
*   `compare`: Compare two cards side-by-side by name to identify differences.
*   `extract`: Extract a single card object from a large JSON database.
*   `shell`: Launch an interactive terminal for quick card lookups and searches.

---

#### **Subcommand: `search`**
Optimized for dataset exploration and bulk field extraction. Supports **Smart Dataset Detection** (automatically uses `data/AllPrintings.json` if available).

```bash
# Quickly search for a card name
python3 scripts/mtg_query.py search "Grizzly Bears"

# List names and costs of all Goblins in a table
python3 scripts/mtg_query.py search data/AllPrintings.json --grep "Goblin" --fields "name,cost" --table

# Find all mythic rares with CMC > 7 and save to a JSON file
python3 scripts/mtg_query.py search data/AllPrintings.json --rarity mythic --cmc ">7" mythics.json
```
*   **Fields:** `name`, `cost`, `cmc`, `type`, `stats`, `rarity`, `text`, `mechanics`, `set`, `complexity`, etc.
*   **Formats:** `--table`, `--md-table`, `--json`, `--jsonl`, `--csv`, `--summary`.

---

#### **Subcommand: `oracle`**
Quick human-readable card lookup with fuzzy matching and smart defaults.

```bash
# Quick lookup (fuzzy matching supported)
python3 scripts/mtg_query.py oracle "Grizly Beers"

# Find cards matching specific filters
python3 scripts/mtg_query.py oracle --set MOM --rarity rare --grep "Battle"

# Find cards mechanically similar to a specific card
python3 scripts/mtg_query.py oracle "Giant Growth" --similar
```

---

#### **Subcommand: `random`**
Display one or more random cards from the dataset. Supports all **Advanced Filtering** flags.

```bash
# See a random card
python3 scripts/mtg_query.py random

# See 5 random rare creatures
python3 scripts/mtg_query.py random 5 --rarity rare --grep "Creature"

# Output 10 random Goblins in a table
python3 scripts/mtg_query.py random 10 --grep "Goblin" --table
```
*   **Options:** `count`, `--table`, `--json`, `--jsonl`, `--csv`, `--summary`, `--fields`.

---

#### **Subcommand: `sets`**
Lists and filters sets.

```bash
# List all sets
python3 scripts/mtg_query.py sets

# Find sets with "Masters" in their name or code
python3 scripts/mtg_query.py sets --grep "Masters"
```
*   **Options:** `--summarize` (stats profile), `--view` (card list), `--sort`.

---

#### **Subcommand: `functional`**
Identifies cards with the same mechanics but different names.

```bash
# List all cards with the same mechanics
python3 scripts/mtg_query.py functional

# Create a deduplicated dataset
python3 scripts/mtg_query.py functional --dedupe unique_cards.json
```

---

#### **Subcommand: `compare`**
Side-by-side card comparison for identifying design differences. Supports N-way comparison (any number of cards), fuzzy matching, and automatic similarity finding.

```bash
# Compare two cards by name
python3 scripts/mtg_query.py compare "Grizzly Bears" "Gray Ogre"

# Compare one card against its most mechanically similar match
python3 scripts/mtg_query.py compare "Grizzly Bears"

# Compare multiple cards (N-way)
python3 scripts/mtg_query.py compare "Grizzly Bears" "Gray Ogre" "Balduvian Bears"

# Compare a pool of cards matching filters
python3 scripts/mtg_query.py compare --set MOM --rarity rare

# Compare cards in a specific file
python3 scripts/mtg_query.py compare "Uthros" "Invasion" testdata/ --color
```

---

#### **Subcommand: `extract`**
Extracts a single card object for debugging or testing.

```bash
python3 scripts/mtg_query.py extract data/AllPrintings.json MOM "Invasion of Tarkir"
```

---

#### **Subcommand: `shell`**
Provides an interactive terminal for browsing card data. Supports tab completion for card names and command history.

```bash
# Start the interactive shell (automatically uses data/AllPrintings.json if available)
python3 scripts/mtg_query.py shell

# Start with a specific file and custom fields for searches
python3 scripts/mtg_query.py shell my_cards.json --fields "name,cost,type,pt,rarity"
```
*   **In-Shell Commands:**
    *   `<card name>`: Type any card name to see its official rules text.
    *   `/search <query>`: Perform a bulk search and display results in a table.
    *   `/help`: Show available commands.
    *   `exit` or `quit`: Leave the shell.

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

### `mtg_analyze.py compare`
Provides a side-by-side statistical comparison of two or more card datasets. This is useful for evaluating how well a generated dataset matches the characteristics of official Magic data.
```bash
# Compare official data vs generated cards
python3 scripts/mtg_analyze.py compare data/AllPrintings.json generated.txt

# Compare multiple sets
python3 scripts/mtg_analyze.py compare --set MOM --set ONE data/AllPrintings.json
```
*   **Comparison includes:** Card counts, validity, uniqueness, average stats (CMC, P/T), and percentage distributions for colors, types, and rarities.
*   **Options:**
    *   `--limit N`: Only process the first N cards from each input.
    *   `--shuffle`: Randomize cards before analysis.
    *   `--sample N`: Pick N random cards (shorthand for `--shuffle --limit N`).
    *   `--color` / `--no-color`: Enable or disable ANSI color output.
    *   Supports standard **Advanced Filtering** flags.

### `mtg_deckgen.py`
Generates a complete Magic deck from a card pool. It supports Commander (EDH) and Standard formats, automatically handling commander color identity filtering and basic land distribution.
```bash
# Generate a Commander deck with a random commander from a pool
python3 scripts/mtg_deckgen.py data/AllPrintings.json --format commander

# Generate a Commander deck with a specific commander
python3 scripts/mtg_deckgen.py data/AllPrintings.json --commander "Atraxa, Praetors' Voice"

# Generate a Standard deck from a pool
python3 scripts/mtg_deckgen.py data/AllPrintings.json --format standard
```
*   **Options:**
    *   `--format {commander,standard}`: Choose the deck format (Default: commander).
    *   `--commander NAME`: Specify a legendary creature to use as your commander.
    *   `--creatures N`, `--spells N`, `--lands N`: Override the target number of cards for each category.
    *   `--curve "1:5,2:10,..."`: Override the target mana curve for creatures.
    *   `--outfile FILE`: Save the decklist to a file instead of printing to the console.

### `mtg_manabase.py`
Recommends a basic land distribution (Mana Base) for a decklist or card dataset. It analyzes the mana pips in casting costs and suggests a proportional count of basic lands (Plains, Islands, Swamps, Mountains, Forests, and Wastes) to meet those requirements.
```bash
# Analyze a decklist and recommend 24 lands
python3 scripts/mtg_manabase.py my_deck.txt --lands 24

# Calculate a mana base for a specific set (40-card Limited deck)
python3 scripts/mtg_manabase.py data/AllPrintings.json --set MOM --lands 17

# Include activation costs in the pip analysis
python3 scripts/mtg_manabase.py my_deck.txt --include-text
```
*   **Options:**
    *   `--lands N`: Target number of basic lands to recommend (Default: 24).
    *   `--include-text`: Include mana symbols found in rules text (e.g., activation costs).
    *   Supports all **Advanced Filtering** flags.

### `mtg_analyze.py power`
Analyzes the creature power balance and curve efficiency in a dataset. It calculates a 'Power Rating' relative to CMC to identify outliers (cards that are significantly above or below the expected power curve for their cost).
```bash
# Find the most efficient creatures in a specific set
python3 scripts/mtg_analyze.py power data/AllPrintings.json --set MOM --limit 10

# Compare average creature efficiency across rarities
python3 scripts/mtg_analyze.py power data/AllPrintings.json --rarity common --rarity rare

# Export balance analysis to JSON
python3 scripts/mtg_analyze.py power generated_cards.txt --json
```
*   **Metric:** A rating of 1.0 represents a basic 2/2 creature with no abilities for 2 mana. Keywords like Flying or Indestructible increase the rating.
*   **Options:** Supports `--json`, `--csv`, and all standard **Advanced Filtering** flags.

### `mtg_analyze.py asfan`
Calculates "As-Fan" (As fanned) statistics for a card dataset. As-Fan represents the average number of cards with a certain characteristic (like a specific color, type, or mechanic) a player can expect to see in a single 15-card booster pack.
```bash
# Analyze As-Fan for a specific set
python3 scripts/mtg_analyze.py asfan data/AllPrintings.json --set MOM

# Compare As-Fan of a generated set vs official data
python3 scripts/mtg_analyze.py asfan data/AllPrintings.json --compare generated.txt
```
*   **Options:**
    *   `--compare FILE`: Side-by-side comparison with a second dataset.
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports standard **Advanced Filtering** flags and 'Smart Positional Argument Handling'.

### `mtg_analyze.py interaction`
Analyzes how different mechanics (like Flying, Kicker, or Flashback) appear together on the same cards. It identifies frequent pairings and calculates a 'Lift Score' to measure if these mechanics appear together more often than expected by chance.
```bash
# Analyze co-occurrence for a specific set
python3 scripts/mtg_analyze.py interaction data/AllPrintings.json --set MOM

# Find frequent pairings in AI designs with at least 5 occurrences
python3 scripts/mtg_analyze.py interaction generated.txt --min-freq 5
```
*   **Options:**
    *   `--min-freq N`: Minimum co-occurrences required to report a pair (Default: 2).
    *   `--top N`: Show the top N pairings (Default: 20).
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports all **Advanced Filtering** flags and 'Smart Positional Argument Handling'.

### `mtg_analyze.py types`
Generates a Type vs. Color heatmap (matrix) cross-referencing card types with Color Identity (W, U, B, R, G, Colorless, Multicolored). This is essential for verifying color-pie balance and archetypal distribution in a set.
```bash
# Analyze the type/color distribution of a specific set
python3 scripts/mtg_analyze.py types data/AllPrintings.json --set MOM

# Compare distribution between official data and AI designs
python3 scripts/mtg_analyze.py types data/AllPrintings.json --compare generated.txt
```
*   **Options:**
    *   `--compare FILE`: Side-by-side comparison with a second dataset.
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports all **Advanced Filtering** flags and 'Smart Positional Argument Handling'.

### `mtg_analyze.py audit`
Performs a comprehensive design 'Health Check' for card datasets. It reports on core metrics (creature density, average CMC, complexity), functional coverage (removal, card advantage, mana fixing), identifies complexity outliers, and flags mechanical color pie violations.
```bash
# Perform a health audit for a generated set
python3 scripts/mtg_analyze.py audit generated.txt

# Audit a specific set and output structured JSON
python3 scripts/mtg_analyze.py audit data/AllPrintings.json --set MOM --json > audit.json
```
*   **Metrics:** Reports on Creature Density, Avg CMC, Avg Complexity, Removal Density, Card Advantage, and Mana Fixing.
*   **Color Pie:** Uses `Card.check_color_pie()` to identify mechanics that contradict a card's color identity.
*   **Options:** Supports all **Advanced Filtering** flags and `--json` output.

### `mtg_analyze.py subtypes`
Analyzes the distribution of card subtypes (like Creature types, Artifact types, or Spell types) in a dataset. It identifies the most popular subtypes and calculates 'Signature' subtypes for each color identity (types that appear significantly more often in one color than others).
```bash
# Analyze subtypes for the March of the Machine set
python3 scripts/mtg_analyze.py subtypes data/AllPrintings.json --set MOM

# See the top 20 signature subtypes for each color
python3 scripts/mtg_analyze.py subtypes data/AllPrintings.json --top 20

# Export subtype analysis to JSON
python3 scripts/mtg_analyze.py subtypes data/AllPrintings.json --json > subtypes.json
```
*   **Options:**
    *   `--top N`: Number of entries to show in tables (Default: 10).
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports all **Advanced Filtering** flags and 'Smart Positional Argument Handling'.

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

### `mtg_forge.py`
Forges a new card or modifies ("reforges") an existing one using command-line arguments. This is useful for quickly creating custom cards for testing or adding to a dataset.
```bash
# Create a card from scratch and view it
python3 scripts/mtg_forge.py --name "Jules" --cost "{U}{R}" --type "Legendary Creature" --pt "2/2" --text "T: Draw a card." | python3 decode.py

# Reforge an existing card (modifying stats and name)
python3 scripts/mtg_forge.py --base "Grizzly Bears" --pt "3/3" --name "Super Bears"
```
*   **Options:** Supports `--name`, `--cost`, `--type`, `--text`, `--pt`, `--loyalty`, `--rarity`, and `--set`. Output formats include `--json` (Default), `--encoded`, and `--summary`.

### `mtg_subset.py`
Creates a filtered subset of an MTGJSON file while preserving its structure. This is useful for creating specialized training datasets or lightweight card databases without losing set-level metadata.
```bash
# Create a subset of only Legendary cards from a specific set
python3 scripts/mtg_subset.py data/AllPrintings.json output.json --set MOM --grep "Legendary"

# Create a tiny dataset of 100 random rare creatures
python3 scripts/mtg_subset.py data/AllPrintings.json tiny.json --rarity rare --grep-type "Creature" --sample 100
```
*   Supports all **Advanced Filtering** flags and sorting.

### `mtg_analyze.py grid`
Provides a generic 2D cross-tabulation tool for card datasets. This allows you to cross-reference attributes like color, rarity, type, cmc, power, toughness, and mechanic to see how they are distributed.
```bash
# Analyze Card Type vs Color Identity for a specific set
python3 scripts/mtg_analyze.py grid type color --set MOM

# Analyze Rarity vs CMC for the whole dataset
python3 scripts/mtg_analyze.py grid rarity cmc data/AllPrintings.json
```
*   **Dimensions:** `color`, `rarity`, `type`, `cmc`, `power`, `toughness`, `loyalty`, `mechanic`.
*   **Options:**
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports all **Advanced Filtering** flags and 'Smart Positional Argument Handling'.

### `mtg_analyze.py mechanics`
Lists all mechanical keywords (e.g., Flying, Trample, Ward) recognized by the toolkit and can calculate their frequency in a dataset. This is useful for seeing which keywords are currently tracked or for analyzing the mechanical profile of a set.
```bash
# List all recognized mechanics
python3 scripts/mtg_analyze.py mechanics

# Count frequency of mechanics in a dataset
python3 scripts/mtg_analyze.py mechanics data/AllPrintings.json --set MOM
```
*   **Options:**
    *   `--sort {name,count}`: Sort results by name or frequency.
    *   `--top N`: Only show the top N mechanics.
    *   Supports standard **Advanced Filtering** flags (e.g., `--grep`, `--set`, `--rarity`).

### `mtg_analyze.py colorpie`
Generates a Color Pie chart that shows which mechanics appear in each color. This helps you check if colors are using the correct mechanics or if some mechanics are appearing where they shouldn't.
```bash
# Analyze the color pie for a specific set
python3 scripts/mtg_analyze.py colorpie data/AllPrintings.json --set MOM

# Compare color pie between official data and AI output
python3 scripts/mtg_analyze.py colorpie data/AllPrintings.json --compare generated.txt
```
*   **Options:**
    *   `--compare FILE`: Side-by-side comparison with a second dataset.
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports all **Advanced Filtering** flags and 'Smart Positional Argument Handling'.

### `mtg_analyze.py lexicon`
Analyzes the words used for each Magic color. It identifies "signature words" that appear much more often in one color than others. This helps you check if AI designs follow the correct color patterns.
```bash
# Analyze lexicon for a dataset
python3 scripts/mtg_analyze.py lexicon data/AllPrintings.json

# Compare lexicon between official data and AI output
python3 scripts/mtg_analyze.py lexicon data/AllPrintings.json --compare generated.txt
```
*   **Options:**
    *   `--top N`: Number of signature words to show per color (Default: 10).
    *   `--min-len N`: Minimum word length to include in analysis (Default: 4).
    *   `--compare FILE`: Side-by-side comparison with a second dataset.
    *   **Filtering:** Supports standard **Advanced Filtering** flags.

### `mtg_analyze.py tokens`
Extracts and summarizes token definitions from card rules text. This tool identifies the properties of tokens created by cards (like P/T, color, types, and abilities) and de-duplicates them to show a consolidated list.
```bash
# List all unique tokens found in a dataset
python3 scripts/mtg_analyze.py tokens data/AllPrintings.json

# Extract tokens from a specific set and output to JSON
python3 scripts/mtg_analyze.py tokens data/AllPrintings.json --set MOM --json
```
*   **Options:**
    *   `--json`: Output results in structured JSON format.
    *   Supports standard **Advanced Filtering** flags (`--grep`, `--set`, `--rarity`).

### `mtg_analyze.py skeleton`
Generates a "Design Skeleton" (Set Skeleton) for a dataset, bucketing cards by their type and CMC (Converted Mana Cost). This provides a high-level view of the mechanical curve and balance of a set.
```bash
# Generate skeleton for a dataset
python3 scripts/mtg_analyze.py skeleton data/AllPrintings.json --set MOM

# Analyze the curve of a specific color identity
python3 scripts/mtg_analyze.py skeleton data/AllPrintings.json --identity "W"
```
*   Supports all **Advanced Filtering** flags, sorting, and booster/box simulation.

### `mtg_analyze.py archetypes`
Analyzes the 10 primary two-color pairs in a dataset. It identifies the most important cards and themes for each color combination.
```bash
# Analyze archetypes in a specific set
python3 scripts/mtg_analyze.py archetypes data/AllPrintings.json --set MOM

# Filter analysis by specific mechanics or rarities
python3 scripts/mtg_analyze.py archetypes data/AllPrintings.json --rarity uncommon --mechanic "Flying"
```
*   **Options:**
    *   `--min-cards N`: Minimum number of cards required to profile an archetype (Default: 5).
    *   `--top-mechanics N`: Number of signature mechanics to show per archetype (Default: 3).
    *   Supports all standard **Advanced Filtering** flags.

### `mtg_analyze.py balance`
Analyzes and compares how color pairs are distributed between datasets. This helps you see if a generated dataset matches the color balance of the original training data.
```bash
# Compare the balance of a generated set against an official set
python3 scripts/mtg_analyze.py balance data/AllPrintings.json generated.txt --set MOM

# See which color pairs are over-represented in a card pool
python3 scripts/mtg_analyze.py balance my_cards.json
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

### `mtg_analyze.py curve`
Analyzes and visualizes the mana curve (CMC distribution) of a card dataset or decklist. It provides a visual distribution chart, global and color-specific average CMC calculations, and a breakdown by card type.
```bash
# Analyze the curve of a specific set
python3 scripts/mtg_analyze.py curve data/AllPrintings.json --set MOM

# Analyze a decklist file
python3 scripts/mtg_analyze.py curve my_deck.txt

# See the curve for only creatures in a dataset
python3 scripts/mtg_analyze.py curve data/AllPrintings.json --grep-type "Creature"
```
*   **Options:**
    *   `-n LIMIT`, `--limit LIMIT`: Only process the first N cards.
    *   `--sample N`: Pick N random cards (shorthand for --shuffle --limit N).
    *   `--booster N`: Simulate opening N booster packs and analyze their curve.
    *   `--box N`: Simulate opening N booster boxes and analyze their curve.
    *   Supports all **Advanced Filtering** flags.

### `mtg_analyze.py mana`
Identifies mana-producing cards using rules text patterns (e.g., 'Add {G}', 'any color') and intrinsic basic land types. It categorizes producers into Creatures, Artifacts, Lands, and Spells, profiles produced colors, and identifies color-fixing density.
```bash
# Analyze mana production for a specific set
python3 scripts/mtg_analyze.py mana data/AllPrintings.json --set MOM

# Compare mana fixing between official data and AI output
python3 scripts/mtg_analyze.py mana data/AllPrintings.json --compare generated.txt
```
*   **Options:**
    *   `--compare FILE`: Side-by-side comparison with a second dataset.
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports all **Advanced Filtering** flags and simulation.

### `mtg_analyze.py costs`
Analyzes the mana cost intensity (colored pips relative to CMC) and color commitment (distribution of Single, Double, Triple pips) in a dataset. This helps designers identify 'pip-heavy' outliers and ensure the set's requirements match its intended archetypes.
```bash
# Analyze cost intensity for a set
python3 scripts/mtg_analyze.py costs data/AllPrintings.json --set MOM

# Find the most mana-intensive cards in a dataset
python3 scripts/mtg_analyze.py costs data/AllPrintings.json --limit 20
```
*   **Options:**
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports standard **Advanced Filtering** flags and 'Smart Positional Argument Handling'.

### `mtg_analyze.py stats`
Analyzes creature combat stats (Power/Toughness) and Planeswalker loyalty in a dataset. It provides a "Combat Stat Curve" (average P/T per CMC), a color-based stat breakdown, and a frequency heatmap of P/T combinations.
```bash
# Analyze stats for a specific set
python3 scripts/mtg_analyze.py stats data/AllPrintings.json --set MOM

# Compare stats of rare creatures vs common creatures
python3 scripts/mtg_analyze.py stats data/AllPrintings.json --rarity rare --grep-type "Creature"
```
*   **Options:**
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports standard **Advanced Filtering** flags and simulation.

### `mtg_analyze.py actions`
Analyzes and categorizes functional card effects (Removal, Protection, Buffs, Card Advantage, Disruption, and Mana) in a dataset. This tool identifies how cards interact with the game state, providing a profile of a set's interactivity.
```bash
# Analyze actions for a specific set
python3 scripts/mtg_analyze.py actions data/AllPrintings.json --set MOM

# Compare action density of different colors
python3 scripts/mtg_analyze.py actions data/AllPrintings.json --colors R
```
*   **Options:**
    *   `--json`: Output results in structured JSON format.
    *   `--csv`: Output results in CSV format.
    *   Supports standard **Advanced Filtering** flags and simulation.

### `mtg_analyze.py pips`
Analyzes the distribution of mana symbols (pips) in a dataset. It counts symbols from casting costs and rules text (optionally via `--include-text`), supports table, JSON, and CSV output formats, and integrates with standard Advanced Filtering and simulation flags.
```bash
# Analyze pip distribution for a set
python3 scripts/mtg_analyze.py pips data/AllPrintings.json --set MOM

# Include pips found in rules text (e.g. activation costs)
python3 scripts/mtg_analyze.py pips data/AllPrintings.json --set MOM --include-text
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
python3 scripts/mtg_analyze.py summary my_custom_set.xml
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
