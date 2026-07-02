import argparse
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from lib import cli_utils

def test_add_standard_filters_parser():
    parser = argparse.ArgumentParser()
    cli_utils.add_standard_filters(parser)
    args = parser.parse_args(['--grep', 'pattern', '--cmc', '3'])
    assert args.grep == ['pattern']
    assert args.cmc == ['3']

def test_add_standard_filters_group():
    parser = argparse.ArgumentParser()
    group = parser.add_argument_group('Test Group')
    cli_utils.add_standard_filters(group)
    args = parser.parse_args(['--grep', 'pattern'])
    assert args.grep == ['pattern']

def test_add_standard_output_args_parser():
    parser = argparse.ArgumentParser()
    cli_utils.add_standard_output_args(parser)
    args = parser.parse_args(['--json', '--verbose', '--color'])
    assert args.json is True
    assert args.verbose is True
    assert args.color is True

def test_add_standard_output_args_group():
    parser = argparse.ArgumentParser()
    group = parser.add_argument_group('Test Group')
    cli_utils.add_standard_output_args(group)
    args = parser.parse_args(['--csv', '--quiet', '--no-color'])
    assert args.csv is True
    assert args.quiet is True
    assert args.color is False

@patch('lib.cli_utils.jdecode.mtg_open_file')
@patch('os.path.exists')
def test_load_and_filter_cards_simple(mock_exists, mock_open):
    mock_exists.return_value = True
    mock_open.return_value = ['card1', 'card2']
    args = argparse.Namespace(infile='data.json', limit=1)
    cards = cli_utils.load_and_filter_cards(args)
    assert cards == ['card1']
    mock_open.assert_called_once()

@patch('lib.cli_utils.jdecode.mtg_open_file')
@patch('os.path.exists')
def test_load_and_filter_cards_swapping(mock_exists, mock_open):
    # infile doesn't exist, outfile exists
    mock_exists.side_effect = lambda x: x == 'real_file.json'
    mock_open.return_value = ['card']

    args = argparse.Namespace(infile='query', outfile='real_file.json', grep=None)
    cli_utils.load_and_filter_cards(args)

    assert args.infile == 'real_file.json'
    assert args.grep == ['query']
    assert args.outfile is None

@patch('lib.cli_utils.jdecode.mtg_open_file')
@patch('os.path.exists')
def test_load_and_filter_cards_auto_grep(mock_exists, mock_open):
    # infile doesn't exist, outfile doesn't exist (or is None)
    mock_exists.return_value = False
    mock_open.return_value = ['card']

    args = argparse.Namespace(infile='query', outfile=None, grep=None)
    cli_utils.load_and_filter_cards(args)

    assert args.infile == '-'
    assert args.grep == ['query']

@patch('lib.cli_utils.jdecode.mtg_open_file')
@patch('sys.stdin.isatty')
@patch('os.path.exists')
def test_load_and_filter_cards_default_dataset(mock_exists, mock_isatty, mock_open):
    mock_isatty.return_value = True
    # Mock AllPrintings.json existence
    mock_exists.side_effect = lambda x: 'AllPrintings.json' in x
    mock_open.return_value = ['card']

    args = argparse.Namespace(infile='-', quiet=False)
    cli_utils.load_and_filter_cards(args)

    assert 'AllPrintings.json' in args.infile

@patch('lib.cli_utils.jdecode.mtg_open_file')
@patch('os.path.exists')
def test_load_and_filter_cards_sample(mock_exists, mock_open):
    mock_exists.return_value = True
    mock_open.return_value = ['c1', 'c2', 'c3']
    args = argparse.Namespace(infile='-', sample=2, limit=0, shuffle=False)
    cards = cli_utils.load_and_filter_cards(args)
    assert len(cards) == 2
    # Verify shuffle was passed to mtg_open_file
    args_passed = mock_open.call_args[1]
    assert args_passed['shuffle'] is True

@patch('lib.cli_utils.jdecode.mtg_open_file')
@patch('os.path.exists')
def test_load_and_filter_cards_all_args(mock_exists, mock_open):
    mock_exists.return_value = True
    args = argparse.Namespace(
        infile='data.json', grep=['g'], vgrep=['vg'],
        grep_name=['gn'], exclude_name=['en'],
        grep_type=['gt'], exclude_type=['et'],
        grep_text=['gtx'], exclude_text=['etx'],
        grep_cost=['gc'], exclude_cost=['ec'],
        grep_pt=['gp'], exclude_pt=['ep'],
        grep_loyalty=['gl'], exclude_loyalty=['el'],
        set=['S'], rarity=['R'], colors=['C'], cmc=['3'],
        pow=['2'], tou=['2'], loy=['5'],
        mechanic=['M'], action=['A'], identity=['I'], id_count=['1'],
        deck='deck.txt', booster=1, box=1,
        limit=0, shuffle=True, seed=42, sample=0
    )
    cli_utils.load_and_filter_cards(args)
    mock_open.assert_called_once_with(
        'data.json', verbose=False,
        grep=['g'], vgrep=['vg'],
        grep_name=['gn'], vgrep_name=['en'],
        grep_types=['gt'], vgrep_types=['et'],
        grep_text=['gtx'], vgrep_text=['etx'],
        grep_cost=['gc'], vgrep_cost=['ec'],
        grep_pt=['gp'], vgrep_pt=['ep'],
        grep_loyalty=['gl'], vgrep_loyalty=['el'],
        sets=['S'], rarities=['R'], colors=['C'], cmcs=['3'],
        pows=['2'], tous=['2'], loys=['5'],
        mechanics=['M'], actions=['A'], produces=None, color_pie_break=False,
        legalities=None,
        identities=['I'], id_counts=['1'],
        decklist_file='deck.txt', booster=1, box=1,
        shuffle=True, seed=42,
        complexities=None, ratings=None, fair_mvs=None
    )

@patch('lib.cli_utils.jdecode.mtg_open_file')
@patch('os.path.exists')
def test_load_and_filter_cards_swapping_append_grep(mock_exists, mock_open):
    # infile doesn't exist, outfile exists, grep is already present
    mock_exists.side_effect = lambda x: x == 'real_file.json'
    mock_open.return_value = ['card']

    args = argparse.Namespace(infile='query2', outfile='real_file.json', grep=['query1'])
    cli_utils.load_and_filter_cards(args)

    assert args.infile == 'real_file.json'
    assert args.grep == ['query1', 'query2']

@patch('lib.cli_utils.jdecode.mtg_open_file')
@patch('os.path.exists')
def test_load_and_filter_cards_auto_grep_append(mock_exists, mock_open):
    # infile doesn't exist, outfile doesn't exist, grep already present
    mock_exists.return_value = False
    mock_open.return_value = ['card']

    args = argparse.Namespace(infile='query2', outfile=None, grep=['query1'])
    cli_utils.load_and_filter_cards(args)

    assert args.infile == '-'
    assert args.grep == ['query1', 'query2']
