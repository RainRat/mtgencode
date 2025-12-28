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
         gatherer = False, for_forum = False, for_mse = False,
         creativity = False, vdump = False, html = False, text = False, quiet=False,
         report_file=None):

    if not (html or text or for_mse):
        text = True

    # there is a sane thing to do here (namely, produce both at the same time)
    # but we don't support it yet.
    if for_mse and html:
        print('ERROR - decode.py - incompatible formats "mse" and "html"', file=sys.stderr)
        return

    if for_mse:
        text = True

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

    cards = jdecode.mtg_open_file(fname, verbose=verbose, fmt_ordered=fmt_ordered, report_file=report_file)

    if creativity:
        namediff = Namediff()
        cbow = CBOW()
        if verbose:
            print('Computing nearest names...', file=sys.stderr)
        nearest_names = namediff.nearest_par([c.name for c in cards], n=3)
        if verbose:
            print('Computing nearest cards...', file=sys.stderr)
        nearest_cards = cbow.nearest_par(cards)
        for i in range(0, len(cards)):
            cards[i].nearest_names = nearest_names[i]
            cards[i].nearest_cards = nearest_cards[i]
        if verbose:
            print('...Done.', file=sys.stderr)

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
                fstring = card.format(gatherer = gatherer, for_forum = for_forum,
                                      vdump = vdump, for_html = for_html)
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
        if text:
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
        if for_mse:
            # Copy whatever output file is produced, name the copy 'set' (yes,
            # no extension).
            if os.path.isfile('set'):
                print('ERROR: tried to overwrite existing file "set" - aborting.', file=sys.stderr)
                return
            shutil.copyfile(oname, 'set')
            # Use the freaky mse extension instead of zip.
            with zipfile.ZipFile(oname+'.mse-set', mode='w') as zf:
                try:
                    # Zip up the set file into oname.mse-set.
                    zf.write('set')
                finally:
                    if verbose:
                        print('Made an MSE set file called ' +
                              oname + '.mse-set.', file=sys.stderr)
                    # The set file is useless outside the .mse-set, delete it.
                    os.remove('set')
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
                        help='Input file containing encoded cards (or a JSON corpus) to decode. Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the decoded output. If not provided, output prints to the console.')

    # Group: Output Format
    fmt_group = parser.add_argument_group('Output Format')
    fmt_group.add_argument('--text', action='store_true',
                           help='Force plain text output (enabled by default unless --html or --mse is used).')
    fmt_group.add_argument('--html', action='store_true',
                           help='Generate a nicely formatted HTML file instead of plain text.')
    fmt_group.add_argument('--mse', action='store_true',
                           help='Generate a Magic Set Editor set file (.mse-set). Requires an output filename to generate the .mse-set file.')

    # Group: Content Formatting
    content_group = parser.add_argument_group('Content Formatting')
    content_group.add_argument('-e', '--encoding', default='std', choices=utils.formats,
                        help="Format of the input data. Default is 'std' (standard).")
    content_group.add_argument('-g', '--gatherer', action='store_true',
                        help='Format output to look like the Gatherer visual spoiler (includes capitalization and formatting).')
    content_group.add_argument('-f', '--forum', action='store_true',
                        help='Use pretty formatting for mana symbols (compatible with MTG Salvation forums).')

    # Group: Processing & Debugging
    proc_group = parser.add_argument_group('Processing & Debugging')
    proc_group.add_argument('-c', '--creativity', action='store_true',
                        help="Enable 'creativity' mode: calculate similarity to existing cards using CBOW (slow).")
    proc_group.add_argument('-d', '--dump', action='store_true',
                        help='Debug mode: print detailed information about cards that failed to validate.')
    proc_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output.')
    proc_group.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress the progress bar.')
    proc_group.add_argument('--report-failed',
                        help='File path to save the text of cards that failed to parse/validate (useful for debugging).')

    args = parser.parse_args()

    main(args.infile, args.outfile, verbose = args.verbose, encoding = args.encoding,
         gatherer = args.gatherer, for_forum = args.forum, for_mse = args.mse,
         creativity = args.creativity, vdump = args.dump, html = args.html, text = args.text, quiet=args.quiet,
         report_file = args.report_failed)

    exit(0)
