#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code - emits user prompt events to tree-signal.

This hook runs when a user submits a prompt, allowing you to track
all user interactions and questions in real-time.
"""
import json
import sys
import os

# Add hooks directory to path to import our helper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tree_signal_emit import TreeSignalEmitter


def main():
    """Process UserPromptSubmit event and emit to tree-signal."""
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)

        # Extract prompt
        prompt = input_data.get("prompt", "")

        if not prompt:
            sys.exit(0)

        # Create emitter and send event
        emitter = TreeSignalEmitter()
        emitter.emit_user_prompt(
            prompt=prompt,
            prompt_length=len(prompt)
        )

    except Exception as e:
        # Silently fail - don't block Claude
        # Uncomment for debugging:
        # print(f"Hook error: {e}", file=sys.stderr)
        pass

    # Always exit 0 to allow the prompt
    sys.exit(0)


if __name__ == "__main__":
    main()
