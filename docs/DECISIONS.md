# Initial assessment

The supplied handoff establishes the right boundary: upstream raw data is handled
locally, notebook authorization is repeated for reads, and only newly constructed
safe response objects reach MCP.

Changes needed before claiming its definition of done:

1. Detection success is not provable from absence of an exception. Undetected PII
   still exits a fail-closed-on-error filter. Evaluate leaks separately from errors.
2. Contextual names, dates, birthdays, and addresses need explicit coverage in
   both English and Turkish, including titles, snippets, and bodies.
3. Validate English and Turkish independently. Success in one language or on a
   single entity example is not evidence of coverage in the other language.
4. Revalidate notebook membership on the fetched note, not only a preliminary
   lookup, to cover a note moving between the two requests.
5. Never trust raw query operators to enforce notebook scope. Validate every
   returned item and verify direct IDs independently.
6. Bounds must apply before expensive processing and after safe serialization.
7. Titles, snippets, URLs, timestamps, identifiers, logs, errors, resources, and
   attachments are possible outbound channels. Disable unused MCP surfaces.
8. A writable development folder is not a security boundary. This unrestricted
   agent session cannot enforce the proposed production filesystem guarantees.
9. PII filtering does not remove malicious instructions from note text.
10. A local exact-output review stage is the conservative initial release gate.

## Implemented prototype decisions

- A local stdio MCP server exposes only `read_safe_note` and `search_safe_notes`.
  Live reads and keyword searches are implemented. The names refer to access
  controls; they do not promise PII redaction.
- Access defaults to one locally configured note. Explicit `denylist` mode allows
  all other IDs while enforcing the private block list. Denial always wins.
- Content defaults to `blocked`. Explicit local `unredacted` opt-in permits
  original text from allowed notes to reach the assistant. This user-authorized
  mode is separate from the unfinished privacy filter and makes no redaction claim.
- Direct IDs are authorized before network access and checked against response
  IDs. Upstream search rows are filtered locally before projecting permitted
  titles/snippets. Blocked metadata can reach the local process; it is discarded.
- Policy is reloaded on each call. A policy change while a request is in flight
  prevents returning its result. The configured modes cannot be tool arguments.
- Actual note IDs, account links, and the block list are private local data in
  the ignored `.everwrap-local.json`. Committed fixtures contain synthetic IDs;
  the committed example has an empty block list. Never publish the local policy.
- OAuth setup and tool-schema discovery succeeded with read-only consent. This
  does not authorize arbitrary note access or prove that filtering is ready.
- English and Turkish privacy validation, exact-output review, and OS-enforced
  runtime isolation remain unfinished. They are still requirements for a future
  redacted-output mode; enabling unredacted access does not satisfy them.

Sources: https://microsoft.github.io/presidio/ and
https://microsoft.github.io/presidio/installation/
