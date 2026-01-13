"""
OAuth 2.0 implementation for MCP authentication.

Implements a minimal OAuth 2.0 server with:
- Discovery endpoint (/.well-known/oauth-authorization-server)
- Token endpoint (/@mcp-oauth-token) with client_credentials grant
- JWT token generation and validation
"""
import hashlib
import hmac
import json
import os
import time
import secrets
import base64

from Products.Five import BrowserView
from plone.protect.interfaces import IDisableCSRFProtection
from zope.interface import alsoProvides

from interaktiv.mcpapi import logger


# OAuth configuration from environment variables
MCP_OAUTH_CLIENT_ID = os.environ.get('MCP_OAUTH_CLIENT_ID', '')
MCP_OAUTH_CLIENT_SECRET = os.environ.get('MCP_OAUTH_CLIENT_SECRET', '')
MCP_SERVER_URL = os.environ.get('MCP_SERVER_URL', '')

# Token settings
TOKEN_EXPIRY_SECONDS = int(os.environ.get('MCP_TOKEN_EXPIRY', 3600))  # 1 hour default
TOKEN_SECRET = os.environ.get('MCP_TOKEN_SECRET', '') or MCP_OAUTH_CLIENT_SECRET

# CORS settings
CORS_ALLOWED_ORIGINS = ['https://claude.ai']


def _get_server_url(request):
    """Get the server URL from environment or request."""
    if MCP_SERVER_URL:
        return MCP_SERVER_URL.rstrip('/')
    # Fallback to request URL
    return request.URL1.rstrip('/')


def _set_cors_headers(request):
    """Set CORS headers for OAuth endpoints."""
    origin = request.getHeader('Origin', '')
    response = request.response

    if origin in CORS_ALLOWED_ORIGINS:
        response.setHeader('Access-Control-Allow-Origin', origin)
    elif '*' in CORS_ALLOWED_ORIGINS:
        response.setHeader('Access-Control-Allow-Origin', '*')

    response.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization')


def generate_access_token(client_id: str) -> tuple[str, int]:
    """
    Generate a signed access token.

    Returns (token, expires_at) tuple.
    """
    if not TOKEN_SECRET:
        raise ValueError("TOKEN_SECRET not configured")

    issued_at = int(time.time())
    expires_at = issued_at + TOKEN_EXPIRY_SECONDS

    # Create token payload
    payload = {
        'client_id': client_id,
        'iat': issued_at,
        'exp': expires_at,
        'jti': secrets.token_hex(16),  # Unique token ID
    }

    # Encode payload
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip('=')

    # Create signature
    signature = hmac.new(
        TOKEN_SECRET.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')

    # Token format: payload.signature
    token = f'{payload_b64}.{signature_b64}'

    return token, expires_at


def validate_access_token(token: str) -> dict | None:
    """
    Validate an access token.

    Returns the payload dict if valid, None otherwise.
    """
    if not TOKEN_SECRET:
        logger.warning("TOKEN_SECRET not configured, cannot validate token")
        return None

    try:
        parts = token.split('.')
        if len(parts) != 2:
            logger.debug("Invalid token format: wrong number of parts")
            return None

        payload_b64, signature_b64 = parts

        # Verify signature
        expected_signature = hmac.new(
            TOKEN_SECRET.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).digest()
        expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode().rstrip('=')

        if not hmac.compare_digest(signature_b64, expected_signature_b64):
            logger.debug("Invalid token: signature mismatch")
            return None

        # Decode payload (add padding if needed)
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding

        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        payload = json.loads(payload_json)

        # Check expiration
        if time.time() > payload.get('exp', 0):
            logger.debug("Invalid token: expired")
            return None

        return payload

    except Exception as e:
        logger.debug(f"Token validation error: {e}")
        return None


class OAuthDiscoveryEndpoint(BrowserView):
    """
    OAuth 2.0 Authorization Server Metadata endpoint.

    RFC 8414: https://tools.ietf.org/html/rfc8414

    Registered at: /.well-known/oauth-authorization-server
    """

    def __call__(self):
        alsoProvides(self.request, IDisableCSRFProtection)
        _set_cors_headers(self.request)

        if self.request.method == 'OPTIONS':
            self.request.response.setStatus(204)
            return ''

        self.request.response.setHeader('Content-Type', 'application/json')
        self.request.response.setHeader('Cache-Control', 'public, max-age=3600')

        server_url = _get_server_url(self.request)

        metadata = {
            'issuer': server_url,
            'token_endpoint': f'{server_url}/@mcp-oauth-token',
            'token_endpoint_auth_methods_supported': [
                'client_secret_post',
                'client_secret_basic',
            ],
            'grant_types_supported': ['client_credentials'],
            'response_types_supported': ['token'],
            'scopes_supported': ['mcp:tools'],
            'service_documentation': f'{server_url}/@mcp',
        }

        return json.dumps(metadata, indent=2)


class OAuthTokenEndpoint(BrowserView):
    """
    OAuth 2.0 Token endpoint.

    Supports client_credentials grant type.

    Registered at: /@mcp-oauth-token
    """

    def __call__(self):
        alsoProvides(self.request, IDisableCSRFProtection)
        _set_cors_headers(self.request)

        if self.request.method == 'OPTIONS':
            self.request.response.setStatus(204)
            return ''

        self.request.response.setHeader('Content-Type', 'application/json')
        self.request.response.setHeader('Cache-Control', 'no-store')
        self.request.response.setHeader('Pragma', 'no-cache')

        if self.request.method != 'POST':
            self.request.response.setStatus(405)
            return json.dumps({
                'error': 'method_not_allowed',
                'error_description': 'Only POST method is allowed'
            })

        # Check OAuth configuration
        if not MCP_OAUTH_CLIENT_ID or not MCP_OAUTH_CLIENT_SECRET:
            logger.error("OAuth not configured: MCP_OAUTH_CLIENT_ID or MCP_OAUTH_CLIENT_SECRET missing")
            self.request.response.setStatus(500)
            return json.dumps({
                'error': 'server_error',
                'error_description': 'OAuth not configured on server'
            })

        # Parse credentials from request
        client_id, client_secret, grant_type = self._parse_credentials()

        # Validate grant type
        if grant_type != 'client_credentials':
            self.request.response.setStatus(400)
            return json.dumps({
                'error': 'unsupported_grant_type',
                'error_description': 'Only client_credentials grant type is supported'
            })

        # Validate credentials
        if not client_id or not client_secret:
            self.request.response.setStatus(400)
            return json.dumps({
                'error': 'invalid_request',
                'error_description': 'Missing client_id or client_secret'
            })

        # Constant-time comparison to prevent timing attacks
        valid_id = hmac.compare_digest(client_id, MCP_OAUTH_CLIENT_ID)
        valid_secret = hmac.compare_digest(client_secret, MCP_OAUTH_CLIENT_SECRET)

        if not (valid_id and valid_secret):
            logger.warning(f"Invalid OAuth credentials attempt for client_id: {client_id[:8]}...")
            self.request.response.setStatus(401)
            return json.dumps({
                'error': 'invalid_client',
                'error_description': 'Invalid client credentials'
            })

        # Generate access token
        try:
            access_token, expires_at = generate_access_token(client_id)
            expires_in = expires_at - int(time.time())

            logger.info(f"OAuth token issued for client: {client_id[:8]}...")

            return json.dumps({
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': expires_in,
                'scope': 'mcp:tools'
            })

        except Exception as e:
            logger.error(f"Failed to generate access token: {e}")
            self.request.response.setStatus(500)
            return json.dumps({
                'error': 'server_error',
                'error_description': 'Failed to generate access token'
            })

    def _parse_credentials(self) -> tuple[str, str, str]:
        """
        Parse OAuth credentials from request.

        Supports:
        - client_secret_post: credentials in form body
        - client_secret_basic: credentials in Authorization header
        - JSON body

        Returns (client_id, client_secret, grant_type) tuple.
        """
        client_id = ''
        client_secret = ''
        grant_type = ''

        # Try Authorization header first (client_secret_basic)
        auth_header = self.request.getHeader('Authorization', '')
        if auth_header.startswith('Basic '):
            try:
                credentials = base64.b64decode(auth_header[6:]).decode()
                if ':' in credentials:
                    client_id, client_secret = credentials.split(':', 1)
            except Exception:
                pass

        # Parse body based on content type
        content_type = self.request.getHeader('Content-Type', '')

        if 'application/json' in content_type:
            # JSON body
            try:
                body = self.request.get('BODY', '{}')
                data = json.loads(body)
                client_id = client_id or data.get('client_id', '')
                client_secret = client_secret or data.get('client_secret', '')
                grant_type = data.get('grant_type', '')
            except json.JSONDecodeError:
                pass
        else:
            # Form data (client_secret_post)
            client_id = client_id or self.request.form.get('client_id', '')
            client_secret = client_secret or self.request.form.get('client_secret', '')
            grant_type = self.request.form.get('grant_type', '')

        return client_id, client_secret, grant_type
