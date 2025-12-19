import unittest

import plone.api as api
from interaktiv.mcpapi.interfaces import IMCPTool
from interaktiv.mcpapi.testing import INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING
from interaktiv.mcpapi.tools.translate_content import TranslateContentTool
from plone.app.testing import TEST_USER_ID, setRoles
from zope.interface.verify import verifyClass, verifyObject


class TestToolTranslateContent(unittest.TestCase):
    layer = INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Site Administrator'])

        self.tool = TranslateContentTool(self.portal, self.request)

    def test_implements_interface(self):
        self.assertTrue(verifyClass(IMCPTool, TranslateContentTool))

    def test_provides_interface(self):
        self.assertTrue(verifyObject(IMCPTool, self.tool))

    def test_tool_has_required_attributes(self):
        self.assertEqual(self.tool.name, 'translate_content')
        self.assertIn('source_path', self.tool.schema['properties'])
        self.assertIn('target_language', self.tool.schema['properties'])
        self.assertIn('title', self.tool.schema['properties'])
        self.assertEqual(
            self.tool.schema['required'],
            ['source_path', 'target_language', 'title']
        )

    def test_permission_requires_add_content(self):
        self.assertEqual(self.tool.permission, 'cmf.AddPortalContent')

    def test___html_to_slate(self):
        # setup
        html = '<p>some <b>text</b></p>'

        # do it
        result = self.tool._html_to_slate(html)

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

    def test__update_slate_block(self):
        # setup
        block = {
            'somekey': 'somevalue'
        }
        html = '<p>some <b>text</b></p>'

        # do it
        result = self.tool._update_slate_block(block, html)

        # postcondition
        self.assertEqual(result['somekey'], 'somevalue')
        self.assertEqual(result['plaintext'], 'some text')
        expected_slate_value = [
            {
                'type': 'p',
                'children': [
                    {'text': 'some '},
                    {'type': 'strong', 'children': [{'text': 'text'}]}
                ]
            }
        ]
        self.assertEqual(result['value'], expected_slate_value)

    def test__set_translated_blocks_recursive__only_changes_when_valid(self):
        # setup
        blocks = {
            'block_id_a': {
                '@type': 'slate'
            },
            'block_id_b': {
                '@type': 'slate'
            },
            'block_id_c': {
                '@type': 'othertype'
            }
        }
        blocks_html = {
            'block_id_a': '<p>text</p>',
            'block_id_c': '<p>type not handled</p>',
        }

        # do it
        self.tool._set_translated_blocks_recursive(blocks, blocks_html)

        # postcondition
        self.assertDictEqual(blocks['block_id_b'], {'@type': 'slate'})
        self.assertDictEqual(blocks['block_id_c'], {'@type': 'othertype'})

        expected_block_a_data = {
            '@type': 'slate',
            'plaintext': 'text',
            'value': [{'type': 'p', 'children': [{'text': 'text'}]}],
        }
        self.assertDictEqual(blocks['block_id_a'], expected_block_a_data)

    def test__set_translated_blocks_recursive__sets_blocks_recursive__sub_data(self):
        # setup
        blocks = {
            'block_id_a': {
                '@type': 'sometype',
                'data': {
                    'blocks': {
                        'sub_block_a': {
                            'blocks': {
                                'sub_sub_block_a': {
                                    '@type': 'slate'
                                }
                            }
                        }
                    }
                }
            },
        }
        blocks_html = {
            'sub_sub_block_a': '<p>text</p>',
        }

        # do it
        self.tool._set_translated_blocks_recursive(blocks, blocks_html)

        # postcondition
        sub_block_a = blocks['block_id_a']['data']['blocks']['sub_block_a']
        sub_sub_block_a = sub_block_a['blocks']['sub_sub_block_a']

        expected_block_a_data = {
            '@type': 'slate',
            'plaintext': 'text',
            'value': [{'type': 'p', 'children': [{'text': 'text'}]}],
        }
        self.assertDictEqual(sub_sub_block_a, expected_block_a_data)

    def test__set_translated_blocks_recursive__sets_blocks_recursive__sub_blocks(self):
        # setup
        blocks = {
            'block_id_a': {
                '@type': 'sometype',
                'blocks': {
                    'sub_block_a': {
                        '@type': 'slate'
                    }
                }
            },
        }
        blocks_html = {
            'sub_block_a': '<p>text</p>',
        }

        # do it
        self.tool._set_translated_blocks_recursive(blocks, blocks_html)

        # postcondition
        sub_block_a = blocks['block_id_a']['blocks']['sub_block_a']

        expected_block_a_data = {
            '@type': 'slate',
            'plaintext': 'text',
            'value': [{'type': 'p', 'children': [{'text': 'text'}]}],
        }
        self.assertDictEqual(sub_block_a, expected_block_a_data)

    def test__set_translated_block_data(self):
        # setup
        blocks = {
            'block_id_a': {
                '@type': 'slate'
            }
        }
        blocks_html = {
            'block_id_a': '<p>text</p>',
        }
        content = api.content.create(
            container=self.portal,
            type='Document',
            id='document_a',
            blocks=blocks,
        )

        # do it
        self.tool._set_translated_block_data(content, blocks_html)

        # postcondition
        blocks = content.blocks
        self.assertEqual(len(blocks), 1)
        expected_block_a_data = {
            '@type': 'slate',
            'plaintext': 'text',
            'value': [{'type': 'p', 'children': [{'text': 'text'}]}],
        }
        self.assertDictEqual(blocks['block_id_a'], expected_block_a_data)
