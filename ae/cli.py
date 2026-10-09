"""aeqr.cli — one command surface for the æQR system.

    aecli registry [--category C]        list resources from the registry
    aecli resolve <id>                    resolve one resource by stable id
    aecli orchard audit <root>            run the inline-script syntax audit
    aecli orchard compare <prev> <cur>    delta between two snapshot JSONs
    aecli orchard queue <root>            findings -> ordered repair queue
    aecli authority <action> [--id R]     is an action permitted? (default deny)
    aecli version
"""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from . import registry as reg
from . import authority as auth
from . import orchard as orch
from . import dispatch as disp


def _p(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(prog="aeqr", description="æQR — resource addressing, verification, audit")
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("version")

    r = sub.add_parser("registry")
    r.add_argument("--category", default=None)
    r.add_argument("--public", action="store_true", help="only public/hybrid resources")

    s = sub.add_parser("resolve")
    s.add_argument("id")

    o = sub.add_parser("orchard")
    os_ = o.add_subparsers(dest="osub")
    oa = os_.add_parser("audit"); oa.add_argument("root"); oa.add_argument("--node", default="node")
    oa.add_argument("--gpu", choices=["auto", "on", "off"], default="auto")
    oc = os_.add_parser("compare"); oc.add_argument("prev"); oc.add_argument("cur")
    oq = os_.add_parser("queue"); oq.add_argument("root"); oq.add_argument("--node", default="node")
    oq.add_argument("--gpu", choices=["auto", "on", "off"], default="auto")

    a = sub.add_parser("authority")
    a.add_argument("action", choices=list(auth.ACTIONS))
    a.add_argument("--id", dest="rid", default=None)
    a.add_argument("--grant", default=None, help="'action:scope' capability to test with")

    d = sub.add_parser("dispatch")
    d.add_argument("spec")
    d.add_argument("--units", type=int, default=8)
    d.add_argument("--workers", type=int, default=8)
    d.add_argument("--registry", action="store_true",
                   help="source units from the 269-resource registry (real inventory)")
    d.add_argument("--gpu", choices=["auto", "on", "off"], default="auto")

    args = ap.parse_args(argv)

    if args.cmd == "version":
        print(f"aeqr {__version__}")
        return 0

    if args.cmd == "registry":
        if args.category:
            rs = reg.by_category(args.category)
        else:
            rs = reg.resources()
        if args.public:
            rs = [x for x in rs if x.public]
        _p([x.to_dict() for x in rs])
        return 0

    if args.cmd == "resolve":
        res = reg.resolve(args.id)
        if res is None:
            print(f"not found: {args.id}", file=sys.stderr); return 1
        _p(res.to_dict())
        return 0

    if args.cmd == "orchard":
        if args.osub == "audit":
            gpu = None if args.gpu == "auto" else (args.gpu == "on")
            snap = orch.audit_inline_scripts(args.root, node=args.node, gpu=gpu)
            _p(snap.to_dict())
            return 1 if snap.blockers else 0
        if args.osub == "compare":
            prev = json.loads(Path(args.prev).read_text(encoding="utf-8"))
            cur = json.loads(Path(args.cur).read_text(encoding="utf-8"))
            _p(orch.compare(prev, cur)); return 0
        if args.osub == "queue":
            gpu = None if args.gpu == "auto" else (args.gpu == "on")
            snap = orch.audit_inline_scripts(args.root, node=args.node, gpu=gpu)
            _p(orch.to_kanban(snap)); return 0
        o.print_help(); return 2

    if args.cmd == "authority":
        caps = []
        if args.grant:
            action, _, scope = args.grant.partition(":")
            caps = [auth.Capability(subject="cli", action=action, scope=scope or "*", granted_by="operator")]
        allowed = auth.authorize(args.action, caps, resource_id=args.rid)
        _p({"action": args.action, "resource": args.rid, "allowed": allowed,
            "requires_authority": auth.requires_authority(args.action)})
        return 0 if allowed else 1

    if args.cmd == "dispatch":
        if args.registry:
            units = disp.units_from_registry(limit=args.units)
        else:
            units = disp.demo_units(args.units)
        gpu = None if args.gpu == "auto" else (args.gpu == "on")
        rec = disp.fleet_dispatch(args.spec, units, workers=args.workers, gpu=gpu)
        _p(rec.to_dict())
        return 0 if rec.sealed else 1

    ap.print_help()
    return 2


# `Path` is referenced in the orchard compare branch
from pathlib import Path  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
