"""
MCP Endpoint implementing Streamable HTTP transport.

This implementation supports stateless mode for compatibility with
load-balanced environments and claude.ai direct connections.

Reference: https://modelcontextprotocol.io/specification/2025-03-26/basic/transports
"""
import json
from interaktiv.mcpapi import logger
from interaktiv.mcpapi.interfaces import IMCPTool

from AccessControl import getSecurityManager
from Products.Five import BrowserView
from plone.protect.interfaces import IDisableCSRFProtection
from zope.component import getAdapters, queryMultiAdapter
from zope.interface import alsoProvides
from interaktiv.mcpapi.mcp import MAX_RESPONSE_SIZE_BYTES


# MCP Protocol versions
LATEST_PROTOCOL_VERSION = '2025-03-26'
SUPPORTED_PROTOCOL_VERSIONS = ['2024-11-05', '2025-03-26']

# Content types
CONTENT_TYPE_JSON = 'application/json'
CONTENT_TYPE_SSE = 'text/event-stream'


class MCPEndpoint(BrowserView):
    """MCP Endpoint implementing Streamable HTTP transport.

    This is a stateless implementation - each request is handled independently
    without session tracking. This ensures compatibility with load-balanced
    environments where requests may hit different workers.
    """

    def _check_accept_headers(self):
        """Check if the request accepts the required media types.

        Returns tuple of (has_json, has_sse).
        """
        accept_header = self.request.getHeader('Accept', '')
        accept_types = [t.strip().split(';')[0] for t in accept_header.split(',')]

        has_json = any(t.startswith(CONTENT_TYPE_JSON) for t in accept_types)
        has_sse = any(t.startswith(CONTENT_TYPE_SSE) for t in accept_types)

        return has_json, has_sse

    def _check_content_type(self):
        """Check if the request has the correct Content-Type."""
        content_type = self.request.getHeader('Content-Type', '')
        return content_type.split(';')[0].strip() == CONTENT_TYPE_JSON

    def _get_protocol_version(self):
        """Get and validate protocol version from request."""
        # For initialize, get from params; for others, get from header
        return self.request.getHeader('Mcp-Protocol-Version', LATEST_PROTOCOL_VERSION)

    def _format_sse_event(self, data, event_id=None):
        """Format a message as an SSE event matching FastMCP format."""
        lines = []
        if event_id:
            lines.append(f'id: {event_id}')
        lines.append('event: message')
        lines.append(f'data: {json.dumps(data)}')
        lines.append('')  # Empty line to end event
        return '\n'.join(lines) + '\n'

    def _set_sse_headers(self):
        """Set headers for SSE response matching FastMCP."""
        self.request.response.setHeader('Content-Type', 'text/event-stream; charset=utf-8')
        self.request.response.setHeader('Cache-Control', 'no-cache, no-transform')
        self.request.response.setHeader('Connection', 'keep-alive')
        self.request.response.setHeader('X-Accel-Buffering', 'no')

    def _set_json_headers(self):
        """Set headers for JSON response."""
        self.request.response.setHeader('Content-Type', 'application/json; charset=utf-8')

    def _json_rpc_error(self, request_id, code, message):
        """Create a JSON-RPC error response matching FastMCP format."""
        return {
            'jsonrpc': '2.0',
            'id': request_id if request_id is not None else 'server-error',
            'error': {
                'code': code,
                'message': message,
            },
        }

    def _json_rpc_result(self, request_id, result):
        """Create a JSON-RPC success response."""
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': result,
        }

    def __call__(self):
        alsoProvides(self.request, IDisableCSRFProtection)

        method = self.request.method

        if method == 'POST':
            return self._handle_post()
        elif method == 'GET':
            return self._handle_get()
        elif method == 'DELETE':
            return self._handle_delete()
        else:
            self.request.response.setStatus(405)
            self.request.response.setHeader('Allow', 'GET, POST, DELETE')
            self._set_json_headers()
            return json.dumps(self._json_rpc_error(None, -32600, 'Method not allowed'))

    def _handle_get(self):
        """Handle GET request for SSE stream.

        In stateless mode, we don't support server-initiated streams.
        """
        self.request.response.setStatus(405)
        self._set_json_headers()
        return json.dumps(self._json_rpc_error(
            None, -32600, 'GET streams not supported in stateless mode'
        ))

    def _handle_delete(self):
        """Handle DELETE request for session termination.

        In stateless mode, this is a no-op but we return success.
        """
        self.request.response.setStatus(200)
        self._set_json_headers()
        return ''

    def _handle_post(self):
        """Handle POST request with JSON-RPC message."""
        logger.info("MCP POST request received")

        # Validate Content-Type
        if not self._check_content_type():
            self.request.response.setStatus(415)
            self._set_json_headers()
            return json.dumps(self._json_rpc_error(
                None, -32600, 'Unsupported Media Type: Content-Type must be application/json'
            ))

        # Validate Accept header - must accept both JSON and SSE
        has_json, has_sse = self._check_accept_headers()
        if not (has_json and has_sse):
            self.request.response.setStatus(406)
            self._set_json_headers()
            return json.dumps(self._json_rpc_error(
                None, -32600,
                'Not Acceptable: Client must accept both application/json and text/event-stream'
            ))

        # Parse request body
        body = self.request.get('BODY', '{}')
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            self.request.response.setStatus(400)
            self._set_json_headers()
            return json.dumps(self._json_rpc_error(None, -32700, f'Parse error: {str(e)}'))

        method = data.get('method')
        request_id = data.get('id')

        # Handle different methods
        if method == 'initialize':
            return self._handle_initialize(data, request_id)
        elif method == 'notifications/initialized':
            # Client notification - return 202 Accepted with empty body
            self.request.response.setStatus(202)
            return ''
        elif method == 'tools/list':
            return self._handle_tools_list(request_id)
        elif method == 'tools/call':
            return self._handle_tools_call(data, request_id)
        elif method == 'ping':
            return self._handle_ping(request_id)
        else:
            return self._send_response(
                self._json_rpc_error(request_id, -32601, f'Method not found: {method}'),
                request_id
            )

    def _handle_initialize(self, data, request_id):
        """Handle initialize request."""
        # Validate protocol version from params
        params = data.get('params', {})
        client_version = params.get('protocolVersion', LATEST_PROTOCOL_VERSION)

        if client_version not in SUPPORTED_PROTOCOL_VERSIONS:
            self.request.response.setStatus(400)
            self._set_json_headers()
            supported = ', '.join(SUPPORTED_PROTOCOL_VERSIONS)
            return json.dumps(self._json_rpc_error(
                request_id, -32600,
                f'Unsupported protocol version: {client_version}. Supported: {supported}'
            ))

        result = self._json_rpc_result(request_id, {
            'protocolVersion': LATEST_PROTOCOL_VERSION,
            'serverInfo': {
                'name': 'plone-mcp',
                'version': '0.4.0',
            },
            'capabilities': {
                'tools': {},
            },
        })

        return self._send_response(result, request_id)

    def _handle_ping(self, request_id):
        """Handle ping request."""
        result = self._json_rpc_result(request_id, {})
        return self._send_response(result, request_id)

    def _handle_tools_list(self, request_id):
        """Handle tools/list request."""
        # Validate protocol version header for non-initialize requests
        protocol_version = self._get_protocol_version()
        if protocol_version not in SUPPORTED_PROTOCOL_VERSIONS:
            self.request.response.setStatus(400)
            self._set_json_headers()
            supported = ', '.join(SUPPORTED_PROTOCOL_VERSIONS)
            return json.dumps(self._json_rpc_error(
                request_id, -32600,
                f'Unsupported protocol version: {protocol_version}. Supported: {supported}'
            ))

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

        result = self._json_rpc_result(request_id, {'tools': tools})
        return self._send_response(result, request_id)

    def _handle_tools_call(self, data, request_id):
        """Handle tools/call request."""
        # Validate protocol version header
        protocol_version = self._get_protocol_version()
        if protocol_version not in SUPPORTED_PROTOCOL_VERSIONS:
            self.request.response.setStatus(400)
            self._set_json_headers()
            supported = ', '.join(SUPPORTED_PROTOCOL_VERSIONS)
            return json.dumps(self._json_rpc_error(
                request_id, -32600,
                f'Unsupported protocol version: {protocol_version}. Supported: {supported}'
            ))

        params = data.get('params', {})
        tool_name = params.get('name')
        tool_args = params.get('arguments', {})

        if not tool_name:
            return self._send_response(
                self._json_rpc_error(request_id, -32602, 'Missing required parameter: name'),
                request_id
            )

        tool = queryMultiAdapter(
            (self.context, self.request),
            IMCPTool,
            name=tool_name
        )

        if tool is None:
            return self._send_response(
                self._json_rpc_error(request_id, -32602, f'Unknown tool: {tool_name}'),
                request_id
            )

        sm = getSecurityManager()
        if not sm.checkPermission(tool.permission, self.context):
            return self._send_response(
                self._json_rpc_error(request_id, -32600, f'Permission denied for tool: {tool_name}'),
                request_id
            )

        try:
            tool_result = tool.execute(tool_args)
            result = self._json_rpc_result(request_id, {
                'content': [
                    {'type': 'text', 'text': json.dumps(tool_result)}
                ]
            })
            return self._send_response(result, request_id)
        except Exception as e:
            logger.error(f'Tool {tool_name} execution failed: {str(e)}')
            return self._send_response(
                self._json_rpc_error(request_id, -32603, f'Tool execution error: {str(e)}'),
                request_id
            )

    def _send_response(self, result, request_id):
        """Send response as SSE (default) or JSON based on Accept header.

        Always uses SSE format for consistency with FastMCP.
        """
        response_json = json.dumps(result)

        # Check response size
        if len(response_json) > MAX_RESPONSE_SIZE_BYTES:
            logger.warning(f'Response size {len(response_json)} exceeds limit {MAX_RESPONSE_SIZE_BYTES}')
            result = self._json_rpc_error(
                request_id,
                -32603,
                f'Response too large (max {MAX_RESPONSE_SIZE_BYTES} bytes)'
            )

        # Always return SSE format for compatibility with claude.ai
        self._set_sse_headers()
        return self._format_sse_event(result, event_id=str(request_id) if request_id else None)
