from zope.interface import implementer
from interaktiv.mcpapi.interfaces import IMCPTool


@implementer(IMCPTool)
class MCPToolBase:
    """Base class for MCP tools."""

    name = ""
    description = ""
    schema = {"type": "object", "properties": {}}
    permission = "zope2.View"

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def execute(self, params):
        raise NotImplementedError("Subclasses must implement execute()")
