from interaktiv.mcpapi.helpers import SlateHTMLParser
from interaktiv.mcpapi.tools.base import MCPBlockToolBase


class AddSlateBlockTool(MCPBlockToolBase):
    """Add a slate (rich text) block to existing content."""

    name = 'add_slate_block'
    description = (
        'Add a rich text block to existing Plone content. '
        'The text parameter accepts HTML with common formatting tags '
        '(p, h1-h6, strong, em, a, ul, ol, li, blockquote, code).'
    )

    block_type = 'slate'
    block_description = (
        'Rich text block for formatted content. Supports headings, paragraphs, '
        'bold, italic, links, lists, blockquotes, and inline code.'
    )
    block_schema = {
        'type': 'object',
        'properties': {
            'text': {
                'type': 'string',
                'description': (
                    'HTML content for the block. Supports: '
                    'p, h1-h6, strong/b, em/i, u, s, a, ul, ol, li, blockquote, code'
                ),
            },
        },
        'required': ['text'],
    }

    def to_volto_block(self, params):
        """Convert HTML text to Volto slate block structure."""
        html = params.get('text', '')

        parser = SlateHTMLParser()
        parser.feed(html)
        value, plaintext = parser.get_result()

        return {
            '@type': self.block_type,
            'value': value,
            'plaintext': plaintext,
        }
