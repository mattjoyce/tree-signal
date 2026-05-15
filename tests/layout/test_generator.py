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


def test_deep_single_channel_collapses_intermediate_parents() -> None:
    """A single deep channel with no sibling traffic should emit only the leaf frame
    spanning the full canvas — no nested empty wrapper frames."""
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("this", "that", "other"), at=now))

    frames = LinearLayoutGenerator().generate(service, timestamp=now)
    paths = [frame.path for frame in frames]

    assert paths == [("this", "that", "other")]
    leaf = frames[0]
    assert leaf.rect.width == 1.0
    assert leaf.rect.height == 1.0


def test_empty_multi_child_parent_does_not_emit_intermediate_frame() -> None:
    """When an intermediate node has no messages of its own, it is collapsed even when
    it has multiple children — the children occupy the would-be parent's slot directly."""
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("this", "that", "other"), at=now))
    service.ingest(_message(("this", "that", "omg"), at=now))

    frames = LinearLayoutGenerator().generate(service, timestamp=now)
    paths = {frame.path for frame in frames}

    assert ("this", "that") not in paths
    assert ("this",) not in paths
    assert ("this", "that", "other") in paths
    assert ("this", "that", "omg") in paths


def test_parent_with_own_messages_still_emits_frame() -> None:
    """A parent that has received its own messages must remain in the layout output;
    only empty intermediate parents collapse."""
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("this", "that"), at=now))  # parent gets a message
    service.ingest(_message(("this", "that", "other"), at=now))

    frames = LinearLayoutGenerator().generate(service, timestamp=now)
    paths = {frame.path for frame in frames}

    assert ("this", "that") in paths
    assert ("this", "that", "other") in paths


def test_nested_children_split_vertically() -> None:
    """Children at depth 1 split vertically (stacked), alternating with horizontal at depth 0."""
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    # Give alpha a direct message so it has visible area
    service.ingest(_message(("alpha",), at=now))
    service.ingest(_message(("alpha", "one"), at=now))
    service.ingest(_message(("alpha", "two"), at=now))

    generator = LinearLayoutGenerator()
    frames = generator.generate(service, timestamp=now)

    alpha = _frame(frames, ("alpha",))
    one = _frame(frames, ("alpha", "one"))
    two = _frame(frames, ("alpha", "two"))

    # alpha takes top portion (20%), children split remaining 80% vertically
    assert alpha.rect.width == 1.0  # Full width
    assert one.rect.width == 1.0  # Full width within parent
    assert two.rect.width == 1.0  # Full width within parent

    # Children are stacked vertically (same x=0, different y, equal heights)
    assert alpha.rect.x == one.rect.x == two.rect.x == 0.0
    # Alpha's y=0 (top), children start below alpha
    assert one.rect.y > alpha.rect.y
    assert two.rect.y > one.rect.y
    # Both children should have equal height (stacked vertically)
    assert round(one.rect.height, 2) == round(two.rect.height, 2)
