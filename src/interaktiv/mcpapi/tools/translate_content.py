from copy import deepcopy
from html.parser import HTMLParser

import plone.api as api
from plone.app.multilingual.interfaces import ITranslationLocator
from plone.app.multilingual.interfaces import ITranslationManager
from plone.restapi.behaviors import IBlocks

from interaktiv.mcpapi.tools.base import MCPToolBase


class TranslateContentTool(MCPToolBase):
    """Create a translation of existing content."""

    name = 'translate_content'
    description = (
        'Create a translation of existing Plone content. '
        'Copies the source content structure (including blocks) to the target language '
        'and links it as a translation. '
        'Workflow: First use get_content to read the source, then translate the title, '
        'description, and blocks_html, then call this tool with the translated values.'
    )
    schema = {
        'type': 'object',
        'properties': {
            'source_path': {
                'type': 'string',
                'description': 'Path to the source content (e.g., "/de/my-document")'
            },
            'target_language': {
                'type': 'string',
                'description': 'Target language code (e.g., "en", "fr", "de")'
            },
            'title': {
                'type': 'string',
                'description': 'Translated title for the new content'
            },
            'description': {
                'type': 'string',
                'description': 'Translated description (optional)'
            },
            'blocks_html': {
                'type': 'object',
                'description': 'Translated HTML for blocks, keyed by block ID (optional)'
            }
        },
        'required': ['source_path', 'target_language', 'title']
    }
    permission = 'cmf.AddPortalContent'

    def execute(self, params):
        source_path = params['source_path']
        target_language = params['target_language']
        title = params['title']
        description = params.get('description', '')
        blocks_html = params.get('blocks_html', {})

        portal = api.portal.get()
        try:
            source = portal.restrictedTraverse(source_path.lstrip('/'))
        except KeyError:
            raise ValueError(f'Source content not found: {source_path}')

        manager = ITranslationManager(source)
        existing = manager.get_translation(target_language)
        if existing is not None:
            raise ValueError(
                f'Translation to "{target_language}" already exists: {existing.absolute_url()}'
            )

        locator = ITranslationLocator(source)
        target_folder = locator(target_language)

        if target_folder is None:
            raise ValueError(
                f'Could not find target folder for language "{target_language}"'
            )

        new_content = api.content.create(
            container=target_folder,
            type=source.portal_type,
            title=title,
        )

        if description:
            new_content.description = description

        if IBlocks.providedBy(source):
            if hasattr(source, 'blocks') and source.blocks:
                new_content.blocks = deepcopy(source.blocks)
            if hasattr(source, 'blocks_layout') and source.blocks_layout:
                new_content.blocks_layout = deepcopy(source.blocks_layout)

        if blocks_html:
            self._set_translated_block_data(new_content, blocks_html)

        manager.register_translation(target_language, new_content)

        new_content.reindexObject()

        return {
            'status': 'success',
            'message': 'Translation created successfully',
            'source': {
                'path': source_path,
                'url': source.absolute_url(),
            },
            'translation': {
                'path': '/'.join(new_content.getPhysicalPath()),
                'url': new_content.absolute_url(),
                'language': target_language,
                'title': title,
            }
        }

    def _set_translated_block_data(self, content, blocks_html):
        content_blocks = getattr(content, 'blocks', {})
        self._set_translated_blocks_recursive(content_blocks, blocks_html)
        setattr(content, 'blocks', content_blocks)

    def _set_translated_blocks_recursive(self, blocks, blocks_html):
        for block_id, block_data in blocks.items():
            block_type = block_data.get('@type', '')

            if block_type == 'slate' and block_id in blocks_html:
                html_value = blocks_html[block_id]
                if html_value:
                    blocks[block_id] = self._update_slate_block(block_data, html_value)

            data = block_data.get('data', {})
            if isinstance(data, dict) and 'blocks' in data:
                nested_blocks = data.get('blocks', {})
                for nested_block in nested_blocks.values():
                    if isinstance(nested_block, dict) and 'blocks' in nested_block:
                        self._set_translated_blocks_recursive(
                            nested_block['blocks'], blocks_html
                        )

            if 'blocks' in block_data and block_type != 'slate':
                self._set_translated_blocks_recursive(
                    block_data['blocks'], blocks_html
                )

    def _update_slate_block(self, block, html):
        slate_data = deepcopy(block)

        value, plaintext = self._html_to_slate(html)
        slate_data['value'] = value
        slate_data['plaintext'] = plaintext

        return slate_data

    def _html_to_slate(self, html):
        parser = SlateHTMLParser()
        parser.feed(html)
        return parser.get_result()


class SlateHTMLParser(HTMLParser):
    TAG_MAP = {
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
        'a': 'link',
        'strong': 'strong',
        'b': 'strong',
        'em': 'em',
        'i': 'em',
        'u': 'u',
        's': 's',
        'code': 'code',
    }

    BLOCK_TAGS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote'}
    INLINE_TAGS = {'strong', 'b', 'em', 'i', 'u', 's', 'code'}

    def __init__(self):
        super().__init__()
        self.result = []
        self.stack = [self.result]
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag in self.BLOCK_TAGS or tag in self.INLINE_TAGS:
            slate_type = self.TAG_MAP.get(tag, 'p')
            node = {'type': slate_type, 'children': []}
            self.stack[-1].append(node)
            self.stack.append(node['children'])

        elif tag == 'a':
            url = attrs_dict.get('href', '')
            node = {
                'type': 'link',
                'data': {'url': url},
                'children': []
            }
            self.stack[-1].append(node)
            self.stack.append(node['children'])

    def handle_endtag(self, tag):
        if tag in self.BLOCK_TAGS or tag in self.INLINE_TAGS or tag == 'a':
            if len(self.stack) > 1:
                self.stack.pop()

    def handle_data(self, data):
        text = data
        if not text:
            return

        self.text_parts.append(text)

        text_node = {'text': text}
        self.stack[-1].append(text_node)

    def get_result(self):
        plaintext = ' '.join(self.text_parts)
        return self.result, plaintext
