#!/usr/bin/env python3
import sys
import os
import zipfile
import shutil
# tqdm is imported inside main/helpers or at top level if we want it global
try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm is not installed (though it is in requirements)
    def tqdm(iterable, **kwargs):
        return iterable

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)
import utils
import jdecode
import cardlib
from cbow import CBOW
from namediff import Namediff

def main(fname, oname = None, verbose = True, encoding = 'std',
         gatherer = True, for_forum = False, for_mse = False,
         creativity = False, vdump = False, html = False, text = False, json_out = False, csv_out = False, quiet=False,
         report_file=None, color_arg=None, limit=0, grep=None):

    # Set default format to text if no specific output format is selected.
    # If an output filename is provided, we try to detect the format from its extension.
    if not (html or text or for_mse or json_out or csv_out):
        if oname:
            if oname.endswith('.html'):
                html = True
            elif oname.endswith('.json'):
                json_out = True
            elif oname.endswith('.csv'):
                csv_out = True
            elif oname.endswith('.mse-set'):
                for_mse = True
            else:
                text = True
        else:
            text = True

    # Mutually exclusive output formats are now enforced by argparse in main block,
    # but we keep this check for programmatic access safety.
    if sum([bool(html), bool(for_mse), bool(json_out), bool(text), bool(csv_out)]) > 1:
        # If user explicitly requested multiple formats programmatically, we warn or error.
        # However, argparse logic below ensures text defaults to True only if others are False.
        # But if someone calls main() directly with multiple True, we should respect that or fail.
        # The original code errored on >1 format.
        print('ERROR - decode.py - incompatible output formats (choose one of --html, --mse, --json, --text)', file=sys.stderr)
        sys.exit(1)

    if for_mse:
        # MSE generation logically uses text generation internally.
        pass

    fmt_ordered = cardlib.fmt_ordered_default

    if encoding in ['std']:
        pass
    elif encoding in ['named']:
        fmt_ordered = cardlib.fmt_ordered_named
    elif encoding in ['noname']:
        fmt_ordered = cardlib.fmt_ordered_noname
    elif encoding in ['rfields']:
        pass
    elif encoding in ['old']:
        fmt_ordered = cardlib.fmt_ordered_old
    elif encoding in ['norarity']:
        fmt_ordered = cardlib.fmt_ordered_norarity
    elif encoding in ['vec']:
        pass
    elif encoding in ['custom']:
        ## put custom format decisions here ##########################
        
        ## end of custom format ######################################
        pass
    else:
        raise ValueError('decode.py: unknown encoding: ' + encoding)

    cards = jdecode.mtg_open_file(fname, verbose=verbose, fmt_ordered=fmt_ordered, report_file=report_file, grep=grep)

    if limit > 0:
        cards = cards[:limit]

    if creativity:
        namediff = Namediff()
        cbow = CBOW()
        # Progress bars in nearest_par will handle status updates unless quiet
        nearest_names = namediff.nearest_par([c.name for c in cards], n=3, quiet=quiet)
        nearest_cards = cbow.nearest_par(cards, quiet=quiet)
        for i in range(0, len(cards)):
            cards[i].nearest_names = nearest_names[i]
            cards[i].nearest_cards = nearest_cards[i]

    def write_csv_output(writer, cards, verbose=False):
        import csv
        fieldnames = ['name', 'mana_cost', 'type', 'subtypes', 'text', 'power', 'toughness', 'loyalty', 'rarity']
        csv_writer = csv.DictWriter(writer, fieldnames=fieldnames)
        csv_writer.writeheader()

        iterator = cards
        # Only use tqdm if we are writing to a file (writer is not stdout) or if we are not in quiet mode
        # But we don't have access to quiet mode here easily without passing it.
        # Since this is a helper, let's just iterate. Main loop handles progress usually.

        for card in cards:
            d = card.to_dict()
            # Flatten/map fields for CSV
            row = {
                'name': d.get('name', ''),
                'mana_cost': d.get('manaCost', ''),
                'type': ' '.join(d.get('supertypes', []) + d.get('types', [])),
                'subtypes': ' '.join(d.get('subtypes', [])),
                'text': d.get('text', ''),
                'power': d.get('power', d.get('pt', '') if '/' not in d.get('pt', '') else ''),
                'toughness': d.get('toughness', ''),
                'loyalty': d.get('loyalty', d.get('defense', '')),
                'rarity': d.get('rarity', ''),
            }
            if 'pt' in d and 'power' not in d:
                    # Handle case where pt is "X/Y" string in to_dict but split in CSV logic
                    if '/' in d['pt']:
                        p, t = d['pt'].split('/', 1)
                        row['power'] = p
                        row['toughness'] = t
                    else:
                        row['power'] = d['pt'] # Fallback?

            csv_writer.writerow(row)

    def hoverimg(cardname, dist, nd, for_html=False):
        # Gracefully handle cases where the card returned by CBOW is not in the Namediff set
        # This happens in testing when CBOW uses full data but Namediff uses a subset
        if cardname not in nd.names:
             return ''

        truename = nd.names[cardname]
        code = nd.codes[cardname]
        namestr = ''
        if for_html:
            if code:
                # Transform legacy magiccards.info code (set/number.jpg) to Scryfall API URL
                # Expected format: "set/number.jpg"
                try:
                    set_code, number_jpg = code.split('/')
                    number = number_jpg.replace('.jpg', '')
                    image_url = 'https://api.scryfall.com/cards/' + set_code + '/' + number + '?format=image&version=normal'
                except ValueError:
                    # In case code format is different than expected
                    image_url = 'http://magiccards.info/scans/en/' + code

                namestr = ('<div class="hover_img"><a href="#">' + truename
                           + '<span><img style="background: url(' + image_url
                           + ');" alt=""/></span></a>' + ': ' + str(dist) + '\n</div>\n')
            else:
                namestr = '<div>' + truename + ': ' + str(dist) + '</div>'
        elif for_forum:
            namestr = '[card]' + truename + '[/card]' + ': ' + str(dist) + '\n'
        else:
            namestr = truename + ': ' + str(dist) + '\n'
        return namestr

    def writecards(writer, for_html=False):
        if for_mse:
            # have to prepend a massive chunk of formatting info
            writer.write(utils.mse_prepend)
        elif for_html:
            # have to prepend html info
            writer.write(utils.html_prepend)
            # separate the write function to allow for writing smaller chunks of cards at a time
            segments = sort_colors(cards)
            for i in range(len(segments)):
                # sort color by CMC
                segments[i] = sort_type(segments[i])
                # this allows card boxes to be colored for each color
                # for coloring of each box separately cardlib.Card.format() must change non-minimally
                writer.write('<div id="' + utils.segment_ids[i] + '">')
                for card in segments[i]:
                    writecard(writer, card, for_html=True)
                writer.write("</div><hr>")
            # closing the html file
            writer.write(utils.html_append)
            return

        for card in tqdm(cards, disable=quiet, desc="Decoding"):
            writecard(writer, card)

        if for_mse:
            # more formatting info
            writer.write('version control:\n\ttype: none\napprentice code: ')

    def writecard(writer, card, for_html=False):
        try:
            if for_mse:
                writer.write(card.to_mse())
                fstring = ''
                if card.json:
                    fstring += 'JSON:\n' + card.json + '\n'
                if card.raw:
                    fstring += 'raw:\n' + card.raw + '\n'
                fstring += '\n'
                fstring += card.format(gatherer = gatherer, for_forum = for_forum,
                                       vdump = vdump) + '\n'
                fstring = fstring.replace('<', '(').replace('>', ')')
                writer.write(('\n' + fstring[:-1]).replace('\n', '\n\t\t'))
            else:
                # Determine if we should use color
                # Use color if:
                # 1. User explicitly requested it (color_arg == True)
                # 2. User didn't specify (color_arg == None) AND writer is stdout AND stdout is a TTY
                # 3. User didn't disable it (color_arg != False)
                use_color = False
                if not for_html and not for_mse:
                    if color_arg is True:
                        use_color = True
                    elif color_arg is None and writer == sys.stdout and sys.stdout.isatty():
                        use_color = True

                fstring = card.format(gatherer = gatherer, for_forum = for_forum,
                                      vdump = vdump, for_html = for_html, ansi_color = use_color)
                if for_html and creativity:
                    fstring = fstring[:-6] # chop off the closing </div> to stick stuff in

                writer.write((fstring + '\n'))
        except Exception as e:
            if vdump:
                # Assuming writer is a file object or stdout
                writer.write('ERROR processing card: ' + str(e) + '\n')
            else:
                raise

        if creativity:
            if for_html:
                cstring = '~~ closest cards ~~\n<br>\n'
            else:
                cstring = '~~ closest cards ~~\n'
            nearest = card.nearest_cards
            for dist, cardname in nearest:
                cstring += hoverimg(cardname, dist, namediff, for_html=for_html)

            if for_html:
                cstring += "<br>\n"
                cstring += '~~ closest names ~~\n<br>\n'
            else:
                cstring += '~~ closest names ~~\n'

            nearest = card.nearest_names
            for dist, cardname in nearest:
                cstring += hoverimg(cardname, dist, namediff, for_html=for_html)
            if for_mse:
                cstring = ('\n\n' + cstring[:-1]).replace('\n', '\n\t\t')
            elif for_html:
                cstring = '<hr><div>' + cstring + '</div>\n</div>'
            writer.write(cstring)

        writer.write('\n')

    # Sorting by colors
    def sort_colors(card_set):
        colors = {
            'W': [], 'U': [], 'B': [], 'R': [], 'G': [],
            'multi': [], 'colorless': [], 'lands': []
        }

        # Wrap in tqdm if not quiet
        iterator = tqdm(card_set, disable=quiet, desc="Sorting")
        for card in iterator:
            card_colors = card.cost.colors
            if len(card_colors) > 1:
                colors['multi'].append(card)
            elif len(card_colors) == 1:
                colors[card_colors[0]].append(card)
            else:
                if "land" in card.types:
                    colors['lands'].append(card)
                else:
                    colors['colorless'].append(card)

        return [colors['W'], colors['U'], colors['B'], colors['R'], colors['G'],
                colors['multi'], colors['colorless'], colors['lands']]

    def sort_type(card_set):
        sorting = ["creature", "enchantment", "instant", "sorcery", "artifact", "planeswalker"]
        sorted_cards = [[],[],[],[],[],[],[]]
        sorted_set = []
        for card in card_set:
            types = card.types
            for i in range(len(sorting)):
                if sorting[i] in types:
                    sorted_cards[i] += [card]
                    break
            else:
                sorted_cards[6] += [card]
        for value in sorted_cards:
            for card in value:
                sorted_set += [card]
        return sorted_set



    def sort_cmc(card_set):
        sorted_cards = []
        sorted_set = []
        for card in card_set:
            # make sure there is an empty set for each CMC
            while len(sorted_cards)-1 < card.cost.cmc:
                sorted_cards += [[]]
            # add card to correct set of CMC values
            sorted_cards[card.cost.cmc] += [card]
        # combine each set of CMC valued cards together
        for value in sorted_cards:
            for card in value:
                sorted_set += [card]
        return sorted_set


    if oname:
        if text and not for_mse:
            if verbose:
                print('Writing text output to: ' + oname, file=sys.stderr)
            with open(oname, 'w', encoding='utf8') as ofile:
                writecards(ofile)
        if html:
            fname = oname
            if not fname.endswith('.html'):
                fname += '.html'
            if verbose:
                print('Writing html output to: ' + fname, file=sys.stderr)
            with open(fname, 'w', encoding='utf8') as ofile:
                writecards(ofile, for_html=True)
        if json_out:
            import json
            if verbose:
                print('Writing json output to: ' + oname, file=sys.stderr)
            with open(oname, 'w', encoding='utf8') as ofile:
                json_cards = [card.to_dict() for card in cards]
                json.dump(json_cards, ofile, indent=2)
        if csv_out:
            if verbose:
                print('Writing csv output to: ' + oname, file=sys.stderr)
            with open(oname, 'w', encoding='utf8', newline='') as ofile:
                write_csv_output(ofile, cards, verbose=verbose)

        if for_mse:
            mse_oname = oname
            if not mse_oname.endswith('.mse-set'):
                mse_oname += '.mse-set'

            if os.path.isfile('set'):
                print('ERROR: tried to overwrite existing file "set" - aborting.', file=sys.stderr)
                return

            if verbose:
                print('Writing MSE output to: ' + mse_oname, file=sys.stderr)

            # Write cards to the temporary 'set' file
            with open('set', 'w', encoding='utf8') as ofile:
                writecards(ofile)

            # Use the freaky mse extension instead of zip.
            with zipfile.ZipFile(mse_oname, mode='w') as zf:
                try:
                    # Zip up the set file into oname.mse-set.
                    zf.write('set')
                finally:
                    # The set file is useless outside the .mse-set, delete it.
                    os.remove('set')
    else:
        if json_out:
            import json
            json_cards = [card.to_dict() for card in cards]
            json.dump(json_cards, sys.stdout, indent=2)
        elif csv_out:
            write_csv_output(sys.stdout, cards, verbose=verbose)
            sys.stdout.flush()
        else:
            # Correctly propagate for_html=html
            writecards(sys.stdout, for_html=html)
        sys.stdout.flush()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Decodes AI-generated text back into readable Magic cards or images.")

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input file containing encoded cards (or a JSON/CSV corpus) to decode. Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the decoded output. If not provided, output prints to the console. The format is automatically detected from the file extension (.html, .json, .csv, .mse-set).')

    # Group: Output Format (Mutually Exclusive)
    # We use a mutually exclusive group to enforce one output format.
    # Note: We cannot attach this directly to a titled argument group in argparse easily while keeping the title.
    # So we define the arguments in the main parser but link them via a mutex group.
    fmt_group = parser.add_mutually_exclusive_group()
    fmt_group.add_argument('--text', action='store_true',
                           help='Force plain text output (Default unless detected from extension).')
    fmt_group.add_argument('--html', action='store_true',
                           help='Generate a nicely formatted HTML file (Auto-detected for .html).')
    fmt_group.add_argument('--json', action='store_true',
                           help='Generate a structured JSON file (Auto-detected for .json).')
    fmt_group.add_argument('--csv', action='store_true',
                           help='Generate a CSV file (Auto-detected for .csv).')
    fmt_group.add_argument('--mse', action='store_true',
                           help='Generate a Magic Set Editor set file (Auto-detected for .mse-set). Requires an output filename.')

    # Group: Content Formatting
    content_group = parser.add_argument_group('Content Formatting')
    content_group.add_argument('-e', '--encoding', default='std', choices=utils.formats,
                        help="Format of the input data. Default is 'std' (standard).")

    # Gatherer formatting is on by default.
    parser.set_defaults(gatherer=True)

    # We provide a --raw flag to disable it.
    # We also keep -g for backward compatibility but make it a no-op that ensures True.
    content_group.add_argument('-g', '--gatherer', action='store_true', default=True,
                        help='Explicitly enable Gatherer formatting (Default).')
    content_group.add_argument('--raw', '--no-gatherer', dest='gatherer', action='store_false',
                        help='Output raw text without Gatherer formatting.')

    content_group.add_argument('-f', '--forum', action='store_true',
                        help='Use pretty formatting for mana symbols (compatible with MTG Salvation forums).')

    # Color options
    # We use a mutual exclusive group to allow --color and --no-color
    color_group = content_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None,
                        help='Force enable ANSI color output (useful for piping to less -R).')
    color_group.add_argument('--no-color', action='store_false', dest='color',
                        help='Disable ANSI color output.')

    # Group: Processing & Debugging
    proc_group = parser.add_argument_group('Processing & Debugging')
    proc_group.add_argument('-c', '--creativity', action='store_true',
                        help="Enable 'creativity' mode: calculate similarity to existing cards using CBOW (slow).")
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Limit the number of cards to decode.')
    proc_group.add_argument('-d', '--dump', action='store_true',
                        help='Debug mode: print detailed information about cards that failed to validate.')
    proc_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output.')
    proc_group.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress the progress bar.')
    proc_group.add_argument('--report-failed',
                        help='File path to save the text of cards that failed to parse/validate (useful for debugging).')
    proc_group.add_argument('--grep', action='append',
                        help='Filter cards by regex (matches name, type, or text). Can be used multiple times (AND logic).')

    args = parser.parse_args()

    # If --mse is used, we must have an output filename.
    if args.mse and not args.outfile:
        parser.error("--mse requires an output filename.")

    main(args.infile, args.outfile, verbose = args.verbose, encoding = args.encoding,
         gatherer = args.gatherer, for_forum = args.forum, for_mse = args.mse,
         creativity = args.creativity, vdump = args.dump, html = args.html, text = args.text, json_out = args.json, csv_out = args.csv, quiet=args.quiet,
         report_file = args.report_failed, color_arg=args.color, limit=args.limit, grep=args.grep)

    exit(0)
