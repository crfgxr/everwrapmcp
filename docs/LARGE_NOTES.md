# Large notes: local selection, bounded masked output

EverWrap-MCP previously rejected note bodies above 100,000 characters, including
formatting. That arbitrary whole-note bound is replaced in **redacted mode** by
local section selection and masked pages. The block list always wins, before fetch.

## Alternatives considered

| Approach | Local work | Text returned to the client | Decision |
| --- | --- | --- | --- |
| Mask every section of every requested note | NLP over the whole note, even for one entry | Entire masked note unless separately paged | Useful for complete exports; unnecessary work for focused questions |
| Select locally, then mask selected context | Parse the note; NLP over the selected section and neighboring sections | A bounded masked page | Default for lower latency and less model input |

Selection is deterministic local code, not a cloud model, embedding service, or
LLM summary. The official upstream get-note call still downloads the complete
permitted note into the local wrapper. This change reduces local NLP work and
outbound text; it does not eliminate Evernote network latency or guarantee a
particular token count. The model is loaded once per server process. There is no
persistent note cache, raw-text log, or local index.

## Usage

`read_safe_note` retains its name. With only `note_id`, redacted mode now returns
the first page, not the complete note. Check `has_more` and `next`.

- `view: "start"` (default): select `section` (default 0).
- `view: "end"`: select the last section; this is not necessarily the latest entry.
- `view: "latest"`: select the beginning of the newest recognized dated entry.
- With `view: "latest"`, optional `year` restricts selection to that calendar year.
  No matching heading returns the explicit empty-result status; other years are
  never used as a fallback.
- `view: "query"`, `query: "prototype architecture"`: first section containing all
  whitespace-separated keywords, case-insensitively. This is not semantic search.
- `max_chars`: output body budget, default 4,000, allowed range 256–16,000.
- `offset`: offset within the masked section, for continuation.

Follow `next.section` and `next.offset` with `view: "start"`. Every call fetches
current content, so editing the note between calls may shift pagination. Pages
are slices of **already masked text**, not separately redacted raw fragments.
Placeholder labels are kept whole. `entry_continues` says whether the following
section carries the same recognized date; `has_more` can also refer to older or
otherwise unrelated sections. Neither field proves the entire journal was read.

Date selection recognizes standalone headings with an explicit year: ISO-style
year-month-day, dotted/hyphenated day-month-year, and English/Turkish month names.
Ambiguous day/month slash dates, yearless headings, and dates embedded in prose
are not selected. `latest_recognized_date_heading` deliberately means the latest
**recognized heading**, not a guarantee about every date format in the note.
No heading or no keyword match returns an explicit empty-result status. Dates
are masked by default; the local `mask_dates: false` preference preserves detected
dates and times in text. Raw dates are not returned as separate metadata.

## Resource and privacy boundaries

- Default source ceiling: 5,000,000 characters of markup, checked before parsing.
  Operators can set local environment variable `EVERWRAP_MAX_SOURCE_CHARS` between
  100,000 and 20,000,000. This is an operational choice, not an Evernote limit or
  an established security standard. Larger values need local performance testing.
- Sections target 8,000 characters and preserve paragraphs and date headings.
  A long paragraph stays whole. The selected section plus its immediate neighbors
  must fit a 100,000-character local analysis window; otherwise the read fails
  closed. The old number now bounds an NLP operation, not an entire journal.
- Neighboring context participates in detection. Detected spans crossing the
  selected boundary are clipped only after detection and masked in the selection.
  Private-key blocks are masked across the entire local note before section selection; incomplete markers fail closed. Arbitrarily long dependencies
  and unfamiliar formats can still exceed recognizer coverage.
- Policy is checked before fetch and again before returning. No selection argument
  can change the block list or turn masking off. Detector failure never returns raw text.
- Explicit unredacted mode retains its original whole-note bounds; section options
  are rejected in that mode. Search results remain masked snippets. Single-note
  search currently matches the first returned page, not the entire long note.

These bounds are configurable/tested operational defaults, not a promise that
PII detection is complete. See [redaction limits](REDACTION.md), especially the
English model's Turkish false positives and missed-entity risks.

## Reproducible comparison

Run `.venv/bin/python -m pytest tests/test_sections.py -q` for synthetic access,
large-note, date, paging, and cross-boundary credential checks.

Run `PYTHONPATH=src .venv/bin/python -m experiments.sections` for the synthetic
whole-note versus selected-section timing comparison. Results are saved in
[section-results.json](section-results.json). This is one local warm-model run,
not a universal latency benchmark. Startup and Evernote network time are excluded;
model load time is reported separately. Output character counts are measured;
model-token counts are not.

After updating an installation, restart its EverWrap-MCP connection/client so
it loads the new tool schema and server code.
