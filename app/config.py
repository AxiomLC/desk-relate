"""Config loading for DeskRelate. Single source of truth: knobs.json.

Knob names are the future UI labels — plain terms a user would pick from:
which folders, how deep, which file types, what privacy rules per class.
Verdicts: keep | hide | block.
"""
from __future__ import annotations
import json, os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _expand(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(p)))


@dataclass
class Knobs:
    folders: list[Path]                      # folders to scan
    never_folders: list[str]                 # folder names never to enter
    file_types: set[str]                     # exts allowed
    file_types_never: set[str]               # exts refused outright
    max_folder_depth: int                    # how deep to walk
    cloud_files: str                         # skip | download (OneDrive On-Demand)
    spool_dir: Path
    graph_path: Path
    out_dir: Path
    llm: dict[str, Any]
    privacy_rules: dict[str, str]            # class → keep|hide|block
    delta: dict[str, Any]

    @classmethod
    def load(cls, path: Path | None = None) -> "Knobs":
        p = path or ROOT / "knobs.json"
        raw = json.loads(p.read_text(encoding="utf-8"))
        return cls(
            folders=[_expand(d) for d in raw.get("folders", raw.get("scan_dirs", []))],
            never_folders=raw.get("never_folders", raw.get("deny_dirs", [])),
            file_types={e.lower() for e in raw.get("file_types", raw.get("ext_allow", []))},
            file_types_never={e.lower() for e in raw.get("file_types_never", raw.get("ext_deny", []))},
            max_folder_depth=int(raw.get("max_folder_depth", 8)),
            cloud_files=raw.get("cloud_files", "skip"),
            spool_dir=_expand(raw["spool_dir"]),
            graph_path=_expand(raw["graph_path"]),
            out_dir=_expand(raw["out_dir"]),
            llm=raw.get("llm", {}),
            privacy_rules=_normalize_rules(raw.get("privacy_rules", raw.get("sensitivity", {}))),
            delta=raw.get("delta", {}),
        )


# old internal names → new plain names (accept both in config files)
_ALIASES = {
    "phone_numbers": "phones",
    "bank_shapes": "bank_details",
    "ids_ssn_style": "id_numbers",
    "software_tokens": "passwords_and_tokens",
}
# old verdicts → new verdicts
_VERDICT_ALIASES = {"ingest": "keep", "redact": "hide", "reject": "block"}


def _normalize_rules(rules: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for cls, verdict in rules.items():
        cls = _ALIASES.get(cls, cls)
        out[cls] = _VERDICT_ALIASES.get(verdict, verdict)
    return out


def jlog(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
