import io
import re
import sys
import unittest
from unittest.mock import patch

from lib import cardlib, utils


class TestCardlibGapsComprehensive(unittest.TestCase):

    def test_fields_from_json_toughness_only_parses_as_invalid_pt(self):
        json_data = {
            'name': 'Shield Wall',
            'types': ['Creature'],
            'toughness': '4'
        }
        parsed, valid, fields = cardlib.fields_from_json(json_data)
        self.assertFalse(parsed)
        self.assertIn(cardlib.field_pt, fields)
        self.assertEqual(fields[cardlib.field_pt][0][1], '/' + utils.to_ascii(utils.to_unary('4')))

    def test_fields_from_format_handles_intermediate_empty_fields(self):
        src_text = "Lightning Bolt|Instant||Common"
        fmt_ordered = [
            cardlib.field_name,
            cardlib.field_types,
            cardlib.field_subtypes,
            cardlib.field_rarity,
        ]
        parsed, valid, fields = cardlib.fields_from_format(
            src_text, fmt_ordered, fmt_labeled=None, fieldsep='|'
        )
        self.assertTrue(parsed)
        self.assertIn(cardlib.field_name, fields)
        self.assertIn(cardlib.field_types, fields)
        self.assertIn(cardlib.field_rarity, fields)

    def test_fields_from_format_excess_unlabeled_fields_assigns_field_other(self):
        src_text = "Grizzly Bears|Creature|C|{1}{G}|2/2|Extra Unlabeled Field"
        fmt_ordered = [
            cardlib.field_name,
            cardlib.field_types,
            cardlib.field_rarity,
            cardlib.field_cost,
            cardlib.field_pt
        ]
        parsed, valid, fields = cardlib.fields_from_format(
            src_text, fmt_ordered, fmt_labeled=None, fieldsep='|'
        )
        self.assertFalse(parsed)
        self.assertFalse(valid)
        self.assertIn(cardlib.field_other, fields)

    def test_card_init_unknown_field_raises_value_error(self):
        with patch('lib.cardlib.fields_from_format') as mock_fff:
            mock_fff.return_value = (True, True, {'nonexistent_field_xyz': [(-1, 'val')]})
            with self.assertRaises(ValueError) as ctx:
                cardlib.Card("some_raw_text")
            self.assertIn("Unknown field for Card object: nonexistent_field_xyz", str(ctx.exception))

    def test_verbose_logging_for_invalid_and_multiple_pt_values(self):
        stderr_buffer = io.StringIO()
        with patch('sys.stderr', stderr_buffer):
            card = cardlib.Card.__new__(cardlib.Card)
            card.name = "Glitch Creature"
            card.verbose = True
            card.valid = True
            card.field_other = []
            setattr(card, cardlib.field_other, [])

            card._set_pt([(-1, 'Invalid PT Format'), (-1, '2/2')])

            self.assertFalse(card.valid)
            output = stderr_buffer.getvalue()
            self.assertIn("Invalid P/T value for card 'Glitch Creature'", output)
            self.assertIn("Multiple P/T values for card 'Glitch Creature'", output)

    def test_verbose_logging_for_multiple_loyalty_values(self):
        stderr_buffer = io.StringIO()
        with patch('sys.stderr', stderr_buffer):
            card = cardlib.Card.__new__(cardlib.Card)
            card.name = "Glitch Walker"
            card.verbose = True
            card.valid = True
            setattr(card, cardlib.field_other, [])

            card._set_loyalty([(-1, '^^^'), (-1, '^^^^')])

            self.assertFalse(card.valid)
            output = stderr_buffer.getvalue()
            self.assertIn("Multiple loyalty values for card 'Glitch Walker'", output)

    def test_format_vdump_field_other_rendering_across_formats(self):
        card = cardlib.Card({
            'name': 'Test Card',
            'types': ['Sorcery'],
            'rarity': 'common',
            'text': 'Deal 3 damage.'
        })
        card.other = [(1, 'Extra Metadata Line 1'), (2, 'Extra Metadata Line 2')]

        plain_text_out = card.format(vdump=True)
        self.assertIn('(1) Extra Metadata Line 1', plain_text_out)
        self.assertIn('(2) Extra Metadata Line 2', plain_text_out)

        html_out = card.format(vdump=True, for_html=True)
        self.assertIn('<i>', html_out)
        self.assertIn('<br>', html_out)

        forum_out = card.format(vdump=True, for_forum=True)
        self.assertIn('[i]', forum_out)

        md_out = card.format(vdump=True, for_md=True)
        self.assertIn('_', md_out)

    def test_format_vdump_unparsed_invalid_and_missing_name_or_types(self):
        card = cardlib.Card.__new__(cardlib.Card)
        card.name = ''
        card.parsed = False
        card.valid = False
        card.rarity = 'C'
        card.cost = cardlib.Manacost('')
        card.text = cardlib.Manatext('')
        card.supertypes = []
        card.types = []
        card.subtypes = []
        card.pt = ''
        card.loyalty = ''
        card.bside = None
        card.fields = {}
        card.printings = []
        card._ability_words = []
        card.other = []

        vdump_out = card.format(vdump=True)
        self.assertIn('_NONAME_', vdump_out)
        self.assertIn('_UNPARSED_', vdump_out)
        self.assertIn('_INVALID_', vdump_out)

        gatherer_out = card.format(gatherer=True, vdump=True)
        self.assertIn('_NOTYPE_', gatherer_out)

    def test_cockatrice_xml_multi_face_instant_sorcery_tablerow(self):
        card_json = {
            'name': 'Fire',
            'manaCost': '{1}{R}',
            'types': ['Instant'],
            'rarity': 'uncommon',
            'text': 'Fire deals 2 damage divided as you choose among one or two targets.',
            'bside': {
                'name': 'Ice',
                'manaCost': '{1}{U}',
                'types': ['Instant'],
                'rarity': 'uncommon',
                'text': 'Tap target permanent. Draw a card.'
            }
        }
        card = cardlib.Card(card_json)
        xml_out = card.to_cockatrice_xml()

        self.assertIn('<name>Fire // Ice</name>', xml_out)
        self.assertIn('<tablerow>3</tablerow>', xml_out)
        self.assertIn('<color>RU</color>', xml_out)
        self.assertIn('<text>Fire deals 2 damage divided as you choose among one or two targets.\n\n---\n\nTap target permanent. Draw a card.</text>', xml_out)

    def test_get_face_mechanics_keyword_abilities_detection(self):
        card_text = (
            "Awaken 3—{4}{U}\n"
            "Surge {1}{U}\n"
            "Investigate\n"
            "Surveil 2\n"
            "Amass Orcs 1\n"
            "Foretell {1}{U}\n"
            "Learn\n"
            "Toxic 1\n"
            "Backup 1\n"
            "Incubate 2\n"
            "Discover 3"
        )
        card = cardlib.Card({
            'name': 'Keyword Omnibus',
            'types': ['Sorcery'],
            'rarity': 'rare',
            'text': card_text
        })
        mechanics = card.get_face_mechanics()

        expected_keywords = [
            'Awaken', 'Surge', 'Investigate', 'Surveil', 'Amass',
            'Foretell', 'Learn', 'Toxic', 'Backup', 'Incubate', 'Discover'
        ]
        for keyword in expected_keywords:
            self.assertIn(keyword, mechanics)

    def test_recursive_search_methods_on_bside_matches(self):
        card_json = {
            'name': 'Front Face',
            'manaCost': '{2}{W}',
            'types': ['Creature'],
            'subtypes': ['Human'],
            'rarity': 'common',
            'pt': '2/2',
            'text': 'Vigilance',
            'bside': {
                'name': 'Back Dragon',
                'manaCost': '{4}{R}',
                'types': ['Creature'],
                'subtypes': ['Dragon'],
                'rarity': 'rare',
                'pt': '5/5',
                'loyalty': '4',
                'text': 'Flying, Trample.',
            }
        }
        card = cardlib.Card(card_json)

        self.assertTrue(card.search_name(re.compile(r'Back Dragon', re.I)))
        self.assertTrue(card.search_types(re.compile(r'Dragon', re.I)))
        self.assertTrue(card.search_text(re.compile(r'Trample', re.I)))
        self.assertTrue(card.search_cost(re.compile(r'\{4\}\{R\}', re.I)))
        self.assertTrue(card.search_pt(re.compile(r'5/5', re.I)))
        self.assertTrue(card.search_loyalty(re.compile(r'4', re.I)))
        self.assertTrue(card.search_rarity(re.compile(r'rare', re.I)))
        self.assertTrue(card.search_mechanics(re.compile(r'Trample', re.I)))


if __name__ == '__main__':
    unittest.main()
