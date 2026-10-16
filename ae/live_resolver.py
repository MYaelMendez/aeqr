"""Read-only, version-pinned GitHub public manifest resolver."""
from __future__ import annotations
import hashlib
import json
import re
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

SHA = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
PART = re.compile(r"[A-Za-z0-9_.-]+")
LIMIT = 2 * 1024 * 1024

class ResolutionError(ValueError):
    """Unsafe input, unsupported record, or failed integrity verification."""

def component(s):
    if not isinstance(s, str) or not PART.fullmatch(s) or s in (".", ".."):
        raise ResolutionError("invalid repository component")
    return s

def path(s):
    if not isinstance(s, str) or not s or len(s) > 1024:
        raise ResolutionError("invalid path")
    parts = s.split("/")
    if any(p in (".", "..") for p in parts):
        raise ResolutionError("path traversal")
    return "/".join(component(p) for p in parts)

def digest(s):
    if not isinstance(s, str) or not DIGEST.fullmatch(s):
        raise ResolutionError("expected full lowercase SHA-256 digest")
    return s

def fetch(url, opener=None):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != "raw.githubusercontent.com" or parts.query or parts.fragment:
        raise ResolutionError("unsupported remote origin")
    if opener is None:
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                raise ResolutionError("redirects are not allowed")
        opener = build_opener(NoRedirect()).open
    req = Request(url, headers={"User-Agent": "aeqr-readonly-resolver/0.1", "Accept": "application/octet-stream"})
    with opener(req, timeout=10) as response:
        if getattr(response, "status", 200) != 200:
            raise ResolutionError("unexpected HTTP response")
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ResolutionError("remote object too large")
    return data

def resolve_live_public(*, owner, repo, commit, manifest_path, manifest_sha256, resource_id, opener=None):
    """Verify manifest and public artifact bytes at the same immutable commit.

    The caller MUST obtain manifest_sha256 independently of the remote manifest.
    Integrity is not issuer authentication; no authority is granted.
    """
    owner, repo = component(owner), component(repo)
    if not isinstance(commit, str) or not SHA.fullmatch(commit):
        raise ResolutionError("full immutable commit SHA required")
    manifest_path = path(manifest_path)
    manifest_sha256 = digest(manifest_sha256)
    if not isinstance(resource_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", resource_id):
        raise ResolutionError("invalid resource ID")
    base = f"https://raw.githubusercontent.com/{owner}/{repo}/{commit}/"
    raw = fetch(base + manifest_path, opener=opener)
    manifest_actual = hashlib.sha256(raw).hexdigest()
    if manifest_actual != manifest_sha256:
        raise ResolutionError("manifest integrity mismatch")
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ResolutionError("invalid manifest JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != "aeqr.public-manifest.v1" or not isinstance(manifest.get("resources"), list):
        raise ResolutionError("unsupported manifest schema")
    matches = [r for r in manifest["resources"] if isinstance(r, dict) and r.get("id") == resource_id]
    if len(matches) != 1:
        raise ResolutionError("resource not found or ambiguous")
    item = matches[0]
    if item.get("scope") != "public" or item.get("hash_domain") != "raw_file_sha256":
        raise ResolutionError("only public raw-file artifacts are supported")
    artifact_path = path(item.get("path"))
    expected = digest(item.get("sha256"))
    artifact = fetch(base + artifact_path, opener=opener)
    actual = hashlib.sha256(artifact).hexdigest()
    if actual != expected:
        raise ResolutionError("artifact integrity mismatch")
    return {
        "schema": "aeqr.discovery-result.v1", "resource_id": resource_id,
        "source_repo": f"{owner}/{repo}", "source_revision": commit,
        "manifest_path": manifest_path, "manifest_sha256": manifest_actual,
        "artifact_path": artifact_path, "artifact_sha256": actual,
        "hash_domain": "raw_file_sha256",
        "media_type": item.get("media_type", "application/octet-stream"),
        "readable_url": base + artifact_path,
        "integrity_verified": True, "issuer_authenticated": False,
        "authorization": "not_granted", "execution": "not_attempted"
    }
