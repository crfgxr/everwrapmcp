# EverWrap

**Take control of your notes: block private notes and mask sensitive data.**

EverWrap gives you two controls over what your AI assistant receives from Evernote:
a private note block list and local masking of detected sensitive data.

**Private preview · macOS · read-only · experimental**

## The problem

Some notes should stay out of your AI conversations entirely. Others are useful
to share, but contain names, contact details, or secrets you want masked.

## The solution

EverWrap sits between your AI client and Evernote, applying two checks:

- **Block whole notes.** Your private block list excludes selected notes from returned reads and search results.
- **Mask sensitive parts.** For allowed notes, local Presidio processing replaces detected sensitive text in titles, bodies, and search snippets.

You get the remaining text to work with. Your original Evernote notes stay unchanged.

```text
Evernote → EverWrap on your Mac → your AI assistant
           block + mask
```

A synthetic example:

```text
Before: Talk to Alex Smith about the chatbot.
After:  Talk to [PERSON] about the chatbot.
```

**Masking is best-effort.** It can miss sensitive details or mask harmless words.
Processed text still goes to your AI provider. English NLP and extra English/Turkish
patterns are included; a full Turkish NLP model is not. [See the limits.](docs/REDACTION.md)

## What is Evernote MCP?

MCP stands for **Model Context Protocol**, a standard for connecting AI assistants
to tools and data. Evernote's official MCP server lets compatible assistants
search, read, and create notes through an OAuth connection. It is currently in beta.
[Read Evernote's official MCP guide.](https://dev.evernote.com/mcp)

EverWrap connects to that official server with read-only access and adds your
local block list and masking step before results reach the assistant.

## Install in your client

You'll need macOS, Git, [uv](https://docs.astral.sh/uv/getting-started/installation/),
and an Evernote account with MCP access. This repository is currently private;
cloning requires GitHub access.

```sh
git clone https://github.com/crfgxr/everwrap.git
cd everwrap
uv sync --python 3.12
uv pip install --python .venv/bin/python -r requirements-live.txt
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

> Use EverWrap to find my latest braindumping note and summarize it.

> Use EverWrap semantic search to find past notes about feeling stuck in a role
> that does not fit my strengths. Distinguish my own writing from saved articles.

Meaning-based search returns small masked passages before fetching full notes.
[Semantic search behavior and privacy limits.](docs/SEMANTIC_SEARCH.md)

EverWrap guides the client to use semantic search for themes and coaching,
keyword search for exact matches and filters, and direct reads for known notes
or their latest dated entries. It does not automatically run all three.
[Tool selection and examples.](docs/RETRIEVAL.md)

Start with the synthetic test note before expanding access. Connect **EverWrap**
and remove any direct Evernote connector if you want requests to use the wrapper.
Your private block list and OAuth credentials stay out of the repository.

## Where it stands

- **246 focused tests passed**, including semantic filtering, large-note paging, date preferences, and masking boundaries.
- Large notes are selected locally and returned as small masked pages. Ask for a
  recognized latest dated entry or a keyword-matching section without sending the
  whole journal to the model. [Large-note behavior and limits.](docs/LARGE_NOTES.md)
- **24/26 synthetic benchmark checks passed**; two harmless-text cases were over-masked.
- Blocked IDs are denied before full-note reads. Blocked search rows are discarded locally.

Independent prototype; not affiliated with Evernote. This is not an OS security sandbox.
[Results](docs/RESULTS.md) · [Redaction details](docs/REDACTION.md) · [Access policy and tests](docs/SINGLE_NOTE_TEST.md)
