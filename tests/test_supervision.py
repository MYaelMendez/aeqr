import pytest
from ae import envelope as e
from ae import supervision as s


def test_produce_returns_receipt_on_pass(tmp_path):
    r = s.produce("secret", {"name": "K", "blob": {"n": "a", "ct": "b"}},
                  out_path=tmp_path / "k.png")
    assert r.kind == "secret"
    assert len(r.envelope_sha256) == 64
    assert len(r.image_sha256) == 64
    assert len(r.chain) == 64
    assert (tmp_path / "k.png").exists()


def test_all_types_pass_the_gate(tmp_path):
    for t in e.TYPES:
        r = s.produce(t, {"probe": t}, out_path=tmp_path / f"{t}.png")
        assert r.kind == t


def test_refuses_rune_class(tmp_path):
    # render a rune-magic envelope anyway, then supervise -> must refuse on charset
    rune = "\u00e6:1:secret:" + e.encode("secret", {"n": 1}).split(":", 3)[3]
    p = tmp_path / "rune.png"
    s._render(rune, p)
    rep = s.supervise(p, envelope=rune)
    assert rep.passed is False
    assert any(c.name == "charset" and not c.ok for c in rep.failed)


def test_refuses_payload_mismatch(tmp_path):
    r = s.produce("secret", {"name": "RIGHT"}, out_path=tmp_path / "g.png")
    rep = s.supervise(tmp_path / "g.png", expect_kind="secret",
                      expect_payload={"name": "WRONG"}, envelope=r.envelope)
    assert rep.passed is False


def test_render_verified_returns_bytes(tmp_path):
    env = e.encode("route", {"cmd": "status"})
    png = s.render_verified(env, out_path=tmp_path / "r.png")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_two_real_decoders_agree(tmp_path):
    r = s.produce("manifest", {"surfaces": ["a", "b"]}, out_path=tmp_path / "m.png")
    rep = s.supervise(tmp_path / "m.png", expect_kind="manifest", envelope=r.envelope)
    assert set(rep.decoders_ok) == {"cv2", "pyzbar"}


@pytest.mark.parametrize("refusals,fail_kind,expected", [
    ([False, False], None, 0),
    ([True, False], None, 1),
    ([False, True], None, 1),
    ([False, False], "manifest", 1),
])
def test_selftest_exit_status_matches_observed_gates(monkeypatch, refusals, fail_kind, expected):
    from types import SimpleNamespace
    from ae import envelope

    def produce(kind, payload, **kwargs):
        if kind == fail_kind:
            raise s.QRRefused("synthetic refusal", s.QRReport(passed=False))
        return SimpleNamespace(envelope=envelope.encode(kind, payload), render=lambda: "synthetic receipt")

    reports = iter(refusals)
    monkeypatch.setattr(s, "produce", produce)
    monkeypatch.setattr(s, "_render", lambda *args, **kwargs: None)
    monkeypatch.setattr(s, "supervise", lambda *args, **kwargs: SimpleNamespace(
        passed=next(reports), reason=lambda: "synthetic observation"))
    assert s.selftest() == expected
