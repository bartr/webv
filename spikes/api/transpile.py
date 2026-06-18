#!/usr/bin/env python3
"""
x-lifecycle transpiler.

Reads an OpenAPI document, finds every schema carrying an `x-lifecycle` block,
and emits three GENERATED artifacts per entity from that single authored source:

  1. A Mermaid stateDiagram-v2 (for docs / interactive review)
  2. A negative-test list (every illegal (from,event) pair -> must be rejected)
  3. A consistency report (drift, unreachable states, dead ends, cross-entity guards)

Design rule enforced here: the generator only RENDERS what the source contains.
It never enriches. If information isn't in x-lifecycle, it doesn't appear downstream.
"""

import sys
import json
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


# ---------- loading ----------

def load_openapi(path: Path) -> dict:
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            raise SystemExit("PyYAML not installed; cannot read YAML.")
        return yaml.safe_load(text)
    return json.loads(text)


def _normalize_transition(t: dict) -> dict:
    """YAML 1.1 coerces a bare `on:` key to boolean True. If the source didn't
    quote it, recover the value here so downstream code can rely on 'on'."""
    if "on" not in t and True in t:
        t = dict(t)
        t["on"] = t.pop(True)
    return t


def find_lifecycles(doc: dict):
    """Yield (entity_name, schema, lifecycle) for each schema with x-lifecycle."""
    schemas = (doc.get("components", {}) or {}).get("schemas", {}) or {}
    for name, schema in schemas.items():
        lc = schema.get("x-lifecycle")
        if lc:
            lc = dict(lc)
            lc["transitions"] = [_normalize_transition(t) for t in lc.get("transitions", [])]
            yield name, schema, lc


# ---------- validation / consistency ----------

def check_consistency(name, schema, lc):
    """Return a list of human-readable findings. Empty list == clean."""
    findings = []
    states = set(lc["states"])
    initial = lc["initial"]
    terminal = set(lc.get("terminal", []))
    transitions = lc["transitions"]
    guard_names = {g["name"] for g in lc.get("guards", [])}

    # initial must be a declared state
    if initial not in states:
        findings.append(f"initial state '{initial}' is not in states")

    # transitions must reference declared states + guards
    for t in transitions:
        if t["from"] not in states:
            findings.append(f"transition from unknown state '{t['from']}'")
        if t["to"] not in states:
            findings.append(f"transition to unknown state '{t['to']}'")
        if "guard" in t and t["guard"] not in guard_names:
            findings.append(f"transition {t['from']}->{t['to']} references "
                            f"undefined guard '{t['guard']}'")

    # status enum (if present) must match states exactly
    enum = (schema.get("properties", {}).get("status", {}) or {}).get("enum")
    if enum is not None:
        if set(enum) != states:
            only_enum = set(enum) - states
            only_states = states - set(enum)
            findings.append(
                "status enum and x-lifecycle.states differ "
                f"(enum-only: {sorted(only_enum)}, states-only: {sorted(only_states)})"
            )

    # reachability from initial
    reachable = {initial}
    changed = True
    while changed:
        changed = False
        for t in transitions:
            if t["from"] in reachable and t["to"] not in reachable:
                reachable.add(t["to"])
                changed = True
    unreachable = states - reachable
    if unreachable:
        findings.append(f"unreachable states: {sorted(unreachable)}")

    # dead ends: non-terminal states with no outgoing transition
    has_out = {t["from"] for t in transitions}
    dead = (states - has_out) - terminal
    if dead:
        findings.append(f"non-terminal states with no outgoing transition: {sorted(dead)}")

    # terminal states must have no outgoing transition
    bad_terminal = terminal & has_out
    if bad_terminal:
        findings.append(f"terminal states with outgoing transitions: {sorted(bad_terminal)}")

    # surface cross-entity guards (the rules a per-entity guard can't fully verify)
    cross = [g["name"] for g in lc.get("guards", []) if g.get("scope") == "cross"]
    if cross:
        findings.append(f"INFO cross-entity guards (verify under concurrency): {cross}")

    return findings


# ---------- emitters ----------

def emit_mermaid(name, lc) -> str:
    """stateDiagram-v2. Renders states, transitions, guard annotations, terminals.
    Everything here is sourced from x-lifecycle; nothing is added."""
    lines = ["stateDiagram-v2", f"    %% GENERATED from x-lifecycle of {name} - do not edit"]
    lines.append(f"    [*] --> {lc['initial']}")

    guards_by_name = {g["name"]: g for g in lc.get("guards", [])}

    for t in lc["transitions"]:
        label = t["on"]
        if "guard" in t:
            label += f" [{t['guard']}]"
        lines.append(f"    {t['from']} --> {t['to']}: {label}")

    for s in lc.get("terminal", []):
        lines.append(f"    {s} --> [*]")

    # guard messages as notes, emitted from x-guards (caveats stay sourced)
    for g in guards_by_name.values():
        msg = g.get("message")
        if msg:
            # attach the note to the first state that has a transition using this guard
            anchor = next((t["from"] for t in lc["transitions"]
                           if t.get("guard") == g["name"]), None)
            if anchor:
                lines.append(f"    note right of {anchor}")
                scope = g.get("scope", "intra")
                lines.append(f"        {g['name']} ({scope}): {msg}")
                lines.append(f"    end note")
    return "\n".join(lines)


def emit_negative_tests(name, lc):
    """Every (state, event) pair that is NOT a declared transition is illegal
    and must be rejected. Also emit guard-denial tests for guarded transitions."""
    states = lc["states"]
    events = sorted({t["on"] for t in lc["transitions"]})
    legal = {(t["from"], t["on"]) for t in lc["transitions"]}

    illegal = []
    for s in states:
        if s in set(lc.get("terminal", [])):
            # from a terminal state, every event is illegal
            for e in events:
                illegal.append((s, e))
            continue
        for e in events:
            if (s, e) not in legal:
                illegal.append((s, e))

    guarded = [t for t in lc["transitions"] if "guard" in t]
    return events, illegal, guarded


def render_negative_test_doc(name, lc):
    events, illegal, guarded = emit_negative_tests(name, lc)
    out = [f"# Generated negative tests for {name}",
           "",
           "## Illegal transitions (must return 409 / be rejected)",
           ""]
    for (s, e) in illegal:
        out.append(f"- in state `{s}`, event `{e}` -> REJECT (no such transition)")
    out.append("")
    out.append("## Guard-denial tests (legal transition, guard false -> reject)")
    out.append("")
    guards_by_name = {g["name"]: g for g in lc.get("guards", [])}
    for t in guarded:
        g = guards_by_name.get(t["guard"], {})
        out.append(
            f"- `{t['from']}` --`{t['on']}`--> `{t['to']}` "
            f"when NOT ({g.get('expression','?')}) -> REJECT "
            f"(\"{g.get('message','denied')}\")"
        )
    return "\n".join(out)


# ---------- main ----------

def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: transpile.py <openapi.yaml> [out_dir]")
    src = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("out")
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = load_openapi(src)
    any_found = False
    for name, schema, lc in find_lifecycles(doc):
        any_found = True
        print(f"== {name} ==")

        findings = check_consistency(name, schema, lc)
        if findings:
            for f in findings:
                print(f"   [check] {f}")
        else:
            print("   [check] clean")

        mermaid = emit_mermaid(name, lc)
        (out_dir / f"{name}.mmd").write_text(mermaid + "\n")

        tests = render_negative_test_doc(name, lc)
        (out_dir / f"{name}.negative-tests.md").write_text(tests + "\n")

        print(f"   wrote {out_dir / (name + '.mmd')}")
        print(f"   wrote {out_dir / (name + '.negative-tests.md')}")

    if not any_found:
        print("No schemas with x-lifecycle found.")


if __name__ == "__main__":
    main()
