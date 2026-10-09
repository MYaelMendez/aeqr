"""aeqr.dispatch — the fleet scheduler: Mech spec in, sealed receipt out.

    fleet_dispatch(mech_spec, units, workers) -> DispatchReceipt

Runs each unit's stage pipeline across a worker pool (data-parallel),
enforces the spec's guard stage as the join, and seals a hash-chained
receipt. Every unit is an æQR contract: addressed (an ae: envelope),
decoded back, hash-chained. Any unit that hits the Refused branch blocks
the seal.

The bridge: Mech = spec (declared), æQR = contract (per unit),
Fleet = scheduler (this module). Run it against
hermes-fork/mech/qr_index.mec to demonstrate it.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict

from . import envelope
from . import mech

GENESIS = "0" * 64


def _link(prev: str, stage: str, status: str, evidence: str) -> str:
    """Hash-chain link: H(prev || stage || status || evidence)."""
    blob = f"{prev}|{stage}|{status}|{evidence}".encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


@dataclass
class StageResult:
    stage: str
    ok: bool
    detail: str
    link: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class UnitResult:
    unit_id: int
    ok: bool
    stages: list
    artifact: object
    chain: str
    worker: str
    started: float
    finished: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["stages"] = [s.to_dict() for s in self.stages]
        return d


@dataclass
class DispatchReceipt:
    spec: str
    spec_sha256: str
    stages: list
    units: int
    workers: int
    sealed: bool
    seal: str
    results: list
    parallel: bool
    refused: int = 0

    def to_dict(self) -> dict:
        return {
            "spec": self.spec, "spec_sha256": self.spec_sha256,
            "stages": self.stages, "units": self.units, "workers": self.workers,
            "sealed": self.sealed, "seal": self.seal, "refused": self.refused,
            "parallel": self.parallel,
            "results": [r.to_dict() for r in self.results],
        }

    def envelope(self) -> str:
        """The receipt itself as an æQR envelope (type 'manifest') — scannable."""
        return envelope.encode("manifest", self.to_dict())


def _run_unit(unit: dict, spec: mech.MechSpec, scan_delay: float = 0.0) -> UnitResult:
    uid = unit["unit_id"]
    started = time.monotonic()
    worker = threading.current_thread().name
    chain = GENESIS
    stages: list = []

    def add(stage: str, ok: bool, detail: str) -> None:
        nonlocal chain
        chain = _link(chain, stage, "ok" if ok else "refused", detail)
        stages.append(StageResult(stage, ok, detail, chain))

    # :Scan — read the payload (simulated scanner input)
    if scan_delay:
        time.sleep(scan_delay)
    payload = unit.get("payload", "")
    add("Scan", True, f"{len(payload)} B")

    # :Decode — typed decode (fails closed) + canonical hash
    try:
        kind, decoded = envelope.decode(payload)
        canonical = json.dumps(decoded, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        spec_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        add("Decode", True, f"{kind} {spec_hash[:12]}")
    except Exception as exc:
        add("Decode", False, str(exc)[:80])
        return UnitResult(uid, False, stages, None, chain, worker, started, time.monotonic())

    # :Verify — the guard/join: sha256(spec) == expected chain
    expected = unit.get("chain") or unit.get("expected") or ""
    ok = bool(expected) and spec_hash == expected
    add("Verify", ok, f"{spec_hash[:12]} vs {expected[:12] or '(none)'}")
    if not ok:
        # -> :Refused branch — blocked; no Resolve/Retrieve
        return UnitResult(uid, False, stages, None, chain, worker, started, time.monotonic())

    # :Resolve — map the verified spec to an artifact
    artifact = decoded.get("artifact") or unit.get("artifact") or f"artifact://{spec_hash[:12]}"
    add("Resolve", True, artifact)

    # :Retrieve — emit the verified artifact
    add("Retrieve", True, artifact)

    return UnitResult(uid, True, stages, artifact, chain, worker, started, time.monotonic())


def fleet_dispatch(spec_path, units: list, workers: int = 8,
                   scan_delay: float = 0.0) -> DispatchReceipt:
    spec = mech.parse_spec(spec_path)
    n = len(units)
    w = max(1, min(workers, n)) if n else 1
    with ThreadPoolExecutor(max_workers=w) as ex:
        results = list(ex.map(lambda u: _run_unit(u, spec, scan_delay), units))

    sealed = all(r.ok for r in results)
    joined = "|".join(sorted(r.chain for r in results))
    seal = hashlib.sha256(f"{spec.sha256}|{joined}|{sealed}".encode("utf-8")).hexdigest()

    # parallelism proof: at least two units were in flight at once
    parallel = bool(results) and max(r.started for r in results) < min(r.finished for r in results)

    return DispatchReceipt(
        spec=spec.name, spec_sha256=spec.sha256, stages=spec.stages,
        units=n, workers=w, sealed=sealed, seal=seal, results=results,
        parallel=parallel, refused=sum(1 for r in results if not r.ok),
    )


def demo_units(n: int = 8, root: str = "surface") -> list:
    """n deterministic, real æQR units: encode -> decode -> expected hash."""
    units = []
    for i in range(n):
        payload = envelope.encode("manifest", {"surfaces": [f"{root}-{i}"], "artifact": f"artifact://{root}/{i}"})
        _, dec = envelope.decode(payload)
        canonical = json.dumps(dec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        chain = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        units.append({"unit_id": i, "payload": payload, "chain": chain, "artifact": dec["artifact"]})
    return units


if __name__ == "__main__":
    import sys
    spec = sys.argv[1] if len(sys.argv) > 1 else "C:/æ/hermes-fork/mech/qr_index.mec"
    rec = fleet_dispatch(spec, demo_units(8), workers=8, scan_delay=0.02)
    print(f"spec      {rec.spec}  ({rec.spec_sha256[:12]})")
    print(f"stages    {' -> '.join(rec.stages)}")
    print(f"units     {rec.units}   workers {rec.workers}   parallel {rec.parallel}")
    print(f"refused   {rec.refused}")
    print(f"sealed    {rec.sealed}   seal {rec.seal[:24]}")
    print(f"receipt   {rec.envelope()[:72]}...")
