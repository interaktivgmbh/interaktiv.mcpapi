from copy import deepcopy

import plone.api as api
from interaktiv.mcpapi.helpers import SlateHTMLParser
from interaktiv.mcpapi.tools.base import MCPToolBase
from plone.app.multilingual.interfaces import ITranslationLocator
from plone.app.multilingual.interfaces import ITranslationManager
from plone.restapi.behaviors import IBlocks


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
