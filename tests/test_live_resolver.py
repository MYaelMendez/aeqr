import hashlib
import io
import json
import pytest
from ae.live_resolver import ResolutionError, resolve_live_public

COMMIT = "a" * 40
ARTIFACT = b"<h1>TEOLOGIA</h1>"

class Response(io.BytesIO):
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

def setup(*, scope="public", path="teologia/lesson.html", content=ARTIFACT):
    manifest = {"schema": "aeqr.public-manifest.v1", "resources": [{
        "id": "teologia-lesson", "scope": scope, "path": path,
        "sha256": hashlib.sha256(ARTIFACT).hexdigest(),
        "hash_domain": "raw_file_sha256", "media_type": "text/html"}]}
    raw = json.dumps(manifest).encode()
    calls = []
    def opener(request, timeout):
        calls.append(request.full_url)
        return Response(raw if request.full_url.endswith("/manifest.json") else content)
    args = dict(owner="LutheranInstitute", repo="aeee-lab", commit=COMMIT,
                manifest_path="manifest.json", manifest_sha256=hashlib.sha256(raw).hexdigest(),
                resource_id="teologia-lesson", opener=opener)
    return args, calls

def test_pinned_verified_read_only_result():
    args, calls = setup()
    result = resolve_live_public(**args)
    assert result["integrity_verified"] is True
    assert result["issuer_authenticated"] is False
    assert result["authorization"] == "not_granted"
    assert result["execution"] == "not_attempted"
    assert len(calls) == 2 and all("/" + COMMIT + "/" in c for c in calls)

def test_changed_manifest_rejected_before_artifact_fetch():
    args, calls = setup()
    args["manifest_sha256"] = "0" * 64
    with pytest.raises(ResolutionError, match="manifest integrity"):
        resolve_live_public(**args)
    assert len(calls) == 1

def test_changed_artifact_rejected():
    args, _ = setup(content=b"modified")
    with pytest.raises(ResolutionError, match="artifact integrity"):
        resolve_live_public(**args)

@pytest.mark.parametrize("field,value", [
    ("commit", "main"), ("manifest_path", "../secret"), ("owner", "bad/owner"),
    ("manifest_path", "https://evil.test/a"), ("resource_id", "../../x"),
    ("manifest_sha256", "short")])
def test_invalid_input_never_fetches(field, value):
    args, calls = setup()
    args[field] = value
    with pytest.raises(ResolutionError):
        resolve_live_public(**args)
    assert not calls

def test_private_manifest_refused_without_artifact_fetch():
    args, calls = setup(scope="private")
    with pytest.raises(ResolutionError, match="only public"):
        resolve_live_public(**args)
    assert len(calls) == 1

def test_path_traversal_refused_without_artifact_fetch():
    args, calls = setup(path="../secret")
    with pytest.raises(ResolutionError, match="path traversal"):
        resolve_live_public(**args)
    assert len(calls) == 1

def test_oversized_manifest_rejected():
    args, _ = setup()
    args["opener"] = lambda request, timeout: Response(b"x" * (2*1024*1024+1))
    with pytest.raises(ResolutionError, match="too large"):
        resolve_live_public(**args)

def test_duplicate_id_rejected():
    args, _ = setup()
    raw = json.dumps({"schema": "aeqr.public-manifest.v1",
                      "resources": [{"id":"teologia-lesson"},{"id":"teologia-lesson"}]}).encode()
    args["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    args["opener"] = lambda request, timeout: Response(raw)
    with pytest.raises(ResolutionError, match="ambiguous"):
        resolve_live_public(**args)
