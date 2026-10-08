# The æQR gate — SPEC → RENDER → SUPERVISE → (PASS: receipt) | (FAIL: refuse)

The producer **proposes** a QR. The supervisor **disposes**. There is no code
path that returns a path to a QR that does not decode.

## Why it exists

A silent failure class: an envelope whose magic was the rune `æ:` **encodes
correctly**, renders a valid-looking QR, and **fails on scan**. pyzbar
re-interprets the two UTF-8 bytes of `æ` (`C3 A6`) as halfwidth katakana
(`ﾃｦ`). An in-memory round trip passes; only a real decoder catches it. That is
why the gate uses **two** independent real decoders.

## The nine checks (deterministic, no ML)

| # | check | threshold |
|---|---|---|
| 1 | charset | pure ASCII (catches the rune class up front) |
| 2 | version | envelope fits the declared QR capacity |
| 3 | roundtrip | the rendered PNG decodes back to the exact envelope |
| 4 | cross_decoder | **cv2 AND pyzbar agree** |
| 5 | payload_match | decoded payload == the payload asked for |
| 6 | type_fidelity | decoded type == the declared type |
| 7 | module_size | modules >= MIN_MODULE_PX (3) |
| 8 | quiet_zone | the required border is present |
| 9 | contrast | (light-dark)/(light+dark) >= MIN_CONTRAST (0.35) |

## Exit codes

`0 = PASS` (receipt emitted), `1 = REFUSED`. Usable as a real gate.

## Retry policy

A **charset** refusal is not retried — the payload itself is wrong and no
rendering fixes it. A **module-size** or **contrast** refusal is retried once
with a larger `box_size` (a real remedy).

## The receipt

Emitted only on PASS. Hash-chained over the artifact and the verdict:

```
chain = H(prev ∥ intent ∥ ops ∥ result ∥ state ∥ evidence)
```

Carries the envelope SHA-256, the image SHA-256, and the decoder list.
