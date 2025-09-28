from datetime import datetime, timezone

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


def _frame(frames, path):
    return next(frame for frame in frames if frame.path == path)


def test_single_channel_consumes_full_canvas() -> None:
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("alpha",), at=now))

    generator = LinearLayoutGenerator()
    frames = generator.generate(service, timestamp=now)

    alpha = _frame(frames, ("alpha",))
    assert alpha.rect.x == 0.0
    assert alpha.rect.y == 0.0
    assert alpha.rect.width == 1.0
    assert alpha.rect.height == 1.0


def test_top_level_nodes_split_horizontally() -> None:
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("alpha",), at=now))
    service.ingest(_message(("bravo",), at=now))

    generator = LinearLayoutGenerator()
    frames = generator.generate(service, timestamp=now)

    alpha = _frame(frames, ("alpha",))
    bravo = _frame(frames, ("bravo",))

    assert round(alpha.rect.width, 2) == 0.5
    assert round(bravo.rect.width, 2) == 0.5
    assert alpha.rect.y == 0.0
    assert bravo.rect.y == 0.0


def test_nested_children_split_vertically() -> None:
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("alpha", "one"), at=now))
    service.ingest(_message(("alpha", "two"), at=now))

    generator = LinearLayoutGenerator()
    frames = generator.generate(service, timestamp=now)

    alpha = _frame(frames, ("alpha",))
    one = _frame(frames, ("alpha", "one"))
    two = _frame(frames, ("alpha", "two"))

    assert alpha.rect.width == 1.0
    assert round(one.rect.height, 2) == 0.5
    assert round(two.rect.height, 2) == 0.5
    assert one.rect.x == two.rect.x == 0.0
