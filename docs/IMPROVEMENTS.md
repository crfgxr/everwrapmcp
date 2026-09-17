# Improvement priorities and open questions

Reviewed 2026-09-17. This is a backlog, not a claim that these features exist or
that all risks have been discovered. Keep private note content, identifiers,
block lists and credentials out of examples, telemetry and commits.

## Current evidence

Local English/Turkish routing and masking are implemented. The application suite
passed 258 tests, followed by two additional passing failure-handling checks.
The final targeted language suite passed 14 tests. The separate historical stock
baseline still has six known failures; it is not the production redactor.
The synthetic masking report passes 25/26 cases; the remaining utility failure
masks `asyncio`. A live semantic-search repeat showed more readable Turkish
snippets with redacted mode enabled. This establishes a useful improvement, not
complete privacy coverage or consistently good retrieval.

## First priorities

| Priority | Gap or observation | Next improvement | Evidence needed before declaring success |
| --- | --- | --- | --- |
| 1 | Masking can miss sensitive spans and over-mask ordinary text; number placeholders can appear in article identifiers. | Expand independent EN/TR fixtures and make phone recognition contextual. Preserve secret detection and block-first behavior. | Per-entity precision and recall, readability and adversarial tests; validate phone/date/identifier distinctions without exposing actual numbers. |
| 1 | Repeated OAuth authorization has interrupted reads. The cause is not established. | Investigate persisted token expiry, refresh after expiry/401, concurrent refresh and revoked consent. | Controlled expiry/restart tests and safe error categories; never log tokens or authorization URLs. |
| 1 | A running MCP process retained old masking behavior until the connection restarted. | Add non-sensitive runtime version/model revision diagnostics. Investigate a supported reconnect or a stable server with a replaceable worker. | Verify an update is active without fetching notes; test in-flight requests, worker crashes and fail-closed recovery. No unauthenticated remote restart endpoint. |
| 2 | Current token estimates use a proxy tokenizer and incomplete accounting. | Measure real client-visible input/output where available, separating schemas, snippets, history and reasoning. | Reproducible per-query measurements, explicit tokenizer and scope; do not present character counts as tokens or estimates as billing. |
| 2 | Notes are fetched again for each page. | Evaluate a bounded in-memory cache tied to source version and policy fingerprint. | Lower repeated-page latency without stale authorization; immediate policy recheck, invalidation on block-list/masking changes and bounded retention. |
| 2 | Semantic candidates are bounded and can be only loosely related. | Add an evaluation set of natural questions and expected evidence, covering both languages and paraphrases. | Relevance and coverage judged separately from masking; useful personal and reference results, with abstention when evidence is weak. |

## Duplication: three separate questions

1. **Output representation:** MCP results may include the same payload in text
   `content` and `structuredContent`. Both were visible in tool responses. Whether
   the client puts both into model context is **unverified**. Measure before
   removing either representation; preserve compatibility with supported clients.
2. **Repeated work:** Page reads can refetch the same upstream note and repeat
   detection. Overlapping detection windows are intentional protection against
   boundary misses; optimize repeated work without removing that protection.
3. **Repeated evidence:** Semantic search already returns one best chunk per
   distinct note ID. It does not detect duplicate articles across different IDs.
   Conversely, one chunk per note can hide several relevant experiences in a long
   journal. Consider diverse passages with a strict total response budget, and
   source-aware deduplication that retains citations.

## Language and masking blind spots to test

- Language detection is restricted to English/Turkish. Other languages are not
  supported merely because the detector chooses one of those two.
- Mixed languages within one sentence, very short titles, names shared between
  languages, Turkish suffixes, missing diacritics, lowercase names and misspellings.
- Names split across markup, paragraphs or token windows; unusual addresses,
  international phone formats, financial/government identifiers and obfuscation.
- Model confidence is not a calibrated probability of privacy. Raising a global
  threshold can reveal genuine sensitive values while leaving some false positives.
- A name detector does not hide every sensitive life event, relationship or
  health-related statement. Define the intended categories before expanding
  masking; do not silently change the user's date/time preference.
- Failures must block output: missing/corrupt models, invalid offsets, resource
  exhaustion, cancellation, concurrent calls and policy edits during inference.
- Use a held-out evaluation set rather than only fixtures used to tune rules.
  Document tradeoffs instead of promising zero leakage.

## Retrieval and reasoning gaps

- Preserve explicit user requests about which tool to test. Current routing is
  client guidance, not a server-side natural-language routing engine.
- Keep personal reflections and saved references together when useful, but label
  their provenance. Saving an article does not establish agreement or lived
  experience. Mixed notes may need passage-level attribution, not a single label.
- Return source references and clear excerpt boundaries. Some upstream passages
  begin mid-sentence and outputs are truncated; avoid presenting them as full entries.
- Distinguish a dated heading, last edit time and event time. Latest within a known
  journal is not latest across the account. Test malformed, ambiguous and future dates.
- Semantic indexing delay and note synchronization are different possible causes
  of stale results; investigate rather than assume either one.
- Preserve contradictory and changing views across time. Coaching suggestions
  should cite supporting passages and distinguish observations from inference.
- Test prompt injection in retrieved content. Masking sensitive spans does not
  neutralize instructions embedded in a note or saved article.

## Performance and observability

Measure cold initialization and warm inference separately, as well as upstream
latency, parsing, detection, response size, memory and concurrent load. The short
synthetic warm timing is not an end-to-end performance promise. Bound parallelism
and retries, and use aggregate timings/counts without retaining source text or
private IDs. Avoid automatic fan-out across every retrieval tool.

## Dependency and deployment gaps

The dated [dependency audit](DEPENDENCY_SECURITY.md) covers the installed macOS
Python environment, with an explicit English-model-wheel exclusion. It does not
certify model weights or every platform dependency. Improve artifact verification,
license inventory, update policy and repeatable advisory scanning. Keep immutable
model revisions, safetensors-only loading, no remote model code and no runtime
downloads. Test clean installation, rollback, offline startup and supported client
compatibility; documentation alone does not verify a client integration.

The wrapper is a boundary for its own tools, not an OS sandbox. A separately
connected raw Evernote integration or other access route can bypass it. Account
permissions, local policy file access and client setup are separate controls.
Search block filtering protects what reaches the client; it does not prevent
Evernote from indexing or internally searching blocked material.

## Later: local index or graph

No local graph, persistent note index or automatic cross-note memory exists yet.
First measure whether semantic retrieval plus bounded reads meets the actual
questions. If gaps remain, compare a local text/vector index with a graph using
the same evaluation set and total maintenance cost. Any persistent derived data
needs access enforcement, deletion/block propagation, source-version tracking,
retention rules and protection against stale facts. Graph links and summaries can
leak information even when the original note is no longer returned. Do not create
an account-wide index as an implicit performance optimization.
