from uuid import uuid4

import plone.api as api
from plone.restapi.behaviors import IBlocks
from zope.interface import implementer

from interaktiv.mcpapi.interfaces import IMCPBlockTool, IMCPTool


@implementer(IMCPTool)
class MCPToolBase:
    """Base class for MCP tools."""

    name = ''
    description = ''
    schema = {'type': 'object', 'properties': {}}
    permission = 'zope2.View'

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def execute(self, params):
        raise NotImplementedError('Subclasses must implement execute()')


@implementer(IMCPBlockTool)
class MCPBlockToolBase(MCPToolBase):
    """Base class for block-specific MCP tools.
    """

    block_type = ''
    block_description = ''
    block_schema = {'type': 'object', 'properties': {}}
    permission = 'cmf.ModifyPortalContent'

    def __init__(self, context, request):
        super().__init__(context, request)
        self._build_tool_schema()

    def _build_tool_schema(self):
        """Build the full tool schema including path and block params."""
        self.schema = {
            'type': 'object',
            'properties': {
                'path': {
                    'type': 'string',
                    'description': 'Path to the content to add the block to',
                },
                'position': {
                    'type': 'integer',
                    'description': 'Position in the block layout (0-indexed). '
                    'If not specified, block is appended at the end.',
                },
                **self.block_schema.get("properties", {}),
            },
            'required': ['path'] + self.block_schema.get('required', []),
        }

    def execute(self, params):
        """Add a block to existing content."""
        path = params.pop('path')
        position = params.pop('position', None)

        portal = api.portal.get()
        try:
            content = portal.restrictedTraverse(path.lstrip('/'))
        except KeyError:
            raise ValueError(f'Content not found: {path}')

        if not IBlocks.providedBy(content):
            raise ValueError(f'Content does not support blocks: {path}')

        block_data = self.to_volto_block(params)
        block_id = str(uuid4())

        blocks = getattr(content, 'blocks', None) or {}
        blocks[block_id] = block_data
        content.blocks = blocks

        blocks_layout = getattr(content, 'blocks_layout', None) or {'items': []}
        items = blocks_layout.get('items', [])
        if position is not None and 0 <= position <= len(items):
            items.insert(position, block_id)
        else:
            items.append(block_id)
        blocks_layout['items'] = items
        content.blocks_layout = blocks_layout

        content.reindexObject()

        return {
            'status': 'success',
            'block_id': block_id,
            'block_type': self.block_type,
            'path': path,
            'position': items.index(block_id),
        }

    def to_volto_block(self, params):
        """Convert simplified params to Volto block structure."""
        raise NotImplementedError('Subclasses must implement to_volto_block()')
