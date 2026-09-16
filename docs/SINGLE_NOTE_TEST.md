# Note access tests

## Private local policy

The original live test allowed only one synthetic dummy note. Its UUID was derived
from the first UUID following the shard in its Evernote internal link. A live read
of that dummy now verified the direct-fetch parser. Other UUIDs in a link are not
tried as fallbacks.

Reference: https://dev.evernote.com/legacy/doc/articles/note_links

The wrapper now supports two explicit access modes:

- `single_note`: only the locally configured `allowed_note_id` is permitted.
- `denylist`: all note IDs are permitted except `blocked_note_ids`.

Denial takes precedence in both modes. The block list allows up to 16 UUIDs and
remains in the ignored `.everwrap-local.json`. Actual IDs and note links must not
appear in fixtures, Markdown, logs, screenshots, issues, or commits. The committed
example contains a placeholder and an empty block list only.

Content is independently controlled by `content_mode`: `blocked` by default,
`unredacted` only with explicit local opt-in. The latter returns original text from
permitted notes without PII filtering. The latest local configuration change was
explicitly authorized by the user; committed defaults remain closed.

## Verified with synthetic fixtures

The latest focused suite passed 135 tests across policy/service, OAuth setup,
MCP boundaries, live-adapter argument mapping, and unredacted-mode handling:

- Malformed and blocked direct IDs cause zero backend calls.
- Explicit denial overrides an allow entry; UUID case cannot bypass the block.
- Missing, malformed, unsupported, or duplicate-key policy fails closed.
- Default blocked content mode prevents network access, including permitted IDs.
- Single-note mode never performs upstream account search.
- Denylist search discards blocked rows before projecting any title or snippet.
- Search pagination and result limits are bounded; raw totals are not forwarded.
- Tool arguments cannot override policy, output mode, or upstream method names.
- Reads reject mismatched upstream identity, malformed fields, and oversized text.
- Unselected upstream fields, error text, and resources do not reach MCP output.
- Policy reload takes effect on the next call; a change during a call blocks output.
- Only the two wrapper tools are exposed, without prompts or resources.

Legacy sanitizer tests use a synthetic canary replacement, not a production
redactor. No sanitization is claimed for unredacted mode. English and Turkish
contextual names, dates, birthdays, and addresses still require independent
privacy validation; six baseline release-gate failures remain unresolved.

## Connection and live checks

Read-only OAuth completed, with Keychain storage and a loopback callback.
The official `get_note` accepts `noteId` and returns note fields in structured
content; the parser selects only a matching `id`, `title`, and ENML `content`.
The official `search_notes` returns structured `hits`, checked by `noteId` before
projecting permitted titles, snippets, and timestamps. Upstream schemas were
inspected rather than guessed. API reference: https://dev.evernote.com/mcp/tools

Initial Codex tool calls confirmed that the closed gate and single-note restriction
blocked output. After explicit authorization for denylist/unredacted mode, a fresh
stdio process verified:

- The blocked ID returns `Request denied by the local note access policy.`
- The permitted dummy is fetched and returned with `content_mode: "unredacted"`.
- A keyword search succeeds and its returned rows exclude blocked IDs.

Live verification reports contain status and field names only, not note text or
private identifiers. The direct Evernote connector stays removed. An existing
Codex process must reload the updated MCP server before using its new behavior.

## Boundaries and remaining work

The wrapper never requests a blocked note body. Upstream search can return blocked
metadata/snippets to the local process, where the whole row is discarded before
cloud output. This does not restrict the upstream OAuth grant itself or prevent
a separate client from accessing the same account.

There is no write access, attachment retrieval, link following, semantic search,
or alternate-ID fallback. Searches scan up to 100 hits and return at most 10
permitted rows. Relative-date queries use UTC. Very large notes fail output bounds.

Production PII filtering, exact-output review, and OS isolation remain unfinished.
This application-level policy cannot constrain an agent that can edit its code or
configuration, or access backend credentials independently.
