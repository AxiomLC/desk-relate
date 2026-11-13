# HANDOVER — DeskRelate state & next-up

> Drop this file into any new thread to resume. Last updated after v0
> build + smoke test + **repo created**.
> Repo: https://github.com/AxiomLC/desk-relate (public, branch `master`).
> Local: `C:\Users\Admin\Zed\desk-relate`.

## What this is

`desk-relate` = the Windows-personal slice of the Relate hackathon (see
`alt_hackathon_idea.md` for the full spec and strategy). It ingests local docs
into a scrubbed, single-file personal graph (Relate `.rl`). Sibling project:
`C:\Users\Admin\Zed\Relate` (the SEC-graph hackathon build; public/private repo
split — do not confuse the two).

## Current state: v0 WORKING — now with fixture tree + delta verified

- Pipeline chain runs: `collector → scrubber → grapher`.
- 18/18 Cypher statements applied into a real `out/personal.rl` via the relate
  **1.0.1** wheel (installed from GitHub releases into `.venv`).
- Refusal log catches: denied ext, secret-like names, reject-class PII.
- Phone + IBAN redaction to aliases works (`PHONE-1`, `BANK-1`).
- **Delta fully verified** on the fixture tree: no-change → clean empty report;
  edited file → `altered`; added file → `new`; deleted file → `gone`; renamed
  file → old path in `gone` + new path in `new` (resolution/purge = UI phase).
- **Fixture generator** `make_test_folders.py`: plants 7 folders × 20 files
  (md/txt/html/csv/json/eml/pdf/docx/xlsx/pptx) across simulated
  my_documents/c_user/OneDrive-sync-tree + refusal traps. Regenerate anytime;
  `_tiny_pdf/_tiny_docx/_tiny_xlsx/_tiny_pptx` hand-roll minimal valid binaries
  so no Office/LibreOffice dependency is needed for fixtures.
- **Cloud-only placeholder detection** (OneDrive On-Demand): Windows file
  attributes OFFLINE/RECALL_ON_DATA_ACCESS bits → files indexed as
  metadata to `spool/cloud_only.jsonl` and skipped from content staging when
  `cloud_files: skip` (hydrate decision = later UI phase). Verified plumbing
  on normal files (returns False; needs real OneDrive placeholder to test the
  positive case).
- **Knobs v2** — plain-terms schema (`folders/never_folders/file_types/
  privacy_rules` with keep/hide/block) = the future UI labels; legacy names
  still parse via aliases.
- CLI: `scan | delta | query | report`, `--knobs` override.

Verified environment: Python 3.13, venv in `.venv` with
`markitdown[pdf,docx,xlsx,pptx,outlook] blake3 httpx` + relate wheel.
**Ollama is NOT installed yet** (LLM QA and embeddings are no-ops that skip
silently; graph stats show `vectors: 0`).

## Run commands (smoke test)

```powershell
cd C:\Users\Admin\Zed\desk-relate
.venv\Scripts\python make_test_folders.py
.venv\Scripts\python main.py scan --knobs knobs.testtree.json
.venv\Scripts\python main.py delta --knobs knobs.testtree.json
.venv\Scripts\python main.py report --knobs knobs.testtree.json
```

For the real run use `knobs.json` (Documents/Downloads/Desktop).

## Key reference docs in this folder

- `NOTES-local-llm-models.md` — preserved hardware research on candidate local
  models (Ling-3.0-Tiny MoE, Qwen3.5-4B/9B, Nanbeige, MiniCPM) + the bake-off
  harness for picking `llm.qa_model`. Read before changing the model knob.

## Next-up: three tracks (Track A + B need NO LLM)

### Track A — collector + scrubber expansion & testing (runs today)

The collector and scrubber are the product's trust core and are far from done.
Any thread can pick these up and test without Ollama:

1. **Pattern expansion** — scrubber currently has 9 classes. Add + test:
   street addresses, passport/driver-license formats, IBAN with checksum
   validation, more API-key shapes (Azure, Google, JWT `eyJ…`), date-of-birth.
   Each new pattern needs a **fixture pair** (should-redact doc + should-keep
   doc) planted into `make_test_folders.py`.
2. **Knob testing matrix** — knobs.json is the product surface; test each:
   - every verdict (`keep/hide/block`) on every class
   - `max_folder_depth` boundary (deep-tree fixture)
   - `cloud_files: skip vs download` behavior
   - `never_folders` mid-path denial (fixture branch named `node_modules`)
   - malformed knobs (missing keys, wrong types) → must fail loud, not silent
3. **Collector hardening** — long paths (>260 chars), unicode filenames,
   locked files (open in Word), zero-byte files, huge-file cap (skip >100 MB?),
   duplicate paths in `folders` (same dir listed twice), file renamed mid-scan.
4. **Delta edge cases** — same-hash different path (copy), dir renamed
   wholesale, file replaced while offline, ledger corruption (bad line).
5. **Escape re-tests** — `..\..\` traversal in knobs entries, symlinked dirs
   inside an allowed folder (must not escape it).

### Track B — connectors (no LLM required)

1. **parser.py** — MarkItDown leg: binary fixtures (pdf/docx/xlsx/pptx in
   `spool/incoming/` already) → MD sidecars → straight into scrubber. Highest
   value single module; enables ALL binary types in tests.
2. **IMAP connector** (Hostinger + any provider) — stdlib `imaplib`; design:
   metadata-first (fetch headers → consent per sender → bodies), creds via a
   local file the user fills in, never committed. Mail is the richest source:
   one email = person/thread/attachment nodes.
3. **OneDrive non-synced leg** — Graph API delta (proven pattern in
   optic-nerve-ui); needed only for files visible in Drive but not synced to
   disk. Synced-folder path already works (add `%USERPROFILE%\OneDrive` to
   `folders`).
4. **GDrive** — `google-api-python-client` InstalledAppFlow OAuth; needs a
   Google Cloud project (user's account, not committable).

### Track C — LLM tier (blocked on Ollama install, lower priority)

1. Install Ollama (user-run command, needs approval) + pull `qwen3:4b` and
   `nomic-embed-text` — this machine or the second one.
2. Verify `qa_text()` catches a semantic miss (person name in prose).
3. Embeddings on → `vectors: N` → hybrid query demo.
4. Model bake-off per `NOTES-local-llm-models.md` (Ling-3.0-Tiny vs qwen3:4b
   on JSON validity + miss rate).

### Later

- UI (FastAPI localhost, spec §5) — better after Track A stabilizes knobs.
- jailbreak_check.py (spec §6) — before first real-user ingest.
- Delta purge/rename UI flow, vault tier, tree graph view.

## Gotchas (learn the hard way)

- **Stale `app/__pycache__` breaks imports after edits** → delete it when
  weird `AttributeError`/`'list' object` errors appear.
- Relate is **single-process**: never two writers on `out/personal.rl`;
  any extra opens (Python REPL, CLI) must be read-only.
- Relate PyPI publish hasn't landed: install wheel from GitHub releases URL
  (see README install block), version 1.0.1 = current as of this handover.
- Ollama absent → everything LLM returns None silently (by design); don't
  misread `vectors: 0` as a bug.
- scrubber: patterns with capture groups must never be `pat.sub`-ed raw
  (already guarded — keep the guard when adding patterns).
- `spool/` contains **copies** of user files incl. unredacted originals in
  `spool/incoming/` — never commit, never include in a public artifact; it
  lives under `.gitignore` already. Consider clearer warning in UI phase.

## Open questions for the user

- ~~Which GitHub repo name~~ — settled: public `AxiomLC/desk-relate`.
- Ollama install approval (global install — needs user-run command).
- Whether hackathon submission should feature both builds (Relate + this)
  or lead with this one — affects which gets tuning time first.
