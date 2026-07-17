# Wave 1 / Task 1 — CLI Labs Step Framework

WHAT TO BUILD
Extend the CLI Labs feature to support step-driven lessons. Current lessons (frontend/src/features/cli-labs/data/lessons/meet-the-cli.json) have objectives+triggers only. New lesson packs need an optional `steps` array per lesson with 6 step types: explanation, multiple-choice, observe, forward-decision, hex-input, frame-builder.

STEP SCHEMA (add to lesson JSON, optional field — existing lessons without steps keep working unchanged)

```json
"steps": [
  { "id": "s1", "type": "explanation", "title": "...", "body": "..." },
  { "id": "s2", "type": "multiple-choice", "title": "...", "question": "...", "options": ["A", "B", "C", "D"], "correctIndex": 1, "explanation": "..." },
  { "id": "s3", "type": "forward-decision", "title": "...", "question": "...", "options": ["Forward to g0/2 only", "Flood all ports in VLAN", "Drop the frame"], "correctIndex": 1, "explanation": "..." },
  { "id": "s4", "type": "hex-input", "title": "...", "question": "...", "answer": "0800", "accept": ["0800", "0x0800"], "explanation": "..." },
  { "id": "s5", "type": "frame-builder", "title": "...", "question": "...", "fields": ["Destination MAC", "Source MAC", "EtherType", "Payload", "FCS"], "correctOrder": [0,1,2,3,4], "explanation": "..." },
  { "id": "s6", "type": "observe", "title": "...", "body": "...", "objectiveIds": ["enter-privileged", "show-table"], "explanation": "..." }
]
```

Notes: forward-decision is an MCQ variant with a topology-flavored frame (same mechanics, distinct rendering label). observe steps complete when ALL listed objectiveIds (from the lesson's existing objectives array) are met via terminal commands. hex-input compares case-insensitive, trims whitespace, accepts any string in `accept` (fallback: exact match on `answer`). frame-builder: user orders shuffled fields; correct when arranged per correctOrder.

FILES TO EDIT/CREATE
1. frontend/src/features/cli-labs/components/StepPanel.jsx (NEW) — renders current step + step progress ("Step 3 of 6"), Continue button for explanation steps, answer widgets for interactive types. Wrong MCQ/hex answer: show inline "Not quite — try again" state, do NOT reveal answer, allow retry. Correct answer: show the step's explanation text in a success style, then Continue advances.
2. frontend/src/features/cli-labs/components/steps/McqStep.jsx, HexInputStep.jsx, FrameBuilderStep.jsx (NEW, small focused files; forward-decision reuses McqStep with a prop). FrameBuilder: click-to-place ordering (click field chips in sequence to build the frame left-to-right, with a reset button) — no drag-drop dependency.
3. frontend/src/features/cli-labs/components/LabRunner.jsx — when lesson.steps exists: render StepPanel above the terminal, track currentStepIndex state, gate lab completion on BOTH all steps completed AND existing isLabComplete() objective logic. observe steps auto-complete when their objectiveIds are all met in progress state (advance only when the observe step is the current step; if user completes objectives early, the observe step completes instantly when reached). Lessons without steps: zero behavior change.
4. frontend/src/features/cli-labs/engine/objectiveTracker.js — export helper isObjectivesMet(lesson, progress, objectiveIds) if not trivially derivable; keep immutable patterns (new objects, no mutation).
5. frontend/scripts/validate-cli-labs.mjs — extend validation: if steps present, validate each step id unique, type in the 6 allowed, MCQ/forward-decision have >=2 options and valid correctIndex, hex-input has answer, frame-builder fields length == correctOrder length and correctOrder is a permutation, observe objectiveIds all exist in lesson objectives. Clear error messages with lesson id + step id.
6. Do NOT modify meet-the-cli.json. Add a small step-schema sanity section to frontend/scripts/cli-engine-sanity.mjs that validates an inline step-demo lesson object exercising all 6 step types.

CONSTRAINTS
- Tailwind only, dark-mode variants like existing components (see ObjectivesPanel.jsx / CliLabsPage.jsx styles).
- Immutability: never mutate state objects; follow existing engine patterns (cloneState).
- Files under 400 lines each; extract widgets to steps/ subfolder.
- No new npm dependencies.
- Do not touch backend in this task.

ACCEPTANCE
- npm run cli:validate passes (run in frontend/).
- npm run cli:sanity passes.
- npm run build passes (use npm.cmd on Windows if npm.ps1 blocked).
- meet-the-cli lessons behave exactly as before (no steps field = no StepPanel rendered).
- Append summary entry to tasks/loop-log.md per project convention.
