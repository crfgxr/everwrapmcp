# EverWrap

A proposed local privacy boundary between Evernote and cloud assistants.

**Status: a local stdio MCP server exposes `read_safe_note` and `search_safe_notes`.
Content access deliberately fails closed: the privacy filter has known failures
and the live note-fetch adapter is not implemented. The macOS OAuth setup probe
has connected successfully and inspected the official read-tool schema without
reading notes.**

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

- Validate English and Turkish NLP, including contextual names, dates, birthdays, and addresses in both languages.
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
path. The MCP server loads this file from its repository root at startup.

An optional `blocked_note_ids` list explicitly denies up to 16 note UUIDs. Denial
wins even if an ID is also the allowed note, and applies to both reads and the
single-note search. IDs are case-insensitive. Keep this list in the ignored local
configuration; restart the MCP connection after policy edits. Other notes remain
denied by default whether or not they appear in the block list.

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
The MCP server exposes only the two safe methods, never the adapter.
This local policy is not an Evernote account permission and cannot restrict a
separate direct Evernote connector.

## Register the local wrapper with Codex

After installing the runtime below and configuring the dummy-note UUID, run from
the repository root:

```sh
codex mcp add everwrap --env "PYTHONPATH=$PWD/src" -- "$PWD/.venv/bin/python" -m everwrap.server
```

This changes the global Codex MCP configuration. Refresh the MCP connection or
restart Codex to load it into an existing session. Keep any direct Evernote MCP
connector removed if the wrapper is intended to be the only exposed note tool.

The server accepts strict tool arguments, returns static errors, and advertises
no resource or prompt access. Its production service currently has **no enabled
sanitizer or live backend**: calls cannot retrieve any note, including the allowed
dummy. Registration and a successful MCP handshake do not mean privacy filtering
or real note reads are ready. The existing six baseline release-gate failures
remain unresolved. View-only OAuth prevents writes under that grant; it does not
provide redaction or limit the grant to the dummy note.

## Connect the official Evernote MCP (macOS setup probe)

Evernote hosts the server at `https://mcp.evernote.com/mcp`; there is no Evernote
server binary to install. This optional command authenticates and inspects the
`get_note` schema. It **does not read, search, or modify notes**.

```sh
uv sync
uv pip install --python .venv/bin/python -r requirements-live.txt
PYTHONPATH=src .venv/bin/python -m everwrap.connect
```

Complete Evernote sign-in in the browser when it opens. The callback listener binds
only to `127.0.0.1:8766`; OAuth state, PKCE, and issuer checks are handled by the
SDK, with additional local callback validation. Tokens and client registration
are stored in the macOS Keychain under `EverWrap:official-evernote-mcp`, never in
the repository. This same-user Keychain storage is not isolation from an agent
with unrestricted access to your user account. The runtime isolation gate remains.

Consent is restricted to the `read` scope. Broader token grants are rejected.
SDK 2.2.0 replaces caller scopes during discovery, so a pinned authorization hook
restores `read` immediately before generating consent. A regression test covers
that behavior. If browser launch fails, the command prints the same sign-in link
for manual use on this Mac. Never share the callback URL containing the code.

Run the focused tests with:

```sh
.venv/bin/python -m pytest tests/test_single_note.py tests/test_connect.py tests/test_server.py -q
```

The optional runtime is pinned separately in `requirements-live.txt`; run its
install command again after `uv sync`, which removes packages outside `uv.lock`.
The dependency split is temporary: universal lock resolution was blocked by
network timeouts and uncached Windows metadata during setup.

Official instructions: https://dev.evernote.com/mcp
