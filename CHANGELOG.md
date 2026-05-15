# Changelog

All notable changes to Tree Signal are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Fixed

- **Decay weight now actually decays.** `schedule_decay` was a documented
  "Phase 1 placeholder" that propagated fade deadlines but never reduced
  weight, *and* nothing on the request path called it. Panels held full
  weight until they were hard-pruned, then popped out — a discontinuous
  rebalance instead of a smooth fade. `ChannelNodeState.apply_decay` now
  fades weight linearly across the `[fade_start, fade_deadline]` window,
  and the `/v1/layout` handler drives the time step explicitly.
- **Panel state labels were inverted.** State resolution reported `ACTIVE`
  during the decay window and `FADING` only after the fade deadline (the
  zone where panels are actually gone). Now: in-hold → `ACTIVE`,
  in-decay → `FADING`, past deadline → `REMOVED`.
- **`README.md` excluded from the Docker build context.** `.dockerignore`
  matched `*.md`, but `pyproject.toml` declares `readme = "README.md"`, so
  `uv pip install .` failed in the container. Added a `!README.md`
  negation.
- **API tests broke on httpx ≥ 0.28.** All four `tests/api/*` files used
  `AsyncClient(app=...)`, removed in httpx 0.28. Migrated to the explicit
  `AsyncClient(transport=ASGITransport(app=app), ...)` form, which works
  on old and new httpx alike. Full suite now 47/47.

### Added

- **Bounded weight accumulation.** A per-node weight cap (default `10.0`,
  `configure_max_weight(...)` to tune or disable). Without it a high-rate
  channel grows unbounded and swamps quiet siblings sharing the screen.
- **`ChannelTreeService.tick(now)`** — the explicit time-evolution step
  (decay then prune). Previously this work was a hidden side effect of
  `LinearLayoutGenerator.generate()`.
- **`ChannelNodeState.state_at(now)`** — a node owns its own lifecycle
  state instead of the generator hardcoding the rules.
- Layout config profiles (`compact`, `minimal`, `spacious`) via
  `LinearLayoutConfig`.

### Changed

- **Decomplected time evolution from rendering** (Hickey). `generate()` is
  now a pure read — the layout is a function of the tree at one moment.
  Callers invoke `tick(now)` to advance simulated time.
- **Split `cleanup_expired`** into `_expire_messages` and
  `_prune_empty_leaves` — one named responsibility each. The empty-leaf
  grace window is now `ChannelTreeService.EMPTY_NODE_LIFESPAN`.
- **Removed defensive dead code** (Armstrong, let-it-crash). The
  `try/except/pass` around `prune` in cleanup guarded against a
  `ValueError` that the loop already makes impossible; the
  `if span <= 0` branch in `apply_decay` masked an invariant that holds by
  construction. Both replaced with surfacing behaviour (drop the guard /
  `assert`). Removed `_resolve_state`, a pure passthrough that added an
  indirection layer with no behaviour.

### Deployment

- New `unraid_admin/tree-signal/` deployment folder following the parsem
  pattern: build context is the NAS clone (no git/python on the Unraid
  host), recipe + config rsynced to appdata, `update.sh` drives the
  upgrade. Single port 8013 (the old 8014 static-client port is gone —
  FastAPI serves the dashboard from `/`).
