from plone.app.textfield.value import IRichTextValue
from plone.app.uuid.utils import uuidToObject
from plone.base.utils import safe_text
from plone.indexer import indexer
from Products.CMFCore.utils import getToolByName
from unibonn.courses.configs.course import (
    COURSE_LANGUAGES,
    FIELD_OF_STUDIES,
    STUDY_GRADUATIONS,
    STUDY_OPPORTUNITIES,
)
from unibonn.courses.contenttypes.course import ICourse


def _get_vocab_label(vocab_config, value_id):
    """Get the label (default) for a vocabulary value by its ID."""
    for item in vocab_config:
        if item['id'] == value_id:
            # The title is a Message object, get its default
            title = item.get('title')
            if title:
                return getattr(title, 'default', str(title))
    return ''


def _get_vocab_labels(vocab_config, value_ids):
    """Get labels for multiple vocabulary values."""
    labels = []
    for value_id in (value_ids or []):
        label = _get_vocab_label(vocab_config, value_id)
        if label:
            labels.append(label)
    return labels

# noinspection PyPep8Naming
@indexer(ICourse)
def SearchableTextCourse(obj):
    """SearchableText indexer for Course content type.

    Indexes:
    - id, title
    - subject/tags (from plone.categorization behavior)
    - text, selection_info (RichText fields)
    - graduation, opportunity labels (human-readable)
    - field_of_study, course_language labels (human-readable)
    - requirements descriptions
    """
    transforms = getToolByName(obj, "portal_transforms")
    parts = []

    # ID and Title
    parts.append(safe_text(obj.id))
    parts.append(safe_text(obj.title) or "")

    # Subject/Tags (from plone.categorization behavior)
    if hasattr(obj, 'Subject'):
        parts.append(" ".join([safe_text(s) for s in obj.Subject()]))

    # Graduation label (e.g., "Bachelor of Science", "Master of Arts")
    graduation = getattr(obj, 'graduation', None)
    if graduation:
        parts.append(_get_vocab_label(STUDY_GRADUATIONS, graduation))

    # Opportunity label (e.g., "Major", "Single-Subject")
    opportunity = getattr(obj, 'opportunity', None)
    if opportunity:
        parts.append(_get_vocab_label(STUDY_OPPORTUNITIES, opportunity))

    # Field of study labels (e.g., "Computer Science", "Natural Sciences")
    field_of_study = getattr(obj, 'field_of_study', None)
    if field_of_study:
        parts.extend(_get_vocab_labels(FIELD_OF_STUDIES, field_of_study))

    # Course language labels (e.g., "German", "English")
    course_language = getattr(obj, 'course_language', None)
    if course_language:
        parts.extend(_get_vocab_labels(COURSE_LANGUAGES, course_language))

    # Requirements descriptions (e.g., "HZB (z.B. Abitur)", "Deutsche Sprachkenntnisse")
    requirements = getattr(obj, 'requirements', None)
    if requirements:
        for req in requirements:
            desc = req.get('description')
            if desc:
                parts.append(safe_text(desc))

    # Main text field (RichText)
    text = getattr(obj, 'text', None)
    if text and IRichTextValue.providedBy(text):
        raw = safe_text(text.raw)
        plain = transforms.convertTo(
            "text/plain", raw, mimetype=text.mimeType
        ).getData().strip()
        parts.append(safe_text(plain))

    # Selection info (RichText)
    selection_info = getattr(obj, 'selection_info', None)
    if selection_info and IRichTextValue.providedBy(selection_info):
        raw = safe_text(selection_info.raw)
        plain = transforms.convertTo(
            "text/plain", raw, mimetype=selection_info.mimeType
        ).getData().strip()
        parts.append(safe_text(plain))

    return " ".join(parts)
