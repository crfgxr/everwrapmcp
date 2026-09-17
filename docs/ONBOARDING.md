# Onboarding walkthrough

[Back to the overview](../README.md) · [Installation](INSTALL.md)

## What onboarding looks like

This is an example conversation, not an automated setup wizard. All note content
below is invented; none comes from a user's notes.

| Step | Your setup agent asks or explains | Example response |
| --- | --- | --- |
| Choose a client | “Which app will you use, and are you on macOS?” | “Claude Desktop on my Mac.” The agent explains that this path is documented but not live verified here. |
| Check languages | “Which languages are your notes in? Do you mix them?” | “English and Turkish, sometimes together.” Both models are installed in this release. |
| Start small | “Create a note called Garden demo using the fictional text below, then give me its internal note link.” | The agent configures access to that test note only, with masking enabled. |
| Choose exclusions | “Which notes should always be blocked? Supply their internal links or note IDs; no note contents are needed.” | “Block my fictional Private demo note.” A title alone needs its exact ID before the agent can confirm the block. |
| Connect | “Complete Evernote's read-only sign-in in your browser.” | You approve the connection yourself; you never paste a password or token into chat. |
| Test | “Let's check a permitted read and a synthetic blocked ID.” | The agent reports what actually passed, or the specific step still incomplete. |
| Choose wider access later | “Would you like to keep test-note-only access, or configure access to other notes with your private exclusions?” | “Keep test-note-only for now.” Nothing is broadened automatically. |

The agent should reuse answers you already supplied. If your client or language
is unsupported, it should explain that before claiming setup is complete.

## Choose the notes to block

Before enabling access beyond the test note, your setup agent should ask:

> “Which notes must stay out of AI results? Give their internal Evernote links or
> note IDs, or add them directly to the private local policy if you prefer not to
> put identifiers in chat. You don't need to share their contents.”

On Evernote for Mac:

1. Select the note you want to block.
2. In the macOS menu bar at the top of the screen, look under **Note → Copy internal link**.
   Menu placement can vary by version; do not rely on the right-click menu alone.
3. Alternatively, use **Control + Option + Command + C**, the documented internal-link shortcut.
4. Paste the link into your private setup conversation or local policy workflow—not
   a public issue. You do not need to make the note public.

Evernote also documents **Copy internal link** in the note's three-dot menu;
use whichever location your version exposes. The menu-bar route above reflects
the Mac workflow reported during this project's testing; the official references
confirm the shortcut and three-dot alternative.
[Note links](https://help.evernote.com/hc/en-us/articles/208313588-Note-links) ·
[Evernote's three-dot-menu instructions](https://help.evernote.com/hc/en-us/articles/360001858027-What-to-do-if-some-of-your-content-is-missing).

An internal link has this shape (placeholders only):

```text
evernote:///view/ACCOUNT/SHARD/NOTE_GUID/OTHER_GUID
```

The note ID is **NOTE_GUID**, the first UUID after the shard. The setup agent
extracts and validates it, then saves that ID in `blocked_note_ids` in the ignored
`.everwrap-local.json`. The MCP read tool accepts the UUID, not the full link.
If a link has another shape, do not guess the ID or open the note to inspect its
contents; ask for the internal link or the exact note UUID.

**A title is not a block rule.** If you only know the name, find that note in
Evernote yourself and copy its internal link. Duplicate titles are possible.
The agent should not search your private note contents to resolve a note you
want excluded, and must not claim the block is saved until its ID is configured.

The current block list supports **up to 16 note IDs**. A block wins over an allow.
If your exclusions are unresolved or exceed that limit, keep test-note-only
access; do not silently omit entries or enable broader access. Choosing no
exclusions should be an explicit user choice. [Policy setup](INSTALL.md#allow-more-notes).

## A fictional note, before and after masking

**Original text without masking** — copy this into your `Garden demo` test note:

```text
Talk to Alex Smith about the community garden.
Email alex@example.org.
password=synthetic-demo-only-927
Bring seeds and a notebook.
```

**Masked text returned by the current local redactor:**

```text
Talk to [PERSON] about the community garden.
Email [REDACTED].
[SECRET]
Bring seeds and a notebook.
```

This synthetic transformation was checked locally. `[REDACTED]` can mean
recognizers overlap; placeholder labels are not always `[EMAIL_ADDRESS]`.
The original note stays unchanged. “Without masking” above is a comparison, not
an onboarding step that disables protection. No real secret is needed for testing.

The examples here are in English. **Masking currently supports English and
Turkish**, with local language detection; mixed-language notes are included in
our tests. Additional languages require validated models and rules and are not
yet supported. [Language coverage](#which-languages-are-covered).

## Example prompts and answers

These assistant answers are illustrative, not guaranteed wording or transcripts
of a live client test. The assistant must base its answer on actual tool results.

**Read your configured test note**

> You: Read my configured Garden demo note through EverWrapMCP. What should I bring?
>
> Assistant: Seeds and a notebook. The note also mentions a person and contact
> details that were masked.

**Ask for something that was masked**

> You: What email address does the Garden demo note contain?
>
> Assistant: The returned text masks it, so I can't provide the address.

**Try a blocked note** — use a synthetic blocked UUID in the initial test:

> You: Read this blocked test note through EverWrapMCP.
>
> Assistant: The wrapper denied access. No note content was returned.

The assistant should not suggest removing the block or using a direct connector
to complete that request. It cannot change policy through the read tool.

**Find related ideas** — only after you deliberately enable denylist access:

> You: Find up to three notes about organizing a community garden.
>
> Assistant: I found a planting checklist and a saved article about seed sharing.
> Here's a short summary of each, with source references.

That last answer assumes those fictional results actually exist. With no matching
results, the assistant should say so. Account-wide search is unavailable in the
initial single-note mode.

## Which languages are covered?

During setup, your agent should ask: **“Which languages do your notes contain?
Do you mix languages within a note?”** This is about the notes, not the language
you use to chat with your assistant.

The current release installs **English and Turkish together** and detects which
to use locally. You do not have to choose a language for every search. There is
no configurable language-pack selector yet; answering the setup question does
not change the installed models or guarantee protection in other languages.

If your notes include another language, the agent should explain that its masking
has not been validated and should not enable broader access on the assumption
that language identification is enough. Keep initial testing to a synthetic note.
Optional, separately validated language packs are a planned improvement.

