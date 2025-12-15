from zope.interface import Interface, Attribute


class IInteraktivMcpapiLayer(Interface):
    """Marker interface for the interaktiv.mcpapi browser layer"""


class IMCPTool(Interface):
    """Interface for MCP tools."""

    name = Attribute('Tool name')
    description = Attribute('Tool description')
    schema = Attribute('JSON Schema for input parameters')
    permission = Attribute('Zope permission required')

    def execute(params):
        """Execute the tool with given parameters."""
