"""Scrubber pass #1: deterministic regex. Verdicts from knobs.sensitivity."""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import Knobs, jlog

# (class_name, compiled_pattern) — deterministic, ordered by danger
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("crypto_keys", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("api_keys", re.compile(r"\b(?:AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,})\b")),
    ("passwords_and_tokens", re.compile(r"\b(?:Bearer|token|api[_-]?key)\s*[:=]\s*\S{16,}", re.I)),
    ("id_numbers", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_cards", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("emails", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("phones", re.compile(r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")),
    ("bank_details", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")),  # IBAN-ish
]


@dataclass
class ScrubResult:
    path: str
    verdicts: dict[str, str] = field(default_factory=dict)   # class → count/verdict
    redactions: int = 0
    rejects: int = 0
    redacted_text: str = ""
    alias: dict[str, str] = field(default_factory=dict)      # original → PERSON-1 etc.


def _alias_for(kind: str, n: int) -> str:
    prefix = {
        "emails": "CONTACT",
        "phones": "PHONE",
        "bank_details": "BANK",
        "addresses": "ADDRESS",
        "person_names": "PERSON",
    }.get(kind, kind.split("_")[0].upper())
    return f"{prefix}-{n}"


def scrub_text(text: str, k: Knobs) -> ScrubResult:
    r = ScrubResult(path="")
    counters: dict[str, int] = {}

    for kind, pat in PATTERNS:
        verdict = k.privacy_rules.get(kind, "hide")
        hits = pat.findall(text)
        if not hits:
            continue
        r.verdicts[kind] = verdict
        if verdict == "block":
            r.rejects += 1
            continue  # caller drops whole doc if rejects > 0
        if verdict == "hide":
            if pat.groups:
                continue  # patterns with capture groups must not be subbed raw
            counters.setdefault(kind, 0)
            def sub(m, kind=kind):
                counters[kind] += 1
                a = _alias_for(kind, counters[kind])
                r.alias[m.group(0)] = a
                return a
            text = pat.sub(sub, text)
            r.redactions += len(hits)
    r.redacted_text = text
    return r


def scrub_staged(k: Knobs) -> list[ScrubResult]:
    """Read staged files (text-shaped), scrub, write sidecar JSON verdicts."""
    inbox = k.spool_dir / "incoming"
    staged_out = k.spool_dir / "scrubbed"
    staged_out.mkdir(parents=True, exist_ok=True)
    results: list[ScrubResult] = []

    TEXT_EXT = {".md", ".txt", ".csv", ".json", ".eml", ".html", ".doc"}  # doc>parsers next phase
    for f in sorted(inbox.iterdir()):
        if f.suffix.lower() not in TEXT_EXT:
            continue
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001 — log and move on
            jlog(k.spool_dir / "refusals.jsonl", {"reason": f"read-fail:{e}", "path": str(f)})
            continue
        r = scrub_text(raw, k)
        r.path = str(f)
        if r.rejects > 0:
            jlog(k.spool_dir / "refusals.jsonl",
                 {"reason": "piggy:reject-class", "path": str(f), "verdicts": r.verdicts})
            f.with_suffix(".rejected").touch()
            continue
        out_json = staged_out / f"{f.stem}.scrub.json"
        out_md = staged_out / f"{f.stem}.md"
        out_json.write_text(json.dumps(
            {"path": r.path, "verdicts": r.verdicts, "redactions": r.redactions,
             "alias": r.alias}, ensure_ascii=False, indent=2), encoding="utf-8")
        out_md.write_text(r.redacted_text, encoding="utf-8")
        results.append(r)
    return results
