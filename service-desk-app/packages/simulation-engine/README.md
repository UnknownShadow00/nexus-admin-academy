# packages/simulation-engine

Framework-free, deterministic ticket simulation state shared by the training
workspace. It owns copy-on-write ticket overlays, typed actions, append-only
action events, attempt reset/serialization, and objective grading.

The current web client persists serialized attempts in browser local storage.
A later backend can replace that adapter without changing the public action or
grading contracts.
