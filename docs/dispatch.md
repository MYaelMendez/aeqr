# The dispatch bridge — Mech = spec, æQR = contract, Fleet = scheduler

`fleet_dispatch(mech_spec, units, workers) -> DispatchReceipt` is the one
build that turns "Mech + æQR = parallel compute" from a claim into a fact.

## Why it exists

Mech (mech-lang.org) declares reactive dataflow, but its engine does not run
on this build — `mechc` v0.3.5 fails to build even its own
`examples/working/*.mec`. So a `.mec` file is a **declaration**, not a
program. This module parses that declaration into a stage DAG and runs it
with real workers, sealing the result as an æQR receipt.

## The three layers, made one

| Mech (grammar) | æQR (contract) | Fleet (this module) |
|---|---|---|
| `:Scan` | image -> bytes | worker reads the payload |
| `:Decode` | `envelope.decode` — typed, fails closed | worker decodes + hashes |
| `:Verify(spec, chain)` | **hash-chain match** | the **join** |
| `:Resolve` | `registry.resolve` + scope | worker routes to the artifact |
| `:Retrieve` | artifact fetch | worker emits it |
| `-> :Refused` | **default-deny** | BLOCKED receipt |

## What the receipt proves

- the spec is what ran (`spec_sha256`)
- every unit **decoded back** (a QR that has not been decoded back is a
  picture of one) — units that don't are `:Refused`
- independent units ran **in parallel** (`parallel: true` when >= 2 units
  were in flight at once)
- the whole run is a single hash-chained **seal**, itself scannable as an
  `ae:1:manifest:` envelope

## The GPU engine (the .mec's claim, made true)

`qr_index.mec` declares "RTX-accelerated SHA-256 batch for chain verification".
CuPy has no hashlib, so `ae/gpu_batch.py` implements SHA-256 as a **CUDA kernel**
(`cupy.RawKernel`): CPU pads each message, the GPU runs the compression function
one thread per message, and every result is checked against hashlib
(`selftest` -> 64/64 match). The `:Verify` join hashes the whole batch in **one
kernel launch** when a GPU is present, and falls back to CPU hashlib otherwise.
The receipt records which engine ran (`engine: cuda|cpu`) — and the **seal is
identical** either way, because the engine is an implementation detail, not part
of the contract.

Verified on this host: `NVIDIA GeForce RTX 3050 6GB` (cupy 14.2.0),
`engine=cuda trials=64 match=True`.

## Units from the real inventory

`units_from_registry()` builds units from the 269-resource registry (the
gh-pages inventory) — each unit is an address + its expected hash, exactly what
`:Verify` checks. `--registry` sources the run from real routes, not synthetic
ones.

## Use

```bash
python -m ae.dispatch C:/æ/hermes-fork/mech/qr_index.mec
aeqr dispatch C:/æ/hermes-fork/mech/qr_index.mec --units 8 --workers 8
aeqr dispatch C:/æ/hermes-fork/mech/qr_index.mec --registry --units 24 --workers 8 --gpu on
```

Exit code is `0` when sealed, `1` when any unit was refused.
