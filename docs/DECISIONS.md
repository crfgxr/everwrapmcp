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
  It has been registered with Codex and called successfully, returning static
  blocking errors. Production content processing remains disabled.
- The test policy allows one locally configured dummy note. An explicit block
  list takes precedence over that allowance, for both reads and searches.
- Actual note IDs, account links, and the block list are private local data in
  the ignored `.everwrap-local.json`. Committed fixtures contain synthetic IDs;
  the committed example has an empty block list. Never publish the local policy.
- OAuth setup and tool-schema discovery succeeded with read-only consent. This
  does not authorize arbitrary note access or prove that filtering is ready.
- The live note adapter, English and Turkish privacy validation, exact-output
  review, and OS-enforced runtime isolation remain unfinished. The wrapper
  therefore denies content access before any upstream note fetch.

Sources: https://microsoft.github.io/presidio/ and
https://microsoft.github.io/presidio/installation/
