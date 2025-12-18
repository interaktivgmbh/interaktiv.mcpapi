import json
import unittest
from interaktiv.mcpapi.interfaces import IInteraktivMcpapiLayer
from interaktiv.mcpapi.mcp.endpoint import MCPEndpoint
from interaktiv.mcpapi.testing import INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING

from plone import api
from plone.app.testing import TEST_USER_ID, setRoles
from unittest.mock import patch
from interaktiv.mcpapi.tools.search import SearchTool


class TestMCPEndpointView(unittest.TestCase):
    layer = INTERAKTIV_MCPAPI_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        setRoles(self.portal, TEST_USER_ID, ['Manager', 'Site Administrator'])

        self.view = api.content.get_view(
            name='@mcp',
            context=self.portal,
            request=self.request,
        )

    def test__handle_initialize(self):
        # do it
        result = self.view._handle_initialize(request_id='some_request_id')

        # postcondition
        expected_result = {
            'jsonrpc': '2.0',
            'id': 'some_request_id',
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
        self.assertDictEqual(result, expected_result)

    def test__handle_tools_list__no_permission(self):
        # do it
        with patch.object(SearchTool, 'permission', 'cmf.ManagePortal'):
            with api.env.adopt_roles(['Member']):
                result = self.view._handle_tools_list(request_id='some_request_id')

        # postcondition
        self.assertIn('result', result)
        self.assertIn('tools', result['result'])
        tools = result['result']['tools']

        self.assertEqual(len(tools), 0)

    def test__handle_tools_list(self):
        # do it
        result = self.view._handle_tools_list(request_id='some_request_id')

        # postcondition
        self.assertIn('result', result)
        self.assertIn('tools', result['result'])
        tools = result['result']['tools']

        tool_names = [tool['name'] for tool in tools]
        self.assertIn('search', tool_names)

    def test__handle_tools_call__no_tool_name(self):
        # setup
        data = {}

        # do it
        result = self.view._handle_tools_call(data=data, request_id='some_request_id')

        # postocondition
        expected_result = {
            'jsonrpc': '2.0',
            'id': 'some_request_id',
            'error': {
                'code': -32602,
                'message': 'Missing required parameter: name',
            },
        }
        self.assertDictEqual(result, expected_result)

    def test__handle_tools_call__unkown_tool(self):
        # setup
        data = {
            'params': {
                'name': 'unkown_tool_name',
            },
        }

        # do it
        result = self.view._handle_tools_call(data=data, request_id='some_request_id')

        # postocondition
        expected_result = {
            'jsonrpc': '2.0',
            'id': 'some_request_id',
            'error': {
                'code': -32602,
                'message': 'Unknown tool: unkown_tool_name',
            },
        }
        self.assertDictEqual(result, expected_result)

    def test__handle_tools_call__no_permission(self):
        # setup
        data = {
            'params': {
                'name': 'search',
                'arguments': {
                    'query': 'mow'
                }
            }
        }

        # do it
        with patch.object(SearchTool, 'permission', 'cmf.ManagePortal'):
            with api.env.adopt_roles(['Member']):
                result = self.view._handle_tools_call(data=data, request_id='some_request_id')

        # postcondition
        expected_result = {
            'jsonrpc': '2.0',
            'id': 'some_request_id',
            'error': {
                'code': -32600,
                'message': 'Permission denied for tool: search',
            },
        }
        self.assertDictEqual(result, expected_result)

    def test__handle_tools_call__tool_execution_error(self):
        # setup
        data = {
            'params': {
                'name': 'search',
                'arguments': {
                    'query': 'mow'
                }
            }
        }

        # do it
        with patch.object(SearchTool, 'execute', side_effect=Exception('Something went wrong')):
            result = self.view._handle_tools_call(data=data, request_id='some_request_id')

        # postcondition
        expected_result = {
            'jsonrpc': '2.0',
            'id': 'some_request_id',
            'error': {
                'code': -32603,
                'message': 'Internal error',
            },
        }
        self.assertDictEqual(result, expected_result)

    def test__handle_tools_call__valid_data(self):
        # setup
        data = {
            'params': {
                'name': 'search',
                'arguments': {
                    'query': 'mow'
                }
            }
        }
        api.content.create(
            container=self.portal,
            type='Document',
            id='document_a',
            title='Mow makes the cow',
        )

        # do it
        result = self.view._handle_tools_call(data=data, request_id='some_request_id')

        # postcondition
        self.assertIn('result', result)
        self.assertIn('content', result['result'])
        content = result['result']['content']

        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]['type'], 'text')
        content_data = json.loads(content[0]['text'])
        self.assertEqual(len(content_data), 1)
        expected_content_data = {
            'title': 'Mow makes the cow',
            'description': '',
            'path': '/plone/document_a',
            'type': 'Document',
            'url': f'{self.portal.absolute_url()}/document_a'
        }
        self.assertDictEqual(content_data[0], expected_content_data)

    def test__json_rpc_error(self):
        # do it
        result = self.view._json_rpc_error(
            request_id='some_request_id',
            code=12345,
            message='Something went wrong'
        )

        # postcondition
        expected_result = {
            'jsonrpc': '2.0',
            'id': 'some_request_id',
            'error': {
                'code': 12345,
                'message': 'Something went wrong',
            },
        }
        self.assertDictEqual(result, expected_result)

    def test__call__invalid_json(self):
        # setup
        self.request['BODY'] = '":\''

        # do it
        result = self.view()

        # postcondition
        self.assertIsInstance(result, str)
        data = json.loads(result)
        expected_data = {
            'jsonrpc': '2.0',
            'id': None,
            'error': {
                'code': -32700,
                'message': 'Parse error',
            },
        }
        self.assertDictEqual(data, expected_data)

    def test__call__unknown_method(self):
        # setup
        self.request['BODY'] = json.dumps({
            'jsonrpc': '2.0',
            'method': 'unknown_method',
            'id': 'some_request_id'
        })

        # do it
        result = self.view()

        # postcondition
        self.assertIsInstance(result, str)
        data = json.loads(result)
        expected_data = {
            'jsonrpc': '2.0',
            'id': 'some_request_id',
            'error': {
                'code': -32601,
                'message': 'Method not found: unknown_method',
            },
        }
        self.assertDictEqual(data, expected_data)

    def test__call__initialize(self):
        # setup
        self.request['BODY'] = json.dumps({
            'jsonrpc': '2.0',
            'method': 'initialize',
            'id': 'some_request_id'
        })

        # do it
        result = self.view()

        # postcondition
        self.assertIsInstance(result, str)
        data = json.loads(result)
        expected_data = {
            'jsonrpc': '2.0',
            'id': 'some_request_id',
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
        self.assertDictEqual(data, expected_data)

    def test__call__tools_list(self):
        # setup
        self.request['BODY'] = json.dumps({
            'jsonrpc': '2.0',
            'method': 'tools/list',
            'id': 'some_request_id'
        })

        # do it
        result = self.view()

        # postcondition
        self.assertIsInstance(result, str)
        data = json.loads(result)

        self.assertIn('result', data)
        self.assertIn('tools', data['result'])
        tools = data['result']['tools']

        tool_names = [tool['name'] for tool in tools]
        self.assertIn('search', tool_names)

    def test__call__tools_call(self):
        # setup
        self.request['BODY'] = json.dumps({
            'jsonrpc': '2.0',
            'method': 'tools/call',
            'id': 'some_request_id',
            'params': {
                'name': 'search',
                'arguments': {
                    'query': 'mow'
                }
            }
        })
        api.content.create(
            container=self.portal,
            type='Document',
            id='document_a',
            title='Mow makes the cow',
        )

        # do it
        result = self.view()

        # postcondition
        self.assertIsInstance(result, str)
        data = json.loads(result)

        self.assertIn('result', data)
        self.assertIn('content', data['result'])
        content = data['result']['content']

        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]['type'], 'text')
        content_data = json.loads(content[0]['text'])
        self.assertEqual(len(content_data), 1)
        expected_content_data = {
            'title': 'Mow makes the cow',
            'description': '',
            'path': '/plone/document_a',
            'type': 'Document',
            'url': f'{self.portal.absolute_url()}/document_a'
        }
        self.assertDictEqual(content_data[0], expected_content_data)
