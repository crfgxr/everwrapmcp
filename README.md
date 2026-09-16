# NoteVeil

A proposed local privacy boundary between Evernote and cloud assistants.

**Status: feasibility experiments only. No MCP server or Evernote connection exists yet.**

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
