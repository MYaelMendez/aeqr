"""aeqr.registry — stable resource IDs to canonical routes + scope.

One discovery layer across many resources, WITHOUT making every resource public.
A registry entry is an ADDRESS and a SCOPE. It is never a grant.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = REPO_ROOT / "registry" / "resources.json"

SCOPES = ("public", "local", "private", "hybrid")
REQUIRED = ("id", "name", "path", "category", "scope", "route", "type")


class RegistryError(ValueError):
    """Raised when the registry is missing, malformed, or ambiguous."""


@dataclass
class Resource:
    id: str
    name: str
    path: str
    category: str
    scope: str
    route: str
    type: str
    verified: bool = False
    evidence: str | None = None
    series: str | None = None
    series_brand: str | None = None
    episode: int | None = None
    episode_title: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def public(self) -> bool:
        return self.scope in ("public", "hybrid")


def validate(data: dict) -> None:
    if not isinstance(data, dict) or "resources" not in data:
        raise RegistryError("registry must be an object with a 'resources' list")
    seen: set[str] = set()
    for r in data["resources"]:
        for f in REQUIRED:
            if f not in r:
                raise RegistryError(f"resource missing field '{f}': {r!r}")
        if r["scope"] not in SCOPES:
            raise RegistryError(f"invalid scope {r['scope']!r} (valid: {SCOPES})")
        if r["id"] in seen:
            raise RegistryError(f"duplicate resource id {r['id']!r}")
        seen.add(r["id"])


def load(path: str | Path = DEFAULT_PATH) -> dict:
    p = Path(path)
    if not p.exists():
        raise RegistryError(f"registry not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    validate(data)
    return data


def resources(path: str | Path = DEFAULT_PATH) -> list[Resource]:
    return [Resource(**r) for r in load(path)["resources"]]


def resolve(rid: str, path: str | Path = DEFAULT_PATH) -> Resource | None:
    for r in resources(path):
        if r.id == rid:
            return r
    return None


def by_category(category: str, path: str | Path = DEFAULT_PATH) -> list[Resource]:
    return [r for r in resources(path) if r.category == category]


def counts(path: str | Path = DEFAULT_PATH) -> dict:
    out: dict[str, int] = {}
    for r in resources(path):
        out[r.category] = out.get(r.category, 0) + 1
    return out
