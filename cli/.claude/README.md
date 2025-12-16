# Claude Code → Tree-Signal Integration

This directory contains Claude Code hooks that emit events to tree-signal for real-time monitoring and visualization of Claude's activities.

## Overview

The hooks capture and emit the following events to tree-signal:

- **Tool Usage** (PostToolUse) - Every tool Claude uses (files, shell, search, etc.)
- **User Prompts** (UserPromptSubmit) - All user messages and questions
- **Session Lifecycle** (SessionStart/SessionEnd) - When Claude sessions begin and end

Events are organized hierarchically in tree-signal as:
```
claude.{project}.{category}.{tool_name}
```

For example:
- `claude.cli.files.Read` - File read operations
- `claude.cli.shell.Bash` - Shell commands
- `claude.cli.agents.Explore` - Agent tasks
- `claude.cli.prompts` - User prompts
- `claude.cli.session` - Session events

## Quick Start

### 1. Start tree-signal Server

Make sure tree-signal is running:

```bash
# From the tree_signal directory
./tree-signal --port 8013
```

### 2. Configure API Key

Copy the example settings file and add your tree-signal API key:

```bash
cd /mnt/Projects/tree_signal/cli
cp .claude/settings.local.json.example .claude/settings.local.json
```

Edit `.claude/settings.local.json` to configure the server URL (and optionally an API key if your server requires authentication):

```json
{
  "env": {
    "TREE_SIGNAL_URL": "http://localhost:8013"
  }
}
```

If your tree-signal server requires authentication, add the API key:
```json
{
  "env": {
    "TREE_SIGNAL_URL": "http://localhost:8013",
    "TREE_SIGNAL_API_KEY": "your-actual-api-key"
  }
}
```

**Note:** `.claude/settings.local.json` is gitignored and won't be committed.

### 3. Start Using Claude Code

The hooks are now active! Start a Claude session in this project:

```bash
claude
```

All activities will automatically appear in tree-signal.

## Architecture

### Files

```
.claude/
├── settings.json                    # Hook configuration
├── settings.local.json.example      # API key template
├── settings.local.json             # Your API key (gitignored)
├── hooks/
│   ├── tree_signal_emit.py         # Shared helper library
│   ├── post_tool_use.py            # Tool usage tracking
│   ├── user_prompt_submit.py       # Prompt tracking
│   ├── session_start.py            # Session start events
│   └── session_end.py              # Session end events
└── README.md                        # This file
```

### Event Flow

1. Claude Code triggers a hook event (e.g., after using a tool)
2. Hook script receives JSON input via stdin
3. Script uses `TreeSignalEmitter` to format and send message
4. Message POSTed to tree-signal's `/v1/messages` endpoint
5. Tree-signal displays event in hierarchical dashboard

### Tool Categorization

Tools are automatically categorized for better organization:

| Category | Tools |
|----------|-------|
| `files` | Read, Write, Edit, Glob |
| `search` | Grep |
| `shell` | Bash |
| `agents` | Task (with subagent type) |
| `web` | WebFetch, WebSearch |
| `other` | Everything else |

## Configuration

### Environment Variables

Set these in `.claude/settings.local.json`:

- `TREE_SIGNAL_URL` - Tree-signal server URL (default: `http://localhost:8013`)
- `TREE_SIGNAL_API_KEY` - API key for authentication (optional, if your server requires it)

### Hook Timeouts

All hooks have a 5-second timeout. If tree-signal is slow/down, hooks won't block Claude.

### Customization

#### Disable Specific Hooks

Edit `.claude/settings.json` and remove unwanted hook sections.

#### Filter Tools

Change the `matcher` in PostToolUse to only track specific tools:

```json
{
  "PostToolUse": [
    {
      "matcher": "Bash|Write|Edit",
      "hooks": [...]
    }
  ]
}
```

#### Enable Debug Output

Uncomment debug lines in hook scripts:

```python
# In any hook script, uncomment:
print(f"Hook error: {e}", file=sys.stderr)
print(f"tree-signal emit failed: {e}", file=sys.stderr)
```

Then run Claude with debug mode:

```bash
claude --debug
```

## Message Format

Messages sent to tree-signal include:

```json
{
  "channel_path": "claude.cli.files.Read",
  "payload": "Read: tree_signal_spec.md",
  "metadata": {
    "tool_name": "Read",
    "event_type": "post",
    "status": "success",
    "timestamp": "2025-12-16T10:30:45.123456",
    "tool_input": {
      "file_path": "/mnt/Projects/tree_signal/tree_signal_spec.md",
      "offset": null,
      "limit": null
    }
  },
  "severity": "info"
}
```

## Troubleshooting

### Hook Not Triggering

1. Check Claude Code detects the hooks:
   ```bash
   claude
   /hooks
   ```

2. Verify scripts are executable:
   ```bash
   ls -la .claude/hooks/
   ```

3. Test the emitter directly:
   ```bash
   # If your server requires authentication, set the API key:
   # export TREE_SIGNAL_API_KEY="your-key"
   .claude/hooks/tree_signal_emit.py "test.channel" "Hello from test"
   ```

### Tree-Signal Not Receiving Messages

1. Verify tree-signal is running:
   ```bash
   curl http://localhost:8013/healthz
   ```

2. Test the API directly:
   ```bash
   curl -X POST http://localhost:8013/v1/messages \
     -H "Content-Type: application/json" \
     -H "x-api-key: your-key" \
     -d '{"channel_path":"test","payload":"Hello"}'
   ```

3. Check tree-signal logs for errors

### Hooks Blocking/Slow

- Hooks have 5-second timeouts and fail silently
- If tree-signal is down, Claude continues normally
- Check hook timeout in settings.json if needed

## Advanced Usage

### Manual Testing

Test individual hooks with mock input:

```bash
echo '{"tool_name":"Read","tool_input":{"file_path":"test.txt"}}' | \
  .claude/hooks/post_tool_use.py
```

### Custom Channels

Modify `tree_signal_emit.py` to change channel organization:

```python
# In emit_tool_use method:
channel = f"claude.{self.project_name}.custom.{tool_name}"
```

### Additional Metadata

Add more metadata in hook scripts:

```python
extra_metadata = {
    "git_branch": subprocess.check_output(
        ["git", "branch", "--show-current"],
        text=True
    ).strip()
}
```

## Security Notes

- Keep `.claude/settings.local.json` private (contains API key)
- It's gitignored by default
- Hooks have limited permissions and timeouts
- Failed hooks don't block Claude operations

## Integration with Tree-Signal Features

### Panel Decay

Claude activity creates panels that decay over time per tree-signal's TTL settings. Active development areas remain prominent while inactive ones fade.

### Manual Controls

Use tree-signal's API or UI to:
- Lock panels for important channels
- Delete panels to clear history
- Adjust decay parameters

### Dashboard Views

Organize your view by:
- Project (multiple Claude projects)
- Category (files, shell, agents, etc.)
- Time (recent activity vs. historical)

## Examples

### Monitoring a Long Task

1. Start Claude on a complex refactoring
2. Watch tree-signal dashboard
3. See real-time updates as Claude:
   - Reads files (`claude.project.files.Read`)
   - Searches code (`claude.project.search.Grep`)
   - Runs tests (`claude.project.shell.Bash`)
   - Makes edits (`claude.project.files.Edit`)

### Tracking Agent Work

When Claude uses the Task tool:

```
claude.project.agents.Explore
claude.project.agents.Plan
claude.project.agents.Test
```

Each agent type gets its own panel showing activity.

### Session Analytics

Track your development sessions:
- Session start/end times
- Tools used per session
- Activity patterns over time

## Contributing

To add new hooks or modify behavior:

1. Edit hook scripts in `.claude/hooks/`
2. Update `settings.json` if adding new events
3. Test thoroughly before committing
4. Update this README with changes

## Resources

- [Claude Code Hooks Documentation](https://code.claude.com/docs/en/hooks.md)
- [Tree-Signal Specification](../tree_signal_spec.md)
- [Claude Code Guide](https://code.claude.com/docs)
