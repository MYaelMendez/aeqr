"""aeqr.authority — scanning never grants execution.

A QR is an ADDRESS, not permission. A registry entry is an ADDRESS, not
permission. Acting on a resource (publish / execute / merge) requires an
explicit Capability grant, scoped to an action and origin. Default DENY.

    resolve -> allowed (reading an address is not acting)
    read    -> allowed
    verify  -> allowed (verification produces evidence, not effect)
    publish -> REQUIRES a capability
    execute -> REQUIRES a capability
    merge   -> REQUIRES a capability
"""
from __future__ import annotations

import time
from dataclasses import dataclass, asdict

ACTIONS = ("resolve", "read", "verify", "publish", "execute", "merge")
OPEN_ACTIONS = ("resolve", "read", "verify")   # granted by scanning alone
GATED_ACTIONS = ("publish", "execute", "merge")  # require an explicit grant


class AuthorityError(Exception):
    """Raised when an action is attempted without a valid capability."""


@dataclass
class Capability:
    subject: str            # who holds it
    action: str             # one of ACTIONS
    scope: str              # resource id, category, or "*"
    granted_by: str = ""    # the human/authority that granted it
    expires: float | None = None  # unix ts; None = no expiry

    def is_valid(self, now: float | None = None) -> bool:
        if self.action not in ACTIONS:
            return False
        if self.expires is not None:
            now = time.time() if now is None else now
            if now >= self.expires:
                return False
        return True

    def covers(self, action: str, resource_id: str | None = None) -> bool:
        if not self.is_valid():
            return False
        if self.action != action:
            return False
        if self.scope == "*":
            return True
        return resource_id is not None and self.scope == resource_id

    def to_payload(self) -> dict:
        return asdict(self)


def requires_authority(action: str) -> bool:
    """True when `action` cannot proceed from scanning alone."""
    return action in GATED_ACTIONS


def authorize(action: str, capabilities: list[Capability],
              resource_id: str | None = None, now: float | None = None) -> bool:
    """Return True only if `action` is permitted.

    Open actions pass without a capability. Gated actions require a valid
    capability that covers the action (and resource, unless scope is '*').
    """
    if action in OPEN_ACTIONS:
        return True
    if action in GATED_ACTIONS:
        return any(c.covers(action, resource_id) and c.is_valid(now) for c in capabilities)
    return False  # unknown action -> deny


def require(action: str, capabilities: list[Capability],
            resource_id: str | None = None, now: float | None = None) -> None:
    """Like authorize() but raises AuthorityError instead of returning False."""
    if not authorize(action, capabilities, resource_id, now):
        raise AuthorityError(
            f"action '{action}' on {resource_id or '*'} requires an explicit "
            f"capability grant (default deny)")
