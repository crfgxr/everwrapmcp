# EverWrapMCP

**Take control of your notes: block private notes and mask sensitive data.**

EverWrapMCP gives you two controls over what your AI assistant receives from Evernote:
a private note block list and local masking of detected sensitive data.

**Private preview · macOS · read-only · experimental**

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

A synthetic example:

```text
Before: Talk to Alex Smith about the chatbot.
After:  Talk to [PERSON] about the chatbot.
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
> Read README.md and docs/AGENT_SETUP.md first. Preserve my existing client
> configuration and any existing EverWrapMCP privacy policy. Start with a synthetic
> test note and masking enabled. Guide me through Evernote's read-only sign-in,
> register only the wrapper, and verify a permitted read and a blocked read.
> Tell me what passed and what still needs my input. Do not broaden note access
> or connect directly to Evernote to work around a failure.

**Today this is an agent-assisted experiment, not a one-click install.** The agent
needs access to this private repository, a local terminal on macOS, and a client
that supports local MCP tools. You supply a dummy note and complete OAuth in your
browser. A normal web chat cannot install software on your Mac from a repo link.
The ChatGPT tunnel route below is a separate, unverified advanced setup.

## Sharing status

The README and agent setup path are ready for collaborators to try. Public launch
still needs repository access to be opened deliberately and a clean-machine
onboarding test. The code is MIT-licensed; distribution is currently a private
preview. Only
Codex has live integration evidence; Claude and ChatGPT remain unverified here.
The privacy model is best-effort masking plus a local block list, not a guarantee
that every sensitive detail is removed. [Known gaps and priorities](docs/IMPROVEMENTS.md).

## Install in your client

You'll need macOS, Git, [uv](https://docs.astral.sh/uv/getting-started/installation/),
and an Evernote account with MCP access. This repository is currently private;
cloning requires GitHub access.

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

> Use EverWrapMCP to find my latest braindumping note and summarize it.

> Use EverWrapMCP semantic search to find past notes about feeling stuck in a role
> that does not fit my strengths. Distinguish my own writing from saved articles.

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

- **258 application tests passed**, followed by two additional failure-handling checks; the historical stock baseline is separate.
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
