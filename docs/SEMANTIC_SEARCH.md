# Meaning-based search through EverWrap MCP

`semantic_search_safe_notes` uses Evernote's own semantic search to retrieve
related passages without downloading complete notes. It returns a bounded set
of masked snippets and routing IDs, not an answer, a graph, or a complete history.

Example: ask EverWrap MCP to find past notes about feeling stuck in a role that does
not fit your strengths. Different wording and languages can produce different
results. Relevant saved articles are not necessarily your own experiences.

Both personal writing and saved references belong in problem-solving results.
Use personal entries to understand the situation, goals, and past attempts; use
saved material to propose relevant methods, alternatives, and decision steps.
Connect the two with source references. The distinction guides interpretation,
not exclusion: saving an article does not prove agreement with it or that its
author's experience happened to the user. If provenance is unclear, say so.

## Tool contract

Arguments: `query` (1–500 nonblank characters), `limit` (1–10, default 3).
The local policy must be `access_mode: "denylist"` and `content_mode: "redacted"`.
Single-note mode and unredacted/disabled modes cannot invoke account-wide semantic
search. No tool argument can override the local policy or masking preference.

The wrapper requests up to three times the requested result count, capped at 50,
with keyword fallback disabled. It filters explicit blocks by canonical note ID
before inspecting a row's score or passage. It validates permitted candidates,
sorts them by score, and keeps the highest-scoring passage for each distinct note.
It then masks the entire selected passage locally before limiting the output to
800 characters. Default output is at most 2,400 snippet characters, plus metadata.

Each result contains `id`, `score`, `snippet`, `snippet_truncated`, and
`content_mode: "redacted"`. The response declares
`coverage: "bounded_semantic_candidates"`. Raw hit maps, blocked IDs, other
upstream metadata, and upstream errors are never forwarded. A result ID can be
used with `read_safe_note` for more context; there is no automatic full-note fetch.

Operational bounds: at most 250 upstream passage rows, 50 entries in the ignored
raw hit map, 100,000 characters in any permitted passage, and 1,000,000 total
permitted passage characters per response. Malformed/oversized data or redaction
failure blocks the response. These are wrapper resource limits, not documented
Evernote limits. Local policy is rechecked before returning any output.

The `mask_dates` preference applies. Dates remain visible when it is false;
other detected types remain masked. Snippets can contain titles, notebook labels,
or OCR-derived text embedded by Evernote: all returned text passes through the
same sanitizer. The wrapper does not request attachments separately.

## Quality and privacy boundaries

- A relevance score is not confidence that a statement is true or autobiographical.
  Identify personal writing versus saved articles before making personal inferences.
- Use exact keyword search for notebook/tag/date constraints; this tool exposes no
  structured filtering or pagination because the verified upstream schema has none.
- Candidate limits, deduplication, and block filtering can return fewer notes than
  requested. No automatic repeated search attempts to fill the result list.
- Snippet truncation is explicit. Do not treat a partial passage as a complete entry.
- Semantic indexing can lag edits. Dates within an entry differ from note metadata.
- English and Turkish live queries both returned results; that is a smoke test,
  not a measured cross-language relevance benchmark. Turkish text may be heavily
  over-masked by the current English NLP model and bilingual heuristics.
- The block list controls export through EverWrap MCP. Evernote may already index
  blocked notes on its own servers; local filtering cannot undo that indexing.
- Detection remains best-effort. No raw fallback, graph, or persistent note index
  is introduced by this feature.

Restart the MCP connection/client after updating to load the new tool schema.

## References and verification

The live MCP schema was inspected without reading notes. It exposes a natural
language query, result limit (up to 50), time zone, and keyword-fallback option.
Its response contains a hit-score map plus passages with note IDs and scores.

- [Evernote MCP tools](https://dev.evernote.com/mcp/tools)
- [Semantic search help](https://help.evernote.com/hc/en-us/articles/45706285591955-Semantic-search)
- [Engineering explanation](https://bendingspoons.com/blog/building-semantic-search-9-billion-notes)

Run `.venv/bin/python -m pytest tests/test_semantic.py tests/test_server.py -q`.
Tests use synthetic IDs and text, including blocked canaries, malformed responses,
masking failures, date preferences, mode restrictions, and policy revocation.
The historical stock-redaction release-gate failures are separate and unchanged.
