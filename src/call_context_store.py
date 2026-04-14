from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CallContext:
    call_id: str
    contact_id: str | None
    contact_type: str | None
    primary_target_id: str
    primary_target_type: str
    spillover_target_id: str | None = None
    spillover_target_type: str | None = None
    spillover_attempted: bool = False


class InMemoryCallContextStore:
    def __init__(self) -> None:
        self._store: dict[str, CallContext] = {}

    def put(self, context: CallContext) -> None:
        self._store[context.call_id] = context

    def get(self, call_id: str) -> CallContext | None:
        return self._store.get(call_id)

    def mark_spillover_attempted(self, call_id: str) -> None:
        context = self._store.get(call_id)
        if context:
            context.spillover_attempted = True
