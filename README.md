# EverWrapMCP

**Take control of your notes: block private notes and mask sensitive data.**

EverWrapMCP gives you two controls over what your AI assistant receives from Evernote:
a private note block list and local masking of detected sensitive data.

**Public experiment · MIT licensed · macOS · read-only**

## The problem

Some notes should stay out of your AI conversations entirely. Others are useful
to share, but contain names, contact details, or secrets you want masked.

## The solution

EverWrapMCP sits between your AI client and Evernote, applying two checks:

- **Block whole notes.** Your private block list excludes selected notes from returned reads and search results.
- **Mask sensitive parts.** For allowed notes, local Presidio processing replaces detected sensitive text in titles, bodies, and search snippets.

You get the remaining text to work with. Your original Evernote notes stay unchanged.

```text
Evernote → EverWrapMCP on your Mac → your AI assistant
           block + mask
```

**Masking is best-effort.** It can miss sensitive details or mask harmless words.
Processed text still goes to your AI provider. Local language routing selects English
or Turkish name detection, alongside shared sensitive-data rules. [See the limits.](docs/REDACTION.md)

## What is Evernote MCP?

MCP stands for **Model Context Protocol**, a standard for connecting AI assistants
to tools and data. Evernote's official MCP server lets compatible assistants
search, read, and create notes through an OAuth connection. It is currently in beta.
[Read Evernote's official MCP guide.](https://dev.evernote.com/mcp)

EverWrapMCP connects to that official server with read-only access and adds your
local block list and masking step before results reach the assistant.

## Do I need Codex?

**No.** EverWrapMCP is an MCP wrapper, not a Codex-only feature. Claude Desktop can
use local MCP servers; ChatGPT cloud chat needs a separate tunnel or remote
connection. Only Codex has been tested live with EverWrapMCP so far. Giving a regular
chat the GitHub URL does not install or connect it.
[ChatGPT vs Claude vs Codex: setup paths and evidence](docs/CLIENT_COMPATIBILITY.md).

## Let your coding agent set it up

Give an agent with local terminal access this prompt:

> Help me install EverWrapMCP from https://github.com/crfgxr/everwrapmcp on my Mac.
> Read README.md and docs/AGENT_SETUP.md first. Ask which languages my notes
> contain, including mixed-language notes, and explain current coverage. Preserve my existing client
> configuration and any existing EverWrapMCP privacy policy. Start with a synthetic
> test note and masking enabled. Guide me through Evernote's read-only sign-in,
> register only the wrapper, and verify a permitted read and a blocked read.
> Tell me what passed and what still needs my input. Do not broaden note access
> or connect directly to Evernote to work around a failure.

**Today this is an agent-assisted experiment, not a one-click install.** The agent
needs a local terminal on macOS and a client
that supports local MCP tools. You supply a dummy note and complete OAuth in your
browser. A normal web chat cannot install software on your Mac from a repo link.
The ChatGPT tunnel route below is a separate, unverified advanced setup.

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
exclusions should be an explicit user choice. [Policy setup](docs/INSTALL.md#allow-more-notes).

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

A Turkish example, also checked locally:

```text
Original: Bugün Ayşe Yılmaz ile konuştum.
          Yarın bahçeye tohum götüreceğim.

Masked:   Bugün [PERSON] ile konuştum.
          Yarın bahçeye tohum götüreceğim.
```

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

## Sharing status

The repository is public and MIT-licensed. Anyone can read or clone it; this is
still an experimental project. A clean-machine onboarding test remains outstanding.
Only Codex has live integration evidence; Claude and ChatGPT remain unverified here.
The privacy model is best-effort masking plus a local block list, not a guarantee
that every sensitive detail is removed. [Known gaps and priorities](docs/IMPROVEMENTS.md).

## Install in your client

You'll need macOS, Git, [uv](https://docs.astral.sh/uv/getting-started/installation/),
and an Evernote account with MCP access. The public repository can be cloned
without collaborator access.

```sh
git clone https://github.com/crfgxr/everwrapmcp.git
cd everwrapmcp
uv sync --python 3.12
uv pip install --python .venv/bin/python -r requirements-live.txt
PYTHONPATH=src .venv/bin/python -m everwrap.language
```

Next, [configure a test note and sign in to Evernote](docs/INSTALL.md#configure-and-sign-in),
then connect your client:

| Client | Setup |
| --- | --- |
| Claude Desktop on macOS | [Local MCP configuration](docs/INSTALL.md#claude-desktop) |
| Claude Code on macOS | [One registration command](docs/INSTALL.md#claude-code) |
| ChatGPT | [Secure MCP Tunnel guide](docs/INSTALL.md#chatgpt) — advanced; not yet tested here |
| Codex | [Local MCP setup](docs/INSTALL.md#codex) — verified in this project |

Claude and ChatGPT instructions are documentation-checked; only Codex has been
tested end-to-end here. [Full installation guide →](docs/INSTALL.md)

## Try it

> Use EverWrapMCP to read the latest dated entry in my garden journal.

> Find notes about keeping a community garden organized. Distinguish my own
> observations from saved reference articles.

Meaning-based search returns small masked passages before fetching full notes.
[Semantic search behavior and privacy limits.](docs/SEMANTIC_SEARCH.md)

EverWrapMCP guides the client to use semantic search for themes and coaching,
keyword search for exact matches and filters, and direct reads for known notes
or their latest dated entries. It does not automatically run all three.
[Tool selection and examples.](docs/RETRIEVAL.md)

Start with the synthetic test note before expanding access. Connect **EverWrapMCP**
and remove any direct Evernote connector if you want requests to use the wrapper.
Your private block list and OAuth credentials stay out of the repository.

## Where it stands

- **260 application tests passed**; the historical stock baseline is separate.
- Large notes are selected locally and returned as small masked pages. Ask for a
  recognized latest dated entry or a keyword-matching section without sending the
  whole journal to the model. [Large-note behavior and limits.](docs/LARGE_NOTES.md)
- **25/26 synthetic benchmark checks passed**; one harmless-code case was over-masked.
- Blocked IDs are denied before full-note reads. Blocked search rows are discarded locally.

Independent prototype; not affiliated with Evernote. This is not an OS security sandbox.
[Results](docs/RESULTS.md) · [Redaction details](docs/REDACTION.md) · [Access policy and tests](docs/SINGLE_NOTE_TEST.md)

[Improvement priorities, duplication, and open questions](docs/IMPROVEMENTS.md).

The product and repository are named **EverWrapMCP** (`everwrapmcp`). The Python
module and MCP registration key remain `everwrap` for compatibility with existing
installations. Existing checkout folders do not need to be renamed.

## License

EverWrapMCP’s original code and documentation are available under the [MIT License](LICENSE).
You may use, modify and redistribute them, including commercially, while retaining
the license notice. Third-party packages and model weights retain their own licenses;
Evernote service access is separate.
