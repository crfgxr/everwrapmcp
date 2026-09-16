# EverWrap

A local access-control wrapper for Evernote MCP, with ongoing privacy-filtering
experiments. Exposes only `read_safe_note` and `search_safe_notes` over stdio.

**Status: live read-only OAuth, note reads, and keyword searches work.** Content
is disabled by default. An explicit local opt-in enables **unredacted** text from
permitted notes. The tool names refer to access checks, not guaranteed PII removal.
English and Turkish privacy filtering is not ready; six baseline checks still fail.

## Access and content modes

Policy lives only in the ignored `.everwrap-local.json`:

- `access_mode: "single_note"` is the default. Only `allowed_note_id` is permitted.
- `access_mode: "denylist"` permits all IDs except those in `blocked_note_ids`.
- `blocked_note_ids` holds up to 16 UUIDs. Explicit denial always wins, including
  when a blocked ID is also the single allowed ID. UUIDs are case-insensitive.
- `content_mode: "blocked"` is the default and stops content calls before network
  access. `content_mode: "unredacted"` explicitly permits original note text,
  titles, and search snippets to reach the assistant without PII redaction.

Copy `single-note.example.json` to `.everwrap-local.json` and replace its placeholder
with a test-note UUID for the default single-note setup. To use denylist access,
edit the local file to set that access mode and populate its private block list;
`allowed_note_id` is optional and unused in denylist mode. Enabling denylist access
does not by itself enable content: unredacted output requires its separate opt-in.

The server reloads policy on every call and discards results if policy changes
while a request is running. Missing, malformed, or unsupported configuration fails
closed. Tool arguments cannot change either mode or the block list. After updating
the server code, restart the MCP connection to load the new implementation.

### What is blocked

Direct reads check local authorization before opening the upstream connection,
then verify the returned ID matches the requested ID. Search results are checked
by ID before titles, snippets, or timestamps are returned. Blocked note bodies are
never fetched. The official search API can return a blocked note's metadata and
snippet to the local wrapper; that entire row is discarded locally, not sent to
the assistant. This is a local policy, not a restriction on Evernote's OAuth grant.

Only selected fields are returned. No upstream errors, resource manifests, tags,
tasks, notebook metadata, or raw tool responses are forwarded. Links and attachments
are not followed. No write tools, semantic search, resources, or prompts are exposed.
Search uses Evernote keyword/search grammar, scans at most the first 100 hits,
returns at most 10 permitted rows, and uses UTC for relative date operators.

A development folder or same-user Keychain is not an OS-enforced security boundary.
This wrapper cannot constrain a separate direct connector or an agent with access
to modify its code/configuration or retrieve backend credentials. Note content is
untrusted data; access controls do not remove instructions embedded in a note.

## Keep the local policy private

The block list, actual note IDs, account links, and OAuth credentials must stay out
of source, documentation, fixtures, logs, issues, and commits. Commit only the empty
example and synthetic test IDs. `.everwrap-local.json` is Git-ignored; verify it is
also untracked before pushing because ignore rules do not remove existing history.
OAuth tokens and client registration are stored in macOS Keychain, never in the repo.

## Install and connect on macOS

```sh
uv sync
uv pip install --python .venv/bin/python -r requirements-live.txt
PYTHONPATH=src .venv/bin/python -m everwrap.connect
```

Configure the local policy before connecting. The setup command performs OAuth
and inspects `get_note` schema only; it does not read or search notes. Complete
sign-in in the browser. Consent and stored grants are restricted to `read`.
The callback binds to `127.0.0.1:8766`, with state, PKCE, and issuer validation.
If browser launch fails, the command prints a manual sign-in link. Do not share
callback URLs containing authorization codes. Credentials use macOS Keychain
service `EverWrap:official-evernote-mcp`.

SDK 2.2.0 replaces caller scopes during discovery, so a version-pinned hook
restores `read` before generating consent. Regression tests cover the behavior.
The live server uses the saved grant and can refresh it; when interactive sign-in
is needed, run the local setup command again. It does not expose OAuth flows as tools.

Evernote hosts its MCP at `https://mcp.evernote.com/mcp`; no upstream server binary
is required. Official instructions: https://dev.evernote.com/mcp

## Register the wrapper with Codex

From the repository root:

```sh
codex mcp add everwrap --env "PYTHONPATH=$PWD/src" -- "$PWD/.venv/bin/python" -m everwrap.server
```

This updates global Codex MCP configuration. Restart the MCP connection or Codex
to load changed server code. Keep the direct Evernote connector removed when the
wrapper is intended to be the only exposed note interface.

## Verification

```sh
.venv/bin/python -m pytest tests/test_single_note.py tests/test_connect.py tests/test_server.py tests/test_live.py -q
```

The latest focused run passed 135 tests. Live checks through a fresh stdio server
confirmed a permitted dummy read, a policy denial for a blocked ID, and a keyword
search returning a permitted hit. Live note text and private identifiers were not
copied into the repository or test reports. These results verify access controls
and transport, not successful redaction.

The runtime is pinned separately in `requirements-live.txt`. Reinstall it after
`uv sync`, which removes packages outside `uv.lock`. This split is temporary;
universal dependency resolution previously hit network and platform-metadata issues.

## Privacy-filtering experiment

Synthetic English and Turkish examples evaluate stock Presidio English NLP, secret
handling gaps, and technical-text preservation. Turkish examples are challenge
cases, not a claim that the English model supports Turkish.

```sh
uv run python -m experiments.baseline
uv run pytest tests/test_benchmark.py tests/test_release_gate.py
```

Inference runs locally; installation downloads public weights. The saved report
contains synthetic data only. Four of ten cases pass; six release-gate tests
intentionally fail on known leaks. Re-run the experiment after changing dependencies
or cases. Passing a small corpus would not prove general privacy.

Before enabling a redacted-output mode:

- Validate contextual names, dates, birthdays, and addresses independently in
  both English and Turkish, across titles, snippets, and bodies.
- Add deterministic secret handling, including encoded and obfuscated forms.
- Test metadata leakage, malformed responses, and sanitizer failures.
- Add local review of exact outbound text and enforce processing/output bounds.
- Deploy policy and credentials behind an OS-enforced runtime boundary.

Unredacted mode is an explicit alternative to that unfinished filter, not evidence
that these gates have been met. See `docs/RESULTS.md` and `docs/SINGLE_NOTE_TEST.md`.
