# BSPMsg Hierarchical Layout Prototype

## Purpose
- Capture the current design direction for a treemap-based successor to BSPMsg.
- Provide enough structure for sprint planning while acknowledging unresolved questions.
- Serve as the single reference for future design additions and clarifications.

## Vision & Goals
- Replace strictly binary partitions with an n-ary adaptive layout driven by channel activity.
- Use hierarchical channel addresses (`project.component.subsystem`) to create consistent spatial groupings.
- Maintain the lightweight, log-style dashboard experience with smooth panel creation, growth, fade, and removal.
- Ensure the backend remains the authoritative source of truth for channel state and lifecycle events.

## Home Project Assumptions
- Single-maintainer, hobby-grade deployment with low to moderate message throughput.
- Preference for batteries-included defaults that minimise ongoing tuning and ops work.
- Happy to trade multi-tenant features and scale for simplicity and easy experimentation.

## Functional Scope (Initial Prototype)
- Accept messages tagged with hierarchical channel paths separated by `.` (e.g., `Project1.main.api`).
- Automatically materialise panels for each segment in the path and maintain an in-memory tree representing active nodes.
- Allocate screen real estate per level using a treemap algorithm that sizes panels by activity/decay weight and enforces minimum visibility.
- Stream incremental layout/state updates to clients over WebSocket; support a REST API for historical message retrieval per channel path.
- Provide opinionated default panel styling while allowing opt-in overrides for typography, wrapping, colours, and sizing.
- Support panel-level lifecycle controls: allow manual removal (pruning a node and all descendants/messages) and locking to prevent layout decay.
- Enforce a configurable maximum channel depth (default `-10` for experimentation while testing).
- Decay panel prominence over time: 
  - Shrink inactive panels while messages remain within TTL.
  - Transition panels into a fade state after TTL expiration.
  - Remove panels once grace periods elapse with no fresh activity.
- Panels and messages are ephemeral (in-memory); survive browser refresh but not service restarts unless later extended.

## Architecture Overview
## Technology Stack
- **Standard Library**: `asyncio`, `contextlib`, `dataclasses`, `datetime`, `enum`, `logging`, `pathlib`, `typing`, `uuid` (message IDs), `argparse` (CLI entrypoint), `json` (config/protocol tooling).
- **Frameworks**: `FastAPI` for HTTP/WebSocket endpoints, `uvicorn` as the ASGI server.
- **Data & Validation**: `pydantic` v2 for request/response schemas, with direct `aiosqlite` access for persistence; ORM abstractions can arrive later if required.
- **Async Utilities**: `anyio` (via FastAPI), plus optional `asyncio.TaskGroup` patterns for coordinated background jobs.
- **Testing & Tooling**: `pytest`, `pytest-asyncio`, `httpx` (async client for tests), `mypy`, `black`, `isort`.
- **Optional Enhancements (future)**: add structured logging (`structlog`/`loguru`), metrics export (`prometheus_client`), or shared-state tooling (`redis`) only if real usage justifies the extra weight.

- **Core Services**
  - FastAPI application exposing REST + WebSocket endpoints.
  - Layout engine module responsible for:
    - Maintaining hierarchical trees.
    - Computing treemap geometries (likely slice-and-dice to start, with squarified treemap as a stretch goal).
    - Applying activity weighting and decay each tick.
  - Persistence handled by a lightweight SQLite module (async `aiosqlite` helpers); richer abstraction can follow if future requirements demand swapping backends.
- **Data Model**
  - Messages carry: channel path, payload blob/string, optional metadata, timestamp, severity.
  - Channel nodes maintain: path, parent, current weight, last message time, fade deadline, child ordering metadata.
  - Layout frames describe: node path, rectangle (x, y, width, height), state (`active`, `fading`, `removed`), weight snapshot.
- **Lifecycle Scheduler**
  - Periodic async task that:
    - Applies globally configured linear decay (defined by `hold_secs` and `decay_secs`) unless a panel (or ancestor) is locked.
    - Triggers state transitions (`active` → `fading` → `removed`) and respects manual deletions.
    - Recomputes layout rectangles and broadcasts diffs to clients.
  - Must handle concurrency with inbound message processing (likely via an internal asyncio queue or locking).

## Panel Presentation & Customisation
- Panels render with auto-generated defaults so first-run setups require no manual tuning.
- Client DOM nests child panels inside their ancestors, with geometry normalised relative to parent rectangles so treemap descendants remain visually contained.
- Each node in the hierarchy may override aspects such as word wrapping behaviour, fonts, colour palettes, and minimum/maximum footprint; unspecified fields inherit from the nearest ancestor.
- Split directions (horizontal/vertical sequencing inside the treemap) can be set at any node and inherited by descendants, with server defaults applied when undefined.
- Style profiles (bundled typography/colour/layout settings) are a stretch goal; MVP ships with sensible defaults and selective per-node overrides only.
- Client should support live updates when profiles or overrides change, keeping runtime adjustments frictionless.
- Deleting a panel removes its subtree and associated messages; locking a panel freezes its layout weight while message TTL still applies.
- Panel locking propagates upward so ancestors remain visible while any descendant is locked or still holds active messages.
- Panel state (locks, overrides) is stored in-memory; persistence across service restarts is out-of-scope for MVP.

## API Surface (Draft)
- `POST /v1/messages`: submit a message (requires auth key); validates channel path, writes to store, schedules layout update.
- `GET /v1/messages/{channel_path}`: retrieve recent messages, supports pagination.
- `GET /v1/layout`: debug endpoint returning the latest full layout snapshot.
- `WebSocket /v1/stream`: push channel/layout deltas (`[{path, state, weight, rect}]`).
- `POST /v1/panels/{path}/lock`: lock or unlock a panel to freeze/unfreeze decay (server records lock state).
- `DELETE /v1/panels/{path}`: remove a panel subtree along with all messages.
- `POST /v1/control/reload`: optional admin endpoint to reload config (requires elevated auth).

## Security & Auth
- Mandatory `x-api-key` header on all mutating endpoints, validated against server configuration or secure storage.
- Start with a single shared `x-api-key`; advanced schemes such as per-prefix keys or reserved top-level panels can be layered in later.
- Enforce channel path validation (allowed characters, max depth, max length per segment) before processing messages.
- Ensure WebSocket connections require the same key (query param/header) before subscribing to updates.

## Deployment & Operations
- Target systemd service deployment:
  - Provide sample unit file with environment file override (`EnvironmentFile=/etc/bspmsg/bspmsg.env`).
  - Support graceful shutdown and readiness/health probes (`GET /healthz`).
  - Log to stdout/stderr with optional structured logging for journald.
- Configuration hierarchy:
  - Base YAML/TOML config committed with defaults.
  - Environment overrides for secrets/keys.
  - Hot-reload mechanism via admin endpoint or SIGHUP.
- Observability baseline:
  - Structured logs including channel path and message metadata.
  - Basic metrics (messages per minute, active panels, connection count) exposed via Prometheus-compatible endpoint (future sprint).

## Client Strategy
- Initial client: lightweight HTML/CSS with Alpine.js for interactivity; keep protocol generic so other clients can be trialled later.
- Define a stable client protocol (JSON schema) so non-web clients (e.g., Qt, Electron) can reuse.
- Plan for theming and custom min/max panel size policies, but keep out of MVP until behaviour is validated.
- Stretch goal: keyboard navigation between panels (shortcut-driven focus cycling) once base UI is stable.

## Phased Delivery
1. **Phase 1 – Simplest Viable Dashboard**
   - FastAPI endpoints with in-memory channel tree and hardcoded layout defaults.
   - Manual refresh HTML/JS client (e.g., Alpine.js) to validate hierarchical addressing.
   - Global linear decay timer (hold + decay seconds) operating on in-memory weights and manual panel removal controls.
2. **Phase 2 – Real-Time Enhancements**
   - Introduce WebSocket stream for live updates and remove manual refresh requirement.
   - Add configurable decay parameters via CLI/config and lock/unlock endpoints.
   - Experiment with alternative browser clients while keeping data ephemeral in memory.
3. **Phase 3 – Polish & Extras**
   - Layer in panel overrides, optional style profile system, CSS animations, and keyboard navigation.
   - Add config file support, optional systemd unit, and revisit logging/metrics needs.
   - Evaluate persistence/backups or advanced auth only if real usage demands it.

## Open Questions
- What UI affordances are needed if channel depth/width exceeds the default limits?
- Do we need lightweight audit trails for manual panel deletions or lock toggles?
- If style profiles arrive later, how will we version or audit overrides to avoid confusion?

## Next Steps
- Socialise this draft with stakeholders to confirm scope and priorities.
- Gather answers to open questions, then refine the spec with concrete requirements and acceptance criteria.
- Once clarified, convert roadmap into backlog tickets with estimates and dependencies.
