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

## Use

```bash
python -m ae.dispatch C:/æ/hermes-fork/mech/qr_index.mec
aeqr dispatch C:/æ/hermes-fork/mech/qr_index.mec --units 8 --workers 8
```

Exit code is `0` when sealed, `1` when any unit was refused.
