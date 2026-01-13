"""
Traverser for .well-known URLs.

This module provides a traverser that handles /.well-known/ URLs in Plone,
which is required for OAuth 2.0 discovery.
"""
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
from Products.Five import BrowserView
from plone.protect.interfaces import IDisableCSRFProtection
from zope.interface import alsoProvides

from interaktiv.mcpapi.mcp.oauth import OAuthDiscoveryEndpoint


@implementer(IPublishTraverse)
class WellKnownTraverser(BrowserView):
    """
    Traverser for /.well-known/ namespace.

    Handles:
    - /.well-known/oauth-authorization-server -> OAuth Discovery
    """

    def __init__(self, context, request):
        super().__init__(context, request)
        self.subpath = None

    def publishTraverse(self, request, name):
        """Handle traversal to .well-known sub-resources."""
        self.subpath = name
        return self

    def __call__(self):
        """Dispatch to the appropriate handler based on subpath."""
        alsoProvides(self.request, IDisableCSRFProtection)

        if self.subpath == 'oauth-authorization-server':
            # Delegate to OAuth Discovery endpoint
            view = OAuthDiscoveryEndpoint(self.context, self.request)
            return view()

        # Unknown .well-known resource
        self.request.response.setStatus(404)
        return f'.well-known/{self.subpath} not found'
