Run the test suite before completing work. When features change, update or add tests accordingly.

testdata/Standard.json contains data of cards in Standard, downloaded from mtgjson.com as a preview of the full data of cards in Vintage. Still it is 34MB, so don't try to load the whole thing into LLM context, nor create a test that involves verifying every value. You can still have a test that loads it into memory, or pulls specific items from it.

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