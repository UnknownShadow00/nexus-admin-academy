# Curriculum Intake Workflow

Nexus accepts externally authored and reviewed curriculum through one inbox:

`references/curriculum-dropbox/`

Put either the downloaded ZIP or its unzipped directory there. Do not rename or
reorganize files inside it. Then ask Codex: `Process the curriculum dropbox.`

## Check and apply

From the repository root:

```bash
backend/.venv/bin/python backend/scripts/process_curriculum_dropbox.py --check
backend/.venv/bin/python backend/scripts/process_curriculum_dropbox.py --apply
```

`--check` discovers every package independently, extracts ZIPs into a temporary
directory, validates and normalizes temporary runtime artifacts, and exercises
the real V2 loaders twice in a fresh migrated scratch database. It does not
change approved or runtime curriculum.

`--apply` repeats all checks, writes normalized files to the existing V2 content
paths, archives the exact approved source, writes a receipt, verifies both, and
only then removes the successful inbox item. A failed package remains in the
inbox, and does not prevent independent packages from being checked.

Reports are written under the ignored
`references/curriculum-dropbox/.reports/` directory.

## Source, normalization, and runtime data

The three layers have deliberately different jobs:

- `references/curriculum-dropbox/` is the temporary owner inbox. Payloads are
  ignored by Git.
- `references/curriculum-approved/<certification>/<version>/<module>/<hash>/`
  is immutable history. It retains the original ZIP bytes or exact submitted
  folder tree, a generated normalized manifest, and `IMPORT_RECEIPT.json`.
- `backend/content/` contains normalized data for the existing V2 loaders.

Structured metadata, not the package filename, selects the canonical
certification, version, domain, and module. Certification versions and
objectives must already exist in `backend/content/certifications/` and
`backend/content/objectives/`. This makes intake certification-agnostic while
preventing a package from inventing or crossing objective versions.

Mechanical normalization includes friendly enum names and workbook column
aliases such as `Job Critical`, `single-choice`, `question`, and `objective`.
It does not rewrite lesson prose, question wording, answers, distractors,
rubrics, objectives, resources, or practical and Service Desk outcomes. A
contradiction that cannot be mapped safely is an error.

The generated manifest records package identity, component counts, objectives,
provenance, and the SHA-256 of the submitted source. Optional resources,
practical, Explain prompts, and Service Desk components may be absent. A
Service Desk component currently names an existing stable Nexus scenario key;
inline scenarios are rejected because Nexus has one Service Desk engine and
intake must not create a competing or partially gradeable ticket format.

## Existing V2 systems used

The processor creates no new teaching runtime. It stages files for:

- the Markdown lesson loader under `backend/content/curriculum/`;
- the existing CSV/XLSX question importer through its canonical columns,
  validation, fingerprints, provenance, and hash-bound editorial approval;
- the learning-resource loader under `backend/content/resources/`;
- `LabTemplate` practicals under `backend/content/labs/`;
- existing Service Desk scenarios via stable keys;
- Explain/interview prompts under `backend/content/interview-prompts/`;
- certification modules, objectives, Quick Checks, and Module Quiz blueprints
  through the certification YAML and module-assessment loader.

The question importer owns its database transaction. Intake therefore performs
all package validation and creates all normalized files in temporary storage,
then runs migrations and both loader passes only against a disposable database.
No development or production database is part of intake. Runtime files are
promoted only after the scratch load succeeds, and file promotion is rolled
back if approved-source archiving or verification fails.

## Repeats and changed packages

- A module with no approved history is `NEW`.
- The same module and identical source hash is `UNCHANGED`; apply verifies the
  archive and safely clears that duplicate from the inbox.
- The same module with a different source hash is
  `CHANGED_REQUIRES_REVIEW`. It remains in the inbox unless an explicit
  reviewed apply is requested with `--apply --allow-changed`.

A changed apply creates a new hash directory and retains every earlier approved
version. The normalized question-bank file receives a newly computed approval
hash; modifying that runtime bank later invalidates the loader’s existing
hash-bound approval check.

## Package components and future certifications

Supported package names are `module_overview.md`, `lessons/*.md`, an XLSX or CSV
question workbook, `module_quiz_blueprint.yaml`, `provenance.yaml`, and optional
`resources.yaml`, `explain_prompts.yaml`, `practical.yaml`, and
`service_desk.yaml`. Other editorial files remain preserved in the exact
approved archive even when they have no runtime mapping.

To add a future certification, first add its canonical certification version,
domains, and objective data to the existing V2 hierarchy. Packages can then
identify those keys without changing this processor. Add new optional package
components only by mapping them to an existing Nexus loader or engine; do not
create a parallel curriculum schema.
