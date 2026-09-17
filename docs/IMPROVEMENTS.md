# Improvement priorities and open questions

Reviewed 2026-09-17. This is a backlog, not a claim that these features exist or
that all risks have been discovered. Keep private note content, identifiers,
block lists and credentials out of examples, telemetry and commits.

## Current evidence

Local English/Turkish routing and masking are implemented. The application suite
passed 260 tests, including the additional failure-handling checks.
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

- Language detection checks the broader Lingua set and withholds unsupported or
  uncertain units. Benchmark misclassification and false withholding, especially
  for short text; masking packs cover English, Turkish, Spanish, French and German.
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

### Latency experiments, in order

1. **Establish the breakdown:** measure connection/OAuth setup, Evernote search,
   local masking and serialization separately. Record cold/warm p50 and p95 over
   multiple runs, result sizes and failures. One slower first call does not prove
   model startup is the cause; network and authorization can dominate.
2. **Reuse expensive initialization:** models already stay loaded in the process.
   Measure remaining cold cost and evaluate safe warm-up without reading notes.
   Investigate upstream client/session reuse with proper expiry, cancellation and
   shutdown handling. Do not assume connection reuse is implemented already.
3. **Reduce repeated work:** evaluate the policy-aware memory cache described
   above for subsequent pages. Keep only necessary data for a short, bounded
   lifetime; caching raw note text increases exposure and must be assessed.
4. **Bound retrieval:** use snippets first and fetch full-note context only when
   necessary. Measure semantic over-fetch and candidate diversity before reducing
   candidates; fewer requests or shorter excerpts can also lose useful evidence.
5. **Batch local inference:** benchmark several small passages together and bound
   CPU concurrency. Preserve exact per-passage offsets, complete token coverage
   and block filtering before inference. Avoid oversubscribing the machine.
6. **Evaluate alternative runtimes only if inference dominates:** compare a
   smaller model, quantization or an optimized CPU runtime against the same held-out
   privacy/readability corpus. A faster model is unacceptable if it materially
   increases missed sensitive spans. Check new dependencies before adopting them.
7. **Keep the interaction responsive:** enforce stage timeouts and cancellation;
   report a static progress/error message without streaming unmasked text. Retries
   must be bounded and appropriate to the error, not repeat expensive work blindly.

Select targets after measuring the baseline. Report latency alongside retrieval
quality, missed-sensitive-span rate, false positives, memory and token estimates.
These are proposed experiments, not implemented speedups or guaranteed savings.

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

## Additional languages: proposed, not enabled

Lingua supports many languages, but this runtime provides packs for English, Turkish, Spanish, French and German. Expanding identification alone does not provide PII protection.
Each supported language needs an evaluated NER model or a validated multilingual
model, localized recognizers/context, mixed-language and unsupported-language
behavior, and held-out privacy/readability tests. Check licenses, dependencies,
install size, cold start and warm latency for each candidate.

Prefer opt-in language packs and incremental releases driven by users' languages.
Do not load ten large models for every user or claim a universal "top ten" without
defining the audience. Compare shared multilingual NER against separate models
on each language; an aggregate score can hide poor coverage in one language.
Unsupported or uncertain text must not silently be treated as reliably masked.
Five-language pack selection and broader language detection are implemented.
Unsupported or uncertain units are withheld. Expand independent evaluation of this
behavior before adding packs; confident misclassification remains possible.

Source: [Lingua language list](https://github.com/pemistahl/lingua-py#4-which-languages-are-supported).

## Future optional editing — not implemented

Current connections and exposed tools are read-only. A possible future editing
feature must be explicitly opted into, with separate write authorization rather
than silently upgrading an existing read-only connection. Before authorization,
warn that write access can modify notes and may overwrite or remove information.
Users should be able to continue using only read/search tools.

Before implementing writes, verify the official upstream tool and OAuth scopes.
Require a concrete change preview and user approval, enforce exclusions before
both reads and writes, detect concurrent edits, and provide a recovery strategy.
Never write masked placeholders back into the source note by accident. Do not
represent upstream edit capability as already supported by EverWrapMCP.
