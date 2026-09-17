# EverWrap

**Ask AI about your Evernote notes. Choose what it can read.**

A small local wrapper that blocks selected notes and masks detected sensitive text
before returning results to your AI assistant.

**Private preview · macOS · read-only · experimental**

## The problem

Your Evernote account holds useful ideas alongside personal details. You want AI
to help with the ideas, without manually cleaning every note or sharing everything.

## The solution

EverWrap sits between your AI client and Evernote:

- **Choose the notes.** Start with one test note, or allow your notes except a private block list.
- **Mask detected details.** Local Presidio processing covers titles, note bodies, and search snippets.
- **Keep originals intact.** The wrapper searches and reads; it cannot edit your notes.

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

Start with the synthetic test note before expanding access. Connect **EverWrap**
and remove any direct Evernote connector if you want requests to use the wrapper.
Your private block list and OAuth credentials stay out of the repository.

## Where it stands

- **183 focused tests passed**, plus a live dummy-note read with masking applied.
- **24/26 synthetic benchmark checks passed**; two harmless-text cases were over-masked.
- Blocked IDs are denied before full-note reads. Blocked search rows are discarded locally.

Independent prototype; not affiliated with Evernote. This is not an OS security sandbox.
[Results](docs/RESULTS.md) · [Redaction details](docs/REDACTION.md) · [Access policy and tests](docs/SINGLE_NOTE_TEST.md)
