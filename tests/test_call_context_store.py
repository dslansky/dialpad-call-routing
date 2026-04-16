from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.call_context_store import CallContext, FirestoreCallContextStore, InMemoryCallContextStore


class FakeSnapshot:
    def __init__(self, data: dict | None, exists: bool = True) -> None:
        self._data = data
        self.exists = exists
        self.update_time = object()

    def to_dict(self) -> dict | None:
        return self._data


class FakeDocument:
    def __init__(self) -> None:
        self.data: dict | None = None

    def set(self, payload: dict) -> None:
        self.data = dict(payload)

    def get(self) -> FakeSnapshot:
        if self.data is None:
            return FakeSnapshot(None, exists=False)
        return FakeSnapshot(dict(self.data))

    def update(self, payload: dict, option: object | None = None) -> None:
        if self.data is None:
            raise RuntimeError("missing document")
        self.data.update(payload)


class FakeCollection:
    def __init__(self) -> None:
        self.documents: dict[str, FakeDocument] = {}

    def document(self, doc_id: str) -> FakeDocument:
        return self.documents.setdefault(doc_id, FakeDocument())


class FakeFirestoreClient:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def collection(self, collection_name: str) -> FakeCollection:
        return self.collections.setdefault(collection_name, FakeCollection())


def test_firestore_call_context_store_round_trips_context() -> None:
    current_time = [datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)]
    store = FirestoreCallContextStore(
        collection_name="dialpad_call_contexts",
        ttl_seconds=3600,
        firestore_client=FakeFirestoreClient(),
        now_fn=lambda: current_time[0],
    )

    store.put(
        CallContext(
            call_id="call-1",
            contact_id="003x",
            contact_type="Client",
            primary_target_id="100",
            primary_target_type="user",
            spillover_target_id="200",
            spillover_target_type="user",
        )
    )

    context = store.get("call-1")

    assert context is not None
    assert context.primary_target_id == "100"
    assert context.spillover_target_id == "200"
    assert context.expires_at is not None


def test_firestore_call_context_store_coerces_integer_call_id_to_string() -> None:
    current_time = [datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)]
    store = FirestoreCallContextStore(
        collection_name="dialpad_call_contexts",
        ttl_seconds=3600,
        firestore_client=FakeFirestoreClient(),
        now_fn=lambda: current_time[0],
    )

    store.put(
        CallContext(
            call_id=123456789,  # type: ignore[arg-type]
            contact_id="003x",
            contact_type="Client",
            primary_target_id="100",
            primary_target_type="user",
        )
    )

    context = store.get("123456789")

    assert context is not None
    assert context.call_id == "123456789"


def test_firestore_call_context_store_ignores_expired_records() -> None:
    current_time = [datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)]
    store = FirestoreCallContextStore(
        collection_name="dialpad_call_contexts",
        ttl_seconds=60,
        firestore_client=FakeFirestoreClient(),
        now_fn=lambda: current_time[0],
    )

    store.put(
        CallContext(
            call_id="expired-call",
            contact_id=None,
            contact_type=None,
            primary_target_id="100",
            primary_target_type="user",
        )
    )
    current_time[0] = current_time[0] + timedelta(seconds=61)

    assert store.get("expired-call") is None


def test_firestore_call_context_store_marks_spillover_once() -> None:
    current_time = [datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)]
    store = FirestoreCallContextStore(
        collection_name="dialpad_call_contexts",
        ttl_seconds=3600,
        firestore_client=FakeFirestoreClient(),
        now_fn=lambda: current_time[0],
    )
    store.put(
        CallContext(
            call_id="claim-call",
            contact_id=None,
            contact_type="Employee",
            primary_target_id="100",
            primary_target_type="user",
            spillover_target_id="200",
            spillover_target_type="user",
        )
    )

    first_claim = store.mark_spillover_attempted("claim-call")
    second_claim = store.mark_spillover_attempted("claim-call")

    assert first_claim is not None
    assert first_claim.spillover_attempted is True
    assert second_claim is None


def test_in_memory_store_claims_spillover_once() -> None:
    current_time = [datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)]
    store = InMemoryCallContextStore(ttl_seconds=3600, now_fn=lambda: current_time[0])
    store.put(
        CallContext(
            call_id="memory-call",
            contact_id=None,
            contact_type="Employee",
            primary_target_id="100",
            primary_target_type="user",
            spillover_target_id="200",
            spillover_target_type="user",
        )
    )

    assert store.mark_spillover_attempted("memory-call") is not None
    assert store.mark_spillover_attempted("memory-call") is None


def test_in_memory_store_accepts_integer_call_ids() -> None:
    current_time = [datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)]
    store = InMemoryCallContextStore(ttl_seconds=3600, now_fn=lambda: current_time[0])
    store.put(
        CallContext(
            call_id=987654321,  # type: ignore[arg-type]
            contact_id=None,
            contact_type="Employee",
            primary_target_id="100",
            primary_target_type="user",
            spillover_target_id="200",
            spillover_target_type="user",
        )
    )

    assert store.get("987654321") is not None
    assert store.mark_spillover_attempted(987654321) is not None
