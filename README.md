# EverWrapMCP

**Block private Evernote notes. Mask sensitive details. Keep the useful context.**

Some notes should never reach your AI assistant. Others are useful, but contain
names, contact details or secrets. EverWrapMCP adds a private block list and local
masking between Evernote and your assistant. Your original notes stay unchanged.

**Public experiment · macOS · read-only · 5 note languages · MIT code**

```text
Evernote → EverWrapMCP on your Mac → your AI assistant
                 block + mask
```

It connects to [Evernote’s official MCP server](https://dev.evernote.com/mcp).
MCP is the protocol that lets an AI assistant use external tools and data.

## See the difference

Fictional example, checked with the local redactor:

| Original note | What your assistant receives |
| --- | --- |
| Talk to Alex Smith about the community garden. | Talk to [PERSON] about the community garden. |
| Email alex@example.org. | Email [REDACTED]. |
| password=synthetic-demo-only-927 | [SECRET] |
| Bring seeds and a notebook. | Bring seeds and a notebook. |

Illustrative conversation after connecting your test note:

> **You:** What should I bring to the garden?
>
> **Assistant:** Seeds and a notebook.

For a blocked note, the wrapper denies access and returns no content.
[More fictional prompts, answers and masking examples](docs/ONBOARDING.md#example-prompts-and-answers).

## Get started

You need a Mac, an Evernote account with MCP access, and a compatible client.
**Codex is not required**, but it is the only client tested live with this project.

| Client | Setup and status |
| --- | --- |
| Codex | [Local setup](docs/INSTALL.md#codex) · live tested |
| Claude Desktop / Claude Code | [Desktop](docs/INSTALL.md#claude-desktop) / [Code](docs/INSTALL.md#claude-code) · documented, not live tested |
| ChatGPT cloud chat | [Private tunnel setup](docs/INSTALL.md#chatgpt) · advanced, not live tested |

## Follow the installation guide

**[Open the step-by-step installation guide →](docs/INSTALL.md)**

Install the wrapper, choose your private exclusions, sign in to Evernote, and
connect your client.

Or give a coding agent with local terminal access this setup request:

> Help me install https://github.com/crfgxr/everwrapmcp. Follow docs/AGENT_SETUP.md.
> Ask about my client, note languages and notes to block. Preserve existing settings,
> start with a fictional test note and masking enabled, and guide me through
> read-only Evernote sign-in. Verify the connection before claiming it works.

A repository link alone does not connect an ordinary web chat to your notes.
[Understand the client options](docs/CLIENT_COMPATIBILITY.md).

## What setup asks you

1. **Your app and note languages.** Choose any combination of **English, Turkish, Spanish, French, and German**. Setup installs and tests the selected masking packs; routing is automatic during use.
   Other languages need additional models, rules and validation. Unsupported or
   uncertain passages are withheld; language detection is not a privacy guarantee.
   [Language packs and coverage](docs/ONBOARDING.md#adding-another-language).
2. **A fictional test note.** Start with access to just that note.
3. **Which notes to block.** Provide internal note links or IDs, not their contents.
4. **Read-only sign-in.** Complete Evernote authorization in your browser.
5. **A read and a denial test.** Broader access is your choice after testing.

On Mac, select a note and look under **Note → Copy internal link** in the menu bar,
or use **Control + Option + Command + C**. Menu placement varies by version.
Titles alone cannot enforce a block; the current list supports up to 16 note IDs.
[How to find IDs and configure exclusions](docs/ONBOARDING.md#choose-the-notes-to-block).

<details>
<summary>Example onboarding conversation</summary>

| Agent asks | Fictional user response |
| --- | --- |
| Which client and note languages do you use? | Codex on Mac; English and Turkish. |
| Which notes must stay out of AI results? | My Private demo note. I’ll supply its internal link. |
| Shall we keep initial access limited to the Garden demo note? | Yes. |

The user completes browser sign-in; the agent reports actual test results.
[Complete walkthrough and dummy note](docs/ONBOARDING.md).

</details>

## Know the limits

Masking is **best-effort**: it can miss sensitive details or mask harmless words.
Processed text reaches your AI provider. A separate direct Evernote connection
bypasses the wrapper. Keep note IDs, credentials and your block list private.
Model wheels are third-party downloads and were not assessed by the advisory scan;
use the pinned official sources. [Model warnings and licenses](docs/LANGUAGE_PACKS.md).

This is an experiment, not a security sandbox or a one-click product. A fresh-Mac
onboarding test and live verification of other clients remain outstanding.
[Privacy details](docs/REDACTION.md) · [Known gaps](docs/IMPROVEMENTS.md)

## For contributors

[Documentation index](docs/README.md) · [Development and test results](docs/RESULTS.md)

Internal Python module and MCP registration names remain `everwrap` for
compatibility. Existing installations do not need their folders renamed.

## License

[MIT](LICENSE) for this project’s original code and documentation. Third-party
packages and models retain their own licenses. Independent project; not affiliated
with Evernote.
