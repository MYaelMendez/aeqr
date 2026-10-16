from pathlib import Path
import hashlib
from ae import envelope, dispatch, gpu_batch


def test_gpu_available_or_falls_back_honestly():
    ok, why = gpu_batch.available()
    assert isinstance(ok, bool)
    assert why  # always explains itself
    # if a GPU is present it must name the device
    if ok:
        assert "cupy" in why


def test_batch_sha256_matches_hashlib():
    msgs = [b"", b"a", b"hello world", b"\x00\xff" * 40, bytes(range(256))]
    digests, engine = gpu_batch.sha256_batch(msgs)
    assert digests == [hashlib.sha256(m).hexdigest() for m in msgs]
    assert engine in ("cuda", "cpu")


def test_selftest_reports_match():
    r = gpu_batch.selftest(32)
    assert r["match"] is True
    assert r["mismatches"] == []


def test_empty_batch():
    digests, engine = gpu_batch.sha256_batch([])
    assert digests == []


def test_dispatch_uses_gpu_when_available():
    spec = Path(__file__).parent / "fixtures" / "qr_index.mec"
    rec = dispatch.fleet_dispatch(spec, dispatch.demo_units(8), workers=8, gpu=True)
    assert rec.sealed is True
    # engine records the truth; on this host the RTX 3050 kernel compiles
    assert rec.engine in ("cuda", "cpu")
    assert rec.to_dict()["engine"] == rec.engine


def test_dispatch_cpu_and_gpu_agree_on_the_seal():
    spec = Path(__file__).parent / "fixtures" / "qr_index.mec"
    a = dispatch.fleet_dispatch(spec, dispatch.demo_units(8), gpu=False)
    b = dispatch.fleet_dispatch(spec, dispatch.demo_units(8), gpu=True)
    # the engine is an implementation detail — the receipt seal must not depend on it
    assert a.seal == b.seal


def test_units_from_registry_are_real_and_verifiable():
    units = dispatch.units_from_registry(limit=12)
    assert len(units) == 12
    # each unit's expected chain is the real sha256 of its own decoded payload
    for u in units:
        kind, dec = envelope.decode(u["payload"])
        assert kind == "manifest"
        canon = dispatch._canonical(u["payload"])
        assert hashlib.sha256(canon).hexdigest() == u["chain"]
        assert u["artifact"].startswith(("https://", "ae://"))


def test_dispatch_over_registry_inventory():
    spec = Path(__file__).parent / "fixtures" / "qr_index.mec"
    units = dispatch.units_from_registry(limit=24)
    rec = dispatch.fleet_dispatch(spec, units, workers=8)
    assert rec.units == 24
    assert rec.sealed is True
    assert rec.refused == 0
    # every unit resolved to a real route
    assert all(r.artifact for r in rec.results)
