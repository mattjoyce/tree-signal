#!/usr/bin/env python3
"""
SessionEnd hook for Claude Code - emits session end events to tree-signal.

This hook runs when a Claude Code session ends, allowing you to track
when development sessions complete.
"""
import json
import sys
import os

# Add hooks directory to path to import our helper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tree_signal_emit import TreeSignalEmitter


def main():
    """Process SessionEnd event and emit to tree-signal."""
    try:
        # Read hook input from stdin (may be empty for SessionEnd)
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            input_data = {}

        # Gather session info
        session_info = {
            "cwd": os.getcwd(),
        }

        # Add any data from the input
        if input_data:
            session_info.update(input_data)

        # Create emitter and send event
        emitter = TreeSignalEmitter()
        emitter.emit_session_event(
            event_type="end",
            session_info=session_info
        )

    except Exception as e:
        # Silently fail - don't block Claude
        # Uncomment for debugging:
        # print(f"Hook error: {e}", file=sys.stderr)
        pass

    # Always exit 0
    sys.exit(0)


if __name__ == "__main__":
    main()
