import plone.api as api
from interaktiv.mcpapi.tools.base import MCPToolBase
from interaktiv.mcpapi.tools import SEARCH_DEFAULT_LIMIT, SEARCH_MAX_LIMIT, SEARCH_MAX_DESCRIPTION_LENGTH


class SearchTool(MCPToolBase):
    """Search content in Plone."""

    name = 'search'
    description = 'Search for content in the Plone site using full-text search'
    schema = {
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': 'Search text (searches title, description, body)'
            },
            'portal_type': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Filter by content type(s)'
            },
            'limit': {
                'type': 'integer',
                'description': 'Maximum results to return',
                'default': SEARCH_DEFAULT_LIMIT
            }
        },
        'required': ['query']
    }
    permission = 'View'

    def execute(self, params):
        catalog = api.portal.get_tool('portal_catalog')

        query = {'SearchableText': params['query']}

        if params.get('portal_type'):
            query['portal_type'] = params['portal_type']

        limit = min(params.get('limit', SEARCH_DEFAULT_LIMIT), SEARCH_MAX_LIMIT)
        results = catalog(**query)[:limit]

        return [
            {
                'title': brain.Title,
                'description': brain.Description[:SEARCH_MAX_DESCRIPTION_LENGTH],
                'path': brain.getPath(),
                'type': brain.portal_type,
                'url': brain.getURL(),
            }
            for brain in results
        ]
