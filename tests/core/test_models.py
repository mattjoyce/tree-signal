from datetime import datetime, timedelta

from tree_signal.core import ChannelNodeState, PanelState
from tree_signal.core.models import LayoutRect


def test_channel_node_touch_updates_weight_and_timestamp() -> None:
    node = ChannelNodeState(path=("alpha",), weight=1.0)
    now = datetime.now()

    node.touch(timestamp=now, weight_delta=0.5)

    assert node.last_message_at == now
    assert node.weight == 1.5


def test_channel_node_schedule_fade_sets_deadline() -> None:
    node = ChannelNodeState(path=("alpha",), weight=1.0)
    now = datetime.now()
    node.touch(timestamp=now, weight_delta=0.0)

    node.schedule_fade(hold=timedelta(seconds=10), decay=timedelta(seconds=5))

    assert node.fade_deadline == now + timedelta(seconds=15)


def test_layout_rect_holds_geometry() -> None:
    rect = LayoutRect(x=0.1, y=0.2, width=0.3, height=0.4)

    assert rect.width == 0.3
    assert rect.height == 0.4


def test_panel_state_enum_values() -> None:
    assert PanelState.ACTIVE.value == "active"
    assert PanelState.FADING.value == "fading"
    assert PanelState.REMOVED.value == "removed"


def test_state_at_returns_active_when_no_fade_scheduled() -> None:
    node = ChannelNodeState(path=("alpha",), weight=1.0)
    assert node.state_at(datetime.now()) == PanelState.ACTIVE


def test_state_at_reports_active_fading_removed_across_window() -> None:
    node = ChannelNodeState(path=("alpha",), weight=1.0)
    now = datetime.now()
    node.touch(timestamp=now, weight_delta=0.0)
    node.schedule_fade(hold=timedelta(seconds=10), decay=timedelta(seconds=5))

    # In hold window
    assert node.state_at(now + timedelta(seconds=5)) == PanelState.ACTIVE
    # In decay window
    assert node.state_at(now + timedelta(seconds=12)) == PanelState.FADING
    # Past fade_deadline (hold + decay = 15s)
    assert node.state_at(now + timedelta(seconds=20)) == PanelState.REMOVED
