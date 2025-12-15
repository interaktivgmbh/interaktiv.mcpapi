from plone.app.testing import (
    FunctionalTesting,
    IntegrationTesting,
    PLONE_FIXTURE,
    PloneSandboxLayer,
)
from plone.testing.zope import WSGI_SERVER_FIXTURE


class InteraktivMcpapiLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        import plone.app.dexterity
        self.loadZCML(package=plone.app.dexterity)
        import interaktiv.mcpapi
        self.loadZCML(package=interaktiv.mcpapi)

    def setUpPloneSite(self, portal):
        self.applyProfile(portal, 'interaktiv.mcpapi:default')


INTERAKTIV_MCPAPI_FIXTURE = InteraktivMcpapiLayer()

INTERAKTIV_MCPAPI_INTEGRATION_TESTING = IntegrationTesting(
    bases=(INTERAKTIV_MCPAPI_FIXTURE,),
    name='InteraktivMcpapiLayer:IntegrationTesting',
)

INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(INTERAKTIV_MCPAPI_FIXTURE, WSGI_SERVER_FIXTURE),
    name='InteraktivMcpapiLayer:FunctionalTesting',
)