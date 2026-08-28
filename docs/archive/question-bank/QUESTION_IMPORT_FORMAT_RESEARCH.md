# Question Import Format Research

Research for the Part 6/7 importer work on `fix/question-bank-integrity-and-import`.
Goal: reduce manual question-authoring effort without replacing Nexus's own quiz
engine, Daily Review/FSRS scheduling, or progression system.

## Summary recommendation

| Format | Recommendation | Why |
|---|---|---|
| CSV | Implement now, stdlib `csv` | No dependency needed; simplest, safest option |
| XLSX | Implement now, `openpyxl` | MIT, mature, pure-Python parser, never executes formulas or macros |
| GIFT | Plan only | Format is simple enough to hand-roll a parser; no actively maintained Python library exists |
| IMS QTI | Plan only, low priority | XML standard is heavyweight; Python tooling is sparse/abandoned; high integration effort for low near-term value here |
| H5P | Do not integrate | Requires a PHP/JS runtime; out of scope per task instructions; no lightweight Python import path |
| Anki / FSRS libraries | Note only, no change now | `fsrs_service.schedule_next()` is a simplified ease-factor scheduler, not the real FSRS algorithm — worth knowing, out of scope for this task per explicit instruction not to touch scheduling without a proven bug |
| Moodle question-bank interop | Do not pursue | Moodle's own export formats (XML/Aiken) largely funnel through GIFT/QTI anyway; no added value beyond those two |

## CSV

- **Library**: Python stdlib `csv` module.
- **License**: PSF (n/a — stdlib).
- **Maintenance**: n/a, ships with Python.
- **Compatibility**: Python only; not needed on the frontend (upload is a raw file, parsed server-side).
- **Security**: CSV has no formula/macro concept — the only risk is CSV/Excel "formula injection" if a cell value starting with `=`, `+`, `-`, `@` is later opened in Excel by an admin. Mitigation: sanitize by prefixing a leading `'` (or rejecting) any imported text field that starts with those characters before it's ever re-exported (e.g. in an error-report download).
- **Integration effort**: trivial. Reads rows into dicts (`csv.DictReader`), each row maps directly onto the `question_validation.validate_question()` payload shape.
- **Replaces Nexus or imports content**: imports only, feeds the shared validator.

## XLSX

- **Library**: [`openpyxl`](https://openpyxl.readthedocs.io/) — MIT licensed, the de facto standard pure-Python `.xlsx` reader/writer.
- **Maintenance**: Mature/stable; release cadence has slowed (no major release in the last ~12 months as of this research) but it remains the standard choice, widely used, no known abandonment signal — slow release cadence is typical for a feature-complete parser, not itself a red flag. [openpyxl on PyPI/Libraries.io](https://libraries.io/pypi/openpyxl)
- **Compatibility**: Python only (backend-side parsing, same as CSV).
- **Security**: openpyxl is a pure XML/zip parser — it does not execute formulas or VBA macros under any circumstances. Load with `data_only=True` to read cached formula *results* rather than formula text, and never open `.xlsm` (macro-enabled) workbooks — reject that extension outright at upload. Zip-bomb style large-file risk is mitigated by the row/size limits already required in Part 7.
- **Integration effort**: low. `openpyxl.load_workbook(path, data_only=True, read_only=True)`, iterate `ws.iter_rows()`, map the header row to the same payload shape as the CSV path so both formats share one `_rows_to_questions()` function feeding the validator.
- **Replaces Nexus or imports content**: imports only.

## GIFT (Moodle's plain-text question format)

- **Format**: simple line-oriented plain text (`::Title:: Question text {=Correct ~Wrong}`), documented at [Moodle GIFT format docs](https://docs.moodle.org/en/GIFT_format).
- **Candidate libraries found**: `pygiftparserrgmf` (last released 2022), `fabiommendes/gift`, `gift-wrapper`. None show recent maintenance activity as of this research.
- **License**: varies by project (mostly MIT/BSD-style), but license doesn't matter much given the maintenance gap.
- **Recommendation**: don't take an external dependency on an unmaintained parser for a format this simple. When GIFT import is actually implemented, hand-roll a small parser (a few hundred lines) directly against the shared validator — GIFT's multi-select (`{~%50%A ~%50%B}`-style) and single-answer (`{=A ~B ~C}`) syntax both map cleanly onto the existing `options` + `correct_answers` payload shape.
- **Integration effort**: low-to-moderate if hand-rolled; not worth it via a third-party dependency.

## IMS QTI (1.2 / 2.1 / 3.0)

- **Format**: XML-based, designed for full interoperability across LMSs (Moodle, Canvas, Blackboard, etc.), but the spec is large — item banks, response processing, outcomes, sections, assessment structure.
- **Python tooling**: sparse and mostly abandoned; most real-world QTI tooling lives in Java (the QTI reference implementation ecosystem) or is embedded in a specific LMS's codebase.
- **Recommendation**: plan only, low priority. High integration effort for a format Nexus doesn't currently need to exchange with any other system. Revisit only if there's a concrete need to import from or export to another LMS.

## H5P

- Explicitly out of scope per task instructions (no full H5P platform install). H5P content types are authored/rendered via a JS+PHP runtime; there's no practical lightweight path to pull H5P question content into a Python backend without effectively re-implementing part of the H5P player. Not recommended.

## Anki / FSRS libraries

- [`open-spaced-repetition/py-fsrs`](https://github.com/open-spaced-repetition/py-fsrs) (PyPI package `fsrs`), MIT licensed, the official reference Python implementation of the real FSRS algorithm.
- **Observation, not a recommendation to act now**: Nexus's `backend/app/services/fsrs_service.py::schedule_next()` is actually a simplified ease-factor/interval scheduler (SM-2-family), not the FSRS algorithm its module name implies. That's a legitimate future improvement (`py-fsrs` would drop in cleanly, taking `(due, stability, difficulty, rating)` and returning the next interval), but this task's instructions are explicit: don't change the scheduling algorithm without a proven bug, and no bug was found in it during root-cause tracing. Left untouched; noting it here for a future, separately-scoped task.

## Moodle question-bank interoperability

No dedicated recommendation beyond GIFT/QTI above — Moodle's own bulk export formats (Moodle XML, Aiken) either overlap with or are strictly less portable than GIFT/QTI, so there's no additional library to evaluate here.

---

Sources consulted:
- [openpyxl on PyPI / Libraries.io](https://libraries.io/pypi/openpyxl)
- [py-fsrs on GitHub](https://github.com/open-spaced-repetition/py-fsrs)
- [py-fsrs license](https://github.com/open-spaced-repetition/py-fsrs/blob/main/LICENSE)
- [pygiftparserrgmf on PyPI](https://pypi.org/project/pygiftparserrgmf/)
- [Moodle GIFT format docs](https://docs.moodle.org/502/en/GIFT_format)
