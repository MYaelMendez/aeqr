import json
from ae import envelope, mech, dispatch, authority as auth

SPEC = "C:/æ/hermes-fork/mech/qr_index.mec"


def test_parse_qr_index_pipeline():
    spec = mech.parse_spec(SPEC)
    assert spec.stages == ["Scan", "Decode", "Verify", "Resolve", "Retrieve"]
    assert ("Verify", "Resolve") in spec.edges
    assert ("Verify", "Refused") in spec.edges
    assert spec.guard == "Verify"
    assert "Refused" in spec.refusals


def test_dispatch_all_pass_and_sealed():
    rec = dispatch.fleet_dispatch(SPEC, dispatch.demo_units(8), workers=8)
    assert rec.units == 8
    assert rec.sealed is True
    assert rec.refused == 0
    assert all(r.ok for r in rec.results)
    assert all(r.artifact for r in rec.results)
    assert rec.stages == ["Scan", "Decode", "Verify", "Resolve", "Retrieve"]


def test_receipt_roundtrips_as_an_envelope():
    rec = dispatch.fleet_dispatch(SPEC, dispatch.demo_units(4))
    kind, payload = envelope.decode(rec.envelope())
    assert kind == "manifest"
    assert payload["sealed"] is True
    assert payload["units"] == 4


def test_tampered_unit_is_refused_and_blocks_seal():
    units = dispatch.demo_units(8)
    units[3]["chain"] = "deadbeef" * 8           # wrong expected hash
    rec = dispatch.fleet_dispatch(SPEC, units)
    assert rec.sealed is False
    assert rec.refused == 1
    bad = [r for r in rec.results if not r.ok]
    assert len(bad) == 1
    # the refused unit stopped at Verify — no Resolve/Retrieve
    assert [s.stage for s in bad[0].stages] == ["Scan", "Decode", "Verify"]


def test_independent_units_run_in_parallel():
    rec = dispatch.fleet_dispatch(SPEC, dispatch.demo_units(8), workers=8, scan_delay=0.04)
    assert rec.parallel is True
    assert len(set(r.worker for r in rec.results)) >= 2


def test_seal_is_deterministic():
    a = dispatch.fleet_dispatch(SPEC, dispatch.demo_units(8))
    b = dispatch.fleet_dispatch(SPEC, dispatch.demo_units(8))
    assert a.seal == b.seal


def test_authority_gates_effectful_actions():
    assert auth.authorize("publish", [], "qr_index") is False
    cap = auth.Capability(subject="op", action="publish", scope="qr_index", granted_by="human")
    assert auth.authorize("publish", [cap], "qr_index") is True
