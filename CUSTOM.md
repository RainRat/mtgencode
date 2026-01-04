# Custom Card Integration Guide

This guide explains how to integrate your own custom Magic: The Gathering cards (or cards from other sources) into the training data. This allows the neural network to learn from your designs, helping it understand power levels, color pie mechanics, and new ideas.

**Note:** The neural network won't reproduce your cards exactly. Instead, it uses them to learn patterns—like what abilities belong in Blue or how strong a 3-mana creature should be.

## Guidelines for Custom Cards

To get the best results, follow these tips:

*   **Balance:** Keep power level and rarity reasonable for a draft environment.
*   **Rules:** Do not invent new keywords or rely on complex rules changes. The AI processes text literally and won't understand undefined mechanics.
*   **Types:** You can create new creature or planeswalker types (e.g., "Creature — Gamer"), as long as they don't require special rules.
*   **Templating:** Use modern wording (e.g., "Create a token" instead of "Put a token onto the battlefield"). This helps the AI recognize patterns.
*   **Variety:** You can include simple, functional cards (Commons/Uncommons) as well as complex ones (Rares/Mythics).
*   **Creativity:** Feel free to tweak existing cards or add radical new ideas.

## How to Add Custom Cards

We provide two scripts in the `scripts/` directory to help you:
*   `scripts/csv2json.py`: Converts a spreadsheet of cards into JSON format.
*   `scripts/combinejson.py`: Merges your custom JSON with the official card data.

### Step 1: Create a Spreadsheet
Create a CSV file with your custom cards. You can start with this [Google Sheet template](https://docs.google.com/spreadsheets/d/1bYqDoRc6tD6uEchANzDUFZp0xaL4GTgFa4iadXcXRRQ/edit#gid=0).
1.  Open the link.
2.  Add your cards following the format (Name, Mana Cost, Type, Subtypes, Text, P/T, Rarity).
3.  Click **File -> Download -> Comma Separated Values (.csv)**.
4.  Save it as `custom.csv`.

### Step 2: Convert to JSON
Run the conversion script to turn your CSV into a format the encoder understands.

```bash
python3 scripts/csv2json.py custom.csv custom.json
```
*   **Input:** `custom.csv` (Your spreadsheet)
*   **Output:** `custom.json` (The converted data)

### Step 3: Merge with Official Data
Combine your custom cards with the official Magic data (`AllPrintings.json`).

```bash
python3 scripts/combinejson.py data/AllPrintings.json custom.json AllCustom.json
```
*   **Input 1:** `data/AllPrintings.json` (The official data, usually in the `data/` folder)
*   **Input 2:** `custom.json` (Your custom cards)
*   **Output:** `AllCustom.json` (The combined file)

### Step 4: Encode
Now you can use `encode.py` with your new combined file.

```bash
python3 encode.py AllCustom.json encoded_custom.txt
```

---

**License:** The scripts `scripts/csv2json.py` and `scripts/combinejson.py` are open source under the MIT License, same as `mtgencode`.
