#!/usr/bin/env python3
"""
Shared library for emitting messages to tree-signal from Claude Code hooks.
"""
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def load_env():
    """Load environment variables from .env file if it exists."""
    # Find .env file (walk up from current directory)
    current_dir = os.getcwd()
    while current_dir != '/':
        env_file = os.path.join(current_dir, '.env')
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            # Only set if not already in environment
                            if key and value and key not in os.environ:
                                os.environ[key] = value
                break
            except Exception:
                pass
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent


# Load .env on module import
load_env()


class TreeSignalEmitter:
    """Helper class for emitting messages to tree-signal."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 2
    ):
        """
        Initialize the emitter.

        Args:
            api_url: Tree-signal API URL (defaults to env TREE_SIGNAL_URL or localhost:8013)
            api_key: API key (defaults to env TREE_SIGNAL_API_KEY)
            timeout: Request timeout in seconds
        """
        self.api_url = api_url or os.environ.get("TREE_SIGNAL_URL", "http://192.168.20.4:8013")
        self.api_key = api_key or os.environ.get("TREE_SIGNAL_API_KEY")
        self.timeout = timeout
        self.project_name = self._get_project_name()

    def _get_project_name(self) -> str:
        """Get the current project name from CLAUDE_PROJECT_DIR."""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if project_dir:
            return os.path.basename(project_dir)
        return "unknown"

    def emit(
        self,
        channel_path: str,
        payload: str,
        metadata: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ) -> bool:
        """
        Emit a message to tree-signal.

        Args:
            channel_path: Hierarchical channel path (e.g., "claude.project.tool")
            payload: Message payload
            metadata: Optional metadata dict
            severity: Message severity (info, warn, error)

        Returns:
            True if successful, False otherwise
        """
        # Convert all metadata values to strings as required by API
        stringified_metadata = {}
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, (dict, list)):
                    stringified_metadata[key] = json.dumps(value)
                else:
                    stringified_metadata[key] = str(value)

        message = {
            "channel": channel_path,
            "payload": payload,
            "metadata": stringified_metadata,
            "severity": severity
        }

        try:
            data = json.dumps(message).encode('utf-8')
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["x-api-key"] = self.api_key

            req = Request(
                f"{self.api_url}/v1/messages",
                data=data,
                headers=headers,
                method="POST"
            )

            with urlopen(req, timeout=self.timeout) as response:
                return response.status in (200, 202)

        except (URLError, HTTPError, Exception) as e:
            # Silently fail - don't block Claude if tree-signal is down
            # Uncomment for debugging:
            # print(f"tree-signal emit failed: {e}", file=sys.stderr)
            return False

    def emit_tool_use(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        event_type: str = "post",
        status: str = "success",
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Emit a tool usage event.

        Args:
            tool_name: Name of the tool (e.g., "Bash", "Read", "Write")
            tool_input: Tool input parameters
            event_type: "pre" or "post"
            status: "success", "error", etc.
            extra_metadata: Additional metadata to include

        Returns:
            True if successful, False otherwise
        """
        # Categorize tools for better organization
        category = self._categorize_tool(tool_name)
        channel = f"claude.{self.project_name}.{category}.{tool_name}"

        # Create concise payload
        payload = self._create_tool_payload(tool_name, tool_input, status)

        # Build metadata
        metadata = {
            "tool_name": tool_name,
            "event_type": event_type,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            **(extra_metadata or {})
        }

        # Add relevant tool input details
        if tool_input:
            metadata["tool_input"] = self._sanitize_tool_input(tool_name, tool_input)

        severity = "error" if status == "error" else "info"
        return self.emit(channel, payload, metadata, severity)

    def emit_user_prompt(
        self,
        prompt: str,
        prompt_length: int
    ) -> bool:
        """
        Emit a user prompt event.

        Args:
            prompt: The user prompt (will be truncated for display)
            prompt_length: Full length of the prompt

        Returns:
            True if successful, False otherwise
        """
        channel = f"claude.{self.project_name}.prompts"

        # Truncate long prompts for display
        display_prompt = prompt[:100] + "..." if len(prompt) > 100 else prompt

        metadata = {
            "full_length": prompt_length,
            "timestamp": datetime.now().isoformat(),
            "truncated": len(prompt) > 100
        }

        return self.emit(channel, display_prompt, metadata, "info")

    def emit_session_event(
        self,
        event_type: str,
        session_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Emit a session lifecycle event.

        Args:
            event_type: "start" or "end"
            session_info: Optional session metadata

        Returns:
            True if successful, False otherwise
        """
        channel = f"claude.{self.project_name}.session"
        payload = f"Session {event_type}"

        metadata = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "project": self.project_name,
            **(session_info or {})
        }

        return self.emit(channel, payload, metadata, "info")

    @staticmethod
    def _categorize_tool(tool_name: str) -> str:
        """Categorize a tool for channel organization."""
        file_tools = {"Read", "Write", "Edit", "Glob"}
        search_tools = {"Grep"}
        execution_tools = {"Bash"}
        agent_tools = {"Task"}
        web_tools = {"WebFetch", "WebSearch"}

        if tool_name in file_tools:
            return "files"
        elif tool_name in search_tools:
            return "search"
        elif tool_name in execution_tools:
            return "shell"
        elif tool_name in agent_tools:
            return "agents"
        elif tool_name in web_tools:
            return "web"
        else:
            return "other"

    @staticmethod
    def _create_tool_payload(
        tool_name: str,
        tool_input: Dict[str, Any],
        status: str
    ) -> str:
        """Create a concise, informative payload for tool usage."""
        if tool_name == "Bash":
            cmd = tool_input.get("command", "")
            # Truncate long commands
            cmd_display = cmd[:60] + "..." if len(cmd) > 60 else cmd
            return f"{tool_name}: {cmd_display}"

        elif tool_name in {"Read", "Write", "Edit"}:
            file_path = tool_input.get("file_path", "")
            filename = os.path.basename(file_path) if file_path else "unknown"
            return f"{tool_name}: {filename}"

        elif tool_name == "Task":
            subagent = tool_input.get("subagent_type", "unknown")
            desc = tool_input.get("description", "")
            return f"Task[{subagent}]: {desc}"

        elif tool_name == "Grep":
            pattern = tool_input.get("pattern", "")
            return f"Grep: {pattern}"

        elif tool_name == "Glob":
            pattern = tool_input.get("pattern", "")
            return f"Glob: {pattern}"

        else:
            return f"{tool_name} [{status}]"

    @staticmethod
    def _sanitize_tool_input(
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sanitize tool input to include only relevant fields."""
        if tool_name == "Bash":
            return {
                "command": tool_input.get("command", "")[:200],  # Limit length
                "description": tool_input.get("description", "")
            }

        elif tool_name in {"Read", "Write", "Edit"}:
            return {
                "file_path": tool_input.get("file_path", ""),
                "offset": tool_input.get("offset"),
                "limit": tool_input.get("limit")
            }

        elif tool_name == "Task":
            return {
                "subagent_type": tool_input.get("subagent_type", ""),
                "description": tool_input.get("description", ""),
                "model": tool_input.get("model")
            }

        elif tool_name in {"Grep", "Glob"}:
            return {
                "pattern": tool_input.get("pattern", ""),
                "path": tool_input.get("path")
            }

        else:
            # For unknown tools, include all but truncate strings
            sanitized = {}
            for key, value in tool_input.items():
                if isinstance(value, str) and len(value) > 200:
                    sanitized[key] = value[:200] + "..."
                else:
                    sanitized[key] = value
            return sanitized


def main():
    """CLI entry point for testing."""
    if len(sys.argv) < 3:
        print("Usage: tree_signal_emit.py <channel_path> <payload> [metadata_json]")
        sys.exit(1)

    emitter = TreeSignalEmitter()
    channel_path = sys.argv[1]
    payload = sys.argv[2]
    metadata = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None

    success = emitter.emit(channel_path, payload, metadata)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
