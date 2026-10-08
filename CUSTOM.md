# Custom Card Integration Guide

This guide explains how to integrate your own custom Magic: The Gathering cards (or cards from other sources) into the training data. This allows the neural network to learn from your designs, helping it understand power levels, color pie mechanics, and new ideas.

**Note:** The neural network won't reproduce your cards exactly. Instead, it uses them to learn patterns—like what abilities belong in Blue or how strong a 3-mana creature should be.

## Guidelines for Custom Cards

To get the best results, follow these tips:

*   **Balance:** Keep power level and rarity reasonable for a draft environment.
*   **Rules:** Do not invent new keywords or rely on complex rules changes. The AI processes text literally and won't understand undefined mechanics.
*   **Types:** You can create new creature or planeswalker types (for example, "Creature — Gamer"), as long as they don't require special rules.
*   **Templating:** Use modern wording (for example, "Create a token" instead of "Put a token onto the battlefield"). This helps the AI recognize patterns.
*   **Variety:** You can include simple, functional cards (Commons/Uncommons) as well as complex ones (Rares/Mythics).
*   **Creativity:** Feel free to tweak existing cards or add radical new ideas.

## How to Add Custom Cards

We provide several scripts in the `scripts/` directory to help you:
*   `scripts/json2csv.py`: Exports existing cards to a CSV format for easy editing.
*   `scripts/csv2json.py`: Converts your edited spreadsheet back into JSON format.
*   `scripts/combinejson.py`: Merges your custom JSON with the official card data.

### Step 0: (Optional) Export Existing Cards
If you want to use existing cards as a starting point, use `json2csv.py`.
```bash
python3 scripts/json2csv.py data/AllPrintings.json my_base.csv --set MOM
```

### Step 1: Create or Edit a Spreadsheet
Create a CSV file with your custom cards. You can start with this [Google Sheet template](https://docs.google.com/spreadsheets/d/1bYqDoRc6tD6uEchANzDUFZp0xaL4GTgFa4iadXcXRRQ/edit#gid=0).

1.  Open the link.
2.  Add your cards following the format:
    *   **Name**: Card title.
    *   **Mana Cost**: Use brackets for symbols (for example, `{1}{W}{B}`).
    *   **Type**: Supertypes and Types (for example, `Legendary Creature`).
    *   **Subtypes**: (for example, `Elf Warrior`).
    *   **Text**: Rules text. Use `\n` or literal newlines for new lines.
    *   **P/T, Loyalty, or Defense**: Use `3/3` for creatures, or a single number for Planeswalker loyalty or Battle defense.
    *   **Rarity**: Use shorthands: `C` (Common), `U` (Uncommon), `R` (Rare), `M` (Mythic), `L` (Basic Land), `I` (Special).

### Multi-Faced Cards (Splits, Transforms, Battles)
To add a card with two faces (like a Split card or a Transforming double-faced card), use the ` // ` separator in any column where the faces differ.
*   **Name**: `Front Name // Back Name`
*   **Mana Cost**: `{1}{W} // {U}`
*   **Type**: `Creature // Instant`
*   **Text**: `Front rules text // Back rules text` (Use `\n` for new lines within a face).
*   **Stats**: `1/1 // ` (If only one face has P/T).

3.  Click **File -> Download -> Comma Separated Values (.csv)**.
4.  Save it as `custom.csv`.

### Step 2: Convert to JSON
Run the conversion script to turn your CSV into a format the encoder understands. You can also specify custom set codes and names using `-s`/`--set-code` and `-n`/`--set-name`.

```bash
# Preview conversion statistics without creating files (dry-run mode)
python3 scripts/csv2json.py custom.csv --dry-run

# Convert CSV spreadsheet to JSON
python3 scripts/csv2json.py custom.csv custom.json

# Convert with a custom set code and set name (useful for batch merging distinct sets)
python3 scripts/csv2json.py set1.csv set1.json -s SET1 -n "My Custom Set 1"
python3 scripts/csv2json.py set2.csv set2.json -s SET2 -n "My Custom Set 2"
```
*   **Input:** `custom.csv` (Your spreadsheet, or `-` for standard input)
*   **Output:** `custom.json` (The converted data, or `-` for standard output)
*   **Options:** `-s`, `--set-code` (Set code, default: `CUS`); `-n`, `--set-name` (Set name, default: `custom` or lowercase set code)

### Step 3: Merge with Official Data
Combine your custom cards with the official Magic data (`AllPrintings.json`). You can merge a single custom file or batch merge multiple custom sets into a single dataset.

```bash
# Preview merged dataset statistics without writing files (dry-run mode)
python3 scripts/combinejson.py data/AllPrintings.json custom.json --dry-run

# Merge a single custom JSON file
python3 scripts/combinejson.py data/AllPrintings.json custom.json -o AllCustom.json

# Batch merge multiple custom JSON files
python3 scripts/combinejson.py data/AllPrintings.json custom1.json custom2.json -o AllCustom.json
```
*   **Input 1:** `data/AllPrintings.json` (The official data, usually in the `data/` folder)
*   **Input 2:** `custom.json` or multiple custom JSON files
*   **Output:** `AllCustom.json` (The combined dataset file specified by `-o` or `--outfile`)

### Step 4: Encode
Now you can use `encode.py` with your new combined file.

```bash
python3 encode.py AllCustom.json encoded_custom.txt
```

---

**License:** The scripts `scripts/csv2json.py` and `scripts/combinejson.py` are open source under the MIT License, same as `mtgencode`.
