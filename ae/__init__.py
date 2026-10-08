"""æQR — resource addressing, verification, and audit for the æ constellation.

  envelope    — the typed ae:1:<type>:<b64url(json)> transport
  supervision — produce-and-verify gate (two real decoders)
  registry    — stable resource IDs → canonical routes + scope
  orchard     — audits, evidence snapshots, comparison, repair queue
  authority   — scanning never grants execution; the human decides
"""
__version__ = "0.1.0"
