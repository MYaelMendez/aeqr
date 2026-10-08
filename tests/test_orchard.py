import json
from pathlib import Path
from ae import orchard as o


def _tree(tmp_path: Path):
    (tmp_path / "good.html").write_text(
        "<html><body><script>var x=1;console.log(x);</script></body></html>", encoding="utf-8")
    (tmp_path / "bad.html").write_text(
        "<html><body><script>var x = ;</script></body></html>", encoding="utf-8")
    return tmp_path


def test_audit_finds_only_the_broken_script(tmp_path):
    snap = o.audit_inline_scripts(_tree(tmp_path))
    assert snap.html_documents == 2
    assert snap.inline_scripts_parsed == 2
    paths = {f.path for f in snap.findings}
    assert paths == {"bad.html"}
    assert snap.blockers and snap.blockers[0].severity == "P1"


def test_snapshot_is_deterministic(tmp_path):
    root = _tree(tmp_path)
    a = o.audit_inline_scripts(root)
    b = o.audit_inline_scripts(root)
    assert a.sha256() == b.sha256()


def test_compare_reports_resolved_and_introduced():
    prev = {"html_documents": 2, "findings": [{"id": "x"}, {"id": "y"}]}
    cur = {"html_documents": 3, "findings": [{"id": "y"}, {"id": "z"}]}
    d = o.compare(prev, cur)
    assert d["html_documents"] == 1
    assert d["resolved"] == ["x"]
    assert d["introduced"] == ["z"]
    assert d["persisting"] == ["y"]


def test_kanban_marks_planning_separate_from_verification(tmp_path):
    snap = o.audit_inline_scripts(_tree(tmp_path))
    tasks = o.to_kanban(snap)
    assert tasks and all(t["ready"] is False and t["verified"] is False for t in tasks)


def test_repair_queue_orders_p1_first():
    snap = o.Snapshot("r", "t", 0, 0, findings=[
        o.Finding("a", "P3", "z", "r3"), o.Finding("b", "P1", "a", "r1"), o.Finding("c", "P2", "m", "r2")])
    order = [f.severity for f in o.repair_queue(snap)]
    assert order == ["P1", "P2", "P3"]
