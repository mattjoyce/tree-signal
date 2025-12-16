# Tree Signal Layout UX Problems

## Document Purpose
This document captures UX inefficiencies in the current hierarchical panel layout system. It serves as a reference for understanding the problems before designing solutions.

**Status:** Problem statement only - no solutions proposed yet
**Date:** 2025-12-16
**Affected Components:** `src/tree_signal/layout/generator.py`, `client/app.js`

---

## Problem Overview

The current layout system creates unnecessary intermediate containers and allocates screen space inefficiently, resulting in poor space utilization and visual clutter when displaying hierarchical message channels.

---

## Problem 1: Unnecessary Intermediate Containers

### Current Behavior
When a message is sent to a hierarchical channel like `this.that.other`, the system **always** creates containers for every path segment:

1. `this` (root level container)
2. `this.that` (intermediate container)
3. `this.that.other` (leaf container with the message)

### The Issue
If only `this.that.other` exists (no sibling channels), then:
- `this` has **no messages** and **only one child** (`this.that`)
- `this.that` has **no messages** and **only one child** (`this.that.other`)
- These intermediate containers provide **no value** - they're just pass-through nodes

### When Intermediate Containers ARE Valuable
An intermediate container like `this.that` is valuable when:
1. **It has its own messages** (user explicitly sent messages to `this.that`), OR
2. **It has multiple children** (e.g., both `this.that.other` AND `this.that.omg` exist)

### Visual Impact
```
Current (wasteful):
┌─────────────────────────────────────┐
│ this (empty, single child)          │
│ ┌─────────────────────────────────┐ │
│ │ this.that (empty, single child) │ │
│ │ ┌─────────────────────────────┐ │ │
│ │ │ this.that.other             │ │ │
│ │ │ "foo"                       │ │ │
│ │ └─────────────────────────────┘ │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘

Desired (efficient):
┌─────────────────────────────────────┐
│ this.that.other                     │
│ "foo"                               │
└─────────────────────────────────────┘
```

### Example Scenarios

#### Scenario A: Single Deep Channel
```bash
# Only one channel exists
./tree-signal --channel this.that.other "foo"
```
**Current:** Creates 3 containers (wasteful)
**Desired:** Should show only the leaf container or collapsed representation

#### Scenario B: Multiple Children at Same Level
```bash
# Two sibling channels
./tree-signal --channel this.that.other "foo"
./tree-signal --channel this.that.omg "bar"
```
**Current:** Creates `this`, `this.that`, `this.that.other`, `this.that.omg`
**Desired:** `this` is still unnecessary (single child), but `this.that` IS valuable (has 2 children)

#### Scenario C: Intermediate Container Gets Messages
```bash
# Intermediate container receives its own message
./tree-signal --channel this.that "important"
./tree-signal --channel this.that.other "foo"
```
**Current:** Creates 3 containers
**Desired:** All 3 containers are valuable now (root still questionable, but `this.that` has messages)

---

## Problem 2: Wasted Space in Empty Parent Containers

### Current Behavior
Located in `src/tree_signal/layout/generator.py:60-66`:

```python
# Determine parent size based on whether it has messages
history = tree.get_history(node.path) if include_self else []
has_messages = len(history) > 0

# Parent gets 50% height if it has messages, 20% if empty (greedy children)
parent_fraction = 0.5 if has_messages else 0.2
children_fraction = 1.0 - parent_fraction
```

### The Issue
Even when a parent container has **no messages**, it still allocates **20% of vertical space** for its message area. This space shows an empty container with no content.

### Visual Impact
```
Current Layout (parent with no messages):
┌─────────────────────────────────────┐
│ this.that          │ state: ACTIVE  │ ← Header
├─────────────────────────────────────┤
│                                     │ ← 20% wasted space
│          (empty message area)       │    (parent_fraction = 0.2)
│                                     │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ this.that.other                 │ │ ← 80% for children
│ │ "foo"                           │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Debug Evidence
When debug mode is enabled (`?debug=true`), the metrics display shows:
```
w=1.00 // 1.00×0.20
```
- Weight: 1.00
- Dimensions: width 1.00 × height **0.20**

The 0.20 height confirms the container is taking 20% vertical space despite having no messages.

### When Space Allocation IS Appropriate
A parent should allocate message space when:
- **It has messages** (50% allocation is correct)
- Otherwise, it should take **0% or minimal space** for just the header/border

---

## Problem 3: Compounding Effect

Problems 1 and 2 compound each other:

### Example: Deep Single Path
```bash
./tree-signal --channel app.services.auth.login.validate "checking credentials"
```

**Current Result:**
- Creates 5 containers: `app`, `app.services`, `app.services.auth`, `app.services.auth.login`, `app.services.auth.login.validate`
- Each of the first 4 containers:
  - Is unnecessary (single child, no messages) ← **Problem 1**
  - Takes 20% vertical space ← **Problem 2**
- Total wasted space: 4 containers × 20% each = significant screen real estate lost

**Visual:**
```
┌─────────────────────────────┐
│ app (20% wasted)            │
│ ┌─────────────────────────┐ │
│ │ app.services (20%)      │ │
│ │ ┌─────────────────────┐ │ │
│ │ │ app.services.auth   │ │ │
│ │ │ (20% wasted)        │ │ │
│ │ │ ┌─────────────────┐ │ │ │
│ │ │ │ ...login (20%)  │ │ │ │
│ │ │ │ ┌─────────────┐ │ │ │ │
│ │ │ │ │ ...validate │ │ │ │ │
│ │ │ │ │ "checking.."│ │ │ │ │
│ │ │ │ └─────────────┘ │ │ │ │
```

---

## Technical Root Causes

### Root Cause 1: Unconditional Node Materialization
**Location:** `src/tree_signal/layout/generator.py:34-56`

The `_populate_frames` method creates a layout frame for every node in the tree, regardless of whether that node provides value. There's no logic to skip or collapse single-child chains.

### Root Cause 2: Fixed Space Allocation
**Location:** `src/tree_signal/layout/generator.py:64-66`

The parent fraction is hardcoded to either 50% (has messages) or 20% (no messages). There's no option for 0% allocation when a parent truly needs no message display space.

---

## Design Constraints & Considerations

Before implementing any solution, consider:

### 1. Dynamic Tree Evolution
- Channels appear and disappear as messages arrive and decay
- A single-child chain can become a branching tree at any moment
- Layout must handle transitions gracefully (though re-layout on change is acceptable)

### 2. User Mental Model
- Users think in hierarchical namespaces (e.g., `project.component.feature`)
- Collapsing too aggressively might hide important structural information
- Full paths should remain visible/accessible somehow

### 3. Message Lifecycle
- Messages have TTL and decay over time
- A parent with messages can become empty (messages expire)
- Empty parents should potentially collapse when they become unnecessary

### 4. Performance
- Layout recalculation happens on every message and decay tick
- Solution should not add significant computational overhead

### 5. Client Rendering
- Client code in `client/app.js` normalizes rectangles relative to parents
- Assumes nested DOM structure matches tree hierarchy
- Major layout changes may require client-side updates

### 6. Edge Cases
- What happens with single root-level channels? (`app` vs `app.feature.x`)
- How to handle rapid channel additions that change tree structure?
- Should manually locked panels behave differently?

---

## Success Criteria

A successful solution should:

1. **Eliminate unnecessary containers** - Don't create intermediate nodes that provide no value
2. **Optimize space allocation** - Don't waste screen real estate on empty message areas
3. **Maintain clarity** - Users can still understand hierarchy and navigate channels
4. **Handle dynamics** - Layout adapts correctly as channels come and go
5. **Preserve information** - Full channel paths remain accessible
6. **Perform well** - No significant performance degradation

---

## Open Questions

1. **Collapsing Strategy:**
   - Should we collapse single-child chains into a single panel with full path label?
   - Or skip intermediate nodes entirely and promote leaves up the tree?
   - Or use a hybrid approach?

2. **Space Allocation:**
   - Should empty parents get 0% space, or some minimal amount for visual separation?
   - How does this interact with gaps/padding between panels?

3. **Transition Behavior:**
   - When a collapsed chain expands (new sibling added), how jarring is the layout shift?
   - Should there be visual continuity, or is instant re-layout acceptable?

4. **User Control:**
   - Should users be able to force certain nodes to always appear?
   - Should locked panels prevent collapsing?

5. **Label Display:**
   - For collapsed chains, show full path (`this.that.other`) or just leaf (`other`)?
   - How to indicate depth/hierarchy when intermediate nodes are hidden?

---

## Next Steps

1. Review and validate this problem statement with stakeholders
2. Gather answers to open questions
3. Explore potential solution approaches (separate document)
4. Prototype on local development instance
5. Test with real-world usage patterns
6. Document chosen solution and rationale
