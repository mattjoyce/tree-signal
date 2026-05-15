# Tab Mode for Tree Signal

## Overview

Add a tab-based navigation mode where each top-level channel (emitter) gets a dedicated tab, allowing users to focus on one subsystem at a time while preserving the ability to see the full hierarchy.

## Requirements

1. **Default to "All"**: Show full hierarchy on load
2. **Dynamic tabs**: New top-level channels auto-appear as tabs
3. **URL persistence**: Hash-based `/#tab=web` for sharing
4. **Close/pin**: Allow users to dismiss or pin tabs

---

## Architecture

### Backend (Minimal)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/channels` | GET | List top-level channel names (emitters) |

*Note: We reuse existing `/v1/layout` - client filters locally.*

### Client State (Alpine.js)

```
state:
  channels: []           // Top-level channels from API
  activeTab: 'all'      // Current tab ('all' or channel name)
  pinnedTabs: []        // Pinned channels (localStorage)
  closedTabs: []        // Dismissed channels (localStorage)
  
methods:
  loadChannels()        // Fetch + merge with pinned/closed
  cycleTab(direction)   // Cycle with Shift+TAB
  selectTab(name)      // Click handler
  closeTab(name)        // X button
  pinTab(name)         // Toggle pin
```

### URL Hash Format

```
/#tab=all      → Show all (default)
/#tab=web      → Show only "web" subtree
```

---

## UI Components

### Tab Bar Layout

```
┌──────────────────────────────────────────────────────────────┐
│ ┌────┐ ┌──────┐ ┌────┐ ┌────┐ ┌────┐            [All ▼]      │
│ │All │ │ web ✸│ │api │ │ db │ │auth│ ...                      │
│ └────┘ └──────┘ └────┘ └────┘ └────┘                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   [Full hierarchy rendered here when activeTab='all']       │
│   [Or filtered subtree for specific channel]                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Tab Item States

| State | Visual |
|-------|--------|
| Active | Solid background, bold text |
| Pinned | ✸ icon, persists when new channels arrive |
| Closed | Hidden from view, accessible via dropdown |
| Normal | Clickable, closeable |

### Interaction

- **Click tab**: Switch to that channel's subtree
- **TAB key**: Cycle forward: all → web → api → db → all...
- **Shift+TAB**: Cycle backward
- **Click ×**: Close tab (move to closedTabs)
- **Click ✸**: Pin/unpin tab

---

## Implementation Steps

### Step 1: Backend - List Channels Endpoint

```python
# src/tree_signal/api/main.py
@app.get("/v1/channels", response_model=List[str])
async def list_channels() -> List[str]:
    """Return top-level channel names (emitters)."""
    tree = get_tree_service()
    return list(tree.root.children.keys())
```

### Step 2: Client - Tab State Management

```javascript
// client/app.js - Add to app initialization
async function initTabs() {
  // Load persisted state
  const saved = localStorage.getItem('tree-signal-tabs');
  if (saved) {
    const { pinned, closed } = JSON.parse(saved);
    app.pinnedTabs = pinned || [];
    app.closedTabs = closed || [];
  }

  // Parse URL hash
  const hash = window.location.hash;
  if (hash.startsWith('#tab=')) {
    app.activeTab = hash.replace('#tab=', '');
  }

  // Start polling for channel updates
  await app.loadChannels();
  setInterval(app.loadChannels, 5000);
}
```

### Step 3: Tab Bar Component (HTML/CSS)

- Horizontal scrollable tab bar
- Fixed "All" tab first
- Dynamic channel tabs
- Dropdown for closed tabs

### Step 4: Layout Filtering

```javascript
// Filter layout frames by active tab
function getFilteredLayout(frames, activeTab) {
  if (activeTab === 'all') return frames;
  
  return frames.filter(frame => {
    const topLevel = frame.path[0];
    return topLevel === activeTab;
  });
}
```

### Step 5: Keyboard Navigation

- `Tab`: Forward cycle
- `Shift+Tab`: Backward cycle
- Only when no input focused

### Step 6: Persistence

- localStorage for pinned/closed tabs
- URL hash for active tab

---

## File Changes

| File | Change |
|------|--------|
| `src/tree_signal/api/main.py` | Add `/v1/channels` endpoint |
| `src/tree_signal/api/schemas.py` | Add response schema |
| `client/index.html` | Add tab bar HTML |
| `client/app.js` | Add tab state + filtering + keyboard |
| `client/styles.css` | Tab bar styles |

---

## Testing Scenarios

1. ✓ "All" default on fresh load
2. ✓ Click tab shows filtered layout
3. ✓ New channel appears as new tab
4. ✓ Close tab hides it, dropdown shows it
5. ✓ Pin tab persists across refresh
6. ✓ URL `/#tab=web` loads web view
7. ✓ TAB key cycles through tabs
8. ✓ Layout updates when switching tabs

---

## Optional Future (Out of Scope)

- Drag to reorder tabs
- Color-coded tabs by severity
- "New messages" badge on tabs