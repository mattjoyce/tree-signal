from datetime import datetime

import pytest

from tree_signal.core import ChannelTreeService
from tree_signal.core.models import ChannelNodeState, Message, MessageSeverity


def _message(path: tuple[str, ...]) -> Message:
    return Message(
        id="test",
        channel_path=path,
        payload="hello",
        received_at=datetime.now(),
        severity=MessageSeverity.INFO,
    )


def test_tree_service_initialises_with_synthetic_root() -> None:
    service = ChannelTreeService()

    assert service.root.path == ()
    assert service.root.children == {}
    assert service.root.weight == 0.0


def test_ingest_creates_nodes_and_updates_weights() -> None:
    service = ChannelTreeService()
    message = _message(("alpha", "beta"))

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

    first = _message(path)
    second = _message(path)

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
    message = _message(("alpha", "beta", "gamma"))
    service.ingest(message)

    node = service.get_node(("alpha", "beta"))

    assert isinstance(node, ChannelNodeState)
    assert node.path == ("alpha", "beta")


def test_get_node_returns_none_for_missing_path() -> None:
    service = ChannelTreeService()

    assert service.get_node(("missing",)) is None


def test_iter_nodes_traverses_depth_first() -> None:
    service = ChannelTreeService()
    service.ingest(_message(("alpha", "beta")))
    service.ingest(_message(("alpha", "gamma")))
    service.ingest(_message(("delta",)))

    paths = [node.path for node in service.iter_nodes()]

    assert paths[0] == ()
    assert ("alpha",) in paths
    assert ("alpha", "beta") in paths
    assert ("alpha", "gamma") in paths
    assert ("delta",) in paths
