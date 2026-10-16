# æQR³ milestone 1 — version-pinned public manifest resolver

**Status:** implementation proposed on review branch. Unit tests run locally with mocked HTTP responses; GitHub CI and live remote fetch are separate verification gates.

## Trust and execution boundary

The caller supplies GitHub owner/repo, a full immutable 40-hex commit SHA, a manifest path, an **independently trusted** full SHA-256 digest of that manifest, and the public resource ID. The resolver retrieves the manifest and the artifact at the **same commit**, checks raw-byte digests, and returns a read-only discovery record.

The manifest is descriptive data, **not** a grant, signer credential, trusted repository selection, workflow or executable plan. Only `https://raw.githubusercontent.com` is accepted. Redirects are denied, paths are bounded and traversal rejected, each response is capped at 2 MiB and a 10-second request timeout applies. Private resources cannot be resolved. Integrity relative to a supplied digest is **not** issuer authentication.

## Minimal public manifest

```json
{
  "schema": "aeqr.public-manifest.v1",
  "resources": [{
    "id": "teologia-lesson",
    "scope": "public",
    "path": "teologia/lesson.html",
    "sha256": "<full 64-character lowercase SHA-256 of raw bytes>",
    "hash_domain": "raw_file_sha256",
    "media_type": "text/html"
  }]
}
```

## Example

```python
from ae.live_resolver import resolve_live_public

result = resolve_live_public(
    owner="LutheranInstitute", repo="aeee-lab",
    commit="<full 40-hex commit SHA>",
    manifest_path="path/to/manifest.json",
    manifest_sha256="<independently trusted full 64-hex digest>",
    resource_id="teologia-lesson",
)
```

This is a contract example, **not** a claim that this manifest is currently published. Obtain the manifest digest from a reviewed commit, authenticated release or other independent trusted source; a digest read from the same untrusted manifest cannot serve as its trust anchor.

## Verification record — 2026-10-16

Local isolated test command: `PYTHONPATH=/mnt/data/aeqr_m1 python -m pytest -q /mnt/data/aeqr_m1/tests/test_live_resolver.py`.

Result: **13 passed in 0.07 seconds**. Test inputs were deterministic mocked HTTP responses, not live GitHub requests. This verifies the resolver logic exercised by those tests, not CI status, live network access, QR decoding, signatures, a deployed Teologia manifest, or ChatGPT/Site synchronization.

## Remaining release gates

- Observe Linux/Windows repository-wide GitHub CI and record exact run URLs.
- Select/publish an actual public Teologia manifest at a pinned commit, obtain its digest independently and perform a real fetch.
- Produce a Witness record tied to actual remote bytes and revision.
- Connect the same public descriptor to ChatGPT and the existing OpenAI Site without claiming shared credentials.
- Implement issuer authentication and QR v2 transport separately.

**Many agents. One principal. Context may propagate; authority does not.**
