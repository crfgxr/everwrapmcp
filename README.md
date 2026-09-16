# EverWrap

A proposed local privacy boundary between Evernote and cloud assistants.

**Status: filtering experiments and a tested single-note service prototype.
No MCP server or live Evernote connection exists yet.**

The architecture should enforce notebook access in code, construct minimal responses,
filter titles and snippets as well as bodies, and fail closed on processing errors.
Automatic PII detection is not a privacy guarantee. A separate OS-enforced runtime
boundary is needed; placing code in another folder does not prevent agent bypass.

## First experiment

Synthetic English and Turkish examples measure the stock Presidio English model,
secret detection gaps, and preservation of technical text. Turkish cases are a
challenge set, not a claim that the English model supports Turkish.

```sh
uv sync
uv run python -m experiments.baseline
uv run pytest
```

Model installation downloads public weights. Inference runs locally. No real notes
are used. `docs/baseline-results.json` contains synthetic data only. The release-gate tests intentionally fail when the baseline leaks an expected
sensitive value or changes the utility control. They check the saved report; rerun
the experiment before pytest after changing dependencies or cases. Passing this
small corpus would not prove general privacy.

## Gates before integration

- Validate Turkish NLP and contextual names, dates, birthdays, addresses.
- Add deterministic secret blocking, including encoded/obfuscated variants.
- Test unauthorized direct IDs, untrusted search results, membership changes,
  malformed responses, sanitizer errors, metadata leakage, and log leakage.
- Enforce input/output bounds and treat note instructions as untrusted content.
- Test review of exact outbound content locally, outside the cloud assistant.
- Inspect actual upstream capabilities without retrieving real notes.
- Deploy policy/credentials beyond the assistant's filesystem permissions;
  remove direct backend access only after reviewing exact configuration changes.

Do not use this prototype to protect real personal data.

## Single-note integration test preparation

The service prototype permits exactly one locally configured UUID. Both reads and
searches are restricted to that note; searches filter its sanitized text locally
and never invoke an upstream account-wide search. Invalid or unauthorized IDs are
rejected before backend access. The service also rejects unexpected response IDs.

Copy `single-note.example.json` to `.everwrap-local.json` and replace the placeholder
with the dummy note's UUID. The local file is Git-ignored; never commit account or
note identifiers. `SingleNotePolicy.from_file` validates an explicitly supplied
path. It does not automatically load this file or alter any app's configuration.

```sh
.venv/bin/python -m pytest tests/test_single_note.py -q
```

These tests use fake backend responses and a canary-replacement test double. They
verify access controls and response handling, **not PII-detection quality**. Without
an explicitly supplied sanitizer the service blocks even the allowed note before
fetching it. The baseline privacy failures remain unresolved.

The next step is a local adapter to the official Evernote MCP, authenticated with
OAuth in the wrapper process. It must perform only the exact requested note fetch,
without link following, attachment downloads, broad searches, or fallback IDs.
The future MCP server must expose only the two safe methods, never the adapter.
This local policy is not an Evernote account permission and cannot restrict a
separate direct Evernote connector. No global configuration has been changed.
