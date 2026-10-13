"""RFC-0001 baseline conformance tests.

These characterize current interoperability boundaries. They do NOT assert that
æQR v2, signed provenance, or CodeMode execution is implemented.
Source fixtures: MYaelMendez.github.io/teologia (inspected 2026-10).
"""
import hashlib
import json
import re

import pytest

from ae import envelope


LEGACY = (
    "æqr://v1|teologia.ai/catecismo-menor|es-LATAM|"
    "sha256:41df530165df46da51b00674734e52cae124073aaebd8e8ba93c505f67d6be05|"
    "issuer:☺://cc"
)
# Same artifact, *different hash domains*. Not interchangeable.
MANIFEST_RAW_FILE_SHA256 = (
    "763421ab26364378fdab8958a6e63fa0cc599257b443455c800ab2669982732d"
)


def parse_legacy_teologia(text):
    """Strict, read-only legacy fixture parser; no authorization semantics."""
    match = re.fullmatch(
        r"æqr://v1\|([A-Za-z0-9._/-]+)\|([A-Za-z0-9-]+)\|"
        r"sha256:([0-9a-f]{64})\|issuer:(.+)",
        text,
    )
    if not match:
        raise ValueError("invalid legacy teologia payload")
    artifact, region, digest, issuer = match.groups()
    return {
        "artifact": artifact,
        "region": region,
        "hash_domain": "canonical_text_sha256",
        "digest": digest,
        "issuer_claim": issuer,
        "authenticated": False,
        "authorized": False,
    }


def test_legacy_payload_is_distinct_from_canonical_ascii_transport():
    assert not LEGACY.isascii()
    with pytest.raises(ValueError):
        envelope.decode(LEGACY)
    parsed = parse_legacy_teologia(LEGACY)
    assert parsed["artifact"] == "teologia.ai/catecismo-menor"
    assert not parsed["authenticated"]
    assert not parsed["authorized"]


def test_legacy_digest_is_not_raw_file_digest():
    parsed = parse_legacy_teologia(LEGACY)
    assert parsed["digest"] != MANIFEST_RAW_FILE_SHA256
    assert len(parsed["digest"]) == len(MANIFEST_RAW_FILE_SHA256) == 64
    assert parsed["hash_domain"] == "canonical_text_sha256"


def test_legacy_parser_rejects_digest_substring_and_mutation():
    for malformed in (
        LEGACY.replace("41df5301", "41df530X"),
        LEGACY + "|execute:true",
        LEGACY.replace("sha256:", "sha1:"),
        LEGACY.replace("æqr://v1", "ae:2"),
    ):
        with pytest.raises(ValueError):
            parse_legacy_teologia(malformed)


def test_current_ascii_envelope_roundtrips_manifest_without_grant():
    record = {
        "artifact": "teologia.ai/catecismo-menor",
        "digest": MANIFEST_RAW_FILE_SHA256,
        "hash_domain": "raw_file_sha256",
        "issuer_claim": "teologia.ai",
    }
    wire = envelope.encode("manifest", record)
    assert wire.isascii()
    kind, decoded = envelope.decode(wire)
    assert kind == "manifest"
    assert decoded == record
    # A decoded manifest is data, never an authorization grant.
    assert "grant" not in decoded


def test_raw_file_digest_requires_exact_current_bytes():
    content = b"<html><body>Study guide</body></html>"
    expected = hashlib.sha256(content).hexdigest()
    assert hashlib.sha256(content).hexdigest() == expected
    assert hashlib.sha256(content + b" ").hexdigest() != expected


def test_receipt_issuer_claim_is_not_signature():
    receipt = json.loads(
        '{"issuer":"☺://cc","decoded_ok":true,"note":"signed intent can travel"}'
    )
    assert "signature" not in receipt
    assert "public_key" not in receipt
    assert receipt["decoded_ok"] is True  # reported claim, not independent proof
