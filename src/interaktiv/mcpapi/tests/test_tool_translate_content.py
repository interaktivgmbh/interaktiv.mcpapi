import unittest

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
