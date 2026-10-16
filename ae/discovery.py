"""Read-only æQR discovery and artifact verification.

No network access, workflow dispatch, credential handling or authority grants.
The caller supplies artifact bytes and a trusted expected digest.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from ae.registry import resolve, DEFAULT_PATH

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Discovery:
    resource_id: str
    name: str
    scope: str
    category: str
    media_type: str
    readable_url: str | None
    verified: bool
    verification_status: str
    authorization: str = "not_granted"

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


def discover(resource_id: str, registry_path: str | Path = DEFAULT_PATH) -> Discovery | None:
    """Look up public metadata only. Private/local routes are never returned."""
    resource = resolve(resource_id, registry_path)
    if resource is None:
        return None
    return Discovery(
        resource_id=resource.id,
        name=resource.name,
        scope=resource.scope,
        category=resource.category,
        media_type="text/html" if resource.type == "page" else "application/octet-stream",
        readable_url=resource.route if resource.public and resource.route.startswith("https://") else None,
        verified=False,
        verification_status="not_checked",
    )


def verify_raw_file(data: bytes, expected_sha256: str) -> dict:
    """Compare supplied bytes to an independently trusted full raw-file SHA-256.

    This verifies integrity relative to the supplied digest, NOT issuer identity,
    a signature, live deployment, or permission to execute.
    """
    if not isinstance(data, bytes):
        raise TypeError("artifact must be bytes")
    if not isinstance(expected_sha256, str) or not _SHA256.fullmatch(expected_sha256):
        raise ValueError("expected_sha256 must be 64 lowercase hex characters")
    actual = hashlib.sha256(data).hexdigest()
    return {
        "hash_domain": "raw_file_sha256",
        "expected_sha256": expected_sha256,
        "actual_sha256": actual,
        "integrity_match": actual == expected_sha256,
        "issuer_authenticated": False,
        "authorization": "not_granted",
    }
