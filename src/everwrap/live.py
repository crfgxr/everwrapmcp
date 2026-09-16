"""Explicitly opted-in unredacted reads, with local note access checks.

Search responses may contain blocked metadata/snippets locally. Those rows are
dropped before projection; their note bodies are never fetched. No sanitization
claim is made. Raw exceptions and unselected upstream fields never leave here.
"""

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


class UnredactedNoteService:
    def __init__(self, policy, backend):
        self.policy = policy
        self.backend = backend

    def require_opt_in(self):
        if self.policy.content_mode != "unredacted":
            raise ProcessingBlocked("Unredacted output is not enabled.")

    async def read_safe_note(self, note_id):
        authorized = self.policy.authorize(note_id)
        self.require_opt_in()
        data = structured(await self.backend.get_note(authorized))
        returned_id = self.policy.authorize(data.get("id"))
        if returned_id != authorized:
            raise ProcessingBlocked("Unexpected upstream identity.")
        return {
            "id": authorized,
            "title": bounded_text(data.get("title"), 1000),
            "content": bounded_text(data.get("content"), 100_000),
            "content_format": "enml", "content_mode": "unredacted",
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
                      "content_mode": "unredacted"}]
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
                results.append({
                    "id": identity, "title": bounded_text(hit.get("title"), 1000),
                    "snippet": bounded_text(hit.get("snippet"), 5000, nullable=True),
                    "created_at": bounded_text(hit.get("createdAt"), 100, nullable=True),
                    "updated_at": bounded_text(hit.get("updatedAt"), 100, nullable=True),
                    "content_mode": "unredacted",
                })
                if len(results) == limit:
                    return results
            if page["isLastPage"] or not hits:
                break
        return results


class ConfiguredService:
    """Reload local policy per call; fail if it changes while a call is in flight."""

    def __init__(self, path: Path, backend_factory=OfficialBackend):
        self.path = path
        self.backend_factory = backend_factory

    async def _run(self, operation, **arguments):
        policy = SingleNotePolicy.from_file(self.path)
        service = UnredactedNoteService(policy, self.backend_factory(policy))
        result = await getattr(service, operation)(**arguments)
        if SingleNotePolicy.from_file(self.path) != policy:
            raise ProcessingBlocked("Local policy changed during processing.")
        return result

    async def read_safe_note(self, note_id):
        return await self._run("read_safe_note", note_id=note_id)

    async def search_safe_notes(self, query, sort="updated_desc", limit=5):
        return await self._run("search_safe_notes", query=query, sort=sort, limit=limit)
