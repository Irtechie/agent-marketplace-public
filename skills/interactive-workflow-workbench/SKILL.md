---
name: interactive-workflow-workbench
description: Create evidence-grounded interactive HTML workbenches with a scrollable overview topology and separate human-readable workflow pages. Each drill-in page shows one coherent start-to-terminal path with ordered steps, limited visible complexity, labeled decisions, bounded repair loops, evidence, and explicit outcomes. Use for interactive workflows, architecture workbenches, clickable step-through flows, decision maps, learning paths, and control-plane visualizations.
---

# Interactive Workflow Workbench

Create a real, evidence-backed interactive workbench rather than a decorative
diagram.

Open `examples/review-gate-workbench.html` for a small, self-contained reference.
It deliberately allows a broad overview page, then separates the normal review
and repair workflows into readable path pages. Reuse that information
architecture, not its subject matter or unsupported claims.

## Establish the Inputs

Resolve these from the request, asking only for values that cannot be determined
safely:

- subject or primary question;
- authoritative repositories, folders, documents, or live systems;
- authoritative output path;
- audience and optional share-copy location;
- whether a README or static preview must be refreshed.

## Preserve the Evidence Boundary

Before mapping:

1. Resolve the exact owner.
2. Inspect only that owner and explicitly named dependencies.
3. Do not infer that similarly named sibling systems share ownership.
4. Prefer current source, runtime contracts, tests, architecture documents,
   manifests, and observed output.
5. Separate current, planned, experimental, deprecated, and uncertain behavior.
6. Timestamp live state and keep it distinct from durable architecture.
7. Stop and resolve contradictory ownership or factual claims before editing.

User corrections govern intent, ownership, scope, and terminology. Evidence
governs factual claims.

## Build the Workbench

### 1. Map the system

Build an internal evidence model containing:

- actors and authority boundaries;
- inputs, outputs, and state transitions;
- components and sources of truth;
- distinct paths, modes, roles, or sub-workflows;
- gates, validation, proof, and human approval;
- failures, retries, fallback, blocked states, and recovery;
- dependencies, causal edges, lifecycle states, and source pointers.

Do not start visual layout until the model is coherent.

### 2. Choose tabs and steps

Use top tabs when the subject has multiple paths, domains, roles, or modes.

- Add an `Overview` or `Full Topology` tab for systems, ownership, dependencies,
  trust boundaries, and entry/exit points. This page may be large and scrollable.
- Treat the overview as a map, not as proof that the workflow is understandable.
- Give each distinct human scenario or outcome path its own tab and ordered step
  list. Prefer more focused tabs and steps over one overloaded diagram.
- Reset the left rail to `1..X` inside each selected tab.
- Encode tab and step in the URL fragment, such as
  `#tab-control-plane-step-3`.
- Let overview components open their corresponding workflow tabs.

Every selected step must identify participating nodes and active edges, explain
what happens, show proof or acceptance, show failure or fallback behavior, list
evidence, provide a short talk track, and state the likely caveat.

### 3. Make every drill-in a readable workflow page

The overview may be a topology dump. Every other tab must read like an actual
workflow a person can follow without reverse-engineering the system map.

Each drill-in tab must:

- represent one coherent scenario, role, mode, or outcome path;
- start with an explicit trigger or entry state;
- present a dominant reading direction: left-to-right or top-to-bottom;
- keep the normal path visually obvious before showing exceptions;
- place each decision next to the action that raises it;
- label every outgoing branch with concrete language such as `Pass`, `Fail`,
  `Yes`, `No`, `Retry 1/2`, `Escalate`, or the typed failure;
- end every branch at an explicit success, blocked, escalated, cancelled, or
  failed state;
- omit nodes and edges that do not participate in that tab's scenario;
- use the inspector for evidence and explanation instead of packing prose into
  the graph.

Default drill-in complexity limits:

- at most 12 visible nodes;
- at most 2 decision diamonds;
- at most 2 simultaneously visible exception branches;
- at most 14 visible edges;
- no unlabeled cross-lane edge;
- no edge crossing through a node card.

If a truthful path exceeds a limit, add another workflow tab or sub-workflow
page. Do not shrink text, stack cards, or route spaghetti around the canvas to
keep it on one page. Scrolling is allowed when it preserves readable spacing;
scrolling does not excuse an ambiguous path.

Never reuse the full overview graph as the canvas for a drill-in tab with most
nodes merely dimmed. Render a path-specific graph so irrelevant topology is not
present.

### 4. Build coordinated graphs

Use custom HTML and SVG node cards and paths rather than Mermaid. Provide:

1. An overview topology for systems, actors, boundaries, dependencies, and
   entry/exit points. It may contain the complete system map.
2. Separate path-specific workflow graphs for ordered actions, decision gates,
   labeled branches, bounded retries, approval gates, and terminal states.

Use these node types:

- `process`: ordinary action or state;
- `decision`: diamond containing a question;
- `gate`: emphasized decision requiring proof, policy, risk, or human authority;
- `artifact`: receipt, manifest, document, output, or stored evidence;
- `external`: person, customer, provider, or system outside the owning flow;
- `terminal-success`, `terminal-blocked`, and `terminal-failure`.

Label every decision edge. State the ceiling or exit condition for every retry
loop. End failure paths in repair, escalation, a typed blocker, cancellation, or
failure rather than silently rejoining success.

Use semantic colors over a dark surface with high-contrast text:

- blue: active flow and ordinary execution;
- yellow: gates, decisions, warnings, and human authority;
- green: proof, validation, receipts, and success;
- red: failure, blocked states, rejection, and danger.

Color must communicate structure rather than decoration.

### 5. Let topology choose the canvas

- Use wide canvases for request/response pipelines.
- Use tall canvases for hierarchies and lifecycles.
- Use large scrollable canvases for dense infrastructure or dependency graphs.
- Size swimlanes to their content.
- Fit and zoom responsively without destroying readable spacing.
- Split dense graphs into overview and path tabs instead of forcing every edge
  into one view. A path tab must use its own reduced graph, not a filtered
  full-topology graph.

### 6. Implement the interaction contract

Include:

- fixed or sticky identity bar;
- top tabs and per-tab numbered left rail;
- central graph and evidence inspector;
- previous/next navigation and keyboard controls;
- autoplay/pause;
- light/dark toggle with dark as default;
- URL-fragment state and final full-system state;
- overview-to-workflow drill-in where appropriate.

Use `addEventListener` for computed interactions.

### 7. Keep claims disciplined

- Use real names and current contracts.
- Expand acronyms only when evidence supports the expansion.
- Mark unsupported and planned paths visibly.
- Do not treat prose, screenshots, route receipts, health checks, or model
  confidence as correctness proof.
- A receipt proves attribution; executable proof establishes acceptance.
- A passing command proves only its covered behavior.
- Never include credentials, tokens, private keys, or literal secret values.

### 8. Produce self-contained share output

When sharing is requested, create sandbox-safe HTML with:

- inline CSS and JavaScript only;
- no external scripts, styles, fonts, images, or network calls;
- no browser storage, cookies, popups, forms, workers, frames, objects, or
  embeds;
- no module imports;
- URL hash for state and UTF-8 metadata.

Keep the authoritative copy with the owning project. When a share copy is
requested, make it byte-identical.

### 9. Refresh a static preview when needed

Render the final overview state to PNG, link the README preview image to the
HTML, and label it as a preview rather than the primary deliverable.

## Verification Gate

Before reporting completion:

1. Parse the HTML.
2. Validate tab, step, node, and edge indexes.
3. Prove deep links restore the expected tab and local step number.
4. Verify every tab's rail starts at 1 and ends at X.
5. Verify every non-overview tab has an explicit entry, ordered main path, and
   explicit terminal outcome.
6. Verify each non-overview graph stays within the default complexity limits or
   documents why another split would make the workflow less truthful.
7. Verify non-overview tabs omit nodes and edges unrelated to their scenario;
   reject a dimmed full-topology graph as a drill-in.
8. Verify decision nodes have labeled outgoing branches.
9. Verify retry loops have bounds or exit conditions.
10. Verify failure branches end in repair, escalation, blocker, cancellation, or
   failure.
11. Verify overview drill-ins select the intended workflow tab.
12. Verify required system names and current/planned distinctions.
13. Verify the file has no external resources, forbidden APIs, or storage.
14. Run a precise secret scan.
15. Verify authoritative and share copies are byte-identical when both exist.
16. Render and inspect the overview, every drill-in page, a decision branch,
   a retry or escalation loop, a success state, and a blocked or failure state.
17. At 100% zoom, perform the human comprehension check on every drill-in: within
   ten seconds a reviewer must be able to identify the trigger, normal next
   action, decision question, branch labels, and terminal outcome.
18. Fix clipping, overlap, crossing or detached edges, contrast, overflow, and
   misleading states, then re-render.
19. Run the owning repository's quality gate when repository files changed.

## Delivery

Report the authoritative, share, and preview paths; tab, step, node, and edge
counts; evidence roots; current/planned/uncertain boundaries; verification
performed; and committed or uncommitted status.
