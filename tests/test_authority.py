import pytest
from ae import authority as a


def test_open_actions_allowed_without_capability():
    for act in a.OPEN_ACTIONS:
        assert a.authorize(act, []) is True


def test_gated_actions_denied_by_default():
    for act in a.GATED_ACTIONS:
        assert a.authorize(act, []) is False
        assert a.requires_authority(act) is True


def test_gated_action_allowed_with_valid_capability():
    cap = a.Capability(subject="op", action="publish", scope="teologia-index", granted_by="human")
    assert a.authorize("publish", [cap], resource_id="teologia-index") is True
    # wrong resource -> denied
    assert a.authorize("publish", [cap], resource_id="other") is False
    # wrong action -> denied
    assert a.authorize("merge", [cap], resource_id="teologia-index") is False


def test_wildcard_scope_covers_anything():
    cap = a.Capability(subject="op", action="execute", scope="*", granted_by="human")
    assert a.authorize("execute", [cap], resource_id="whatever") is True


def test_expired_capability_denied():
    cap = a.Capability(subject="op", action="publish", scope="*", granted_by="human", expires=1.0)
    assert a.authorize("publish", [cap], now=2.0) is False


def test_require_raises_on_deny():
    with pytest.raises(a.AuthorityError):
        a.require("merge", [])
    a.require("read", [])  # open action: no raise
