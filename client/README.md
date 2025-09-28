# Tree Signal Client

Minimal console that previews the in-memory layout and channel history using the Tokyo Night palette and Fira Code typography.

## Quick Start

1. Ensure the FastAPI service is running locally on `http://localhost:8000`.
2. Serve the static assets:
   ```bash
   uv run python -m http.server --directory client 5173
   ```
3. Open `http://localhost:5173` in the browser. Use the channel input to load history for specific paths (e.g. `alpha.beta`).

## Implementation Notes

- Design tokens map to the Tokyo Night palette (`#1a1b26` background, `#7aa2f7` accents) with Fira Code for all UI text.
- `client/app.js` polls the REST endpoints (`/v1/layout`, `/v1/messages/{channel}`) and renders layout cards plus a message list.
- Update the API origin by setting `localStorage.setItem('tree-signal.api', 'http://your-host:port')` in the developer console.

## Linting & Formatting

- Run `uv run python -m http.server --directory client` before committing to ensure the assets load and there are no console errors.
- Use a formatter like `prettier` if you expand the client; current files follow two-space indentation for HTML/JS and align with project ASCII policy.
