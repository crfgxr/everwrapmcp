"""Minimal stdio MCP boundary. Production content access is deliberately closed."""

import asyncio
import json
import logging
from pathlib import Path

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from .policy import AccessDenied, SingleNotePolicy
from .service import ProcessingBlocked, SingleNoteService


class DisabledBackend:
    async def get_note(self, note_id: str):
        raise ProcessingBlocked("Live note retrieval is not enabled.")


def build_server(service: SingleNoteService) -> Server:
    annotations = types.ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, idempotentHint=True,
        openWorldHint=False,
    )
    tools = [
        types.Tool(
            name="read_safe_note",
            description=("Read the single locally allowed test note through the privacy gate. "
                         "Content access is currently blocked pending privacy validation."),
            inputSchema={
                "type": "object", "additionalProperties": False,
                "properties": {"note_id": {"type": "string", "minLength": 36, "maxLength": 36}},
                "required": ["note_id"],
            },
            annotations=annotations,
        ),
        types.Tool(
            name="search_safe_notes",
            description=("Search only the single locally allowed test note after privacy processing. "
                         "Never searches the account. Content access is currently blocked."),
            inputSchema={
                "type": "object", "additionalProperties": False,
                "properties": {
                    "query": {"type": "string", "minLength": 1, "maxLength": 500},
                    "sort": {"type": "string", "enum": ["updated_desc", "updated_asc", "relevance"], "default": "updated_desc"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
                },
                "required": ["query"],
            },
            annotations=annotations,
        ),
    ]

    async def list_tools(context, params):
        return types.ListToolsResult(tools=tools)

    async def call_tool(context, params):
        # Validate again at dispatch: schema hints alone do not enforce policy.
        # Never return upstream exceptions, request arguments, or tracebacks.
        error = None
        try:
            args = params.arguments
            if type(args) is not dict:
                raise AccessDenied()
            if params.name == "read_safe_note" and set(args) == {"note_id"}:
                safe = await service.read_safe_note(args["note_id"])
            elif (params.name == "search_safe_notes" and "query" in args
                  and set(args) <= {"query", "sort", "limit"}):
                safe = {"notes": await service.search_safe_notes(**args)}
            else:
                raise AccessDenied()
            encoded = json.dumps(safe, ensure_ascii=False)
        except AccessDenied:
            error = "Request denied by the local single-note policy."
        except ProcessingBlocked:
            error = "Content blocked: privacy processing is not enabled or could not safely complete."
        except Exception:
            error = "Request could not be safely processed."
        if error is not None:
            return types.CallToolResult(content=[types.TextContent(text=error)], isError=True)
        return types.CallToolResult(
            content=[types.TextContent(text=encoded)], structuredContent=safe,
        )

    return Server(
        "everwrap", version="0.0.1",
        instructions=("Only the configured dummy note is permitted. Privacy processing is "
                      "not ready, so content calls currently fail closed. No raw Evernote tools are exposed."),
        on_list_tools=list_tools, on_call_tool=call_tool,
    )


async def serve():
    root = Path(__file__).resolve().parents[2]
    policy = SingleNotePolicy.from_file(root / ".everwrap-local.json")
    server = build_server(SingleNoteService(policy, DisabledBackend(), sanitizer=None))
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())


def main():
    # stdout belongs exclusively to MCP. Avoid SDK diagnostics containing payloads.
    logging.disable(logging.CRITICAL)
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    except Exception:
        import sys
        print("EverWrap could not start safely. Check local configuration and runtime.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
