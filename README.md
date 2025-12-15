# interaktiv.mcpapi

MCP (Model Context Protocol) integration for Plone 6.

This addon provides an MCP endpoint for Plone, allowing Large Language Models (LLMs) like Claude and ChatGPT to interact with your Plone site using standardized tools.

## What is MCP?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) is an open standard for connecting AI models to external tools and data sources. Originally developed by Anthropic, MCP is now governed by the [Agentic AI Foundation (AAIF)](https://aaif.io/) under the Linux Foundation, with backing from major industry players including OpenAI, Google, Microsoft, Amazon, and others.

## Features

- JSON-RPC 2.0 compliant MCP endpoint at `/@mcp`
- Extensible tool system via Zope adapters
- Permission-aware tool filtering
- Anonymous and authenticated access support
- Built-in security measures (response size limits, input validation)
- Includes a `search` tool out of the box

## Compatibility

- Plone 6.x
- Python 3.11+

## Installation

Add `interaktiv.mcpapi` to your buildout:

```ini
[buildout]
...
eggs =
    interaktiv.mcpapi
```

Run buildout:

```bash
bin/buildout
```

Install the addon via the Plone control panel or portal_setup.

## MCP Client Compatibility

| Client | Support | Notes |
|--------|---------|-------|
| Claude Code CLI | Yes | `claude mcp add` |
| Claude Desktop | Yes | Config file |
| ChatGPT (browser) | Yes | Pro/Plus users, Developer mode |
| ChatGPT Desktop | Yes | Developer mode |
| OpenAI Agents SDK | Yes | Full support |

## Usage

### Connecting from Claude Code CLI

```bash
# Anonymous access
claude mcp add --transport http plone-mcp https://your-plone-site.com/@mcp

# With authentication
claude mcp add --transport http plone-mcp https://your-plone-site.com/@mcp \
  --header "Authorization: Basic <base64-credentials>"
```

### Connecting from ChatGPT

1. Go to **Settings > Connectors > Advanced > Developer mode**
2. Add your MCP endpoint URL: `https://your-plone-site.com/@mcp`
3. Configure authentication if required

### Testing the Endpoint

```bash
# Initialize
curl -X POST https://your-plone-site.com/@mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1}'

# List available tools
curl -X POST https://your-plone-site.com/@mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# Call the search tool
curl -X POST https://your-plone-site.com/@mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":1,"params":{"name":"search","arguments":{"query":"my search term"}}}'
```

## Built-in Tools

### search

Search for content in the Plone site using full-text search.

**Parameters:**
- `query` (string, required): Search text
- `portal_type` (array, optional): Filter by content type(s)
- `limit` (integer, optional): Maximum results (default: 10, max: 100)

**Example:**
```json
{
  "name": "search",
  "arguments": {
    "query": "news",
    "portal_type": ["Document", "News Item"],
    "limit": 20
  }
}
```

## Creating Custom Tools

### 1. Create a Tool Class

```python
# your.addon/tools/mytool.py
from interaktiv.mcpapi.tools.base import MCPToolBase


class MyCustomTool(MCPToolBase):
    """Description of what your tool does."""

    name = 'my_tool'
    description = 'A helpful description for the LLM to understand when to use this tool'
    schema = {
        'type': 'object',
        'properties': {
            'param1': {
                'type': 'string',
                'description': 'Description of parameter 1'
            },
            'param2': {
                'type': 'integer',
                'description': 'Description of parameter 2',
                'default': 10
            }
        },
        'required': ['param1']
    }
    permission = 'View'  # Zope permission title (not ID)

    def execute(self, params):
        # Your tool logic here
        # self.context and self.request are available
        result = do_something(params['param1'], params.get('param2', 10))
        return {'result': result}
```

### 2. Register the Tool

```xml
<!-- your.addon/tools/configure.zcml -->
<configure xmlns="http://namespaces.zope.org/zope">

  <adapter
      factory=".mytool.MyCustomTool"
      provides="interaktiv.mcpapi.interfaces.IMCPTool"
      for="* zope.publisher.interfaces.browser.IDefaultBrowserLayer"
      name="my_tool"
  />

</configure>
```

### Permission Values

Use Zope permission **titles** (not IDs) for the `permission` attribute:

| Permission Title | Permission ID | Description |
|-----------------|---------------|-------------|
| `View` | `zope2.View` | View content |
| `Modify portal content` | `cmf.ModifyPortalContent` | Edit content |
| `Add portal content` | `cmf.AddPortalContent` | Create content |
| `Manage portal` | `cmf.ManagePortal` | Full admin access |

## Security Considerations

### Built-in Protections

- **CSRF Protection**: Disabled for the MCP endpoint (required for JSON-RPC)
- **Response Size Limit**: Responses exceeding 100KB return an error
- **Search Result Limits**: Maximum 100 results, descriptions truncated to 500 characters
- **Permission Checking**: Each tool can define required permissions
- **Error Handling**: Internal errors are logged but not exposed to clients

### CORS Configuration

For browser-based access (e.g., ChatGPT), you may need CORS headers. Add to your endpoint or webserver:

```python
# In the endpoint
self.request.response.setHeader('Access-Control-Allow-Origin', '*')
self.request.response.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS')
self.request.response.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization')
```

### Recommendations

- Use HTTPS in production
- Consider rate limiting at the webserver level
- Review tool permissions carefully
- Monitor usage logs for abuse

## Documentation

See the `docs/` folder for additional documentation:

- [vision.md](docs/vision.md) - Future vision for MCP on websites
- [current-state.md](docs/current-state.md) - Current MCP ecosystem status

## Links

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [MCP GitHub Repository](https://github.com/modelcontextprotocol)
- [Agentic AI Foundation (AAIF)](https://aaif.io/)

## License

GPL version 2

## Author

[Interaktiv GmbH](https://www.interaktiv.de/)
