# x-lifecycle

A small, declarative OpenAPI vendor extension that makes your **OpenAPI spec the
single source of truth for entity lifecycles** — and generates everything else
from it.

```
                       x-lifecycle (authored, in the OpenAPI spec)
                                      │
            ┌─────────────────┬───────┴────────┬─────────────────────┐
            ▼                 ▼                ▼                     ▼
      guard code        negative tests     Mermaid diagram     consistency report
   (enforcement)     (verify enforcement)   (communication)      (catch drift)
```

You author the lifecycle **once**, as structured data hung off the schema. Guards,
tests, and the docs diagram are all *projections* of it. They cannot drift from
each other, because none of them is hand-maintained.

## Why this shape

- **Structure** already lives in OpenAPI (schemas, enums, required fields).
- **Behavior** — the states and the legal transitions between them — is the one
  thing OpenAPI's type system can't express. `x-lifecycle` adds exactly that,
  as data, in the same file.
- Every downstream artifact is **generated**, so the diagram in your docs is
  guaranteed to match the rules your server enforces. A diagram that shows a
  transition the guards don't allow becomes structurally impossible.

## The core rule

> The generator only **renders** what the source contains. It never enriches.

If a fact isn't in `x-lifecycle`, it doesn't appear in the guards, the tests, or
the diagram. Guard *messages* and *caveats* live in `x-guards`, so even the
annotations on the diagram are sourced — never typed in by hand. Break this once
and the generated diagram becomes a hand-maintained diagram wearing a generated
file's name.

## Files

| Path | What it is |
|---|---|
| `schema/x-lifecycle.schema.json` | The canonical, reusable shape. Standardize on this across every entity. |
| `examples/kb-version.openapi.yaml` | Worked example: the KB answer `Version` lifecycle. |
| `src/transpile.py` | The transpiler. Emits Mermaid + negative tests + consistency report. |
| `out/` | Generated output (regenerate any time; never edit by hand). |

## Run it

```bash
pip install pyyaml
python3 src/transpile.py examples/kb-version.openapi.yaml out
```

Produces `out/Version.mmd` and `out/Version.negative-tests.md`, and prints a
consistency report.

## What the consistency check catches

Run in CI; fail the build on any finding. It detects:

- **enum drift** — `status` enum and `x-lifecycle.states` no longer match
- **undefined guards** — a transition references a guard that isn't declared
- **unknown states** — a transition from/to a state not in `states`
- **unreachable states** — no path from `initial`
- **dead ends** — non-terminal states with no way out
- **bad terminals** — a terminal state that still has outgoing transitions
- **cross-entity guards** (INFO) — guards whose truth depends on *other*
  entities (e.g. `refcount == 0`). Flagged because a per-entity guard cannot
  fully verify these under concurrency — see below.

## The `scope` field, and the one rule this approach can't fully verify

Each guard declares a `scope`:

- `intra` — depends only on the entity's own fields (e.g. `status == approved`).
  A guard at the transition enforces this completely.
- `cross` — depends on facts about *other* entities or relationships
  (e.g. `refcount == 0`, meaning "no RFP references this version").

The `notReferenced` guard on `delete` is `cross`. A per-entity guard checks it at
one instant, but says nothing about **interleavings** — two RFPs acquiring
references while a delete is in flight. That single rule is the one place where,
*if* you ever need machine-checked proof across concurrent orderings, you'd lift
just that invariant into a formal model (P, TLA+, Alloy) — while everything else
stays on this lightweight pipeline. `scope: cross` is the marker for "this is the
rule to watch."

## The forward-compile path (why this isn't a dead end)

`x-lifecycle` is intentionally isomorphic to a state machine, so it compiles
forward when you outgrow it:

- → **Mermaid** `stateDiagram-v2` (today, in this repo)
- → **XState** machine definition, if you later want a runtime engine + visual editor
- → **P / TLA+** skeleton, for the one `cross` invariant if it ever needs proof

You don't throw the annotation away when requirements grow — you point a new
emitter at the same authored source.

## Adding a new entity

1. Add the schema to `components/schemas` with a `status` enum.
2. Add an `x-lifecycle` block matching `schema/x-lifecycle.schema.json`.
3. Keep the enum and `states` identical (CI enforces it).
4. Mark any guard that depends on other entities as `scope: cross`.
5. Regenerate. Review the Mermaid diagram with stakeholders; wire the negative
   tests into your suite; generate guard predicates from the same block.

## A YAML gotcha baked into the tooling

YAML 1.1 (PyYAML) coerces a bare `on:` key to boolean `true`. Quote it as
`"on":` in your specs. The transpiler also recovers from the unquoted form
defensively, but quoting is the clean fix.
