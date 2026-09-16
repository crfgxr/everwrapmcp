# Baseline result — 2026-09-17

**Privacy-filter decision: do not enable automatic redacted output.** Read-only
OAuth and live retrieval are now verified separately. The user explicitly enabled
unredacted output for locally permitted notes; this is not a successful filter test.

Presidio 2.2.364, spaCy 3.8.16, en_core_web_lg 3.8.0, Python 3.12.13.
Exact package resolution is in uv.lock.

Four of ten synthetic checks passed: English person, email, Turkish phone removal,
and unchanged technical English text. Six failed: Turkish person, Turkish birthday,
OpenAI-style test key, password assignment, bearer value, password in connection URL.

The Turkish person example retained the surname Yılmaz. The birthday example
retained 14 Mart. All four synthetic credential values remained visible.
The English model also over-redacted Turkish non-sensitive words. Phone removal
passing does not mean the surrounding Turkish text was preserved correctly.

This is a tiny deliberately challenging corpus, not an estimate of population-wide
accuracy. Secret patterns use synthetic placeholders; tests of realistic formats,
obfuscation, and transformations remain necessary. This evaluates stock Presidio
with English NLP, not the custom recognizers proposed in the handoff and not a
Turkish NLP configuration.

Next experiment: add independent deterministic secret handling and suitable local
NLP for both English and Turkish. Evaluate contextual names, dates, birthdays,
and addresses in each language, using new held-out cases as well as regressions.
The passing English person example does not establish English privacy coverage.

## Integration checks — 2026-09-17

The latest focused suite passed 135 tests covering single-note and denylist
authorization, explicit block-list precedence, OAuth setup safeguards, upstream
argument mapping, response validation, policy reload, and the MCP boundary.
These tests use synthetic fixtures and do not validate production redaction.

Read-only OAuth completed and the official `get_note` input schema was inspected.
The local wrapper was registered with Codex. Calls through its exposed MCP tool
returned a privacy-gate error for the allowed dummy and a policy denial for an
excluded note. A fresh stdio process also verified the configured denial.
Those initial checks fetched no note content.

After explicit opt-in to denylist access and unredacted output, a fresh stdio
server verified a live read of the permitted synthetic dummy, a denial of the
blocked ID, and a keyword search returning a permitted result. The dummy response
structure was inspected locally to implement the parser. Raw content and private
note identifiers were not copied into code or reports. Search rows are filtered
locally before output; upstream search can supply blocked metadata to the local
wrapper, but the wrapper never requests a blocked note body.

The production sanitizer, exact-output review, and OS isolation remain
unimplemented. Static error and canary tests cover selected
leakage paths, not a complete logging-isolation guarantee. The six baseline
release-gate failures remain unresolved; the focused suite does not replace them.
