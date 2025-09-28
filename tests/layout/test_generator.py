from datetime import datetime, timedelta, timezone

from tree_signal.core import ChannelTreeService, Message, MessageSeverity
from tree_signal.layout import LinearLayoutGenerator


def _message(path: tuple[str, ...], *, at: datetime) -> Message:
    return Message(
        id="msg",
        channel_path=path,
        payload="payload",
        received_at=at,
        severity=MessageSeverity.INFO,
        metadata=None,
    )


def test_generate_returns_frame_per_node() -> None:
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("alpha",), at=now))
    service.ingest(_message(("beta",), at=now))

    generator = LinearLayoutGenerator()
    frames = generator.generate(service, timestamp=now)

    paths = [frame.path for frame in frames]
    assert ("alpha",) in paths
    assert ("beta",) in paths
    assert all(frame.rect.width == 1.0 for frame in frames)


def test_generate_marks_panels_fading_after_deadline() -> None:
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    message = _message(("alpha",), at=now)
    service.ingest(message)

    node = service.get_node(("alpha",))
    assert node is not None
    node.fade_deadline = now - timedelta(seconds=1)

    generator = LinearLayoutGenerator()
    frames = generator.generate(service, timestamp=now)

    assert frames[0].state.value == "fading"


def test_generate_enforces_min_height() -> None:
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("alpha",), at=now))

    generator = LinearLayoutGenerator(min_height=0.2)
    frames = generator.generate(service, timestamp=now)

    assert frames[0].rect.height >= 0.2
