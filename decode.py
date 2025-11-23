#!/usr/bin/env python3
import sys
import os
import zipfile
import shutil

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)
import utils
import jdecode
import cardlib
from cbow import CBOW
from namediff import Namediff

def main(fname, oname = None, verbose = True, encoding = 'std',
         gatherer = False, for_forum = False, for_mse = False,
         creativity = False, vdump = False, html = False, text = False):

    if not (html or text or for_mse):
        text = True

    # there is a sane thing to do here (namely, produce both at the same time)
    # but we don't support it yet.
    if for_mse and html:
        print('ERROR - decode.py - incompatible formats "mse" and "html"')
        return

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

    cards = jdecode.mtg_open_file(fname, verbose=verbose, fmt_ordered=fmt_ordered)

    if creativity:
        namediff = Namediff()
        cbow = CBOW()
        if verbose:
            print('Computing nearest names...')
        nearest_names = namediff.nearest_par([c.name for c in cards], n=3)
        if verbose:
            print('Computing nearest cards...')
        nearest_cards = cbow.nearest_par(cards)
        for i in range(0, len(cards)):
            cards[i].nearest_names = nearest_names[i]
            cards[i].nearest_cards = nearest_cards[i]
        if verbose:
            print('...Done.')

    def hoverimg(cardname, dist, nd, for_html=False):
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

        for card in cards:
            writecard(writer, card)

        if for_mse:
            # more formatting info
            writer.write('version control:\n\ttype: none\napprentice code: ')

    def writecard(writer, card, for_html=False):
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

        for card in card_set:
            card_colors = card.get_colors()
            if len(card_colors) > 1:
                colors['multi'].append(card)
            elif len(card_colors) == 1:
                colors[card_colors[0]].append(card)
            else:
                if "land" in card.get_types():
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
            types = card.get_types()
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
            while len(sorted_cards)-1 < card.get_cmc():
                sorted_cards += [[]]
            # add card to correct set of CMC values
            sorted_cards[card.get_cmc()] += [card]
        # combine each set of CMC valued cards together
        for value in sorted_cards:
            for card in value:
                sorted_set += [card]
        return sorted_set


    if oname:
        if text:
            if verbose:
                print('Writing text output to: ' + oname)
            with open(oname, 'w', encoding='utf8') as ofile:
                writecards(ofile)
        if html:
            fname = oname
            if not fname.endswith('.html'):
                fname += '.html'
            if verbose:
                print('Writing html output to: ' + fname)
            with open(fname, 'w', encoding='utf8') as ofile:
                writecards(ofile, for_html=True)
        if for_mse:
            # Copy whatever output file is produced, name the copy 'set' (yes,
            # no extension).
            if os.path.isfile('set'):
                print('ERROR: tried to overwrite existing file "set" - aborting.')
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
                              oname + '.mse-set.')
                    # The set file is useless outside the .mse-set, delete it.
                    os.remove('set')
    else:
        writecards(sys.stdout)
        sys.stdout.flush()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('infile', #nargs='?'. default=None,
                        help='encoded card file or json corpus to encode')
    parser.add_argument('outfile', nargs='?', default=None,
                        help='output file, defaults to stdout')
    parser.add_argument('-e', '--encoding', default='std', choices=utils.formats,
                        #help='{' + ','.join(formats) + '}',
                        help='encoding format to use',
    )
    parser.add_argument('-g', '--gatherer', action='store_true',
                        help='emulate Gatherer visual spoiler')
    parser.add_argument('-f', '--forum', action='store_true',
                        help='use pretty mana encoding for mtgsalvation forum')
    parser.add_argument('-c', '--creativity', action='store_true',
                        help='use CBOW fuzzy matching to check creativity of cards')
    parser.add_argument('-d', '--dump', action='store_true',
                        help='dump out lots of information about invalid cards')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='verbose output')
    parser.add_argument('--mse', action='store_true',
                        help='use Magic Set Editor 2 encoding; will output as .mse-set file')
    parser.add_argument('--html', action='store_true', help='create a .html file with pretty forum formatting')
    parser.add_argument('--text', action='store_true', help='create a text file with pretty forum formatting')

    args = parser.parse_args()

    main(args.infile, args.outfile, verbose = args.verbose, encoding = args.encoding,
         gatherer = args.gatherer, for_forum = args.forum, for_mse = args.mse,
         creativity = args.creativity, vdump = args.dump, html = args.html, text = args.text)

    exit(0)
