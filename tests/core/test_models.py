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
