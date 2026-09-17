"""Local selection of large notes; only sanitized pages leave this module."""

from datetime import date
import os
import re

from .policy import AccessDenied
from .redaction import MAX_TEXT, PlainText, normalize_text
from .service import ProcessingBlocked

# Operational defaults, not privacy guarantees or provider limits.
DEFAULT_SOURCE_LIMIT = 5_000_000
TARGET_SECTION = 8_000
MONTH_NAMES = (
    ('january', 'jan', 'ocak'), ('february', 'feb', 'şubat'), ('march', 'mar', 'mart'),
    ('april', 'apr', 'nisan'), ('may', 'mayıs'), ('june', 'jun', 'haziran'),
    ('july', 'jul', 'temmuz'), ('august', 'aug', 'ağustos'),
    ('september', 'sep', 'sept', 'eylül'), ('october', 'oct', 'ekim'),
    ('november', 'nov', 'kasım'), ('december', 'dec', 'aralık'),
)
MONTH_MAP = {name: i for i, names in enumerate(MONTH_NAMES, 1) for name in names}


def source_limit():
    try:
        value = int(os.environ.get('EVERWRAP_MAX_SOURCE_CHARS', DEFAULT_SOURCE_LIMIT))
        if not 100_000 <= value <= 20_000_000:
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise ProcessingBlocked('Invalid local source limit.') from None


def validate_selection(view, section, offset, max_chars, query):
    if (type(view) is not str or view not in ('start', 'end', 'latest', 'query')
            or type(section) is not int or section < 0
            or type(offset) is not int or offset < 0
            or type(max_chars) is not int or not 256 <= max_chars <= 16_000
            or (query is not None and (type(query) is not str or not 1 <= len(query) <= 500 or not query.strip()))
            or (view == 'query' and query is None)
            or (view != 'query' and query is not None)
            or (view != 'start' and section != 0)):
        raise AccessDenied('Invalid section request.')


def heading_date(line):
    """Recognize standalone headings, with explicit year; ambiguous slash dates ignored."""
    line = line.strip().strip('#* ').casefold()
    year = month = day = None
    match = re.fullmatch(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', line)
    if match:
        year, month, day = map(int, match.groups())
    else:
        match = re.fullmatch(r'(\d{1,2})[.-](\d{1,2})[.-](\d{4})', line)
        if match:
            day, month, year = map(int, match.groups())
        else:
            match = re.fullmatch(r'(\d{1,2})\s+([^\W\d_]+)\s+(\d{4})', line)
            if match:
                day, name, year = match.groups()
                month = MONTH_MAP.get(name)
            else:
                match = re.fullmatch(r'([^\W\d_]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})', line)
                if match:
                    name, day, year = match.groups()
                    month = MONTH_MAP.get(name)
    try:
        return date(int(year), int(month), int(day))
    except (TypeError, ValueError):
        return None


def sections_from_markup(markup):
    if type(markup) is not str or len(markup) > source_limit():
        raise ProcessingBlocked('Note exceeds local source limit.')
    parser = PlainText()
    parser.feed(markup)
    parser.close()
    # Preserve paragraph boundaries before normalization; no raw fragments returned.
    lines = [line.strip() for line in ''.join(parser.parts).splitlines() if line.strip()]
    lines = [normalize_text(line) if len(line) <= MAX_TEXT else line for line in lines]
    plain = '\n'.join(lines)
    # Credential blocks can span arbitrarily many small sections. Handle their
    # delimiters across the whole local note before selecting an NLP window.
    begin = r'-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----'
    end = r'-----END (?:[A-Z]+ )?PRIVATE KEY-----'
    if len(re.findall(begin, plain)) != len(re.findall(end, plain)):
        raise ProcessingBlocked('Incomplete credential block in note.')
    plain = re.sub(begin + r'[\s\S]*?' + end, '[SECRET]', plain)
    if re.search(begin + '|' + end, plain):
        raise ProcessingBlocked('Invalid credential block in note.')
    lines = plain.splitlines()
    sections, dates, current, length, current_date = [], [], [], 0, None
    def flush():
        nonlocal current, length
        if current:
            sections.append('\n'.join(current))
            dates.append(current_date)
            current, length = [], 0
    for line in lines:
        # Overlong paragraphs remain opaque, so an unrelated one cannot block a
        # small requested section. A selected overlong paragraph fails closed.
        normalized = line
        found = heading_date(normalized) if len(normalized) < 100 else None
        if found or (current and length + len(normalized) + 1 > TARGET_SECTION):
            flush()
        if found:
            current_date = found
        current.append(normalized)
        length += len(normalized) + 1
    flush()
    return sections or [''], dates or [None]


def read_section(markup, redactor, *, view='start', section=0, offset=0,
                 max_chars=4_000, query=None):
    validate_selection(view, section, offset, max_chars, query)
    sections, dates = sections_from_markup(markup)
    if view == 'end':
        section = len(sections) - 1
    elif view == 'latest':
        candidates = [(value, -i, i) for i, value in enumerate(dates) if value is not None]
        if not candidates:
            return {'content': '', 'selection_status': 'no_recognized_date_heading',
                    'has_more': False, 'next': None}
        section = max(candidates)[2]
    elif view == 'query':
        terms = query.casefold().split()
        section = next((i for i, text in enumerate(sections)
                        if all(term in text.casefold() for term in terms)), -1)
        if section < 0:
            return {'content': '', 'selection_status': 'no_keyword_match',
                    'has_more': False, 'next': None}
    if section >= len(sections):
        raise AccessDenied('Invalid section request.')
    selected = sections[section]
    # Whole sections are masked BEFORE paging. Never redact isolated page slices.
    # Keep original paragraph context; do not cut long secrets at page boundaries.
    before = sections[section - 1] + '\n' if section else ''
    after = '\n' + sections[section + 1] if section + 1 < len(sections) else ''
    # Do not let an unrelated huge neighboring paragraph prevent a bounded read.
    # Omitting it would weaken boundary detection, so fail closed instead.
    window = before + selected + after
    if len(window) > MAX_TEXT:
        raise ProcessingBlocked('Selected context exceeds local analysis limit.')
    if window.count('-----BEGIN ') != window.count('-----END '):
        raise ProcessingBlocked('Incomplete credential block in selected context.')
    safe = redactor.sanitize_window(window, len(before), len(before) + len(selected))
    if type(safe) is not str or len(safe) > MAX_TEXT:
        raise ProcessingBlocked('Invalid redaction output.')
    if offset > len(safe):
        raise AccessDenied('Invalid page offset.')
    end = min(offset + max_chars, len(safe))
    continuation = ({'section': section, 'offset': end} if end < len(safe)
                    else {'section': section + 1, 'offset': 0} if section + 1 < len(sections) else None)
    # Pages must not split placeholder labels (including custom entity labels).
    if end < len(safe):
        start_marker = safe.rfind('[', offset, end)
        if start_marker >= offset and ']' not in safe[start_marker:end]:
            close = safe.find(']', end)
            if close >= 0 and close - start_marker < 100:
                end = start_marker
                continuation = {'section': section, 'offset': end}
    return {'content': safe[offset:end], 'selection_status':
            'latest_recognized_date_heading' if view == 'latest' else 'selected_section',
            'section': section, 'section_count': len(sections), 'offset': offset,
            'has_more': continuation is not None, 'next': continuation,
            'entry_continues': section + 1 < len(sections) and dates[section + 1] == dates[section]}
