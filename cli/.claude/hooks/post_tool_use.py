#!/usr/bin/env python3
"""
PostToolUse hook for Claude Code - emits tool usage events to tree-signal.

This hook runs after every tool execution and sends details to tree-signal
for real-time monitoring and activity visualization.
"""
import json
import sys
import os

# Add hooks directory to path to import our helper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tree_signal_emit import TreeSignalEmitter


def main():
    """Process PostToolUse event and emit to tree-signal."""
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)

        # Extract tool information
        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})

        # PostToolUse provides execution results
        tool_output = input_data.get("tool_output", {})
        status = "success" if input_data.get("success", True) else "error"

        # Create emitter and send event
        emitter = TreeSignalEmitter()

        # Add extra metadata from output if available
        extra_metadata = {}
        if tool_output:
            # Include execution time if available
            if "execution_time" in tool_output:
                extra_metadata["execution_time_ms"] = tool_output["execution_time"]

            # Include error info if failed
            if status == "error" and "error" in tool_output:
                extra_metadata["error"] = str(tool_output["error"])[:200]

        emitter.emit_tool_use(
            tool_name=tool_name,
            tool_input=tool_input,
            event_type="post",
            status=status,
            extra_metadata=extra_metadata
        )

    except Exception as e:
        # Silently fail - don't block Claude
        # Uncomment for debugging:
        # print(f"Hook error: {e}", file=sys.stderr)
        pass

    # Always exit 0 to allow the tool execution
    sys.exit(0)


if __name__ == "__main__":
    main()
