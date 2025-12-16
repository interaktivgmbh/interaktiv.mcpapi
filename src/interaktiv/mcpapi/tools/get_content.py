import plone.api as api
from plone.restapi.behaviors import IBlocks

from interaktiv.mcpapi.tools.base import MCPToolBase


class GetContentTool(MCPToolBase):
    """Get content data from Plone."""

    name = 'get_content'
    description = (
        'Get content data from a Plone object including title, description, '
        'and blocks. Useful for reading content before translation. '
        'Returns blocks_html with translatable text extracted as HTML. '
        'Use this before translate_content to get the source text for translation.'
    )
    schema = {
        'type': 'object',
        'properties': {
            'path': {
                'type': 'string',
                'description': 'Path to the content (e.g., "/de/my-document")'
            },
        },
        'required': ['path']
    }
    permission = 'zope2.View'

    def execute(self, params):
        path = params['path']

        portal = api.portal.get()
        try:
            content = portal.restrictedTraverse(path.lstrip('/'))
        except KeyError:
            raise ValueError(f'Content not found: {path}')

        result = {
            'path': path,
            'url': content.absolute_url(),
            'portal_type': content.portal_type,
            'title': content.Title(),
            'description': content.Description() or '',
        }

        if IBlocks.providedBy(content):
            blocks = getattr(content, 'blocks', None)
            blocks_layout = getattr(content, 'blocks_layout', None)

            if blocks:
                result['blocks'] = blocks
                result['blocks_html'] = self._extract_blocks_html(blocks)

            if blocks_layout:
                result['blocks_layout'] = blocks_layout

        return result

    def _extract_blocks_html(self, blocks):
        html_blocks = {}
        self._extract_blocks_html_recursive(blocks, html_blocks)
        return html_blocks

    def _extract_blocks_html_recursive(self, blocks, html_blocks):
        for block_id, block_data in blocks.items():
            block_type = block_data.get('@type', '')

            if block_type == 'slate':
                value = block_data.get('value', [])
                if value:
                    html = self._slate_to_html(value)
                    if html and html.strip():
                        html_blocks[block_id] = html.strip()

            data = block_data.get('data', {})
            if isinstance(data, dict) and 'blocks' in data:
                nested_blocks = data.get('blocks', {})
                for nested_block in nested_blocks.values():
                    if isinstance(nested_block, dict) and 'blocks' in nested_block:
                        self._extract_blocks_html_recursive(
                            nested_block['blocks'], html_blocks
                        )

            if 'blocks' in block_data and block_type != 'slate':
                self._extract_blocks_html_recursive(
                    block_data['blocks'], html_blocks
                )

    def _slate_to_html(self, nodes):
        if not nodes:
            return ''

        html_parts = []
        for node in nodes:
            if isinstance(node, dict):
                html_parts.append(self._slate_node_to_html(node))

        return ''.join(html_parts)

    def _slate_node_to_html(self, node):
        if 'text' in node and 'type' not in node:
            text = node.get('text', '')

            if node.get('bold'):
                text = f'<strong>{text}</strong>'
            if node.get('italic'):
                text = f'<em>{text}</em>'
            if node.get('underline'):
                text = f'<u>{text}</u>'
            if node.get('strikethrough'):
                text = f'<s>{text}</s>'
            if node.get('code'):
                text = f'<code>{text}</code>'
            return text

        node_type = node.get('type', 'p')
        children = node.get('children', [])
        children_html = self._slate_to_html(children)

        tag_map = {
            'p': 'p',
            'h1': 'h1',
            'h2': 'h2',
            'h3': 'h3',
            'h4': 'h4',
            'h5': 'h5',
            'h6': 'h6',
            'ul': 'ul',
            'ol': 'ol',
            'li': 'li',
            'blockquote': 'blockquote',
            'link': 'a',
            'strong': 'strong',
            'em': 'em',
            'u': 'u',
            's': 's',
            'code': 'code',
        }

        tag = tag_map.get(node_type, 'p')

        if node_type == 'link':
            url = node.get('url', node.get('data', {}).get('url', '#'))
            return f'<a href="{url}">{children_html}</a>'

        return f'<{tag}>{children_html}</{tag}>'
