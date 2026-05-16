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


def test_empty_multi_child_parent_emits_grouping_container() -> None:
    """An empty intermediate node with >= 2 children is drawn as a grouping
    container (LAYOUT_UX_PROBLEMS.md Scenario B) so the hierarchy is legible.
    A single-child empty parent still collapses — no value boxing one thing."""
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("this", "that", "other"), at=now))
    service.ingest(_message(("this", "that", "omg"), at=now))

    frames = LinearLayoutGenerator().generate(service, timestamp=now)
    paths = {frame.path for frame in frames}

    assert ("this", "that") in paths      # 2 children → grouping container
    assert ("this",) not in paths         # single child → still collapsed
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


def test_children_tile_parent_without_overlap() -> None:
    """Children partition the parent's area without overlapping and stay in
    bounds. Split *direction* is aspect-driven (longer axis), not a fixed
    function of depth, so this asserts tiling correctness, not orientation."""
    service = ChannelTreeService()
    now = datetime.now(tz=timezone.utc)
    # alpha gets a direct message so it takes a content strip of its own.
    service.ingest(_message(("alpha",), at=now))
    service.ingest(_message(("alpha", "one"), at=now))
    service.ingest(_message(("alpha", "two"), at=now))

    frames = LinearLayoutGenerator().generate(service, timestamp=now)
    alpha = _frame(frames, ("alpha",))
    one = _frame(frames, ("alpha", "one"))
    two = _frame(frames, ("alpha", "two"))

    # Every rect stays inside the unit canvas.
    for r in (alpha.rect, one.rect, two.rect):
        assert r.x >= 0.0 and r.y >= 0.0
        assert r.x + r.width <= 1.0 + 1e-9
        assert r.y + r.height <= 1.0 + 1e-9
        assert r.width > 0.0 and r.height > 0.0

    # The two siblings do not overlap (separated on at least one axis).
    sep_x = one.rect.x + one.rect.width <= two.rect.x + 1e-9 or \
            two.rect.x + two.rect.width <= one.rect.x + 1e-9
    sep_y = one.rect.y + one.rect.height <= two.rect.y + 1e-9 or \
            two.rect.y + two.rect.height <= one.rect.y + 1e-9
    assert sep_x or sep_y

    # Siblings share the split evenly (equal extent on the divided axis).
    if sep_x:
        assert round(one.rect.width, 2) == round(two.rect.width, 2)
    else:
        assert round(one.rect.height, 2) == round(two.rect.height, 2)
