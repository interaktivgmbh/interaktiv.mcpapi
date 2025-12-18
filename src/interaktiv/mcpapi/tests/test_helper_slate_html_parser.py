import unittest

from interaktiv.mcpapi.testing import INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING
from plone.app.testing import TEST_USER_ID, setRoles
from interaktiv.mcpapi.helpers import SlateHTMLParser


class TestSlateHTMLParser(unittest.TestCase):
    layer = INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Site Administrator'])

        self.parser = SlateHTMLParser()

    def test_slate_html_parser__handle_starttag__inline_tag(self):
        # setup
        tag = 'b'
        attrs = {}

        # do it
        self.parser.handle_starttag(tag, attrs)

        # postcondition
        expected_stack = [
            [
                {'type': 'strong', 'children': []}
            ],
            []
        ]
        self.assertEqual(self.parser.stack, expected_stack)

    def test_slate_html_parser__handle_starttag__a_tag(self):
        # setup
        tag = 'a'
        attrs = {'href': 'https://interaktiv.de'}

        # do it
        self.parser.handle_starttag(tag, attrs)

        # postcondition
        expected_stack = [
            [
                {'type': 'link', 'data': {'url': 'https://interaktiv.de'}, 'children': []}
            ],
            []
        ]
        self.assertEqual(self.parser.stack, expected_stack)

    def test_slate_html_parser__handle_endtag__keeps_stack_entry(self):
        # setup
        self.parser.stack = [1, 2, 3]
        tag = 'unkown_tag'

        # do it
        self.parser.handle_endtag(tag)

        # postcondition
        self.assertEqual(self.parser.stack, [1, 2, 3])

    def test_slate_html_parser__handle_endtag__removes_stack_entry(self):
        # setup
        self.parser.stack = [1, 2, 3]
        tag = 'b'

        # do it
        self.parser.handle_endtag(tag)

        # postcondition
        self.assertEqual(self.parser.stack, [1, 2])

    def test_slate_html_parser__handle_data(self):
        # setup
        data = 'some text'

        # do it
        self.parser.handle_data(data)

        # postcondition
        self.assertEqual(self.parser.text_parts, ['some text'])
        self.assertEqual(self.parser.stack, [[{'text': 'some text'}]])

    def test_slate_html_parser__get_result__no_data(self):
        # do it
        result = self.parser.get_result()

        # postcondition
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

        self.assertEqual(result[0], [])
        self.assertEqual(result[1], '')

    def test_slate_html_parser__get_result(self):
        # setup
        self.parser.text_parts = ['some ', 'text']
        parser_result = [
            {
                'type': 'p',
                'children': [
                    {'text': 'some '},
                    {'type': 'strong', 'children': [{'text': 'text'}]}
                ]
            }
        ]
        self.parser.result = parser_result

        # do it
        result = self.parser.get_result()

        # postcondition
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

        self.assertEqual(result[0], parser_result)
        self.assertEqual(result[1], 'some text')

    def test_slate_html_parser__feed(self):
        # setup
        html = '<p>some <b>text</b></p>'

        # do it
        self.parser.feed(data=html)
        result = self.parser.get_result()

        # postcondition
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

        expected_slate_value = [
            {
                'type': 'p',
                'children': [
                    {'text': 'some '},
                    {'type': 'strong', 'children': [{'text': 'text'}]}
                ]
            }
        ]
        self.assertEqual(result[0], expected_slate_value)
        self.assertEqual(result[1], 'some text')

    def test_slate_html_parser__link(self):
        # setup
        html = '<p>some <a href="https://interaktiv.de">link</a></p>'

        # do it
        self.parser.feed(data=html)
        result = self.parser.get_result()

        # postcondition
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

        expected_slate_value = [
            {
                'type': 'p',
                'children': [
                    {
                        'text': 'some '
                    },
                    {
                        'type': 'link',
                        'data': {'url': 'https://interaktiv.de'},
                        'children': [{'text': 'link'}]
                    }
                ]
            }
        ]
        self.assertEqual(result[0], expected_slate_value)
        self.assertEqual(result[1], 'some link')
