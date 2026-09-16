# Single-note test boundary

Only one dummy note is authorized for the first live test. Its identifier belongs
in the ignored `.everwrap-local.json`, not in source, fixtures, commits, or logs.
The first UUID following the shard in the supplied internal link is used as the
candidate note ID. No other identifier from the link is tried as a fallback.
This interpretation has not been verified by a live fetch.

Reference: https://dev.evernote.com/legacy/doc/articles/note_links

## Private local policy

The local file contains `allowed_note_id` and an optional `blocked_note_ids` list
of up to 16 UUIDs. Explicit denial wins even if a note is also the allowed note.
Every other note is denied by default. Both reads and searches enforce this
policy before fetching content. Restart the MCP connection after policy changes.

The actual block list and note links are private. Keep them out of Markdown,
fixtures, issues, screenshots, commits, and diagnostic output. The committed
`single-note.example.json` contains a placeholder and an empty block list only.
Before pushing, verify `.everwrap-local.json` is ignored and untracked; an ignore
rule cannot remove a file or identifier already committed to Git history.

## Verified with synthetic fixtures

- Unauthorized, wildcard, malformed, and multiple IDs cause zero backend calls.
- Missing or malformed policy fails closed; duplicate keys and overrides fail.
- Explicit blocks override the allowed ID in both read and search paths.
- A missing sanitizer causes zero backend calls, including for the allowed ID.
- With a test sanitizer, search fetches only the pinned ID, never upstream search.
- Arguments cannot override the policy or add notebook scope.
- Wrong upstream identity, malformed fields, and oversized content are blocked.
- Title, body, and snippet flow through the injected sanitizer.
- Backend and sanitizer exceptions are replaced with static, unchained errors.
- Only explicitly constructed output fields are returned.
- MCP exposes only the two wrapper tools and no resources or prompts.

The latest focused run passed 92 tests across policy/service, OAuth setup, and
MCP transport checks. The fake sanitizer only replaces a synthetic canary.
It is not a production redactor. The six PII/secret benchmark failures remain
blockers. Validate contextual names, dates, birthdays, and addresses independently
in both English and Turkish before enabling any production content output.

## Connection and callable-tool status

MCP SDK 2.2.0 and keyring 25.7.0 are installed locally. `everwrap.connect`
completed read-only OAuth and schema discovery, with Keychain storage and a
loopback callback. It does not read notes. The official read tool accepts
`get_note` with a `noteId` argument; it advertises no output schema, so the actual
response structure still needs local validation before an adapter is implemented.

The direct Codex Evernote MCP entry was removed. The local `everwrap` server is
registered, and its `read_safe_note` tool has been called from Codex:

- Allowed dummy: `Content blocked: privacy processing is not enabled or could not safely complete.`
- Excluded note: `Request denied by the local single-note policy.`

A fresh stdio process also confirmed policy denial after the local block list
was saved. These checks prove tool availability and blocking, not successful
note retrieval or filtering. No Evernote notes have been fetched by this project.
The wrapper cannot establish whether another application has direct access.

## Remaining live-test prerequisites

1. Implement the official direct-fetch adapter and validate its actual response
   locally. Do not invent field names or expose raw responses to the assistant.
2. Test the adapter's outbound method and ID allowlist against fake MCP responses.
3. Validate local English and Turkish privacy processing, deterministic secret
   blocking, and exact outbound review. Keep unvalidated output out of the cloud.
4. Fetch only the configured dummy for the authorized filtering test, then measure
   leaks and retained useful text. Never fetch another note to demonstrate denial.
5. Do not resolve links, retrieve attachments, search the account, or try fallback IDs.

The current server has no live backend or enabled sanitizer. This code is a
prototype application-level restriction, not an OS sandbox. It cannot constrain
an agent with write access to the code or separate access to backend credentials.
Runtime isolation remains a separate deployment task.
