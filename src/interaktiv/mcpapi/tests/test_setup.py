import unittest

from plone import api
from plone.app.testing import TEST_USER_ID, setRoles
from plone.browserlayer import utils

from interaktiv.mcpapi.interfaces import IInteraktivMcpapiLayer
from interaktiv.mcpapi.testing import INTERAKTIV_MCPAPI_INTEGRATION_TESTING
from plone.base.utils import get_installer


class TestSetup(unittest.TestCase):
    layer = INTERAKTIV_MCPAPI_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        self.installer = get_installer(self.portal, self.request)

    def test_product_installed(self):
        self.assertTrue(self.installer.is_product_installed('interaktiv.mcpapi'))

    def test_browserlayer(self):
        self.assertIn(IInteraktivMcpapiLayer, utils.registered_layers())


class TestUninstall(unittest.TestCase):

    layer = INTERAKTIV_MCPAPI_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        self.installer = get_installer(self.portal, self.request)

        self.installer.uninstall_product('interaktiv.mcpapi')

    def test_product_uninstalled(self):
        self.assertFalse(self.installer.is_product_installed('interaktiv.mcpapi'))

    def test_browserlayer_removed(self):
        self.assertNotIn(IInteraktivMcpapiLayer, utils.registered_layers())
