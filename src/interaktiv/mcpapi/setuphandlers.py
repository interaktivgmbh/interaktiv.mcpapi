from Products.CMFPlone.interfaces import INonInstallable
from zope.interface import implementer


@implementer(INonInstallable)
class HiddenProfiles(object):
    def getNonInstallableProfiles(self):
        """Hide uninstall profile from site-creation and quickinstaller."""
        return [
            'interaktiv.mcpapi:uninstall',
        ]


def post_install(context):
    """Post install script"""
    pass


def uninstall(context):
    """Uninstall script"""
    pass