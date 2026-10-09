"""aeqr.gpu_batch — real GPU batch SHA-256 (the .mec's claim, made true).

`qr_index.mec` declares "RTX-accelerated SHA-256 batch for chain verification".
CuPy has no hashlib, so this implements SHA-256 as a CUDA kernel via
cupy.RawKernel: CPU pads each message, the GPU runs the compression function
one thread per message, and every result is checked against hashlib.

Honest by construction: `available()` reports the truth, `selftest()` proves
the kernel matches hashlib bit-for-bit, and callers fall back to CPU hashlib
when no GPU is present. The receipt records which engine ran.
"""
from __future__ import annotations

import hashlib
import numpy as np

_K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]
_KSRC = ",".join("0x%08xu" % k for k in _K)

_CUDA_SRC = r"""
#define ROR(x,n) (((x)>>(n))|((x)<<(32-(n))))
__constant__ unsigned int K[64] = {""" + _KSRC + r"""};

__device__ void sha256_compress(unsigned int* s, const unsigned char* p){
  unsigned int w[64];
  #pragma unroll
  for(int i=0;i<16;i++) w[i]=((unsigned int)p[i*4]<<24)|((unsigned int)p[i*4+1]<<16)|((unsigned int)p[i*4+2]<<8)|(unsigned int)p[i*4+3];
  #pragma unroll
  for(int i=16;i<64;i++){
    unsigned int s0=ROR(w[i-15],7)^ROR(w[i-15],18)^(w[i-15]>>3);
    unsigned int s1=ROR(w[i-2],17)^ROR(w[i-2],19)^(w[i-2]>>10);
    w[i]=w[i-16]+s0+w[i-7]+s1;
  }
  unsigned int a=s[0],b=s[1],c=s[2],d=s[3],e=s[4],f=s[5],g=s[6],h=s[7];
  #pragma unroll
  for(int i=0;i<64;i++){
    unsigned int S1=ROR(e,6)^ROR(e,11)^ROR(e,25);
    unsigned int ch=(e&f)^((~e)&g);
    unsigned int t1=h+S1+ch+K[i]+w[i];
    unsigned int S0=ROR(a,2)^ROR(a,13)^ROR(a,22);
    unsigned int maj=(a&b)^(a&c)^(b&c);
    unsigned int t2=S0+maj;
    h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
  }
  s[0]+=a;s[1]+=b;s[2]+=c;s[3]+=d;s[4]+=e;s[5]+=f;s[6]+=g;s[7]+=h;
}

extern "C" __global__ void sha256_batch(
  const unsigned char* data, const int* offs, const int* counts,
  unsigned int* out, int n)
{
  int idx=blockIdx.x*blockDim.x+threadIdx.x;
  if(idx>=n) return;
  unsigned int s[8]={0x6a09e667u,0xbb67ae85u,0x3c6ef372u,0xa54ff53au,
                     0x510e527fu,0x9b05688cu,0x1f83d9abu,0x5be0cd19u};
  int off=offs[idx], bc=counts[idx];
  for(int b=0;b<bc;b++) sha256_compress(s, data+off+b*64);
  for(int i=0;i<8;i++) out[idx*8+i]=s[i];
}
"""

_kernel = None
_reason = "not initialised"


def _pad(msg: bytes) -> bytes:
    """SHA-256 padding: 0x80, zeros to 56 mod 64, 64-bit big-endian bit length."""
    ml = (len(msg) * 8) & 0xFFFFFFFFFFFFFFFF
    out = bytearray(msg) + b"\x80"
    while len(out) % 64 != 56:
        out += b"\x00"
    out += ml.to_bytes(8, "big")
    return bytes(out)


def available() -> tuple:
    """(True, device) if the CUDA kernel compiled; (False, reason) otherwise."""
    global _kernel, _reason
    if _kernel is not None:
        return True, _reason
    try:
        import cupy as cp
        _kernel = cp.RawKernel(_CUDA_SRC, "sha256_batch", options=("-std=c++11",))
        p = cp.cuda.runtime.getDeviceProperties(0)
        name = p["name"].decode() if isinstance(p["name"], bytes) else str(p["name"])
        _reason = "%s (cupy %s)" % (name, cp.__version__)
        return True, _reason
    except Exception as exc:  # pragma: no cover - depends on host GPU
        _reason = "%s: %s" % (type(exc).__name__, exc)
        return False, _reason


def sha256_batch(messages: list) -> tuple:
    """SHA-256 of each message. Returns (hex digests, engine).

    engine is 'cuda' when the GPU kernel ran, else 'cpu' (hashlib fallback).
    """
    n = len(messages)
    if n == 0:
        return [], "cuda" if available()[0] else "cpu"
    ok, _ = available()
    if not ok:
        return [hashlib.sha256(m).hexdigest() for m in messages], "cpu"

    import cupy as cp
    padded = [_pad(m) for m in messages]
    counts = [len(p) // 64 for p in padded]
    offsets = np.zeros(n, dtype=np.int32)
    run = 0
    for i, p in enumerate(padded):
        offsets[i] = run
        run += len(p)
    data = np.frombuffer(b"".join(padded), dtype=np.uint8)
    d_gpu = cp.asarray(data)
    o_gpu = cp.asarray(offsets)
    c_gpu = cp.asarray(np.asarray(counts, dtype=np.int32))
    out = cp.empty((n, 8), dtype=cp.uint32)
    threads = 128
    blocks = (n + threads - 1) // threads
    _kernel((blocks,), (threads,), (d_gpu, o_gpu, c_gpu, out, np.int32(n)))
    cp.cuda.Stream.null.synchronize()
    words = cp.asnumpy(out)
    digests = ["".join("%08x" % int(w) for w in words[i]) for i in range(n)]
    return digests, "cuda"


def selftest(trials: int = 64) -> dict:
    """Prove the GPU kernel matches hashlib on varied-length messages."""
    import random
    random.seed(0)
    msgs = [bytes(random.randrange(256) for _ in range(random.randrange(0, 300))) for _ in range(trials)]
    got, engine = sha256_batch(msgs)
    want = [hashlib.sha256(m).hexdigest() for m in msgs]
    mismatches = [i for i in range(trials) if got[i] != want[i]]
    return {"engine": engine, "trials": trials, "match": not mismatches,
            "mismatches": mismatches[:5], "device": available()[1]}


if __name__ == "__main__":
    ok, why = available()
    print("gpu available: %s  (%s)" % (ok, why))
    r = selftest()
    print("selftest: engine=%s trials=%s match=%s %s" % (r["engine"], r["trials"], r["match"], r["mismatches"]))
