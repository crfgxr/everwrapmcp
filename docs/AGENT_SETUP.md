# Agent-assisted setup

This guide is for a local coding agent helping a new user install EverWrapMCP. Read
[INSTALL.md](INSTALL.md) for commands and client configuration. Do not claim an
integration is verified until the target client actually calls the wrapper.

Use the [fictional onboarding and before/after examples](ONBOARDING.md#what-onboarding-looks-like)
to explain the experience. Example assistant answers are illustrations: never
report them as successful checks without actual tool evidence.

## Establish the environment

- Check macOS, repository access, Git, uv and the intended client. Only the Codex
  integration has been tested live in this project. Do not silently substitute
  another client or expose a public server to make an unsupported setup work.
- Use a stable checkout location chosen with the user's context. Record absolute
  paths for client registration. Do not put a checkout in a disposable temp folder.
- Inspect existing configuration before changing it. Merge the EverWrapMCP entry;
  preserve unrelated servers and never overwrite an existing private policy.
- The repository is public and its original code is MIT-licensed. It is still
  experimental; do not claim a packaged one-click release exists.

## Ask about note languages

Ask: “Which languages do your notes contain? Do you mix languages within a note?”
Offer English, Turkish, both, or another language as conversational answers.
Use an answer already supplied by the user; do not ask repeatedly. The answer
is a compatibility check, not a working configuration parameter.

Explain that this release installs both EN/TR models and routes text locally.
English-only and Turkish-only installation modes are not implemented. Do not add
an invented `languages` field to the strict policy JSON or tool arguments. Other
languages are not validated; offer synthetic testing and describe the gap rather
than claiming that Lingua's full language list is supported masking coverage.

A future language-pack setting should be installation/local policy configuration,
not a per-request tool argument that lets the assistant weaken protection. Mixed
notes should be routed automatically, and unsupported-language behavior must be
explicitly tested before a pack is released. Selection should govern validated
models and recognizers together, not merely the language identifier.

## Ask about blocked notes before broader access

Ask which notes must be excluded, using [the README link/ID instructions](ONBOARDING.md#choose-the-notes-to-block).
Offer internal links, exact UUIDs, or direct editing of the private local policy.
Never request the contents of an excluded note. If only a title is given, ask the
user to locate it in Evernote and copy its internal link; do not use account-wide
search or read candidates to identify the intended private note. Titles are not
supported block rules and may be duplicated.

Extract the first note UUID only from the documented internal-link format;
otherwise request an unambiguous ID. Validate and deduplicate locally, merge with
existing exclusions, and preserve the current access mode. Confirm configuration
without echoing private links unnecessarily. Do not broaden access with unresolved
exclusions, silently discard entries beyond the 16-ID limit, or infer an empty
block list from no response. A user can explicitly choose no exclusions.

## Install and configure

1. Follow the runtime commands in INSTALL.md, including requirements-live.txt and
   the explicit pinned Turkish model download. `uv sync` can remove the separately
   installed live dependencies; reinstall requirements-live.txt afterward.
2. For a new installation, request a synthetic Evernote note link/UUID. Use the
   first note UUID from its internal link. Keep it only in the ignored local
   policy. Start with single_note access and redacted content. Leave access
   disabled if required user input is missing; never substitute a real note.
3. Keep the policy file private (mode 600), ignored and untracked. Preserve any
   existing block list. Policy changes must reflect the user's requested scope;
   passing a test is not authorization to enable account-wide access.
4. Run the wrapper's read-only OAuth flow. The user completes the browser sign-in
   and consent. Do not request credentials in chat, copy tokens into configuration,
   or print Keychain contents. Never authenticate a direct Evernote connector as a
   fallback for the wrapper.
5. Register EverWrapMCP using the chosen client's instructions and absolute paths.
   Confirm which reload/restart action is available; do not invent an MCP restart
   command. If another direct Evernote route exists, explain that it bypasses the
   wrapper and help the user disable it within their authorized setup scope.

## Verify before calling setup complete

- Confirm tool discovery in the actual client: read_safe_note, search_safe_notes,
  semantic_search_safe_notes. Discovery alone does not prove OAuth or redaction.
- Read only the configured synthetic note. Include harmless text plus fictional
  names, an example.org email and a clearly synthetic secret. Confirm redacted
  mode, readable remainder and removal of those test values. Do not test with
  real credentials or real private contact information.
- Add a synthetic UUID to the new test policy's blocked list and verify a denied
  read. Do not fetch a real blocked note's body to prove it is blocked. Existing
  automated backend-spy tests check denial before an upstream fetch; a live error
  alone does not independently demonstrate that internal ordering.
- Single-note mode intentionally prevents account-wide search. Test search only
  after the user has chosen denylist access and their private exclusions. Do not
  weaken the policy to get a green search test.
- If models, authentication or processing fail, report the step and a safe error
  summary. Do not return raw notes, disable masking, empty the block list or switch
  to a direct Evernote tool. Keep sensitive exception text out of reports.

Report the installed location, client, tool availability, completed checks and
remaining user steps. Explain that masking is fallible, dates are masked by
default unless configured otherwise, and processed content reaches the AI
provider. Keep actual note IDs, note text and private policies out of commits,
issues and shared installation reports. Use the user's real-note scope only when
explicitly established; installation is not an account-wide retrieval request.

## Before promoting broader adoption

The project MIT license is in place. Review dependencies/model licenses;
review tracked files and Git history for private data; verify a fresh macOS
installation from the documented commands. Repository visibility is already public. Test other clients before promoting them as working integrations.
These release steps are not performed merely by following this setup guide.
