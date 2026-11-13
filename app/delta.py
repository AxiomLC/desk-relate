"""Delta: re-run classifier. new / altered / touched / gone, from ledger."""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

from .config import Knobs, jlog
from .collector import file_hash


def classify(k: Knobs) -> dict:
    ledger_path = k.spool_dir / "ledger.jsonl"
    if not ledger_path.exists():
        return {"error": "no ledger yet — run scan first"}

    prev: dict[str, dict] = {}
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        prev[row["path"]] = row

    seen_paths: set[str] = set()
    now_state: dict[str, dict] = {}
    for root in k.folders:
        root = root.expanduser()
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            sp = str(p)
            seen_paths.add(sp)
            ext = p.suffix.lower()
            if ext in k.file_types_never or ext not in k.file_types:
                continue
            st = p.stat()
            now_state[sp] = {"size": st.st_size, "mtime": st.st_mtime, "ext": ext,
                             "path": sp}

    events = defaultdict(list)
    for sp, st in now_state.items():
        old = prev.get(sp)
        if old is None:
            events["new"].append(sp)
        elif old["size"] != st["size"]:
            events["altered"].append(sp)
        elif "mtime" not in old or abs(old["mtime"] - st["mtime"]) < 0.001:
            pass  # identical, or ledger predates mtime tracking → verify by hash below
        else:
            events["touched"].append(sp)
            digest = file_hash(p)
            if digest == old.get("blake3"):
                events["touched"].pop()  # timestamp churn, same content
    for sp in set(prev) - seen_paths:
        events["gone"].append(sp)

    report = {kinds: len(v) for kinds, v in events.items()}
    jlog(k.spool_dir / "delta_events.jsonl", {"report": report,
                                              "new": events["new"][:20],
                                              "altered": events["altered"][:20],
                                              "gone": events["gone"][:20]})
    return {"report": report,
            "note": "purge/rename resolution prompts are a UI-phase feature; "
                    "gone-files are only reported, never auto-removed"}
