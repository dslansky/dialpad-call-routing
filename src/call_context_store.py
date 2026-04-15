from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    from google.api_core import exceptions as google_exceptions
    from google.cloud import firestore
except ImportError:  # pragma: no cover - exercised only when dependency is missing locally.
    firestore = None
    google_exceptions = None


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
    expires_at: datetime | None = None


class InMemoryCallContextStore:
    def __init__(self, ttl_seconds: int = 3600, now_fn: Any | None = None) -> None:
        self._store: dict[str, CallContext] = {}
        self.ttl_seconds = ttl_seconds
        self._now_fn = now_fn or self._default_now

    def _default_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _build_expires_at(self) -> datetime:
        return self._now_fn() + timedelta(seconds=max(self.ttl_seconds, 1))

    def _is_expired(self, context: CallContext) -> bool:
        return context.expires_at is not None and context.expires_at <= self._now_fn()

    def put(self, context: CallContext) -> None:
        if context.expires_at is None:
            context.expires_at = self._build_expires_at()
        self._store[context.call_id] = context

    def get(self, call_id: str) -> CallContext | None:
        context = self._store.get(call_id)
        if context and self._is_expired(context):
            self._store.pop(call_id, None)
            return None
        return context

    def mark_spillover_attempted(self, call_id: str) -> CallContext | None:
        context = self._store.get(call_id)
        if not context or self._is_expired(context) or context.spillover_attempted:
            self._store.pop(call_id, None)
            return None
        if not context.spillover_target_id or not context.spillover_target_type:
            return None
        context.spillover_attempted = True
        return context

    def clear_spillover_attempted(self, call_id: str) -> None:
        context = self._store.get(call_id)
        if context and not self._is_expired(context):
            context.spillover_attempted = False


class FirestoreCallContextStore:
    def __init__(
        self,
        collection_name: str,
        ttl_seconds: int = 3600,
        firestore_client: Any | None = None,
        now_fn: Any | None = None,
    ) -> None:
        self.collection_name = collection_name
        self.ttl_seconds = ttl_seconds
        self._now_fn = now_fn or self._default_now
        if firestore_client is not None:
            self._firestore_client = firestore_client
        else:
            if firestore is None:
                raise RuntimeError("google-cloud-firestore must be installed for call context storage")
            self._firestore_client = firestore.Client()
        self._collection = self._firestore_client.collection(collection_name)

    def _default_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _build_expires_at(self) -> datetime:
        return self._now_fn() + timedelta(seconds=max(self.ttl_seconds, 1))

    def _document(self, call_id: str):
        return self._collection.document(call_id)

    def _normalize_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _payload_from_context(self, context: CallContext) -> dict[str, Any]:
        expires_at = self._normalize_datetime(context.expires_at) or self._build_expires_at()
        context.expires_at = expires_at
        return {
            "call_id": context.call_id,
            "contact_id": context.contact_id,
            "contact_type": context.contact_type,
            "primary_target_id": context.primary_target_id,
            "primary_target_type": context.primary_target_type,
            "spillover_target_id": context.spillover_target_id,
            "spillover_target_type": context.spillover_target_type,
            "spillover_attempted": context.spillover_attempted,
            "expires_at": expires_at,
        }

    def _context_from_data(self, data: dict[str, Any] | None) -> CallContext | None:
        if not data:
            return None
        expires_at = self._normalize_datetime(data.get("expires_at"))
        context = CallContext(
            call_id=data["call_id"],
            contact_id=data.get("contact_id"),
            contact_type=data.get("contact_type"),
            primary_target_id=data["primary_target_id"],
            primary_target_type=data["primary_target_type"],
            spillover_target_id=data.get("spillover_target_id"),
            spillover_target_type=data.get("spillover_target_type"),
            spillover_attempted=bool(data.get("spillover_attempted", False)),
            expires_at=expires_at,
        )
        if expires_at is not None and expires_at <= self._now_fn():
            return None
        return context

    def put(self, context: CallContext) -> None:
        self._document(context.call_id).set(self._payload_from_context(context))

    def get(self, call_id: str) -> CallContext | None:
        snapshot = self._document(call_id).get()
        if not getattr(snapshot, "exists", False):
            return None
        return self._context_from_data(snapshot.to_dict())

    def mark_spillover_attempted(self, call_id: str) -> CallContext | None:
        document = self._document(call_id)
        for _ in range(3):
            snapshot = document.get()
            if not getattr(snapshot, "exists", False):
                return None
            context = self._context_from_data(snapshot.to_dict())
            if context is None or context.spillover_attempted:
                return None
            if not context.spillover_target_id or not context.spillover_target_type:
                return None
            try:
                update_kwargs = {"spillover_attempted": True}
                if firestore is not None:
                    document.update(
                        update_kwargs,
                        option=firestore.LastUpdateOption(snapshot.update_time),
                    )
                else:
                    document.update(update_kwargs)
                context.spillover_attempted = True
                return context
            except Exception as exc:
                if not self._is_retryable_write_error(exc):
                    raise
        return None

    def clear_spillover_attempted(self, call_id: str) -> None:
        document = self._document(call_id)
        snapshot = document.get()
        if not getattr(snapshot, "exists", False):
            return
        context = self._context_from_data(snapshot.to_dict())
        if context is None:
            return
        document.update({"spillover_attempted": False})

    def _is_retryable_write_error(self, exc: Exception) -> bool:
        if google_exceptions is None:
            return False
        return isinstance(
            exc,
            (
                google_exceptions.Aborted,
                google_exceptions.Conflict,
                google_exceptions.FailedPrecondition,
            ),
        )
