#!/usr/bin/env python3
import sys
import os
import argparse
import json
import re
from contextlib import redirect_stdout

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import cardlib
import datalib

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

# Try to import transformers
try:
    from transformers import pipeline
    import torch
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

DEFAULT_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

def get_prompt(card):
    """Formats a card for LLM judgment."""
    card_str = card.format(gatherer=True)
    # Using a chat-style prompt template for TinyLlama
    prompt = (
        "<|system|>\n"
        "You are an expert Magic: The Gathering rules judge. Your task is to evaluate the mechanical validity of custom cards. "
        "A card is INVALID if it uses non-existent game terms, has nonsensical costs, or violates core rules logic. "
        "A card is VALID if it follows MTG rules conventions, even if it is unique or powerful.\n\n"
        "Respond strictly in this format:\n"
        "JUDGMENT: VALID or INVALID\n"
        "REASON: [One sentence explanation]\n"
        "<|user|>\n"
        f"Evaluate this card:\n{card_str}\n"
        "<|assistant|>\n"
    )
    return prompt

def validate_cards_llm(cards, model_name, device, batch_size=1, quiet=False, verbose=False):
    """Processes cards through the LLM for validation."""
    if not HAS_TRANSFORMERS:
        print("Error: The 'transformers' and 'torch' libraries are required for LLM validation.", file=sys.stderr)
        print("Install them with: pip install transformers torch", file=sys.stderr)
        sys.exit(1)

    if verbose:
        print(f"Loading model '{model_name}' on {device}...", file=sys.stderr)

    # Detect dtype
    dtype = torch.float32
    if device != "cpu" and torch.cuda.is_available():
        if torch.cuda.is_bf16_supported():
            dtype = torch.bfloat16
        else:
            dtype = torch.float16

    try:
        # Determine device and device_map
        device_map = None
        device_arg = None

        if device == "auto" or device == "cuda":
             try:
                 import accelerate
                 device_map = "auto"
             except ImportError:
                 if torch.cuda.is_available():
                     device_arg = 0
                 else:
                     device_arg = -1 # cpu
        elif device == "cpu":
            device_arg = -1
        else:
            # For specific strings like 'mps' or 'cuda:1'
            device_arg = device

        # Use pipeline for simplicity
        pipe = pipeline(
            "text-generation",
            model=model_name,
            torch_dtype=dtype,
            device_map=device_map,
            device=device_arg
        )
    except Exception as e:
        print(f"Error initializing model: {e}", file=sys.stderr)
        sys.exit(1)

    results = []
    # Batch processing (manual because pipeline batching can be tricky with different prompt lengths)
    for i in tqdm(range(0, len(cards), batch_size), disable=quiet or len(cards) < 2, desc="LLM Validation"):
        batch = cards[i:i+batch_size]
        prompts = [get_prompt(c) for c in batch]

        # Generation settings: do_sample=False for deterministic evaluation
        outputs = pipe(
            prompts,
            max_new_tokens=100,
            do_sample=False,
            pad_token_id=pipe.tokenizer.eos_token_id,
            truncation=True
        )

        # Normalize outputs to always be a list of lists (one per prompt)
        # pipeline returns a single list if one prompt is passed, or a list of lists if multiple.
        if len(prompts) == 1:
            if not isinstance(outputs[0], list):
                outputs = [outputs]

        for j, output in enumerate(outputs):
            # Extract response part after the assistant tag
            full_text = output[0]['generated_text']
            assistant_tag = "<|assistant|>\n"
            if assistant_tag in full_text:
                response = full_text.split(assistant_tag)[-1].strip()
            else:
                response = full_text.strip()

            judgment_match = re.search(r'JUDGMENT:\s*(VALID|INVALID)', response, re.IGNORECASE)
            reason_match = re.search(r'REASON:\s*(.*)', response, re.IGNORECASE)

            judgment = judgment_match.group(1).upper() if judgment_match else "UNKNOWN"
            reason = reason_match.group(1).strip() if reason_match else "Reason not found in LLM response."

            results.append({
                'card': batch[j],
                'judgment': judgment,
                'reason': reason
            })

    return results

def main():
    parser = argparse.ArgumentParser(
        description="Validate card mechanical integrity using a Large Language Model.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Validate cards in a file using the default model
  python3 scripts/mtg_llm_validate.py generated_cards.txt

  # Validate specific cards by name
  python3 scripts/mtg_llm_validate.py --grep "Grizzly Bears"

  # Use a different model and output valid cards to a JSON file
  python3 scripts/mtg_llm_validate.py generated.txt --model "microsoft/phi-2" --json > valid.json
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, encoded text, etc.). Defaults to stdin or data/AllPrintings.json.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Optional path to save the validation report.')

    # Group: Model Options
    model_group = parser.add_argument_group('Model Options')
    model_group.add_argument('--model', default=DEFAULT_MODEL,
                        help=f'The HuggingFace model to use (Default: {DEFAULT_MODEL}).')

    default_device = 'cpu'
    if HAS_TRANSFORMERS and torch.cuda.is_available():
        default_device = 'cuda'

    model_group.add_argument('--device', default=default_device,
                        help='Device to run the model on (cuda, cpu, mps). Default: cuda if available.')
    model_group.add_argument('--batch-size', type=int, default=1,
                        help='Number of cards to process in each LLM batch. Default: 1.')

    # Group: Output Format
    fmt_group = parser.add_argument_group('Output Format')
    fmt_group.add_argument('-j', '--json', action='store_true', help='Output results as JSON.')
    fmt_group.add_argument('--csv', action='store_true', help='Output results as CSV.')
    fmt_group.add_argument('-t', '--table', action='store_true', help='Output results as a table (Default).')
    fmt_group.add_argument('--only-valid', action='store_true', help='Only include valid cards in the output.')

    # Group: Filtering Options
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--limit', type=int, default=0, help='Limit the number of cards to process.')
    filter_group.add_argument('--grep', action='append', help='Filter cards by search pattern.')
    filter_group.add_argument('--set', action='append', help='Filter cards by set code.')
    filter_group.add_argument('--rarity', action='append', help='Filter cards by rarity.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress the progress bar.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # Smart positional argument handling
    if args.infile and args.infile != '-' and not os.path.exists(args.infile):
        if args.outfile and os.path.exists(args.outfile):
            query = args.infile
            args.infile = args.outfile
            args.outfile = None
            if not args.grep: args.grep = [query]
            else: args.grep.append(query)
        else:
            if not args.grep: args.grep = [args.infile]
            else: args.grep.append(args.infile)
            args.infile = '-'

    # Default Dataset
    if args.infile == '-' and sys.stdin.isatty():
        default_data = 'data/AllPrintings.json'
        if os.path.exists(default_data):
            args.infile = default_data
            if not args.quiet:
                print(f"Notice: Using default dataset: {args.infile}", file=sys.stderr)

    # Load cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose, grep=args.grep, sets=args.set, rarities=args.rarity)
    if args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if args.verbose:
            print("No cards found matching criteria.", file=sys.stderr)
        return

    # Run LLM Validation
    results = validate_cards_llm(
        cards,
        model_name=args.model,
        device=args.device,
        batch_size=args.batch_size,
        quiet=args.quiet,
        verbose=args.verbose
    )

    if args.only_valid:
        results = [r for r in results if r['judgment'] == 'VALID']

    # Handle Output
    output_f = sys.stdout
    if args.outfile:
        output_f = open(args.outfile, 'w', encoding='utf8')

    use_color = args.color if args.color is not None else output_f.isatty()

    with redirect_stdout(output_f):
        if args.json:
            json_results = []
            for r in results:
                d = r['card'].to_dict()
                d['llm_judgment'] = r['judgment']
                d['llm_reason'] = r['reason']
                json_results.append(d)
            json.dump(json_results, sys.stdout, indent=2)
        elif args.csv:
            import csv
            writer = csv.DictWriter(sys.stdout, fieldnames=['name', 'judgment', 'reason', 'text'])
            writer.writeheader()
            for r in results:
                writer.writerow({
                    'name': r['card'].name,
                    'judgment': r['judgment'],
                    'reason': r['reason'],
                    'text': r['card'].text.text.replace('\n', '\\n')
                })
        else:
            # Table output
            header = ["Name", "Judgment", "Reason"]
            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

            rows = [header]
            for r in results:
                name = r['card'].name
                judgment = r['judgment']
                reason = r['reason']

                if use_color:
                    name = utils.colorize(name, utils.Ansi.BOLD)
                    if judgment == 'VALID':
                        judgment = utils.colorize(judgment, utils.Ansi.BOLD + utils.Ansi.GREEN)
                    elif judgment == 'INVALID':
                        judgment = utils.colorize(judgment, utils.Ansi.BOLD + utils.Ansi.RED)
                    else:
                        judgment = utils.colorize(judgment, utils.Ansi.BOLD + utils.Ansi.YELLOW)

                rows.append([name, judgment, reason])

            datalib.add_separator_row(rows)
            datalib.printrows(datalib.padrows(rows, aligns=['l', 'l', 'l']), indent=2)

    if args.outfile:
        output_f.close()

if __name__ == "__main__":
    main()
