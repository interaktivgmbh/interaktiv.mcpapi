"""
Traverser for .well-known URLs.

This module provides a traverser that handles /.well-known/ URLs in Plone,
which is required for OAuth 2.0 discovery.
"""
import json

from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
from Products.Five import BrowserView
from plone.protect.interfaces import IDisableCSRFProtection
from zope.interface import alsoProvides

from interaktiv.mcpapi.mcp.oauth import OAuthDiscoveryEndpoint, _get_server_url, _set_cors_headers
from interaktiv.mcpapi import logger


@implementer(IPublishTraverse)
class WellKnownTraverser(BrowserView):
    """
    Traverser for /.well-known/ namespace.

    Handles:
    - /.well-known/oauth-authorization-server -> OAuth Authorization Server Metadata (RFC 8414)
    - /.well-known/oauth-protected-resource -> Protected Resource Metadata (RFC 9728)
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
        _set_cors_headers(self.request)

        logger.info(f".well-known request: subpath={self.subpath}")

        if self.request.method == 'OPTIONS':
            self.request.response.setStatus(204)
            return ''

        if self.subpath == 'oauth-authorization-server':
            # Delegate to OAuth Discovery endpoint
            view = OAuthDiscoveryEndpoint(self.context, self.request)
            return view()

        if self.subpath == 'oauth-protected-resource':
            # Protected Resource Metadata (RFC 9728)
            return self._handle_protected_resource_metadata()

        # Unknown .well-known resource
        self.request.response.setStatus(404)
        return f'.well-known/{self.subpath} not found'

    def _handle_protected_resource_metadata(self):
        """Return Protected Resource Metadata (RFC 9728)."""
        server_url = _get_server_url(self.request)

        logger.info(f"Protected Resource Metadata request, server_url={server_url}")

        self.request.response.setHeader('Content-Type', 'application/json')
        self.request.response.setHeader('Cache-Control', 'public, max-age=3600')

        metadata = {
            'resource': f'{server_url}/@mcp',
            'authorization_servers': [server_url],
            'bearer_methods_supported': ['header'],
            'scopes_supported': ['mcp:tools'],
        }

        return json.dumps(metadata, indent=2)
