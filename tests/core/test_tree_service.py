from datetime import datetime

import pytest

from tree_signal.core import ChannelTreeService
from tree_signal.core.models import Message, MessageSeverity


def test_tree_service_initialises_with_synthetic_root() -> None:
    service = ChannelTreeService()

    assert service.root.path == ()
    assert service.root.children == {}
    assert service.root.weight == 0.0


def test_ingest_not_implemented_yet() -> None:
    service = ChannelTreeService()
    message = Message(
        id="test",
        channel_path=("alpha",),
        payload="hello",
        received_at=datetime.now(),
        severity=MessageSeverity.INFO,
    )

    with pytest.raises(NotImplementedError):
        service.ingest(message)
