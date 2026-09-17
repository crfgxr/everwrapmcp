# Choosing the right retrieval tool

EverWrap exposes three tools. Their descriptions and MCP server instructions
explain which to choose; the client model makes the decision. There is no hidden
server-side classifier, automatic fan-out, or promise that every client obeys
these instructions. Access control and masking are enforced in server code.

| User intent | Starting tool | Follow-up only if needed |
| --- | --- | --- |
| Related experiences, recurring themes, coaching, possible approaches | `semantic_search_safe_notes` | Read the most useful permitted matches when snippets lack context |
| Exact phrase, known title, tag, notebook, or structured date constraints | `search_safe_notes` | Read selected matches |
| A known note or its newest recognized dated entry | `read_safe_note` (with `view: "latest"` for the entry) | Continue that entry only if its page is incomplete |
| Explicit test of a named tool | The requested tool, within local policy | Explain separately if another tool is needed to answer accurately |

For an unknown journal with a known title, start with keyword/title search, then
read its dated entry. For a semantic-search test involving that journal, use
semantic search first and then the dated reader: that proves the semantic tool
was exercised without pretending its relevance score establishes chronology.

Note modification order, semantic relevance, and dates written inside notes are
three different signals. Preserve requested year restrictions explicitly. Latest
means the newest recognized date heading within that selection, not an exhaustive
claim about every date format or event in the account.

## Personal problem-solving workflow

Start with one focused semantic query and the default three masked snippets.
Use both personal reflections and saved references: one provides personal
context, the other can provide useful methods and alternatives. Saving an article
does not mean endorsing its claims or having its author's experiences. Label
uncertain provenance and tie suggestions to sources rather than inventing
connections. Search again only when specific evidence is missing; do not call
all tools automatically for every question.

For full read bounds see [large notes](LARGE_NOTES.md), and for snippet limits,
privacy, indexing lag, and incomplete coverage see [semantic search](SEMANTIC_SEARCH.md).
Reload the MCP connection after updating to load the revised tool guidance.

## What tests establish

Protocol and privacy tests establish that only allowed tool calls reach their
backends, blocked content is excluded, and errors do not fall back to raw text.
A live semantic-first followed by dated-read smoke test establishes that the
workflow works. Neither proves reliable autonomous tool choice by every client;
that requires a separate model/client evaluation with recorded tool traces.
