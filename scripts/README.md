# Utility Scripts

## `seed_demo.py`

Populate the running Tree Signal instance with sample data:

```bash
TREE_SIGNAL_API=http://localhost:8013 uv run python scripts/seed_demo.py
```

Configuration is handled via environment variables:

- `TREE_SIGNAL_API` (default `http://localhost:8000`)
- `TREE_SIGNAL_API_KEY` (optional `x-api-key` header)

The script posts to `/v1/messages`, seeding multiple channels (`alpha.beta`, `charlie.ops.alerts`, etc.) so the layout and message dashboards light up immediately.
