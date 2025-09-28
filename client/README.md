# Tree Signal Client

Minimal console that previews the in-memory layout and channel history using the Tokyo Night palette and Fira Code typography.

## Quick Start

1. Start the API (e.g. `uv run uvicorn tree_signal.api.main:app --reload --port 8013`).
2. Serve the static assets:
   ```bash
   uv run python -m http.server --directory client 5173
   ```
3. Open `http://localhost:5173` in the browser. Append query parameters to override defaults if needed:
   - `?api=http://localhost:8013`
   - `&apiKey=YOUR_KEY`
   - `&refresh=7000`

The client persists these settings to `localStorage`, so reloads keep the same configuration.

## Implementation Notes

- Design tokens map to the Tokyo Night palette (`#1a1b26` background, `#7aa2f7` accents) with Fira Code for all UI text.
- `client/app.js` polls `/v1/layout` and `/v1/messages/{channel}`; auto-refresh defaults to 5 seconds and can be overridden via `refresh` query param or `tree-signal.refreshMs` local storage key.
- API origin/key can be set via URL parameters or local storage keys (`tree-signal.api`, `tree-signal.apiKey`).

## Linting & Formatting

- Run `uv run python -m http.server --directory client` before committing to ensure the assets load and there are no console errors.
- Use a formatter like `prettier` if you expand the client; current files follow two-space indentation for HTML/JS and align with project ASCII policy.
