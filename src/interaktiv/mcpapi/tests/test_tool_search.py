import unittest
from interaktiv.mcpapi.interfaces import IMCPTool
from interaktiv.mcpapi.testing import INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING
from interaktiv.mcpapi.tools.base import MCPToolBase
from interaktiv.mcpapi.tools.search import SearchTool

import plone.api as api
from plone.app.testing import TEST_USER_ID, setRoles
from zope.interface.verify import verifyClass, verifyObject


class TestToolSearch(unittest.TestCase):
    layer = INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Site Administrator'])

        self.tool = SearchTool(self.portal, self.request)

    def test_implements_interface(self):
        self.assertTrue(verifyClass(IMCPTool, SearchTool))

    def test_provides_interface(self):
        self.assertTrue(verifyObject(IMCPTool, self.tool))

    def test_execute(self):
        # setup
        params = {
            'query': 'mow'
        }
        api.content.create(
            container=self.portal,
            type='Document',
            id='document_a',
            title='Mow makes the cow',
        )

        # do it
        result = self.tool.execute(params)

        # postcondition
        self.assertEqual(len(result), 1)
        expected_content_data = {
            'title': 'Mow makes the cow',
            'description': '',
            'path': '/plone/document_a',
            'type': 'Document',
            'url': f'{self.portal.absolute_url()}/document_a'
        }
        self.assertDictEqual(result[0], expected_content_data)
