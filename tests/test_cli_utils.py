import pytest
import argparse
import os
import sys
from unittest.mock import patch, MagicMock
from lib import cli_utils

def test_add_standard_filters():
    parser = argparse.ArgumentParser()
    cli_utils.add_standard_filters(parser)

    # Check if some expected arguments were added
    args = parser.parse_args(['--grep', 'flying', '--colors', 'W', '--limit', '10'])
    assert args.grep == ['flying']
    assert args.colors == ['W']
    assert args.limit == 10

def test_add_standard_filters_group():
    # Pass a non-ArgumentParser to add_standard_filters (the else branch of line 9)
    parser = argparse.ArgumentParser()
    group = parser.add_argument_group('Filtering')
    cli_utils.add_standard_filters(group)

    # Check if some expected arguments were added
    args = parser.parse_args(['--rarity', 'common', '--cmc', '>3'])
    assert args.rarity == ['common']
    assert args.cmc == ['>3']

def test_add_standard_output_args():
    parser = argparse.ArgumentParser()
    cli_utils.add_standard_output_args(parser)

    # Mutually exclusive group check
    args = parser.parse_args(['--json', '--verbose'])
    assert args.json is True
    assert args.verbose is True
    assert args.csv is False
    assert args.table is False

    with pytest.raises(SystemExit):
        parser.parse_args(['--json', '--csv'])

def test_add_standard_output_args_group():
    # Pass a non-ArgumentParser to add_standard_output_args (else branch of line 95 and 106)
    parser = argparse.ArgumentParser()
    group = parser.add_argument_group('Output')
    cli_utils.add_standard_output_args(group)

    args = parser.parse_args(['--csv', '--quiet', '--no-color'])
    assert args.csv is True
    assert args.quiet is True
    assert args.color is False

def test_load_and_filter_cards_infile_exists():
    args = argparse.Namespace(infile='exists.json', outfile=None, quiet=True)

    with patch('os.path.exists', return_value=True), \
         patch('lib.cli_utils.jdecode.mtg_open_file', return_value=['card1']) as mock_open:
        cards = cli_utils.load_and_filter_cards(args)
        assert cards == ['card1']
        assert args.infile == 'exists.json'
        mock_open.assert_called_once()
        # Verify default filter arguments are passed as None or default
        call_args = mock_open.call_args[1]
        assert call_args['grep'] is None
        assert call_args['booster'] == 0

def test_load_and_filter_cards_smart_swap():
    # If infile doesn't exist but outfile does, swap them.
    # Case: getattr(args, 'grep', None) is None
    args = argparse.Namespace(infile='query', outfile='data.json', quiet=True, grep=None)

    def mock_exists(path):
        if path == 'query': return False
        if path == 'data.json': return True
        return False

    with patch('os.path.exists', side_effect=mock_exists), \
         patch('lib.cli_utils.jdecode.mtg_open_file', return_value=['card1']) as mock_open:
        cards = cli_utils.load_and_filter_cards(args)
        assert args.infile == 'data.json'
        assert args.outfile is None
        assert args.grep == ['query']
        mock_open.assert_called_once()

def test_load_and_filter_cards_smart_swap_append():
    # If infile doesn't exist but outfile does, swap them.
    # Case: getattr(args, 'grep', None) is NOT None
    args = argparse.Namespace(infile='query', outfile='data.json', quiet=True, grep=['other'])

    def mock_exists(path):
        if path == 'query': return False
        if path == 'data.json': return True
        return False

    with patch('os.path.exists', side_effect=mock_exists), \
         patch('lib.cli_utils.jdecode.mtg_open_file', return_value=['card1']) as mock_open:
        cards = cli_utils.load_and_filter_cards(args)
        assert args.infile == 'data.json'
        assert args.grep == ['other', 'query']

def test_load_and_filter_cards_treat_as_query():
    # If infile doesn't exist and no outfile to swap, treat infile as query.
    # Case: getattr(args, 'grep', None) is None
    args = argparse.Namespace(infile='query', outfile=None, quiet=True, grep=None)

    with patch('os.path.exists', return_value=False), \
         patch('lib.cli_utils.jdecode.mtg_open_file', return_value=['card1']) as mock_open:
        cards = cli_utils.load_and_filter_cards(args)
        assert args.infile == '-'
        assert args.grep == ['query']

def test_load_and_filter_cards_treat_as_query_append():
    # If infile doesn't exist and no outfile to swap, treat infile as query.
    # Case: getattr(args, 'grep', None) is NOT None
    args = argparse.Namespace(infile='query', outfile=None, quiet=True, grep=['existing'])

    with patch('os.path.exists', return_value=False), \
         patch('lib.cli_utils.jdecode.mtg_open_file', return_value=['card1']) as mock_open:
        cards = cli_utils.load_and_filter_cards(args)
        assert args.infile == '-'
        assert args.grep == ['existing', 'query']

def test_load_and_filter_cards_default_dataset():
    # If infile is '-' and stdin is a TTY, try to find AllPrintings.json
    args = argparse.Namespace(infile='-', quiet=False)

    def mock_exists(path):
        if 'AllPrintings.json' in path: return True
        return False

    with patch('sys.stdin.isatty', return_value=True), \
         patch('os.path.exists', side_effect=mock_exists), \
         patch('lib.cli_utils.jdecode.mtg_open_file', return_value=['card1']):
        cards = cli_utils.load_and_filter_cards(args)
        assert 'AllPrintings.json' in args.infile

def test_load_and_filter_cards_sample():
    args = argparse.Namespace(infile='exists.json', sample=5, limit=0, shuffle=False, quiet=True)

    with patch('os.path.exists', return_value=True), \
         patch('lib.cli_utils.jdecode.mtg_open_file', return_value=[i for i in range(10)]) as mock_open:
        cards = cli_utils.load_and_filter_cards(args)
        assert len(cards) == 5
        # Verify shuffle was passed as True to mtg_open_file
        assert mock_open.call_args[1]['shuffle'] is True

def test_load_and_filter_cards_complex_filters():
    args = argparse.Namespace(
        infile='exists.json',
        quiet=True,
        rarity=['common'],
        colors=['W', 'U'],
        cmc=['>2'],
        mechanic=['Flying'],
        action=['Removal'],
        identity=['W'],
        id_count=['1'],
        booster=1,
        box=0,
        shuffle=True,
        seed=42,
        limit=10
    )

    with patch('os.path.exists', return_value=True), \
         patch('lib.cli_utils.jdecode.mtg_open_file', return_value=[i for i in range(20)]) as mock_open:
        cards = cli_utils.load_and_filter_cards(args)
        assert len(cards) == 10
        call_kwargs = mock_open.call_args[1]
        assert call_kwargs['rarities'] == ['common']
        assert call_kwargs['colors'] == ['W', 'U']
        assert call_kwargs['cmcs'] == ['>2']
        assert call_kwargs['mechanics'] == ['Flying']
        assert call_kwargs['actions'] == ['Removal']
        assert call_kwargs['identities'] == ['W']
        assert call_kwargs['id_counts'] == ['1']
        assert call_kwargs['booster'] == 1
        assert call_kwargs['box'] == 0
        assert call_kwargs['shuffle'] is True
        assert call_kwargs['seed'] == 42
