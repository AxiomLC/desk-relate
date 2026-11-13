"""DeskRelate CLI: python main.py scan | delta | query \"...\" | report"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from app.config import Knobs


def main() -> int:
    ap = argparse.ArgumentParser(prog="deskrelate")
    ap.add_argument("cmd", choices=["scan", "delta", "query", "report"])
    ap.add_argument("arg", nargs="?", help="cypher for query cmd")
    ap.add_argument("--knobs", default=None, help="path to knobs.json")
    args = ap.parse_args()
    k = Knobs.load(args.knobs and Path(args.knobs) or None)

    if args.cmd == "scan":
        from app.collector import collect
        from app.scrubber import scrub_staged
        from app.grapher import graphify
        step = collect(k)
        print("collect:", json.dumps(step))
        results = scrub_staged(k)
        print("scrub:", json.dumps({"docs": len(results),
                                    "redactions": sum(r.redactions for r in results),
                                    "rejected": sum(r.rejects for r in results)}))
        stats = graphify(k)
        print("graph:", json.dumps(stats))

    elif args.cmd == "delta":
        from app.delta import classify
        print(json.dumps(classify(k), indent=2))

    elif args.cmd == "query":
        import relate  # type: ignore
        db = relate.connect(str(k.graph_path))
        rows = db.execute(args.arg)
        for row in rows:
            print(row)

    else:  # report
        for name in ("refusals.jsonl", "delta_events.jsonl"):
            p = k.spool_dir / name
            if p.exists():
                print(f"--- {name} ---")
                print(p.read_text(encoding="utf-8")[-2000:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
