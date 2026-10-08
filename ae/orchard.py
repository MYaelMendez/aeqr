"""aeqr.orchard — audits, evidence snapshots, comparison, repair queue.

An audit is a MEASUREMENT, not an opinion. A snapshot records what was measured
at a revision. Comparing two snapshots yields deltas. Planning readiness is
tracked SEPARATELY from verified repair: marking a task "ready" records intent,
it does not certify a fix.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, asdict, field
from pathlib import Path

from . import registry as _reg


@dataclass
class Finding:
    id: str
    severity: str          # P1 | P2 | P3
    path: str
    reason: str
    evidence: str = ""
    verified: bool = False  # a finding is unverified until a real check proves it fixed

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Snapshot:
    revision: str
    measured_at: str
    html_documents: int
    inline_scripts_parsed: int
    findings: list[Finding] = field(default_factory=list)
    scope: list[str] = field(default_factory=list)  # what was NOT checked

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "P1"]

    def sha256(self) -> str:
        blob = json.dumps(
            {"revision": self.revision, "html": self.html_documents,
             "scripts": self.inline_scripts_parsed,
             "findings": [f.to_dict() for f in self.findings]},
            sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["findings"] = [f.to_dict() for f in self.findings]
        d["sha256"] = self.sha256()
        return d


# ── a real, deterministic inline-script syntax audit ──────────────────────────

_SCRIPT_RE = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.S | re.I)
_SKIP_TYPES = ("application/ld+json", "application/json", "text/template")


def _inline_scripts(html: str) -> list[tuple[str, str]]:
    """Return [(type, body)] for inline scripts only (no src=)."""
    out = []
    for attrs, body in _SCRIPT_RE.findall(html):
        if "src=" in attrs.lower():
            continue
        m = re.search(r'type\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        stype = (m.group(1).strip().lower() if m else "")
        if stype in _SKIP_TYPES:
            continue
        out.append((stype, body))
    return out


def audit_inline_scripts(root: str | Path, node: str = "node") -> Snapshot:
    """Parse every inline <script> in every HTML doc; report syntax failures.

    Deterministic: same tree -> same findings. External scripts and JSON data
    scripts are excluded (they are not JavaScript we can parse here).
    """
    root = Path(root)
    pages = sorted(p for p in root.rglob("*.html")
                   if not any(x in p.parts for x in (".git", "node_modules", "vendor")))
    findings: list[Finding] = []
    parsed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for page in pages:
            try:
                html = page.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            for i, (stype, body) in enumerate(_inline_scripts(html)):
                target = Path(tmp) / ("s.mjs" if stype == "module" else "s.js")
                target.write_text(body, encoding="utf-8")
                r = subprocess.run([node, "--check", str(target)],
                                   capture_output=True, text=True)
                parsed += 1
                if r.returncode:
                    # normalize the temp path OUT of the message so the finding is
                    # deterministic across runs (same tree -> same sha256)
                    err = r.stderr.strip().replace(str(Path(tmp)), "<tmp>")
                    lines = err.splitlines()
                    reason = next((ln.strip() for ln in lines
                                   if ln.strip().startswith(("SyntaxError", "ReferenceError",
                                                             "TypeError", "RangeError"))),
                                  (lines or [""])[0].strip())
                    findings.append(Finding(
                        id=f"p1-{page.relative_to(root).as_posix()}-{i}",
                        severity="P1",
                        path=page.relative_to(root).as_posix(),
                        reason=reason[:160],
                        evidence=err[:400]))
    return Snapshot(
        revision="(unknown)", measured_at="(unknown)",
        html_documents=len(pages), inline_scripts_parsed=parsed, findings=findings)


def compare(previous: dict, current: dict) -> dict:
    """Delta between two snapshot dicts. Pure arithmetic over measurements."""
    def g(d, k):
        return d.get(k, 0)
    prev_ids = {f["id"] for f in previous.get("findings", [])}
    cur_ids = {f["id"] for f in current.get("findings", [])}
    return {
        "html_documents": g(current, "html_documents") - g(previous, "html_documents"),
        "blockers": len(current.get("findings", [])) - len(previous.get("findings", [])),
        "resolved": sorted(prev_ids - cur_ids),
        "introduced": sorted(cur_ids - prev_ids),
        "persisting": sorted(prev_ids & cur_ids),
    }


def repair_queue(snapshot: Snapshot) -> list[Finding]:
    """Ordered repair queue: P1 first, then path order. Stable, deterministic."""
    order = {"P1": 0, "P2": 1, "P3": 2}
    return sorted(snapshot.findings, key=lambda f: (order.get(f.severity, 9), f.path))


def to_kanban(snapshot: Snapshot) -> list[dict]:
    """Findings -> kanban tasks. `ready` records intent; `verified` needs a real check."""
    return [{
        "id": f.id,
        "title": f"Repair {f.severity}: {f.path}",
        "detail": f.reason,
        "priority": f.severity,
        "evidence": f.evidence,
        "ready": False,       # planning state — the human moves this
        "verified": False,    # proof state — only a re-audit sets this
    } for f in repair_queue(snapshot)]
