Run the test suite before completing work. When features change, update or add tests accordingly.

This project was originally written for Python 2. You may update code to use Python 3.10 idiom as you encounter it.

You may be provided with a .json for a full set, downloaded from mtgjson.com to debug processing a specific type of card. Still they are quite large, don't try to load the whole thing into LLM context, nor create a test that involves verifying every card. The .json will be removed from the repository after the bug is fixed. Copy only the specific card you need for a test, using a program like scripts/extract_one.py or a custom process.

## Docker Usage

This project includes a Docker setup for a consistent development environment.

### Linux/macOS

To build the Docker image and start an interactive session, run the following command:

```bash
./docker-interactive.sh
```

### Windows

For Windows users, a batch script is provided to avoid line-ending issues:

```bash
./docker-interactive.bat
```

## Reporting Unparsed Cards

When working with large JSON files like `AllPrinting.json`, you may encounter cards that fail to parse. To make it easier to debug these issues without sharing the entire file, you can use the `--report-unparsed` flag to save the problematic card data to a separate file.

```bash
./encode.py data/AllPrinting.json --report-unparsed unparsed_cards.json
```

This will create a file named `unparsed_cards.json` containing the raw JSON data for any cards that could not be parsed.