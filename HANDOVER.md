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

## Next-up list (ordered)

1. **parser.py** — MarkItDown leg for binaries (PDF/DOCX/XLSX/PPTX/MSG) → MD
   sidecars, then auto-feed scrubber. Fixtures already prove the binaries
   stage (16 pdf + 16 docx + 8 xlsx + 8 pptx in spool) — they just don't
   produce text sidecars yet (only 12 text files of 144 make the graph).
   Files: new `app/parser.py`, hook into `main.py scan`.
2. **Install Ollama** on this box + `ollama pull qwen3:4b nomic-embed-text`
   (agent does not run global installs — hand user the command; user then
   approves). After install, verify `qa_text()` catches a semantic MISS in
   testdata (person name in a sentence) and embeddings fill `vectors: N`.
3. **Vector search demo** — one hybrid query: vector top-K + traversal, one
   Cypher statement, quoted in handover when done.
4. **UI** — FastAPI on 127.0.0.1:8388; tabs per spec §5 (Dashboard/Spool/
   Refusals/Redactions/Memory/Delta/Knobs). Use force-graph-3d later.
5. **jailbreak_check.py** — spec §6; runs BEFORE first real ingest of
   real user data; must print a 5-item report card.
6. **Delta purge/rename flow** — recycle-bin check, `gone` → prompt-gated
   purge (v0 only reports `gone`).
7. ~~git init + first commit~~ — **DONE**: public repo `AxiomLC/desk-relate`
   created via gh, committed and pushed (see README for clone/install).
8. Then: OneDrive synced-folder scan config, GDrive connector, Gmail/IMAP
   (optional), vault tier.

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
