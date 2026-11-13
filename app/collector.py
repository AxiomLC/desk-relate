"""Collector: deterministic staging. Paths + hashes only. No LLM, no network."""
from __future__ import annotations
import shutil
from pathlib import Path

import blake3  # type: ignore

from .config import Knobs, jlog

SECRET_NAME_PATTERNS = ("password", "credential", "secret", "wallet", "id_rsa", "id_ed25519")
def is_denied_dir(rel_parts: tuple[str, ...], deny_dirs: list[str]) -> bool:
    low = {part.lower() for part in rel_parts}
    return any(d.lower() in low for d in deny_dirs)


def file_hash(p: Path) -> str:
    h = blake3.blake3()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# OneDrive On-Demand: cloud-only placeholders carry these attribute bits
_WIN_HAS_ATTRS = hasattr(__import__("os").stat(r"."), "st_file_attributes")
_CLOUD_ONLY_BITS = 0x00001000 | 0x00400000  # OFFLINE | RECALL_ON_DATA_ACCESS


def is_cloud_only(p: Path) -> bool:
    if not _WIN_HAS_ATTRS:
        return False
    attrs = getattr(p.stat(), "st_file_attributes", 0)
    return bool(attrs & _CLOUD_ONLY_BITS) if attrs else False


def walk_files(root: Path, k):
    """Yield (path, rel_parts) within depth and denial limits."""
    def rec(dir_path: Path, rel: tuple[str, ...], depth: int):
        if depth > k.max_folder_depth:
            return
        for p in dir_path.iterdir():
            rel_p = rel + (p.name,)
            if p.is_dir():
                if is_denied_dir(rel_p, k.never_folders):
                    continue
                yield from rec(p, rel_p, depth + 1)
            elif p.is_file():
                yield p, rel_p
    yield from rec(root, (), 1)


def collect(k: Knobs) -> dict:
    """Index + stage allowlisted files into spool/incoming. Returns a summary."""
    inbox = k.spool_dir / "incoming"
    inbox.mkdir(parents=True, exist_ok=True)
    ledger = k.spool_dir / "ledger.jsonl"
    refusals = k.spool_dir / "refusals.jsonl"
    staged = refused = cloud_only = 0

    for root in k.folders:
        root = root.expanduser()
        if not root.is_dir():
            jlog(refusals, {"reason": "missing-dir", "path": str(root)})
            continue
        for p, rel in walk_files(root, k):
            lname = p.name.lower()
            ext = p.suffix.lower()
            if ext in k.file_types_never:
                jlog(refusals, {"reason": "file_types_never", "path": str(p)})
                refused += 1
                continue
            if any(s in lname for s in SECRET_NAME_PATTERNS):
                jlog(refusals, {"reason": "name-like-secret", "path": str(p)})
                refused += 1
                continue
            if ext not in k.file_types:
                continue
            cloud = is_cloud_only(p)
            if cloud and k.cloud_files == "skip":
                jlog(k.spool_dir / "cloud_only.jsonl", {"path": str(p), "size": p.stat().st_size})
                cloud_only += 1
                continue  # indexed nowhere yet — surfaced for a later hydrate decision
            try:
                digest = file_hash(p)
            except PermissionError:
                jlog(refusals, {"reason": "permission", "path": str(p)})
                refused += 1
                continue
            dest = inbox / f"{digest[:16]}{ext}"
            if not dest.exists():
                shutil.copy2(p, dest)
            st = p.stat()
            jlog(ledger, {"path": str(p), "blake3": digest, "size": st.st_size,
                          "mtime": st.st_mtime, "ext": ext, "staged_as": dest.name})
            staged += 1

    return {"staged": staged, "refused": refused, "cloud_only_skipped": cloud_only,
            "inbox": str(inbox)}
