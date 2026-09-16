# Single-note test boundary

Only one dummy note is authorized for the first live test. Its identifier belongs
in the ignored `.everwrap-local.json`, not in source, fixtures, commits, or logs.
The first UUID following the shard in the supplied internal link is used as the
candidate note ID. No other identifier from the link is tried as a fallback.
This interpretation has not been verified by a live fetch.

Reference: https://dev.evernote.com/legacy/doc/articles/note_links

## Verified with synthetic fixtures

- Unauthorized, wildcard, malformed, and multiple IDs cause zero backend calls.
- Missing or malformed policy fails closed; duplicate keys and overrides fail.
- A missing sanitizer causes zero backend calls, including for the allowed ID.
- Search always fetches only the pinned ID, never upstream search.
- Arguments cannot override the policy or add notebook scope.
- Wrong upstream identity, malformed fields, and oversized content are blocked.
- Title, body, and snippet flow through the injected sanitizer.
- Backend and sanitizer exceptions are replaced with static, unchained errors.
- Only explicitly constructed output fields are returned.

54 focused tests passed. The fake sanitizer only replaces a synthetic canary.
It is not a production redactor. Earlier PII benchmark failures remain blockers.

## Live test prerequisites

1. Connect the local wrapper process to the official upstream MCP using OAuth.
2. Inspect the upstream tool schema without reading notes. Implement its actual
   direct-fetch arguments and response parser; do not invent field names.
3. Test the adapter's outbound method and ID allowlist against fake MCP responses.
4. Apply a real local sanitizer; keep unvalidated output out of the cloud assistant.
   The synthetic note can be inspected locally for the requested filtering test.
5. Fetch exactly the configured note, then measure leaks and retained useful text.
6. Reject all other requested IDs locally; never fetch another note to demonstrate
   that access is denied. Do not resolve links or retrieve attachments.

The current session has no callable Evernote connector. The inspected user Codex
MCP configuration has no Evernote server. This does not establish whether Evernote
is connected in another app. No Evernote notes have been fetched by this project.

## Connection setup status

The user confirmed there was no existing installation. MCP SDK 2.2.0 and keyring
25.7.0 are now installed locally. `everwrap.connect` performs OAuth and schema
discovery only, with Keychain storage and a loopback callback. It has no note-read
method. The 54 policy tests plus 14 setup tests pass (68 total).

The live setup attempt did not complete. Independent HTTPS checks to PyPI,
GitHub, and `mcp.evernote.com:443` timed out from the local shell. No successful
OAuth exchange, live tool schema, or live note read has been verified. Retry the
documented setup command once local connectivity is restored.

Later setup check: the direct Codex `evernote_mcp` entry was removed, and its
unfinished login process was cancelled. The endpoint became reachable. The
wrapper then blocked SDK scope discovery widening `read` to all advertised
scopes; this is fixed with a version-pinned scope constraint and grant validation.
80 focused tests now pass. An EverWrap-specific read-only consent link has been
generated. Authentication is not complete until the callback and token exchange
succeed; generating a consent link does not establish note access.

This code is a prototype application-level restriction. It is not an OS sandbox,
and it cannot constrain an agent with write access to the code or separate access
to backend credentials. Runtime isolation remains a separate deployment task.
