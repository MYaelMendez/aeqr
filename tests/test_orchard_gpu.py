from pathlib import Path
from ae import orchard as o
from ae import gpu_batch


def _tree(tmp_path: Path):
    (tmp_path / "good.html").write_text(
        "<html><body><script>var x=1;</script></body></html>", encoding="utf-8")
    (tmp_path / "bad.html").write_text(
        "<html><body><script>var x = ;</script></body></html>", encoding="utf-8")
    return tmp_path


def test_audit_engine_is_recorded(tmp_path):
    snap = o.audit_inline_scripts(_tree(tmp_path))
    assert snap.engine in ("cuda", "cpu")


def test_audit_gpu_on_matches_cpu(tmp_path):
    a = o.audit_inline_scripts(_tree(tmp_path), gpu=False)
    b = o.audit_inline_scripts(_tree(tmp_path), gpu=True)
    assert a.sha256() == b.sha256()
    assert a.findings and b.findings


def test_audit_gpu_on_reports_cuda_when_available(tmp_path):
    ok, why = gpu_batch.available()
    if ok:
        snap = o.audit_inline_scripts(_tree(tmp_path), gpu=True)
        assert snap.engine == "cuda"
        assert "RTX" in why or "cupy" in why
