import unittest

import plone.api as api
from interaktiv.mcpapi.interfaces import IMCPBlockTool, IMCPTool
from interaktiv.mcpapi.testing import INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING
from interaktiv.mcpapi.tools.add_slate_block import AddSlateBlockTool
from interaktiv.mcpapi.tools.base import MCPBlockToolBase
from plone.app.testing import TEST_USER_ID, setRoles
from plone.restapi.behaviors import IBlocks
from zope.interface import alsoProvides
from zope.interface.verify import verifyClass, verifyObject


class TestMCPBlockToolBase(unittest.TestCase):
    layer = INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Site Administrator'])

        self.tool = MCPBlockToolBase(self.portal, self.request)

    def test_implements_interface(self):
        self.assertTrue(verifyClass(IMCPBlockTool, MCPBlockToolBase))

    def test_provides_interface(self):
        self.assertTrue(verifyObject(IMCPBlockTool, self.tool))

    def test_also_implements_imcptool(self):
        self.assertTrue(verifyClass(IMCPTool, MCPBlockToolBase))

    def test_default_attributes(self):
        self.assertEqual(self.tool.block_type, '')
        self.assertEqual(self.tool.block_description, '')
        self.assertEqual(self.tool.permission, 'cmf.ModifyPortalContent')

    def test_schema_includes_path_and_position(self):
        self.assertIn('path', self.tool.schema['properties'])
        self.assertIn('position', self.tool.schema['properties'])
        self.assertIn('path', self.tool.schema['required'])

    def test_to_volto_block_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError) as cm:
            self.tool.to_volto_block({})
        self.assertEqual(
            str(cm.exception), 'Subclasses must implement to_volto_block()'
        )


class TestAddSlateBlockTool(unittest.TestCase):
    layer = INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Site Administrator'])

        self.tool = AddSlateBlockTool(self.portal, self.request)

    def test_implements_interface(self):
        self.assertTrue(verifyClass(IMCPBlockTool, AddSlateBlockTool))

    def test_provides_interface(self):
        self.assertTrue(verifyObject(IMCPBlockTool, self.tool))

    def test_tool_has_required_attributes(self):
        self.assertEqual(self.tool.name, 'add_slate_block')
        self.assertEqual(self.tool.block_type, 'slate')
        self.assertIn('text', self.tool.block_schema['properties'])
        self.assertIn('text', self.tool.block_schema['required'])

    def test_schema_includes_path_and_text(self):
        self.assertIn('path', self.tool.schema['properties'])
        self.assertIn('text', self.tool.schema['properties'])
        self.assertIn('path', self.tool.schema['required'])
        self.assertIn('text', self.tool.schema['required'])

    def test_permission_requires_modify_content(self):
        self.assertEqual(self.tool.permission, 'cmf.ModifyPortalContent')

    def test_to_volto_block(self):
        params = {'text': '<p>Hello <strong>World</strong></p>'}
        result = self.tool.to_volto_block(params)

        self.assertEqual(result['@type'], 'slate')
        self.assertIn('value', result)
        self.assertIn('plaintext', result)
        self.assertEqual(result['plaintext'], 'Hello World')

    def test_to_volto_block_structure(self):
        params = {'text': '<p>Simple text</p>'}
        result = self.tool.to_volto_block(params)

        expected_value = [
            {
                'type': 'p',
                'children': [{'text': 'Simple text'}]
            }
        ]
        self.assertEqual(result['value'], expected_value)

    def test_execute_adds_block_to_content(self):
        # Create a document with IBlocks behavior
        doc = api.content.create(
            container=self.portal,
            type='Document',
            id='test-doc',
            title='Test Document',
            blocks={},
            blocks_layout={'items': []},
        )
        alsoProvides(doc, IBlocks)

        params = {
            'path': '/test-doc',
            'text': '<p>New block content</p>',
        }

        result = self.tool.execute(params)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['block_type'], 'slate')
        self.assertIn('block_id', result)

        # Verify block was added
        self.assertEqual(len(doc.blocks), 1)
        self.assertEqual(len(doc.blocks_layout['items']), 1)

        block_id = result['block_id']
        self.assertIn(block_id, doc.blocks)
        self.assertEqual(doc.blocks[block_id]['@type'], 'slate')

    def test_execute_appends_block_at_end(self):
        # Create a document with existing blocks
        existing_block_id = 'existing-block'
        doc = api.content.create(
            container=self.portal,
            type='Document',
            id='test-doc-append',
            title='Test Document',
            blocks={
                existing_block_id: {'@type': 'slate', 'value': [], 'plaintext': ''}
            },
            blocks_layout={'items': [existing_block_id]},
        )

        params = {
            'path': '/test-doc-append',
            'text': '<p>Appended block</p>',
        }

        result = self.tool.execute(params)

        # Verify new block is at the end
        self.assertEqual(len(doc.blocks_layout['items']), 2)
        self.assertEqual(doc.blocks_layout['items'][0], existing_block_id)
        self.assertEqual(doc.blocks_layout['items'][1], result['block_id'])

    def test_execute_inserts_block_at_position(self):
        # Create a document with existing blocks
        block_a = 'block-a'
        block_b = 'block-b'
        doc = api.content.create(
            container=self.portal,
            type='Document',
            id='test-doc-insert',
            title='Test Document',
            blocks={
                block_a: {'@type': 'slate', 'value': [], 'plaintext': ''},
                block_b: {'@type': 'slate', 'value': [], 'plaintext': ''},
            },
            blocks_layout={'items': [block_a, block_b]},
        )

        params = {
            'path': '/test-doc-insert',
            'text': '<p>Inserted block</p>',
            'position': 1,
        }

        result = self.tool.execute(params)

        # Verify new block is at position 1
        self.assertEqual(len(doc.blocks_layout['items']), 3)
        self.assertEqual(doc.blocks_layout['items'][0], block_a)
        self.assertEqual(doc.blocks_layout['items'][1], result['block_id'])
        self.assertEqual(doc.blocks_layout['items'][2], block_b)
        self.assertEqual(result['position'], 1)

    def test_execute_raises_for_invalid_path(self):
        params = {
            'path': '/nonexistent-doc',
            'text': '<p>Text</p>',
        }

        with self.assertRaises(ValueError) as cm:
            self.tool.execute(params)
        self.assertIn('Content not found', str(cm.exception))

    def test_execute_raises_for_non_blocks_content(self):
        # Create a file (which doesn't support blocks)
        api.content.create(
            container=self.portal,
            type='File',
            id='test-file',
            title='Test File',
        )

        params = {
            'path': '/test-file',
            'text': '<p>Text</p>',
        }

        with self.assertRaises(ValueError) as cm:
            self.tool.execute(params)
        self.assertIn('does not support blocks', str(cm.exception))
