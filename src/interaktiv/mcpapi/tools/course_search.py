import plone.api as api
from interaktiv.mcpapi.tools.base import MCPToolBase
from interaktiv.mcpapi.tools import SEARCH_DEFAULT_LIMIT, SEARCH_MAX_LIMIT, SEARCH_MAX_DESCRIPTION_LENGTH


class CourseSearchTool(MCPToolBase):
    """Search courses in the Plone study database."""

    name = 'course_search'
    description = 'Search for courses/study programs in the university study database. Can list all courses or filter by degree type, field of study, language, etc.'
    schema = {
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': 'Optional: Search text (searches title, description, body). Leave empty to list all courses.'
            },
            'graduation': {
                'type': 'string',
                'description': 'Filter by degree type: bachelor_of_arts, bachelor_of_science, bachelor_of_laws, master_of_arts, master_of_science, master_of_education, master_further_forming, state_examination, lectureship, theological_exam, theological_magister'
            },
            'opportunity': {
                'type': 'string',
                'description': 'Filter by program option: bachelor_core (Major), bachelor_dual (Double Major), bachelor_single (Single-Subject), bachelor_supplemental (Minor), dual, lectureship_gymnasium, lectureship_berufskolleg_great_specialisation, lectureship_berufskolleg_small_specialisation, lectureship_berufskolleg_two_subject'
            },
            'field_of_study': {
                'type': 'string',
                'description': 'Filter by field of study: natural_sciences_mathematics_and_environmental_sciences, computer_science_and_engineering_sciences, agricultural_nutritional_and_food_sciences, medicine_life_and_health_sciences, economics_law, social_sciences, humanities_linguistics_cultural_studies_theology, teaching_degrees'
            },
            'course_language': {
                'type': 'string',
                'description': 'Filter by course language: german, english, french, italian, spanish, other_languages'
            },
            'study_starts': {
                'type': 'string',
                'description': 'Filter by start semester: winter_term, summer_term'
            },
            'limit': {
                'type': 'integer',
                'description': 'Maximum results to return',
                'default': SEARCH_DEFAULT_LIMIT
            }
        },
        'required': []
    }
    permission = 'View'

    def execute(self, params):
        catalog = api.portal.get_tool('portal_catalog')

        # Always filter by Course portal_type
        query = {'portal_type': 'Course'}

        # Optional text search
        if params.get('query'):
            query['SearchableText'] = params['query']

        # Course-specific filters using catalog indexes
        if params.get('graduation'):
            query['graduation'] = params['graduation']

        if params.get('opportunity'):
            query['opportunity'] = params['opportunity']

        if params.get('field_of_study'):
            query['field_of_study'] = params['field_of_study']

        if params.get('course_language'):
            query['course_language'] = params['course_language']

        if params.get('study_starts'):
            query['study_starts'] = params['study_starts']

        limit = min(params.get('limit', SEARCH_DEFAULT_LIMIT), SEARCH_MAX_LIMIT)
        results = catalog(**query)[:limit]

        return [
            self._format_result(brain)
            for brain in results
        ]

    def _format_result(self, brain):
        """Format a course object into a result dict with all available data."""
        obj = brain.getObject()

        result = {
            'title': obj.title,
            'description': obj.description[:SEARCH_MAX_DESCRIPTION_LENGTH] if obj.description else '',
            'path': brain.getPath(),
            'url': brain.getURL(),
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

        # Rich text field - extract plain text
        text = getattr(obj, 'text', None)
        if text and hasattr(text, 'raw'):
            # Limit text length to avoid huge responses
            raw_text = text.raw or ''
            if len(raw_text) > 1000:
                raw_text = raw_text[:1000] + '...'
            result['text'] = raw_text

        # Selection info
        selection_info = getattr(obj, 'selection_info', None)
        if selection_info and hasattr(selection_info, 'raw'):
            raw_text = selection_info.raw or ''
            if len(raw_text) > 500:
                raw_text = raw_text[:500] + '...'
            result['selection_info'] = raw_text

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
