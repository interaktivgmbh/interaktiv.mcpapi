"""
OAuth 2.0 implementation for MCP authentication.

Implements OAuth 2.0 Authorization Code Flow with PKCE:
- Discovery endpoint (/.well-known/oauth-authorization-server)
- Authorization endpoint (/authorize)
- Token endpoint (/@mcp-oauth-token)
"""
import hashlib
import hmac
import json
import os
import time
import secrets
import base64
from urllib.parse import urlencode, urlparse, parse_qs

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

# Authorization code settings
AUTH_CODE_EXPIRY_SECONDS = 600  # 10 minutes

# CORS settings
CORS_ALLOWED_ORIGINS = ['https://claude.ai']

# In-memory storage for authorization codes (use Redis in production)
_authorization_codes = {}


def _cleanup_expired_codes():
    """Remove expired authorization codes."""
    now = time.time()
    expired = [code for code, data in _authorization_codes.items()
               if now > data.get('expires_at', 0)]
    for code in expired:
        del _authorization_codes[code]


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


def _verify_pkce(code_verifier: str, code_challenge: str, method: str = 'S256') -> bool:
    """Verify PKCE code challenge."""
    if method == 'S256':
        # SHA256 hash of verifier, base64url encoded
        digest = hashlib.sha256(code_verifier.encode()).digest()
        computed_challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')
        return hmac.compare_digest(computed_challenge, code_challenge)
    elif method == 'plain':
        return hmac.compare_digest(code_verifier, code_challenge)
    return False


def generate_access_token(client_id: str) -> tuple[str, int]:
    """Generate a signed access token. Returns (token, expires_at) tuple."""
    if not TOKEN_SECRET:
        raise ValueError("TOKEN_SECRET not configured")

    issued_at = int(time.time())
    expires_at = issued_at + TOKEN_EXPIRY_SECONDS

    payload = {
        'client_id': client_id,
        'iat': issued_at,
        'exp': expires_at,
        'jti': secrets.token_hex(16),
    }

    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip('=')

    signature = hmac.new(
        TOKEN_SECRET.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')

    token = f'{payload_b64}.{signature_b64}'
    return token, expires_at


def validate_access_token(token: str) -> dict | None:
    """Validate an access token. Returns payload dict if valid, None otherwise."""
    if not TOKEN_SECRET:
        logger.warning("TOKEN_SECRET not configured, cannot validate token")
        return None

    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None

        payload_b64, signature_b64 = parts

        expected_signature = hmac.new(
            TOKEN_SECRET.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).digest()
        expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode().rstrip('=')

        if not hmac.compare_digest(signature_b64, expected_signature_b64):
            return None

        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding

        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        payload = json.loads(payload_json)

        if time.time() > payload.get('exp', 0):
            return None

        return payload

    except Exception as e:
        logger.debug(f"Token validation error: {e}")
        return None


class OAuthDiscoveryEndpoint(BrowserView):
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""

    def __call__(self):
        alsoProvides(self.request, IDisableCSRFProtection)
        _set_cors_headers(self.request)

        logger.info(f"OAuth Discovery request from {self.request.getHeader('Origin', 'unknown')}")

        if self.request.method == 'OPTIONS':
            self.request.response.setStatus(204)
            return ''

        self.request.response.setHeader('Content-Type', 'application/json')
        self.request.response.setHeader('Cache-Control', 'public, max-age=3600')

        server_url = _get_server_url(self.request)
        logger.info(f"OAuth Discovery returning metadata for server: {server_url}")

        metadata = {
            'issuer': server_url,
            'authorization_endpoint': f'{server_url}/authorize',
            'token_endpoint': f'{server_url}/token',
            'token_endpoint_auth_methods_supported': [
                'client_secret_post',
                'client_secret_basic',
                'none',  # For public clients with PKCE
            ],
            'grant_types_supported': ['authorization_code'],
            'response_types_supported': ['code'],
            'code_challenge_methods_supported': ['S256', 'plain'],
            'scopes_supported': ['mcp:tools', 'claudeai'],
            'service_documentation': f'{server_url}/@mcp',
        }

        return json.dumps(metadata, indent=2)


class OAuthAuthorizeEndpoint(BrowserView):
    """
    OAuth 2.0 Authorization Endpoint.

    Handles Authorization Code Flow with PKCE.
    Since this is a machine-to-machine integration, we auto-approve
    if the client_id matches our configured client.
    """

    def __call__(self):
        alsoProvides(self.request, IDisableCSRFProtection)

        # Get parameters from query string
        response_type = self.request.get('response_type', '')
        client_id = self.request.get('client_id', '')
        redirect_uri = self.request.get('redirect_uri', '')
        code_challenge = self.request.get('code_challenge', '')
        code_challenge_method = self.request.get('code_challenge_method', 'S256')
        state = self.request.get('state', '')
        scope = self.request.get('scope', '')

        logger.info(f"OAuth authorize request: client_id={client_id[:8] if client_id else 'none'}...")

        # Validate response_type
        if response_type != 'code':
            return self._error_redirect(
                redirect_uri, state,
                'unsupported_response_type',
                'Only code response type is supported'
            )

        # Validate client_id
        if not client_id or client_id != MCP_OAUTH_CLIENT_ID:
            return self._error_redirect(
                redirect_uri, state,
                'invalid_client',
                'Unknown client_id'
            )

        # Validate redirect_uri (must be claude.ai callback)
        if not redirect_uri or not redirect_uri.startswith('https://claude.ai/'):
            return self._error_redirect(
                redirect_uri, state,
                'invalid_request',
                'Invalid redirect_uri'
            )

        # PKCE is required
        if not code_challenge:
            return self._error_redirect(
                redirect_uri, state,
                'invalid_request',
                'code_challenge is required'
            )

        # Generate authorization code
        _cleanup_expired_codes()
        auth_code = secrets.token_urlsafe(32)

        # Store code with associated data
        _authorization_codes[auth_code] = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'code_challenge': code_challenge,
            'code_challenge_method': code_challenge_method,
            'scope': scope,
            'expires_at': time.time() + AUTH_CODE_EXPIRY_SECONDS,
        }

        logger.info(f"Authorization code issued for client: {client_id[:8]}...")

        # Redirect back to client with code
        params = {'code': auth_code}
        if state:
            params['state'] = state

        redirect_url = f"{redirect_uri}?{urlencode(params)}"
        logger.info(f"Redirecting to: {redirect_url[:100]}...")

        self.request.response.redirect(redirect_url)
        return ''

    def _error_redirect(self, redirect_uri, state, error, description):
        """Redirect with error parameters."""
        if not redirect_uri:
            self.request.response.setStatus(400)
            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps({
                'error': error,
                'error_description': description
            })

        params = {
            'error': error,
            'error_description': description,
        }
        if state:
            params['state'] = state

        redirect_url = f"{redirect_uri}?{urlencode(params)}"
        self.request.response.redirect(redirect_url)
        return ''


class OAuthTokenEndpoint(BrowserView):
    """
    OAuth 2.0 Token Endpoint.

    Supports:
    - authorization_code grant (with PKCE)
    - client_credentials grant
    """

    def __call__(self):
        alsoProvides(self.request, IDisableCSRFProtection)
        _set_cors_headers(self.request)

        # Log all headers for debugging
        logger.info(f"OAuth Token request: method={self.request.method}, origin={self.request.getHeader('Origin', 'unknown')}, content-type={self.request.getHeader('Content-Type', 'none')}")

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

        if not MCP_OAUTH_CLIENT_ID or not MCP_OAUTH_CLIENT_SECRET:
            logger.error("OAuth not configured")
            self.request.response.setStatus(500)
            return json.dumps({
                'error': 'server_error',
                'error_description': 'OAuth not configured on server'
            })

        # Parse request
        params = self._parse_request()
        grant_type = params.get('grant_type', '')
        logger.info(f"OAuth Token request: grant_type={grant_type}, client_id={params.get('client_id', 'none')[:8] if params.get('client_id') else 'none'}...")

        if grant_type == 'authorization_code':
            return self._handle_authorization_code(params)
        elif grant_type == 'client_credentials':
            return self._handle_client_credentials(params)
        else:
            self.request.response.setStatus(400)
            return json.dumps({
                'error': 'unsupported_grant_type',
                'error_description': f'Grant type {grant_type} is not supported'
            })

    def _handle_authorization_code(self, params):
        """Handle authorization_code grant type."""
        code = params.get('code', '')
        redirect_uri = params.get('redirect_uri', '')
        code_verifier = params.get('code_verifier', '')
        client_id = params.get('client_id', '')
        client_secret = params.get('client_secret', '')

        logger.info(f"Token exchange: code={code[:16] if code else 'none'}..., has_verifier={bool(code_verifier)}")

        # Validate authorization code
        _cleanup_expired_codes()
        code_data = _authorization_codes.get(code)

        logger.info(f"Authorization codes in memory: {len(_authorization_codes)}, code_found={code_data is not None}")

        if not code_data:
            logger.warning("Invalid or expired authorization code")
            self.request.response.setStatus(400)
            return json.dumps({
                'error': 'invalid_grant',
                'error_description': 'Invalid or expired authorization code'
            })

        # Remove code (one-time use)
        del _authorization_codes[code]

        # Validate redirect_uri matches
        if redirect_uri and redirect_uri != code_data['redirect_uri']:
            self.request.response.setStatus(400)
            return json.dumps({
                'error': 'invalid_grant',
                'error_description': 'redirect_uri mismatch'
            })

        # Validate client_id if provided
        if client_id and client_id != code_data['client_id']:
            self.request.response.setStatus(400)
            return json.dumps({
                'error': 'invalid_client',
                'error_description': 'client_id mismatch'
            })

        # Verify PKCE
        if not code_verifier:
            self.request.response.setStatus(400)
            return json.dumps({
                'error': 'invalid_request',
                'error_description': 'code_verifier is required'
            })

        if not _verify_pkce(code_verifier, code_data['code_challenge'], code_data['code_challenge_method']):
            logger.warning("PKCE verification failed")
            self.request.response.setStatus(400)
            return json.dumps({
                'error': 'invalid_grant',
                'error_description': 'PKCE verification failed'
            })

        # Generate access token
        try:
            access_token, expires_at = generate_access_token(code_data['client_id'])
            expires_in = expires_at - int(time.time())

            logger.info(f"Access token issued via authorization_code for client: {code_data['client_id'][:8]}...")

            return json.dumps({
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': expires_in,
                'scope': code_data.get('scope', 'mcp:tools')
            })

        except Exception as e:
            logger.error(f"Failed to generate access token: {e}")
            self.request.response.setStatus(500)
            return json.dumps({
                'error': 'server_error',
                'error_description': 'Failed to generate access token'
            })

    def _handle_client_credentials(self, params):
        """Handle client_credentials grant type."""
        client_id = params.get('client_id', '')
        client_secret = params.get('client_secret', '')

        if not client_id or not client_secret:
            self.request.response.setStatus(400)
            return json.dumps({
                'error': 'invalid_request',
                'error_description': 'Missing client_id or client_secret'
            })

        valid_id = hmac.compare_digest(client_id, MCP_OAUTH_CLIENT_ID)
        valid_secret = hmac.compare_digest(client_secret, MCP_OAUTH_CLIENT_SECRET)

        if not (valid_id and valid_secret):
            logger.warning(f"Invalid OAuth credentials for client_id: {client_id[:8]}...")
            self.request.response.setStatus(401)
            return json.dumps({
                'error': 'invalid_client',
                'error_description': 'Invalid client credentials'
            })

        try:
            access_token, expires_at = generate_access_token(client_id)
            expires_in = expires_at - int(time.time())

            logger.info(f"Access token issued via client_credentials for client: {client_id[:8]}...")

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

    def _parse_request(self) -> dict:
        """Parse OAuth token request parameters."""
        params = {}

        # Try Authorization header for client credentials (Basic auth)
        auth_header = self.request.getHeader('Authorization', '')
        if auth_header.startswith('Basic '):
            try:
                credentials = base64.b64decode(auth_header[6:]).decode()
                if ':' in credentials:
                    params['client_id'], params['client_secret'] = credentials.split(':', 1)
            except Exception:
                pass

        # Parse body
        content_type = self.request.getHeader('Content-Type', '')

        if 'application/json' in content_type:
            try:
                body = self.request.get('BODY', '{}')
                data = json.loads(body)
                for key in ['grant_type', 'code', 'redirect_uri', 'code_verifier', 'client_id', 'client_secret']:
                    if key in data and key not in params:
                        params[key] = data[key]
            except json.JSONDecodeError:
                pass
        else:
            # Form data
            for key in ['grant_type', 'code', 'redirect_uri', 'code_verifier', 'client_id', 'client_secret']:
                if key not in params and key in self.request.form:
                    params[key] = self.request.form[key]

        return params
