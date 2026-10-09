"""aeqr.mech — parse a Mech state-machine spec into a stage DAG.

Mech (mech-lang.org) is the GRAMMAR. It does not execute on this build
(mechc v0.3.5 fails to build even its own examples/working/*.mec), so a
.mec file is treated as a DECLARATION: parse its stage pipeline and
transitions into a DAG the fleet scheduler can run. The spec says WHAT;
ae.dispatch does HOW.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

# Mech glyphs (UTF-8)
ARROW = "\u2192"     # transition
PRODUCES = "\u21d2"  # produces
BRANCH = "\u251c"    # branch arm
TERM = "\u2514"      # last arm
ASSIGN = ":="        # definition

_STAGE = re.compile(r":([A-Z][A-Za-z0-9_]*)")
REFUSAL_HINT = ("refused", "refuse", "blocked", "error", "fail")


@dataclass
class MechSpec:
    name: str
    stages: list          # ordered pipeline stage names
    edges: list           # [(from, to)] transitions
    terminals: list       # stages that produce a value
    refusals: list        # refusal targets
    raw: str
    sha256: str

    @property
    def guard(self):
        """The stage that branches to a refusal target (the join/verify)."""
        for a, b in self.edges:
            if any(h in b.lower() for h in REFUSAL_HINT):
                return a
        return None

    def to_dict(self) -> dict:
        return {"name": self.name, "stages": self.stages,
                "edges": [list(e) for e in self.edges],
                "terminals": self.terminals, "refusals": self.refusals,
                "guard": self.guard, "sha256": self.sha256}


def parse_text(text: str, name: str = "") -> MechSpec:
    lines = text.splitlines()
    entry = name
    stages: list = []

    # 1) entry block -> ordered stage pipeline
    for i, ln in enumerate(lines):
        s = ln.strip()
        if ASSIGN in s and PRODUCES in s and "(" in s and not s.startswith((":", "#")):
            entry = entry or s.split("(", 1)[0].strip()
            j = i + 1
            while j < len(lines):
                t = lines[j].strip()
                if t.startswith((BRANCH, TERM)):
                    m = _STAGE.search(t)
                    if m:
                        stages.append(m.group(1))
                    j += 1
                elif t == "" or t.startswith("#"):
                    if stages:
                        break
                    j += 1
                else:
                    break
            break

    # 2) transitions -> edges (track the enclosing stage for branch arms)
    edges: list = []
    current = None
    for ln in lines:
        s = ln.strip()
        if s.startswith("#"):
            continue
        m = re.match(r":([A-Z][A-Za-z0-9_]*)\s*\(", s)
        if m:
            current = m.group(1)
        if ARROW in s:
            left, _, right = s.partition(ARROW)
            a = _STAGE.findall(left)
            b = _STAGE.findall(right)
            if b:
                src = a[-1] if a else current
                if src:
                    edges.append((src, b[0]))

    # 3) terminals (=> lines that are a stage)
    terminals: list = []
    for ln in lines:
        s = ln.strip()
        if PRODUCES in s and s.startswith(":"):
            m = _STAGE.search(s)
            if m:
                terminals.append(m.group(1))

    # de-dup edges, preserve order
    seen = set()
    dedup = []
    for e in edges:
        if e not in seen:
            seen.add(e)
            dedup.append(e)

    refusals = sorted({b for _, b in dedup if any(h in b.lower() for h in REFUSAL_HINT)})

    return MechSpec(
        name=entry or "(spec)",
        stages=stages,
        edges=dedup,
        terminals=terminals,
        refusals=refusals,
        raw=text,
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def parse_spec(path) -> MechSpec:
    p = Path(path)
    return parse_text(p.read_text(encoding="utf-8", errors="replace"), name=p.stem)
