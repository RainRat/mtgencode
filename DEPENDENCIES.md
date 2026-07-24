# External Tools & Data

This guide covers external data and tools that extend the functionality of `mtgencode`.

## 1. Magic: The Gathering Data (Required)

To encode card data, you need the JSON corpus from [MTGJSON](https://mtgjson.com).

1.  Go to [MTGJSON Downloads](https://mtgjson.com/downloads/all-files/).
2.  Download the **AllPrintings.json.zip** file (or the raw **AllPrintings.json** if available).
3.  Place it in the `data/` directory of this repository (create the directory if it doesn't exist).

You have two options for setting up this file:
*   **Option A: Unzip the file (Recommended)**
    Unzip the file to extract `AllPrintings.json`, and place it in the `data/` folder. This allows the tools' automatic default dataset detection to find it without any extra options.
*   **Option B: Keep the ZIP file**
    Keep the file as `AllPrintings.json.zip` inside `data/`. The tools in this project can read directly from ZIP files when you specify the file path.

Example commands to create the folder and move the file:
```bash
mkdir -p data
# Move the file from your downloads folder
mv ~/Downloads/AllPrintings.json data/
# Or if you downloaded the ZIP file:
mv ~/Downloads/AllPrintings.json.zip data/
```

## 2. Magic Set Editor (Optional)

[Magic Set Editor (MSE)](https://magicseteditor.boards.net/) is a tool for designing and visualizing custom cards. The `decode.py` script can generate `.mse-set` files (using the `--mse` flag) that you can open in MSE to see your generated cards as if they were real Magic cards.

### Installation

*   **Windows:** Download the installer from the [official website](https://magicseteditor.boards.net/page/downloads) and run it.
*   **Linux/macOS:** MSE is a Windows application, but it runs well on Linux and macOS using [Wine](https://www.winehq.org/), which acts as a compatibility layer.
    1.  **Install Wine:** Use your system's package manager (e.g., `sudo apt install wine` on Ubuntu, or `brew install --cask wine-stable` on macOS).
    2.  **Download MSE:** Get the standard Windows installer from the MSE website.
    3.  **Run Installer:** Open your terminal and run the installer with Wine: `wine mse-installer.exe`.
    4.  **Run MSE:** After installation, launch MSE using Wine: `wine "C:/Program Files/Magic Set Editor 2/mse.exe"` (path may vary).

### Fonts
MSE requires specific fonts to render card text and symbols correctly. Without them, you might see **squares or generic text** instead of mana symbols (like the skull for Black mana) or the correct card title font.

*   **Required Fonts:**
    *   **Beleren** (Bold, Small Caps) - Used for card titles.
    *   **Relay** (Medium) - Used for card text.
    *   **MPlantin** - Used for flavor text and other details.

*   **How to find them:**
    Due to copyright, we cannot host these fonts. However, a quick web search for "**Magic The Gathering fonts**" or "**MSE fonts pack**" will help you find them.

*   **How to install:**
    *   **Windows:** Right-click the font file (`.ttf` or `.otf`) and select "Install".
    *   **Linux/macOS (Wine):** To make fonts available to MSE running in Wine, copy the font files into the Wine fonts directory:
        ```bash
        cp *.ttf ~/.wine/drive_c/windows/Fonts/
        ```

### Usage
To generate an MSE set file:
```bash
python3 decode.py encoded_output.txt my_set --mse
```
This creates a file named `my_set.mse-set`. Double-click it (or open it via Wine) to view your cards.

## 3. Creativity Analysis (Advanced)

The `--creativity` flag in `decode.py` helps you evaluate your AI model. It calculates how "original" your generated cards are by comparing them to existing real cards.

**What it does:**
It uses a vector model (Word2Vec) to measure the semantic distance between your generated card and the nearest real Magic card.
*   **Low distance:** The card is very similar (or identical) to an existing card.
*   **High distance:** The card is unique or "creative."

**Note:** This is an advanced feature. It requires you to compile the `word2vec` tool from its source code.

### Setup Steps

1.  **Install word2vec:**
    You need the original C implementation of `word2vec`. Since the original repository is archived, we recommend using this reliable mirror:
    *   **Get the code:**
        ```bash
        git clone https://github.com/tmikolov/word2vec.git
        cd word2vec
        ```
    *   **Build the tool:**
        ```bash
        make
        ```
    *   **Copy the binary:**
        Move the `word2vec` file into your `mtgencode` root folder so the scripts can find it.

2.  **Generate Reference Data and Vectors:**
    The creativity analyzer compares your custom cards against a reference dataset of real cards. This requires two files in your `data/` folder:
    *   `data/output.txt`: The reference card dataset in standard-encoded text format.
    *   `data/cbow.bin`: The compiled Word2Vec binary model.

    **Important:** The cards in both files must be in the exact same order. Always use the stable ordering flag (`-s`) when generating them.

    Follow these steps to generate both files:

    *   **Step A: Create the reference dataset (`data/output.txt`)**
        ```bash
        python3 encode.py data/AllPrintings.json data/output.txt -s
        ```

    *   **Step B: Create the vector training text (`data/cbow.txt`)**
        ```bash
        python3 encode.py data/AllPrintings.json data/cbow.txt -s -e vec
        ```

    *   **Step C: Compile `cbow.bin` using the `word2vec` tool**
        ```bash
        ./word2vec -train data/cbow.txt -output data/cbow.bin -cbow 1 -size 200 -window 8 -negative 25 -hs 0 -sample 1e-4 -threads 20 -binary 1 -iter 15
        ```

3.  **Run with Creativity:**
    Once both `data/cbow.bin` and `data/output.txt` exist in your `data/` folder, you can run decoding with creativity analysis:
    ```bash
    python3 decode.py encoded_output.txt decoded.txt --creativity
    ```

## 4. Training (Optional)
The `train.py` script requires [PyTorch](https://pytorch.org/) and [tqdm](https://github.com/tqdm/tqdm) for its character-level RNN implementation. These are included in the standard `requirements.txt`.
```bash
pip install -r requirements.txt
```
If you have a CUDA-compatible GPU, the training script will automatically use it for significantly faster training.
