"""
æQR Surfaces Indexer — walks github-pages, builds a SURFACES index.

NOTE: this emits a DIFFERENT schema (dict keyed by id, {id,label,route,kind,
scope,sha256,produced}) than the CONTRACT registry that ae/registry.py +
the tests expect (list of {id,name,path,category,scope,route,type}).
It therefore writes to registry/surfaces-index.json — NEVER to
registry/resources.json, which is the contract.

Usage: python C:/æ/aeqr/index.py
Output: C:/æ/aeqr/registry/surfaces-index.json
"""
import pathlib, json, hashlib, re
from datetime import datetime, timezone

GH_PAGES = pathlib.Path(r"C:\æ\github-pages")
REGISTRY_OUT = pathlib.Path(r"C:\æ\aeqr\registry\surfaces-index.json")


def classify_kind(rel: str, content: str) -> str:
    """Classify HTML surface by kind based on path + content signals."""
    r = rel.lower()
    if "three.min.js" in content or "Three.js" in content:
        return "threejs"
    if "dodecahedron" in content.lower() or "icosahedron" in content.lower():
        return "threejs"
    if "calendar" in r or "liturgical" in r:
        return "calendar"
    if "storyboard" in r:
        return "storyboard"
    if "verify" in r:
        return "verification"
    if "constellation" in r:
        return "constellation"
    if "kaenbaen" in r:
        return "memory"
    if "teologia" in r:
        return "theology"
    if "mp4-factory" in r or "vidæo" in r or "vidao" in r:
        return "video"
    if "capture" in r:
        return "capture"
    if "taskbar" in r:
        return "shell"
    return "page"


def build_registry() -> dict:
    """Walk filesystem, build resource records from actual HTML files."""
    resources = {}
    html_files = sorted(GH_PAGES.rglob("*.html"))

    for f in html_files:
        rel = f.relative_to(GH_PAGES).as_posix()
        rid = rel.replace(".html", "").replace("/", "-").replace("_", "-")

        content = f.read_text(encoding="utf-8", errors="replace")
        kind = classify_kind(rel, content)
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        label = rel.replace(".html", "").replace("/", " · ")

        resources[rid] = {
            "id": rid,
            "label": label,
            "route": rel,
            "kind": kind,
            "scope": "public",
            "sha256": sha,
            "produced": mtime,
        }

    return {
        "version": 1,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "aeqr-index-python",
        "source": "filesystem",
        "resource_count": len(resources),
        "resources": resources,
    }


def verify_registry(registry: dict) -> list[str]:
    """Run integrity checks on the built registry."""
    errors = []
    resources = registry["resources"]
    routes = [r["route"] for r in resources.values()]

    # Check for duplicate routes
    seen = set()
    for r in routes:
        if r in seen:
            errors.append(f"Duplicate route: {r}")
        seen.add(r)

    # Check all routes exist on disk
    for r in resources.values():
        p = GH_PAGES / r["route"]
        if not p.exists():
            errors.append(f"Route missing on disk: {r['route']}")

    # Check required fields
    required = {"id", "label", "route", "kind", "scope", "sha256", "produced"}
    for rid, r in resources.items():
        missing = required - set(r.keys())
        if missing:
            errors.append(f"Resource {rid} missing fields: {missing}")

    return errors


def main():
    print(f"Indexing: {GH_PAGES}")
    registry = build_registry()
    resources = registry["resources"]
    print(f"Found {len(resources)} HTML files")

    # Count by kind
    kinds = {}
    for r in resources.values():
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    for k, v in sorted(kinds.items()):
        print(f"  {k}: {v}")

    # Verify
    errors = verify_registry(registry)
    if errors:
        print(f"\n{len(errors)} ERRORS:")
        for e in errors[:20]:
            print(f"  ❌ {e}")
    else:
        print("\n✓ All integrity checks passed")

    # Write registry
    REGISTRY_OUT.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"✓ Registry written: {REGISTRY_OUT} ({REGISTRY_OUT.stat().st_size} bytes)")

    return len(errors)


if __name__ == "__main__":
    exit_code = main()
    if exit_code:
        exit(1)
