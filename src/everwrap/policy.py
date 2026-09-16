"""Local access policy. Never accepts policy overrides in tool arguments."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


class AccessDenied(Exception):
    """Safe to expose: no request IDs, account details, or note text."""


class InvalidPolicy(Exception):
    """Local configuration is absent or invalid; access stays disabled."""


def canonical_note_id(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value
    ):
        raise AccessDenied("Note access denied.")
    result = value.lower()
    if result == "00000000-0000-0000-0000-000000000000":
        raise AccessDenied("Note access denied.")
    return result


@dataclass(frozen=True, slots=True)
class SingleNotePolicy:
    allowed_note_id: str | None = field(default=None, repr=False)
    blocked_note_ids: frozenset[str] = field(default_factory=frozenset, repr=False)
    access_mode: str = "single_note"
    content_mode: str = "blocked"

    def __post_init__(self):
        try:
            if self.access_mode not in ("single_note", "denylist") or self.content_mode not in ("blocked", "unredacted"):
                raise AccessDenied()
            normalized = (None if self.allowed_note_id is None and self.access_mode == "denylist"
                          else canonical_note_id(self.allowed_note_id))
            if not isinstance(self.blocked_note_ids, frozenset) or len(self.blocked_note_ids) > 16:
                raise AccessDenied()
            blocked = frozenset(canonical_note_id(value) for value in self.blocked_note_ids)
        except AccessDenied:
            raise InvalidPolicy("Single-note policy is invalid.") from None
        object.__setattr__(self, "allowed_note_id", normalized)
        object.__setattr__(self, "blocked_note_ids", blocked)

    @classmethod
    def from_file(cls, path: Path) -> "SingleNotePolicy":
        try:
            # Bound the read before JSON parsing; never echo configuration errors.
            with path.open("rb") as handle:
                raw = handle.read(1025)
            if len(raw) > 1024:
                raise ValueError

            def unique_fields(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError
                    result[key] = value
                return result

            data = json.loads(raw, object_pairs_hook=unique_fields)
            if (not isinstance(data, dict)
                    or not set(data) <= {"allowed_note_id", "blocked_note_ids", "access_mode", "content_mode"}):
                raise ValueError
            blocked = data.get("blocked_note_ids", [])
            if type(blocked) is not list or len(blocked) > 16:
                raise ValueError
            return cls(data.get("allowed_note_id"), frozenset(blocked),
                       data.get("access_mode", "single_note"), data.get("content_mode", "blocked"))
        except (OSError, ValueError, TypeError, InvalidPolicy):
            raise InvalidPolicy("Single-note policy is unavailable or invalid.") from None

    def authorize(self, note_id: object) -> str:
        normalized = canonical_note_id(note_id)
        if (normalized in self.blocked_note_ids
                or (self.access_mode == "single_note" and normalized != self.allowed_note_id)):
            raise AccessDenied("Note access denied.")
        return normalized
