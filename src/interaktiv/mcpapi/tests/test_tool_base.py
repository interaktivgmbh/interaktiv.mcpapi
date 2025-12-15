import unittest
from interaktiv.mcpapi.interfaces import IMCPTool
from interaktiv.mcpapi.testing import INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING
from interaktiv.mcpapi.tools.base import MCPToolBase

from plone.app.testing import TEST_USER_ID, setRoles
from zope.interface.verify import verifyClass, verifyObject


class TestToolBase(unittest.TestCase):
    layer = INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Site Administrator'])

        self.tool = MCPToolBase(self.portal, self.request)

    def test_implements_interface(self):
        self.assertTrue(verifyClass(IMCPTool, MCPToolBase))

    def test_provides_interface(self):
        self.assertTrue(verifyObject(IMCPTool, self.tool))

    def test_default_attributes(self):
        self.assertEqual(self.tool.name, '')
        self.assertEqual(self.tool.description, '')
        self.assertEqual(self.tool.schema, {'type': 'object', 'properties': {}})
        self.assertEqual(self.tool.permission, 'zope2.View')

    def test_context_and_request(self):
        self.assertEqual(self.tool.context, self.portal)
        self.assertEqual(self.tool.request, self.request)

    def test_execute_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError) as cm:
            self.tool.execute({})
        self.assertEqual(str(cm.exception), 'Subclasses must implement execute()')
