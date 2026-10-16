import hashlib
import json

import pytest

from ae.discovery import discover, verify_raw_file


@pytest.fixture
def registry(tmp_path):
    path = tmp_path / "resources.json"
    path.write_text(json.dumps({"resources": [
        {"id":"lesson","name":"Lesson","path":"lesson.html","category":"education","scope":"public","route":"https://example.org/lesson.html","type":"page"},
        {"id":"secret","name":"Secret","path":"private","category":"internal","scope":"private","route":"https://example.org/private","type":"page"},
        {"id":"local","name":"Local","path":"local","category":"internal","scope":"local","route":"file:///secret","type":"page"},
    ]}), encoding="utf-8")
    return path


def test_public_discovery_does_not_claim_verification(registry):
    result = discover("lesson", registry)
    assert result.readable_url == "https://example.org/lesson.html"
    assert result.verification_status == "not_checked"
    assert not result.verified
    assert result.authorization == "not_granted"


def test_private_and_local_routes_are_hidden(registry):
    assert discover("secret", registry).readable_url is None
    assert discover("local", registry).readable_url is None


def test_unknown_resource(registry):
    assert discover("unknown", registry) is None


def test_matching_raw_bytes():
    data = b"<h1>Lesson</h1>"
    digest = hashlib.sha256(data).hexdigest()
    result = verify_raw_file(data, digest)
    assert result["integrity_match"] is True
    assert result["issuer_authenticated"] is False
    assert result["authorization"] == "not_granted"


def test_mutated_bytes_fail():
    digest = hashlib.sha256(b"original").hexdigest()
    assert verify_raw_file(b"changed", digest)["integrity_match"] is False


@pytest.mark.parametrize("bad", ["1234", "A" * 64, "z" * 64, ""])
def test_invalid_expected_digest_rejected(bad):
    with pytest.raises(ValueError):
        verify_raw_file(b"data", bad)


def test_wrong_artifact_type_rejected():
    with pytest.raises(TypeError):
        verify_raw_file("not bytes", "0" * 64)
