# Phase 1 artwork provenance and missing assets

The owner package was read in full: `CODEX_PHASE1_BUILD_PROMPT.md` and `NEXUS_FINAL_DESIGN_SPEC_V1.md` (2026-10-08). All four boards were visually inspected:

- Nexus Academy UI Concept Board-3.png
- Nexus Academy Dark UI Concept-2.png
- Nexus Academy UI Design Board-1.png
- nexus_academy_dashboard_style_guide.png

The boards remain local review references. No board, board crop, franchise character, external image URL, or font file is included in this PR. The Stage 0 teaching pack is outside Phase 1 and was not imported.

## Supplied asset limitation

The archive contains composite reference boards, not cleared standalone production assets. Therefore the implementation follows the brief's explicit fallback: **asset slots and compositing styles**, with no substitute stock images or character art. This is a functional shell prototype awaiting its cinematic artwork. It does not meet the finished castle/protagonist/shadow-army fidelity examples yet.

| Slot | Composition | Asset needed |
| --- | --- | --- |
| `castle` | Hero background, cover, center; reused subtly at sidebar foot | Original daylight and moonlit panoramic castle scenes, suggested 2400×900 or larger |
| `shadow-army` | Lower right background; 50% opacity, below the protagonist | Cleared transparent shadow silhouettes with no franchise likeness |
| `hooded-protagonist` | Off-center right, contain, bottom anchored | Original faceless hooded figure as a transparent cutout, day/night variants |
| Brand monogram | Header | Standalone owner-approved stylized N artwork matching the intended identity |

`AcademyScene.jsx` reserves these decorative layers with `aria-hidden`. `academy.css` exposes `--academy-castle-art`, `--academy-protagonist-art`, and `--academy-shadow-art`, all `none` until assets are provided. Bind local cleared files under `frontend/public/academy/` in the light selector and override them in `.dark .academy-shell`; record source, creator, and usage clearance here first. This is a future review step, not permission to add arbitrary art.

The atmosphere is original CSS: blue/violet gradients and a simple day/night orb. The strong scrim protects the next-task copy; narrow layouts use a nearly opaque scrim. Approved art will require another screenshot and contrast review after compositing.

The header currently reuses `frontend/public/favicon.svg`, the existing repository N mark at verified main `663d623`. This PR does not introduce a new logo or claim that the favicon is the stylized logo in the boards. The requested standalone original logo is still missing.

Typography uses installed local/system fallbacks, with Poppins/Avenir Next preferences for display headings. No remote font calls or new font files are introduced. Commands retain the existing monospace rendering.
