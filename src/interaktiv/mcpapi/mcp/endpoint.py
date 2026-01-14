import json
import secrets
import time
from interaktiv.mcpapi import logger
from interaktiv.mcpapi.interfaces import IMCPTool

from AccessControl import getSecurityManager
from Products.Five import BrowserView
from plone.protect.interfaces import IDisableCSRFProtection
from zope.component import getAdapters, queryMultiAdapter
from zope.interface import alsoProvides
from interaktiv.mcpapi.mcp import MAX_RESPONSE_SIZE_BYTES


# Session storage (in-memory for simplicity - consider Redis for production)
_sessions = {}
SESSION_TIMEOUT = 3600  # 1 hour

# MCP Protocol version
MCP_PROTOCOL_VERSION = '2025-03-26'


def _cleanup_expired_sessions():
    """Remove expired sessions."""
    now = time.time()
    expired = [sid for sid, data in _sessions.items()
               if now - data['created'] > SESSION_TIMEOUT]
    for sid in expired:
        del _sessions[sid]


def _generate_session_id():
    """Generate a cryptographically secure session ID."""
    return secrets.token_hex(32)


class MCPEndpoint(BrowserView):
    """MCP Endpoint implementing Streamable HTTP transport.

    Supports both JSON and SSE response formats.
    Reference: https://modelcontextprotocol.io/specification/2025-03-26/basic/transports
    """

    def _get_session_id(self):
        """Get session ID from request header."""
        return self.request.getHeader('Mcp-Session-Id', '')

    def _create_session(self):
        """Create a new session and return its ID."""
        _cleanup_expired_sessions()
        session_id = _generate_session_id()
        _sessions[session_id] = {
            'created': time.time(),
            'initialized': False
        }
        return session_id

    def _validate_session(self, session_id):
        """Validate session ID. Returns True if valid."""
        if not session_id:
            return False
        if session_id not in _sessions:
            return False
        session = _sessions[session_id]
        if time.time() - session['created'] > SESSION_TIMEOUT:
            del _sessions[session_id]
            return False
        return True

    def _format_sse_event(self, data, event_id=None):
        """Format a message as an SSE event."""
        lines = []
        if event_id:
            lines.append(f'id: {event_id}')
        lines.append(f'data: {json.dumps(data)}')
        lines.append('')  # Empty line to end event
        return '\n'.join(lines) + '\n'

    def __call__(self):
        alsoProvides(self.request, IDisableCSRFProtection)

        # Handle session termination
        if self.request.method == 'DELETE':
            return self._handle_delete()

        # Handle GET for SSE stream (server-to-client notifications)
        if self.request.method == 'GET':
            return self._handle_get()

        # Handle POST for client messages
        if self.request.method == 'POST':
            return self._handle_post()

        self.request.response.setStatus(405)
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(self._json_rpc_error(None, -32600, 'Method not allowed'))

    def _handle_delete(self):
        """Handle DELETE request for session termination."""
        session_id = self._get_session_id()
        if session_id and session_id in _sessions:
            del _sessions[session_id]
            self.request.response.setStatus(204)
            return ''
        self.request.response.setStatus(404)
        return ''

    def _handle_get(self):
        """Handle GET request for SSE stream.

        This allows the server to send notifications/requests to the client.
        For now, we return 405 as we don't have server-initiated messages.
        """
        session_id = self._get_session_id()
        if not self._validate_session(session_id):
            self.request.response.setStatus(404)
            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps({'error': 'Invalid or expired session'})

        # We don't currently support server-initiated streams
        self.request.response.setStatus(405)
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps({'error': 'GET streams not supported'})

    def _handle_post(self):
        """Handle POST request with JSON-RPC message."""
        logger.info(f"MCP POST request received")

        accept_header = self.request.getHeader('Accept', 'application/json')
        session_id = self._get_session_id()

        body = self.request.get('BODY', '{}')

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.request.response.setStatus(400)
            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps(self._json_rpc_error(None, -32700, 'Parse error'))

        method = data.get('method')
        request_id = data.get('id')

        # Initialize doesn't require session
        if method == 'initialize':
            return self._handle_initialize(request_id)

        # All other methods require valid session
        if not self._validate_session(session_id):
            self.request.response.setStatus(404)
            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps(self._json_rpc_error(
                request_id, -32600, 'Invalid or expired session'
            ))

        # Route to appropriate handler
        if method == 'notifications/initialized':
            # Client notification that initialization is complete
            _sessions[session_id]['initialized'] = True
            self.request.response.setStatus(202)
            return ''
        elif method == 'tools/list':
            result = self._handle_tools_list(request_id)
        elif method == 'tools/call':
            result = self._handle_tools_call(data, request_id)
        elif method == 'ping':
            result = self._handle_ping(request_id)
        else:
            result = self._json_rpc_error(request_id, -32601, f'Method not found: {method}')

        # Return as JSON or SSE based on Accept header
        response_json = json.dumps(result)

        if len(response_json) > MAX_RESPONSE_SIZE_BYTES:
            logger.warning(f'Response size {len(response_json)} exceeds limit {MAX_RESPONSE_SIZE_BYTES}')
            result = self._json_rpc_error(
                request_id,
                code=-32603,
                message=f'Response too large (max {MAX_RESPONSE_SIZE_BYTES} bytes)'
            )
            response_json = json.dumps(result)

        if 'text/event-stream' in accept_header:
            self.request.response.setHeader('Content-Type', 'text/event-stream')
            self.request.response.setHeader('Cache-Control', 'no-cache')
            return self._format_sse_event(result, event_id=str(request_id))
        else:
            self.request.response.setHeader('Content-Type', 'application/json')
            return response_json

    def _handle_initialize(self, request_id):
        """Handle initialize request - creates new session."""
        session_id = self._create_session()

        self.request.response.setHeader('Content-Type', 'application/json')
        self.request.response.setHeader('Mcp-Session-Id', session_id)

        return json.dumps({
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {
                'protocolVersion': MCP_PROTOCOL_VERSION,
                'serverInfo': {
                    'name': 'plone-mcp',
                    'version': '0.2.0',
                },
                'capabilities': {
                    'tools': {},
                },
            },
        })

    def _handle_ping(self, request_id):
        """Handle ping request."""
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {}
        }

    def _handle_tools_list(self, request_id):
        """Handle tools/list request."""
        tools = []
        sm = getSecurityManager()

        available_tools = getAdapters((self.context, self.request), IMCPTool)
        for name, tool in available_tools:
            if not sm.checkPermission(tool.permission, self.context):
                continue

            tools.append({
                'name': tool.name,
                'description': tool.description,
                'inputSchema': tool.schema
            })

        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {
                'tools': tools,
            },
        }

    def _handle_tools_call(self, data, request_id):
        """Handle tools/call request."""
        params = data.get('params', {})
        tool_name = params.get('name')
        tool_args = params.get('arguments', {})

        if not tool_name:
            return self._json_rpc_error(
                request_id,
                code=-32602,
                message='Missing required parameter: name'
            )

        tool = queryMultiAdapter(
            (self.context, self.request),
            IMCPTool,
            name=tool_name
        )

        if tool is None:
            return self._json_rpc_error(
                request_id,
                code=-32602,
                message=f'Unknown tool: {tool_name}'
            )

        sm = getSecurityManager()
        if not sm.checkPermission(tool.permission, self.context):
            return self._json_rpc_error(
                request_id,
                code=-32600,
                message=f'Permission denied for tool: {tool_name}'
            )

        try:
            result = tool.execute(tool_args)
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'content': [
                        {'type': 'text', 'text': json.dumps(result)}
                    ]
                }
            }
        except Exception as e:
            logger.error(f'Tool {tool_name} execution failed, error: {str(e)}')
            return self._json_rpc_error(
                request_id,
                code=-32603,
                message='Internal error'
            )

    def _json_rpc_error(self, request_id, code, message):
        """Create a JSON-RPC error response."""
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {
                'code': code,
                'message': message,
            },
        }
