from ae import envelope as e


def test_all_types_roundtrip():
    for t in e.TYPES:
        kind, payload = e.decode(e.encode(t, {"probe": t, "n": 1}))
        assert kind == t
        assert payload == {"probe": t, "n": 1}


def test_unknown_type_rejected():
    import pytest
    with pytest.raises(ValueError):
        e.encode("nope", {})


def test_non_dict_payload_rejected():
    import pytest
    with pytest.raises(TypeError):
        e.encode("key", ["not", "a", "dict"])


def test_decode_fails_closed():
    import pytest
    with pytest.raises(ValueError):
        e.decode("hello world")
    with pytest.raises(ValueError):
        e.decode("ae:2:key:AAAA")   # wrong version
    with pytest.raises(ValueError):
        e.decode("ae:1:bogus:AAAA")  # unknown type


def test_legacy_vaeult_maps_to_secret():
    kind, payload = e.decode('VAEULT1:{"name":"X"}')
    assert kind == "secret"
    assert payload == {"name": "X"}


def test_rune_form_tolerated_on_decode():
    good = e.encode("key", {"a": 1})
    rune = "\u00e6:" + good[3:]   # æ:... instead of ae:...
    assert e.decode(rune) == ("key", {"a": 1})


def test_is_envelope_and_inspect():
    good = e.encode("secret", {"name": "K", "blob": {"n": "a", "ct": "b"}})
    assert e.is_envelope(good)
    assert not e.is_envelope("plain")
    info = e.inspect(good)
    assert info["type"] == "secret"
    assert info["sealed"] is True
    assert "K" not in str(info)  # never leaks values
