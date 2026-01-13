import json
from interaktiv.mcpapi import logger
from interaktiv.mcpapi.interfaces import IMCPTool

from AccessControl import getSecurityManager
from Products.Five import BrowserView
from plone.protect.interfaces import IDisableCSRFProtection
from zope.component import getAdapters, queryMultiAdapter
from zope.interface import alsoProvides
from interaktiv.mcpapi.mcp import MAX_RESPONSE_SIZE_BYTES


class MCPEndpoint(BrowserView):
    # claude mcp add --transport http plone-local http://localhost:8000/site/@mcp

    # CORS configuration
    CORS_ALLOWED_ORIGINS = ['https://claude.ai']
    CORS_ALLOWED_METHODS = 'POST, OPTIONS'
    CORS_ALLOWED_HEADERS = 'Content-Type, Authorization'

    def _set_cors_headers(self):
        """Set CORS headers for cross-origin requests from claude.ai."""
        origin = self.request.getHeader('Origin', '')
        response = self.request.response

        if origin in self.CORS_ALLOWED_ORIGINS:
            response.setHeader('Access-Control-Allow-Origin', origin)
        elif '*' in self.CORS_ALLOWED_ORIGINS:
            response.setHeader('Access-Control-Allow-Origin', '*')

        response.setHeader('Access-Control-Allow-Methods', self.CORS_ALLOWED_METHODS)
        response.setHeader('Access-Control-Allow-Headers', self.CORS_ALLOWED_HEADERS)

    def __call__(self):
        # Disable CSRF protection for MCP JSON-RPC endpoint
        # TODO this needed to be done for anonymous POST request access
        alsoProvides(self.request, IDisableCSRFProtection)

        # Set CORS headers for all responses
        self._set_cors_headers()

        # Handle CORS preflight request
        if self.request.method == 'OPTIONS':
            self.request.response.setStatus(204)
            return ''

        self.request.response.setHeader('Content-Type', 'application/json')

        body = self.request.get('BODY', '{}')

        try:
            data = json.loads(body)
        except json.decoder.JSONDecodeError:
            return json.dumps(self._json_rpc_error(None, -32700, 'Parse error'))

        method = data.get('method')
        request_id = data.get('id')

        if method == 'initialize':
            result = self._handle_initialize(request_id)
        elif method == 'tools/list':
            result = self._handle_tools_list(request_id)
        elif method == 'tools/call':
            result = self._handle_tools_call(data, request_id)
        else:
            result = self._json_rpc_error(request_id, -32601, f'Method not found: {method}')

        response = json.dumps(result)

        if len(response) > MAX_RESPONSE_SIZE_BYTES:
            logger.warning(f'Response size {len(response)} exceeds limit {MAX_RESPONSE_SIZE_BYTES}')
            return json.dumps(self._json_rpc_error(
                request_id,
                code=-32603,
                message=f'Response too large (max {MAX_RESPONSE_SIZE_BYTES} bytes)'
            ))

        return response

    def _handle_initialize(self, request_id):
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {
                'protocolVersion': '2024-11-05',
                'serverInfo': {
                    'name': 'plone-mcp',
                    'version': '0.1.0',
                },
                'capabilities': {
                    'tools': {},
                },
            },
        }

    def _handle_tools_list(self, request_id):
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
        params = data.get('params', {})
        tool_name = params.get('name')
        tool_args = params.get('arguments', {})

        if not tool_name:
            return self._json_rpc_error(
                request_id,
                code=-32602,
                message='Missing required parameter: name'
            )

        # Look up the tool by name
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

        # Check permission
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
        # reference for JSON-RPC error codes: https://www.jsonrpc.org/specification#error_object
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {
                'code': code,
                'message': message,
            },
        }
