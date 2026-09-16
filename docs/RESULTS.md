# Baseline result — 2026-09-17

**Decision: do not connect real notes.**

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

Next experiment: add independent deterministic secret handling and select a local
Turkish-capable NLP model, then evaluate new held-out cases as well as regressions.
Authorization, MCP transport, upstream integration, logging isolation, and OS
isolation are unimplemented and untested. No real Evernote data was accessed.
