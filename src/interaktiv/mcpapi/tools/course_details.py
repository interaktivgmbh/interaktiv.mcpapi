import plone.api as api
from interaktiv.mcpapi.tools.base import MCPToolBase
from interaktiv.mcpapi.tools import SEARCH_MAX_DESCRIPTION_LENGTH


class CourseDetailsTool(MCPToolBase):
    """Get full details of a single course."""

    name = 'course_details'
    description = 'Get full details of a single course/study program by its path. Use this after course_search to get complete information including requirements, information links, and full text content.'
    schema = {
        'type': 'object',
        'properties': {
            'path': {
                'type': 'string',
                'description': 'The path to the course (e.g., /de/studium/studienangebot/informatik-bsc)'
            },
        },
        'required': ['path']
    }
    permission = 'View'

    def execute(self, params):
        path = params.get('path', '')

        # Normalize path - remove leading /site if present
        if path.startswith('/site'):
            path = path[5:]

        # Get the course object
        portal = api.portal.get()
        try:
            obj = portal.restrictedTraverse(path.lstrip('/'))
        except (KeyError, AttributeError):
            return {'error': f'Course not found at path: {path}'}

        # Verify it's a Course
        if getattr(obj, 'portal_type', None) != 'Course':
            return {'error': f'Object at path is not a Course: {path}'}

        return self._format_full_result(obj)

    def _format_full_result(self, obj):
        """Format a course object into a full result dict with all available data."""
        result = {
            'title': obj.title,
            'description': obj.description[:SEARCH_MAX_DESCRIPTION_LENGTH] if obj.description else '',
            'path': '/'.join(obj.getPhysicalPath()),
            'url': obj.absolute_url(),
        }

        # Core course fields
        course_fields = [
            'graduation',
            'opportunity',
            'period',
            'course_language',
            'study_starts',
            'field_of_study',
            'int_orientation',
            'international_double_degree',
        ]

        for field in course_fields:
            value = getattr(obj, field, None)
            if value is not None:
                result[field] = value

        # Information links (datagrid field)
        info_links = getattr(obj, 'information_links', None)
        if info_links:
            result['information_links'] = info_links

        # Requirements (datagrid field)
        requirements = getattr(obj, 'requirements', None)
        if requirements:
            result['requirements'] = requirements

        # Rich text field - extract content
        text = getattr(obj, 'text', None)
        if text and hasattr(text, 'raw'):
            result['text'] = text.raw or ''

        # Selection info
        selection_info = getattr(obj, 'selection_info', None)
        if selection_info and hasattr(selection_info, 'raw'):
            result['selection_info'] = selection_info.raw or ''

        # Get human-readable labels using Course methods
        if hasattr(obj, 'get_graduation'):
            result['graduation_label'] = obj.get_graduation()
        if hasattr(obj, 'get_opportunity'):
            result['opportunity_label'] = obj.get_opportunity()
        if hasattr(obj, 'get_start'):
            result['study_starts_label'] = obj.get_start()
        if hasattr(obj, 'get_language'):
            result['course_language_label'] = obj.get_language()
        if hasattr(obj, 'get_period'):
            result['period_label'] = obj.get_period()

        return result
