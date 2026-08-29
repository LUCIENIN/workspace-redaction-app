# Design QA

- Source visual truth: session-local ImageGen result `exec-4a9a1f88-6ce8-4798-91c5-a5ba2c6257e3.png` (not committed).
- Implementation screenshot: `.tmp/implementation-1440x1024-final.png` (not committed).
- Mobile screenshot: `.tmp/implementation-390x844-final.png` (not committed).
- Full comparison: `.tmp/design-comparison-final.png` (not committed).
- State: initial page load with the local snapshot available; copy control focused after interaction.

## Normalization

- Source pixels: 1487 × 1058.
- Source normalized pixels: 1425 × 1013.
- Implementation browser viewport: 1440 × 1024 CSS px at density 1.
- Implementation capture pixels: 1425 × 1013; browser scrollbars account for the smaller captured content area.
- Mobile browser viewport: 390 × 844 CSS px at density 1.
- Mobile capture pixels: 375 × 812; measured document width is 375 px with no horizontal overflow.

## Findings

No actionable P0, P1, or P2 differences remain.

- Fonts and typography: the implementation preserves the source's compact sans-serif hierarchy and restrained monospace labels. It uses system fonts instead of a network font so the privacy tool remains dependency-free and works offline.
- Spacing and layout rhythm: the two-column hero, three-step desk, boundary ledger, and four trust principles match the source hierarchy. The implementation keeps more breathing room around long Chinese copy and preserves the primary action above the fold.
- Colors and visual tokens: warm paper, deep forest green, mint, ink, and restrained red map closely to the source. Contrast remains clear in light and dark sections.
- Image quality and assets: the selected design contains no required photography or custom illustration. Decorative mock icons were omitted instead of approximated with inline SVG, CSS drawings, emoji, or a new icon dependency.
- Copy and content: the implementation uses the repository's real Python command and explicitly states that scanning is a gate rather than proof. Snapshot figures remain secondary and are labeled static.
- Accessibility: skip link, visible focus, semantic headings, tab roles, selected states, high-contrast controls, and 44 px minimum primary controls are present.

## Comparison History

1. First pass — P2: the hero title rendered as three oversized lines instead of the source's two-line composition. Fixed by widening the hero frame, rebalancing the columns, and tightening the display size. Post-fix evidence: `.tmp/implementation-1440x1024-final.png`.
2. Second pass — P1: the mobile layout expanded to 515 px in a 390 px viewport, and the copy action did not write to the browser clipboard. Fixed with zero-minimum grid tracks, mobile snapshot reflow, and a selection-based copy fallback. Post-fix evidence: `.tmp/implementation-390x844-final.png`; final clipboard value exactly matches the displayed scan command.
3. Final pass — desktop and mobile screenshots inspected; privacy-zone and architecture controls changed state correctly; browser console produced no warnings or errors.

## Primary Interactions Tested

- Copy command writes `python3 scripts/sanitize_workspace.py scan . --fail-on high` to the browser clipboard.
- Selecting `Wiki 生成层` sets its tab to `aria-selected=true` and refreshes the detail panel.
- Selecting `混合检索` activates the correct architecture detail.
- Snapshot JSON loads and is presented as static evidence, not a safety result.

## Follow-up Polish

- P3: a future release could add a vetted local icon asset set, but it is intentionally excluded from this dependency-free privacy tool.

final result: passed
