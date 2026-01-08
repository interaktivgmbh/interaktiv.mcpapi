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


class IMCPBlockTool(IMCPTool):
    """Interface for block-specific MCP tools.

    Block tools can add individual blocks to existing content.
    They also provide metadata that can be used by discovery tools
    (list_addable_blocks) and creation tools (create_content_with_blocks).
    """

    block_type = Attribute('Volto block @type identifier (e.g., "slate", "image")')
    block_description = Attribute('Description of when/how to use this block type')
    block_schema = Attribute('JSON Schema for block-specific parameters')

    def to_volto_block(params):
        """Convert simplified parameters to native Volto block structure.

        Args:
            params: Block parameters matching block_schema

        Returns:
            dict: Native Volto block structure with @type and block-specific data
        """
