from datetime import datetime, timedelta, timezone

import pytest

from tree_signal.core import ChannelTreeService
from tree_signal.core.models import ChannelNodeState, Message, MessageSeverity


def _message(path: tuple[str, ...], *, at: datetime) -> Message:
    return Message(
        id="test",
        channel_path=path,
        payload="hello",
        received_at=at,
        severity=MessageSeverity.INFO,
        metadata=None,
    )


def test_tree_service_initialises_with_synthetic_root() -> None:
    service = ChannelTreeService()

    assert service.root.path == ()
    assert service.root.children == {}
    assert service.root.weight == 0.0


def test_ingest_creates_nodes_and_updates_weights() -> None:
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    message = _message(("alpha", "beta"), at=now)

    service.ingest(message)

    alpha = service.root.children["alpha"]
    beta = alpha.children["beta"]

    assert alpha.weight == 1.0
    assert alpha.last_message_at == message.received_at
    assert beta.weight == 1.0
    assert beta.last_message_at == message.received_at
    assert service.root.weight == 1.0


def test_ingest_accumulates_weight_for_existing_nodes() -> None:
    service = ChannelTreeService()
    path = ("alpha", "beta")

    first = _message(path, at=datetime.now(tz=timezone.utc))
    second = _message(path, at=datetime.now(tz=timezone.utc))

    service.ingest(first, weight_delta=0.5)
    service.ingest(second, weight_delta=1.5)

    alpha = service.root.children["alpha"]
    beta = alpha.children["beta"]

    assert alpha.weight == 2.0
    assert beta.weight == 2.0
    assert service.root.weight == 2.0
    assert beta.last_message_at == second.received_at


def test_get_node_returns_existing_node() -> None:
    service = ChannelTreeService()
    message = _message(("alpha", "beta", "gamma"), at=datetime.now(tz=timezone.utc))
    service.ingest(message)

    node = service.get_node(("alpha", "beta"))

    assert isinstance(node, ChannelNodeState)
    assert node.path == ("alpha", "beta")


def test_get_node_returns_none_for_missing_path() -> None:
    service = ChannelTreeService()

    assert service.get_node(("missing",)) is None


def test_iter_nodes_traverses_depth_first() -> None:
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("alpha", "beta"), at=now))
    service.ingest(_message(("alpha", "gamma"), at=now))
    service.ingest(_message(("delta",), at=now))

    paths = [node.path for node in service.iter_nodes()]

    assert paths[0] == ()
    assert ("alpha",) in paths
    assert ("alpha", "beta") in paths
    assert ("alpha", "gamma") in paths
    assert ("delta",) in paths


def test_prune_removes_subtree_and_updates_weights() -> None:
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("alpha", "beta"), at=now))
    service.ingest(_message(("alpha", "gamma"), at=now))

    service.prune(("alpha", "beta"))

    alpha = service.get_node(("alpha",))
    assert alpha is not None
    assert "beta" not in alpha.children
    assert alpha.weight == 1.0
    assert service.root.weight == 1.0


def test_prune_missing_path_is_noop() -> None:
    service = ChannelTreeService()
    service.ingest(_message(("alpha",), at=datetime.now(tz=timezone.utc)))

    service.prune(("missing",))

    assert service.get_node(("alpha",)) is not None


def test_prune_root_raises() -> None:
    service = ChannelTreeService()

    with pytest.raises(ValueError):
        service.prune(())


def test_schedule_decay_updates_fade_deadlines() -> None:
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    message = _message(("alpha",), at=now)
    service.ingest(message)

    node = service.get_node(("alpha",))
    assert node is not None
    node.fade_deadline = None

    service.schedule_decay(datetime.now(tz=timezone.utc))

    assert node.fade_deadline is not None


def test_configure_decay_overrides_hold_and_decay() -> None:
    service = ChannelTreeService()
    custom_hold = timedelta(seconds=20)
    custom_decay = timedelta(seconds=15)

    service.configure_decay(hold=custom_hold, decay=custom_decay)
    now = datetime.now(tz=timezone.utc)
    message = _message(("alpha",), at=now)
    service.ingest(message)

    node = service.get_node(("alpha",))
    assert node is not None
    expected_deadline = message.received_at + custom_hold + custom_decay
    assert node.fade_deadline == expected_deadline


def test_schedule_decay_preserves_weight_during_hold() -> None:
    service = ChannelTreeService()
    service.configure_decay(hold=timedelta(seconds=10), decay=timedelta(seconds=4))
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("alpha",), at=now))

    # Mid-hold: half-way through the hold window, well before fade_start.
    service.schedule_decay(now + timedelta(seconds=5))

    node = service.get_node(("alpha",))
    assert node is not None
    assert node.weight == 1.0
    assert node.decay_start_weight is None


def test_schedule_decay_reduces_weight_linearly_during_decay() -> None:
    service = ChannelTreeService()
    service.configure_decay(hold=timedelta(seconds=2), decay=timedelta(seconds=4))
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("alpha",), at=now))
    node = service.get_node(("alpha",))
    assert node is not None

    # At fade_start exactly: still full weight, snapshot captured.
    service.schedule_decay(now + timedelta(seconds=2))
    assert node.weight == pytest.approx(1.0)
    assert node.decay_start_weight == pytest.approx(1.0)

    # 1s into the 4s decay window: 75% remaining.
    service.schedule_decay(now + timedelta(seconds=3))
    assert node.weight == pytest.approx(0.75)

    # 3s into the 4s decay window: 25% remaining.
    service.schedule_decay(now + timedelta(seconds=5))
    assert node.weight == pytest.approx(0.25)


def test_schedule_decay_zeros_weight_after_decay_window() -> None:
    service = ChannelTreeService()
    service.configure_decay(hold=timedelta(seconds=2), decay=timedelta(seconds=4))
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("alpha",), at=now))

    # Past fade_deadline (hold + decay = 6s).
    service.schedule_decay(now + timedelta(seconds=10))

    node = service.get_node(("alpha",))
    assert node is not None
    assert node.weight == 0.0
    assert node.decay_start_weight is None


def test_weight_is_capped_at_default_max() -> None:
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    for i in range(50):
        service.ingest(_message(("alpha",), at=now + timedelta(milliseconds=i)))

    node = service.get_node(("alpha",))
    assert node is not None
    assert node.weight == 10.0  # default cap
    assert service.root.weight == 10.0  # root capped too


def test_configure_max_weight_relaxes_cap() -> None:
    service = ChannelTreeService()
    service.configure_max_weight(50.0)
    now = datetime.now(tz=timezone.utc)
    for i in range(30):
        service.ingest(_message(("alpha",), at=now + timedelta(milliseconds=i)))

    node = service.get_node(("alpha",))
    assert node is not None
    assert node.weight == 30.0  # still below new cap


def test_configure_max_weight_none_disables_cap() -> None:
    service = ChannelTreeService()
    service.configure_max_weight(None)
    now = datetime.now(tz=timezone.utc)
    for i in range(100):
        service.ingest(_message(("alpha",), at=now + timedelta(milliseconds=i)))

    node = service.get_node(("alpha",))
    assert node is not None
    assert node.weight == 100.0  # unbounded


def test_configure_max_weight_rejects_zero_or_negative() -> None:
    service = ChannelTreeService()
    with pytest.raises(ValueError):
        service.configure_max_weight(0.0)
    with pytest.raises(ValueError):
        service.configure_max_weight(-1.0)


def test_touch_resets_decay_snapshot() -> None:
    service = ChannelTreeService()
    service.configure_decay(hold=timedelta(seconds=2), decay=timedelta(seconds=4))
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("alpha",), at=now))
    node = service.get_node(("alpha",))
    assert node is not None

    # Decay halfway, snapshot is captured at 1.0.
    service.schedule_decay(now + timedelta(seconds=4))
    assert node.weight == pytest.approx(0.5)
    assert node.decay_start_weight == pytest.approx(1.0)

    # New activity arrives — snapshot must clear so the next fade window
    # measures from the freshly-touched weight, not the stale 1.0.
    service.ingest(_message(("alpha",), at=now + timedelta(seconds=4)))
    assert node.decay_start_weight is None
    assert node.weight == pytest.approx(1.5)


def test_history_stores_recent_messages() -> None:
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)

    message = _message(("alpha",), at=now)
    service.ingest(message)

    history = service.get_history(("alpha",))
    assert len(history) == 1
    assert history[0].id == message.id


def test_history_respects_capacity_limit() -> None:
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)

    for index in range(105):
        service.ingest(
            _message(("alpha",), at=now),
        )

    history = service.get_history(("alpha",))
    assert len(history) == 100
