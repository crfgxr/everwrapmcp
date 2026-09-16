"""Locally configured reads with access checks and optional Presidio redaction.

Search responses may contain blocked metadata/snippets locally. Those rows are
dropped before projection; their note bodies are never fetched. Redacted mode
processes every returned text field without falling back to raw text on errors.
"""

import asyncio
from pathlib import Path

from .policy import AccessDenied, SingleNotePolicy, canonical_note_id
from .service import ProcessingBlocked
from .upstream import OfficialBackend


def bounded_text(value, limit, nullable=False):
    if nullable and value is None:
        return None
    if type(value) is not str or len(value) > limit:
        raise ProcessingBlocked("Invalid upstream text.")
    return value


def structured(result):
    # Never fall back to upstream text/error/resource content.
    if result.is_error or type(result.structured_content) is not dict:
        raise ProcessingBlocked("Invalid upstream response.")
    return result.structured_content


class NoteService:
    def __init__(self, policy, backend, redactor=None):
        self.policy = policy
        self.backend = backend
        self.redactor = redactor

    def require_opt_in(self):
        if self.policy.content_mode not in ("unredacted", "redacted"):
            raise ProcessingBlocked("Content output is not enabled.")
        if self.policy.content_mode == "redacted" and self.redactor is None:
            raise ProcessingBlocked("Redaction is unavailable.")

    async def text_field(self, value, limit, nullable=False, markup=False):
        value = bounded_text(value, limit, nullable)
        if value is None or self.policy.content_mode != "redacted":
            return value
        method = self.redactor.sanitize_markup if markup else self.redactor.sanitize_text
        output = await asyncio.to_thread(method, value)
        return bounded_text(output, limit)

    async def read_safe_note(self, note_id):
        authorized = self.policy.authorize(note_id)
        self.require_opt_in()
        data = structured(await self.backend.get_note(authorized))
        returned_id = self.policy.authorize(data.get("id"))
        if returned_id != authorized:
            raise ProcessingBlocked("Unexpected upstream identity.")
        return {
            "id": authorized,
            "title": await self.text_field(data.get("title"), 1000),
            "content": await self.text_field(data.get("content"), 100_000, markup=True),
            "content_format": "plain_text" if self.policy.content_mode == "redacted" else "enml",
            "content_mode": self.policy.content_mode,
        }

    async def search_safe_notes(self, query, sort="updated_desc", limit=5):
        if (type(query) is not str or not 1 <= len(query) <= 500 or not query.strip()
                or type(limit) is not int or not 1 <= limit <= 10
                or sort not in ("updated_desc", "updated_asc", "relevance")):
            raise AccessDenied("Invalid search request.")
        self.require_opt_in()
        if self.policy.access_mode == "single_note":
            note = await self.read_safe_note(self.policy.allowed_note_id)
            text = (note["title"] + "\n" + note["content"]).casefold()
            return ([{"id": note["id"], "title": note["title"], "snippet": note["content"][:300],
                      "content_mode": self.policy.content_mode}]
                    if all(word in text for word in query.casefold().split()) else [])

        results = []
        seen = set()
        # A bounded scan of the first 100 hits. Do not expose upstream totals,
        # blocked IDs, blocked titles, blocked snippets, or raw pagination data.
        for start in range(0, 100, 20):
            page = structured(await self.backend.search_notes(query, sort, start, 20))
            hits = page.get("hits")
            if type(hits) is not list or len(hits) > 20 or type(page.get("isLastPage")) is not bool:
                raise ProcessingBlocked("Invalid search response.")
            for hit in hits:
                if type(hit) is not dict:
                    raise ProcessingBlocked("Invalid search hit.")
                identity = canonical_note_id(hit.get("noteId"))
                try:
                    self.policy.authorize(identity)
                except AccessDenied:
                    continue  # No other fields from this row are inspected or returned.
                if identity in seen:
                    continue
                seen.add(identity)
                projected = {
                    "id": identity, "title": await self.text_field(hit.get("title"), 1000),
                    "snippet": await self.text_field(hit.get("snippet"), 5000, nullable=True, markup=True),
                    "content_mode": self.policy.content_mode,
                }
                # Keep sorted order, but do not leak date metadata in redacted mode.
                if self.policy.content_mode == "unredacted":
                    projected.update({
                        "created_at": bounded_text(hit.get("createdAt"), 100, nullable=True),
                        "updated_at": bounded_text(hit.get("updatedAt"), 100, nullable=True),
                    })
                results.append(projected)
                if len(results) == limit:
                    return results
            if page["isLastPage"] or not hits:
                break
        return results


# Compatibility for the original access-control regression tests.
UnredactedNoteService = NoteService


class ConfiguredService:
    """Reload local policy per call; fail if it changes while a call is in flight."""

    def __init__(self, path: Path, backend_factory=OfficialBackend, redactor_factory=None):
        self.path = path
        self.backend_factory = backend_factory
        self.redactor_factory = redactor_factory

    async def _run(self, operation, **arguments):
        policy = SingleNotePolicy.from_file(self.path)
        if operation == "read_safe_note":
            policy.authorize(arguments["note_id"])
        redactor = None
        if policy.content_mode == "redacted":
            from .redaction import get_redactor
            redactor = await asyncio.to_thread(self.redactor_factory or get_redactor)
        service = NoteService(policy, self.backend_factory(policy), redactor)
        result = await getattr(service, operation)(**arguments)
        if SingleNotePolicy.from_file(self.path) != policy:
            raise ProcessingBlocked("Local policy changed during processing.")
        return result

    async def read_safe_note(self, note_id):
        return await self._run("read_safe_note", note_id=note_id)

    async def search_safe_notes(self, query, sort="updated_desc", limit=5):
        return await self._run("search_safe_notes", query=query, sort=sort, limit=limit)
