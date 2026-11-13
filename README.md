# DeskRelate

Your local files → one private knowledge graph file. Windows-first, fully local.

A privacy-scrubbed personal memory: DeskRelate scans the documents already on
your machine (Documents, Downloads, Desktop, Outlook `.eml` exports, markdown
notes), redacts or refuses anything sensitive **before** it's ever stored, and
builds a single embeddable graph database file (`personal.rl`) you can query,
search semantically, and copy anywhere.

**The pitch in one line:** a second brain as a file — one process, no server,
no cloud, and a refusal log you can read.

## How it works (for investors/judges: 30 seconds)

1. **Collect** — a deterministic script stages copies from folders you allowlisted. Never touches deny-listed extensions (`.env`, `.pem`, key files) or secret-named files.
2. **Scrub** — regex pass removes phones, bank/IBAN shapes, API keys; classes you flagged `reject` refuse the whole document (it lands in a visible refusal log).
3. **Local LLM QA** — an optional second pass with a small model (Qwen 3 4B via Ollama) catches semantic PII the regex missed. Runs on your laptop, never online.
4. **Graph** — documents, contacts, and mentions become nodes and edges (plus vector embeddings for semantic search) in one Relate `.rl` file.
5. **Delta** — re-run later; new / altered / touched / deleted files are detected by content hash, never by trust-you-later.

## Requirements (slim Windows machine, no GPU)

| | |
|---|---|
| OS | Windows 10/11 |
| Python | 3.12+ |
| Model runtime | [Ollama](https://ollama.com) |
| Models | `qwen3:4b` (~3 GB), `nomic-embed-text` (~274 MB) |
| RAM ceiling | ~6 GB free is plenty — this build targets **16 GB laptops with iGPUs, no discrete GPU** |

## Install

```powershell
cd desk-relate
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install https://github.com/relatedb/relate/releases/download/v1.0.1/relate_db-1.0.1-cp39-abi3-win_amd64.whl
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

(`markitdown` adds Word/Excel/PDF/PowerPoint/Outlook readers; `blake3` hashes fast on CPU; `watchdog` watches folders.)

## Setup

Edit `knobs.json` — knob names are the future UI labels:

- `folders` — which folders it may read (deny others by default)
- `never_folders` — folder names it must not enter
- `file_types` / `file_types_never` — allowed vs refused file types
- `max_folder_depth` — how deep to walk
- `cloud_files` — `skip` (index cloud-only OneDrive placeholders as
  metadata, never download) or `download`
- `privacy_rules` — per sensitive class: `keep` / `hide` (alias-replace,
  reversible locally) / `block` (refuse the whole document)

## Demo run (no real data needed)

The repo ships `make_test_folders.py` (fixture generator) + `knobs.testtree.json`:

```powershell
.venv\Scripts\python make_test_folders.py                     # plant 140 demo files
.venv\Scripts\python main.py scan --knobs knobs.testtree.json # crawl fixtures
.venv\Scripts\python main.py delta --knobs knobs.testtree.json  # re-run: catches diffs
.venv\Scripts\python main.py report --knobs knobs.testtree.json # refusals + delta log
```

`make_test_folders.py` plants a fake windows-like tree (`my_documents/`,
`c_user/Desktop`, `one_drive_sync-root/` incl. a nested folder and a weirdly
named USB-thumb folder) with ~20 files per folder: MD, TXT, HTML, CSV, JSON,
EML, plus binary PDF/DOCX/XLSX/PPTX fixtures and deliberately dangerous traps
(`.env`, `.pem`, credentials files) that the collector must refuse. Delete
`test_folders/`, `spool/`, `out/` to fully reset.

## Real run

```powershell
.venv\Scripts\python main.py scan     # first ingest of your real folders
.venv\Scripts\python main.py delta    # re-run days later — catches diffs
```

Everything stays under `spool/` (staging) and `out/` (the graph + build
log). Delete `out/personal.rl` and nothing of your life remains in this folder.

## What's next on the roadmap

System-DocX/Excel/PDF binary parsing is wired into the plan (MarkItDown leg), not yet active;
localhost UI, jailbreak self-probe (attack its own config and report), and
OneDrive / Gmail connectors are on the roadmap — see `techREADME.md`.
