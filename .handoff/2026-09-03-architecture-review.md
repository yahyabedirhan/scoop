# Scoop architecture handoff

Both accepted architecture candidates and the interface/documentation follow-ups
are implemented. No further structural refactor was recommended.

## Session context and change map

The user requested a low-level design review informed by the vault's design
principles and patterns articles, adapted to a small JavaScript extension.
The review identified two concrete ownership problems: an old clipboard result
could stop a newly started inspection, and copying a page ancestor could include
Scoop's own UI. The user approved both fixes and chose page HTML without Scoop's
additions, then requested a narrower controller interface and cohesive
current-state documentation.

```diff
 Scoop
 ├── content.js
-│   exposes toggle, start, stop, isActive
-│   copy completion uses whichever inspection exists
+│   exposes only toggle
+│   each copy belongs to its originating inspection
+│   duplicate copy requests wait; failures allow retry
+│   fallback textarea always gets cleaned up
 │
+├── lib/page-content.js
+│   owns injected nodes and temporary class/style changes
+│   copies page HTML without Scoop’s additions
+│   preserves page-owned content and edits
 │
 ├── lib/dom-nav.js
 │   existing navigation design retained
 │
+├── test/content.test.js
+│   12 behavior tests alongside 12 navigation tests
 │
 ├── README.md
+│   lifecycle diagram and ownership rules
 └── .specs/00-scoop.md
+    cohesive description of the current implementation
```

Stale copies cannot stop a new inspection; copying `<body>` or `<html>` excludes
Scoop's UI. Additional copy requests during a pending write are ignored, not
queued. All 24 tests and the controlled Chrome checks pass; real clipboard
permissions still need an unpacked-extension check.

## Read first

- [Current specification](../.specs/00-scoop.md) is the authoritative description
  of architecture, inspection ownership, page-content fidelity, and limitations.
- [README](../README.md) contains the file map, lifecycle diagram, and local
  development instructions.
- [Content tests](../test/content.test.js) capture the regression behavior.

## Completed and verified

The controller owns pending copies per inspection and exposes only `toggle()`.
The page-content module owns temporary DOM changes and captures page HTML without
Scoop additions. Navigation retains its existing design. The specification was
rewritten cohesively around the current implementation.

All 24 tests, JavaScript syntax checks, and whitespace checks passed. Standards
and Spec reviews found no actionable issues. A temporary Chrome harness verified
snapshot fidelity, page-edited `!important` preservation, stale-copy restart,
and ancestor capture using a controlled clipboard.

## Continuation

TODO: If validating the installed extension, reload it and the target page, then
check real clipboard permissions, input suppression, scrolling, and feedback.
The controlled browser harness did not establish real clipboard permission or
user-gesture behavior. No implementation task remains from this review.

Keep plain JavaScript and the no-build packaging. The user wants design
principles applied pragmatically, without imposed OOP or speculative modules.
Keep the specification about current behavior; session history belongs in
handoffs and the vault log. The user authorized committing this architecture
work together with its tests, documentation, and this handoff.

## Suggested skills

- `codebase-design` for a concrete future module/interface decision.
- `diagnosing-bugs` if the browser check exposes a failure.
- `show-me` for concise visual explanations.
