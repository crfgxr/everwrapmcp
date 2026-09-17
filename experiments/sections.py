"""Synthetic local timing comparison; no network or personal notes."""
import json
import time
from pathlib import Path

from everwrap.redaction import get_redactor
from everwrap.sections import read_section, sections_from_markup


def main():
    markup = '<en-note>' + ('<div>older notes about the chatbot architecture.</div>' * 8500) + (
        '<div>17 Eylül 2026</div><div>Email alex@example.com about the final prototype.</div></en-note>')
    start = time.perf_counter()
    redactor = get_redactor()
    load_seconds = time.perf_counter() - start
    start = time.perf_counter()
    sections, _ = sections_from_markup(markup)
    full = []
    for i, selected in enumerate(sections):
        before = sections[i - 1] + '\n' if i else ''
        after = '\n' + sections[i + 1] if i + 1 < len(sections) else ''
        full.append(redactor.sanitize_window(before + selected + after, len(before), len(before) + len(selected)))
    full_seconds = time.perf_counter() - start
    start = time.perf_counter()
    page = read_section(markup, redactor, view='latest')
    section_seconds = time.perf_counter() - start
    assert 'alex@example.com' not in page['content'] and 'final prototype' in page['content']
    report = {'synthetic': True, 'source_characters': len(markup), 'sections': len(sections),
              'model_load_seconds': round(load_seconds, 3),
              'full_local_masking_seconds': round(full_seconds, 3),
              'selected_local_masking_seconds': round(section_seconds, 3),
              'full_output_characters': sum(map(len, full)),
              'selected_output_characters': len(page['content']),
              'notes': 'Single warm-model comparison on this machine; excludes network. Character counts are not token counts.'}
    Path('docs/section-results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
