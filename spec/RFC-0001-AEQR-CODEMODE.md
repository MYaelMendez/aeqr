# RFC-0001 · æQRMode / CodeMode Interoperability Specification

**Status:** Draft proposal · **Canonical repo:** `MYaelMendez/aeqr` · **Source inspection:** `MYaelMendez/MYaelMendez.github.io` (October 2026).

## 1. Scope and observed implementations

æQR already spans two independently evolving surfaces:

1. **Canonical æQR Python package:** `ae/envelope.py` encodes `ae:1:<type>:<base64url(json)>`; `ae/supervision.py` uses two-decoder QR supervision; `ae/registry.py` resolves stable IDs and scopes; `ae/authority.py` demonstrates default-deny decisions; `.github/workflows/resolve-resource.yml` performs a read-only GitHub Actions lookup.
2. **GitHub Pages / Teologia publishing:** `aeqr.html` documents the public-facing registry; `teologia/scripts/make_aqr_generic.py` generates `æqr://v1|<artifact>|<region>|sha256:<digest>|issuer:<issuer>` badges and JSON receipts; `teologia/platform-manifest.json` contains full file-byte SHA-256 digests for 17 HTML artifacts; `teologia/wasm/src/lib.rs` computes SHA-256 in Rust/WASM and exposes artifact metadata/payload generation.

These are **observed source files**, not proof that every claimed runtime check passed.

## 2. Interoperability problems that MUST be resolved

### P0: Incompatible wire formats
- The Python envelope is ASCII `ae:1:...`; the Teologia QR payload begins with Unicode `æqr://v1` and uses `☺://cc` as an issuer string.
- The canonical æQR README explicitly warns that a non-ASCII prefix may be mangled by a decoder.
- **Requirement:** new cross-platform QR transport MUST be ASCII-only, versioned, and typed. Legacy `æqr://v1` payloads MAY be parsed by a separate legacy adapter, but MUST NOT silently be considered compliant with the new wire format.

### P0: Inconsistent QR acceptance criteria
- `ae/supervision.py` describes **cv2 AND pyzbar agreement**.
- `teologia/scripts/make_aqr_generic.py` returns success on **cv2 OR pyzbar** and its `_matches()` accepts a decoded string merely containing the expected digest.
- **Requirement:** a supervised release MUST require exact payload equality from both independent decoders, or explicitly record `not_supervised` and refuse verified-badge status. Substring hash matches MUST NOT count as exact decoding.

### P0: Different hash domains and stale evidence
- Teologia's generic badge hashes normalized visible text after stripping markup/badge; `platform-manifest.json` hashes raw HTML file bytes; Rust/WASM embeds hard-coded hash prefixes.
- Example: `teologia/catecismo-menor.aqr.json` has canonical-text digest beginning `41df5301`, whereas the platform manifest has file-byte digest beginning `763421ab`. They are not interchangeable.
- The WASM table includes prefixes that differ from the inspected manifest. Its `verify_artifact()` returns metadata, not a live comparison of fetched bytes.
- **Requirement:** every digest MUST declare `hash_domain` (`raw_file_sha256`, `canonical_text_sha256`, etc.), `canonicalization_id` where applicable, and a **full** 64-hex SHA-256. Display prefixes are non-authoritative. Verification MUST compute the digest over current bytes and compare it with a trusted expected value. A compiled-in digest or receipt is a claim until independently checked.

### P1: Issuer is not an authenticated signer
- `issuer:☺://cc` is a label; a plain JSON receipt and `issued_at` timestamp are not cryptographic signatures.
- **Requirement:** represent `issuer_id` separately from optional signature metadata; `authenticated` is false unless signature and trust chain are validated. Avoid saying “signed” for unsigned payloads.

### P1: Deployment portability
- Teologia badge generators use `C:\\æ\\site\\teologia` absolute paths and embed them in receipts.
- **Requirement:** relative paths, no private filesystem disclosure in public receipts, portable POSIX/Windows tests, deterministic artifact output (timestamps isolated from hashed payload).

### P1: Registry drift
- Public pages mention 269/8, 277, and 278/9 resources, while the canonical registry may have a different snapshot.
- **Requirement:** derive counts and examples from the version-pinned registry during CI; never treat embedded webpage statistics as live inventory.

## 3. Proposed æQR v2 logical record

The following is a **logical manifest**, not a QR payload or a claim of implementation:

```json
{
  "spec": "aeqr/2",
  "resource_id": "teologia/catecismo-menor",
  "revision": "<immutable-git-commit-sha>",
  "scope": "public",
  "media_type": "text/html",
  "hashes": [{
    "domain": "raw_file_sha256",
    "algorithm": "sha256",
    "digest": "<64-lowercase-hex-digits>"
  }],
  "issuer_id": "teologia.ai",
  "signature_ref": null,
  "capability_manifest_ref": null
}
```

Validation: `resource_id` is bounded and normalized; `revision` immutable; `scope` is one of public/local/private/hybrid; `digest` is full-length; untrusted fields never become shell commands, filesystem paths or executable URLs.

**Transport:** `ae:2:resource:<base64url(canonical-json)>` is a proposed interoperable ASCII encoding. If QR density prevents reliable scanning, encode a short stable HTTPS resolver URL pointing to a versioned manifest, not an unbounded JSON blob. The resolved manifest is untrusted until verified.

## 4. Capability composition contract (CodeMode, planned)

```text
SCAN / LINK -> PARSE -> RESOLVE -> VERIFY
           -> DISCOVER typed capability manifest
           -> COMPOSE proposed effect graph (CodeMode sandbox)
           -> AUTHORIZE via separate trusted principal/policy service
           -> EXECUTE allowlisted GitHub Actions workflow
           -> WITNESS receipt with evidence and verification status
```

A capability manifest SHOULD define stable ID, input/output JSON schemas, allowed effects, executor adapter ID, version and provenance. CodeMode MUST NOT hold executor credentials. A scan or a manifest MUST NOT mint authority. External writes MUST require a separate scoped grant and appropriate human approval.

GitHub Actions is the **initial** substrate, not the identity provider or authorization root. Workflow dispatch MUST use allowlisted workflow IDs and validated inputs; actions SHOULD be pinned to immutable SHAs. `contents: read` remains the default token permission.

## 5. Witness receipt requirements

Each execution receipt SHOULD bind: `spec`, `resource_id`, `source_revision`, `capability_id`, `plan_digest`, `run_id`, `principal_approval_ref` (not credentials), `input_digests`, `output_digests`, `attempted/completed/verified` status, `evidence_refs`, and optional signer attestation. A workflow exit code alone is not proof of external effect.

## 6. Conformance tests

- ASCII v2 transport round-trip across cv2 and pyzbar; exact byte/payload match.
- Legacy Unicode payload decoded via explicit compatibility adapter; no silent upgrade.
- Mutated QR/payload fails supervision; digest substring acceptance rejected.
- Raw-file and canonical-text hashes produce independently labeled results.
- Changed HTML invalidates the matching manifest digest.
- WASM recomputes SHA-256 over fetched bytes rather than returning hard-coded metadata as verification.
- No grant: publishing, merging and executing are denied; untrusted QR cannot elevate permissions.
- Public receipts omit local paths and credentials; forked repositories start with no grants.
- GitHub Actions resolver remains read-only; effectful workflows require approval and emit receipts.
- Accessibility: printed QR has an adjacent readable URL/resource ID.

## 7. Migration plan

1. Add fixture-driven tests using the existing Teologia `*.aqr.json` and `platform-manifest.json`; label old claims accurately.
2. Implement a versioned legacy adapter for `æqr://v1` and the new ASCII transport.
3. Make the Python supervision gate the normative QR acceptance test; refactor Teologia generators to call it.
4. Generate the WASM artifact index from the same version-pinned manifest rather than embedding drifting hash prefixes.
5. Add typed capability and execution-plan schemas, then a non-privileged CodeMode planner.
6. Add approved GitHub Actions execution adapter and Witness receipt validation.
7. Only after tests pass, publish `æQRMode` as a forkable GitHub template experience.

## 8. Foundational invariant

**Discovery != permission. Integrity != authenticity. Planning != execution. Execution != verified success. Context may propagate; authority does not.**

**æQRMode senses the entry point. CodeMode composes the capability. Human authority governs the effect. Witness closes the loop. Many agents. One principal.**
