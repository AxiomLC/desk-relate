# LLM model research — local hardware bake-off candidates

> Source: a hardware-specific research pass pasted into chat 2026-11-13 (agent
> session) for the local box: **Lenovo IdeaPad 3 15IAU7 — i5-1235U (2P/8E,
> 12 threads), 16GB DDR4-3200, Iris Xe iGPU, no discrete GPU.** Windows 11 eats
> ~4–5 GB, so the safe ceiling for model weights + KV cache is **~6–8 GB**.
> MoE models and 3B–4B dense models beat 8B–9B dense on this box's memory
> bandwidth.
>
> **Status caveat:** these are recommendations from the research; NOT yet all
> verified as pullable Ollama tags. Before flipping `llm.qa_model`, run the
> bake-off in §2.

---

## 1. The rankings (preserved verbatim in substance)

### 1. Speed & MoE champion: **Ling-3.0-Tiny** (Ant Group / InclusionAI)
- ~8B total params (MoE), **1.3B active per token**.
- Best quant for this box: `Q4_K_M` (~4.5GB) or `Q5_K_M` (~5.3GB).
- Why it wins: MoE activation makes it fly on laptop CPUs/iGPUs (~25–32 tok/s
  in community laptop benchmarks) while keeping 8B-class knowledge. Engineered
  for structured tool-calling / function execution / long-context extraction
  (62.7 on BFCL v4).

### 2. Balanced workhorse: **Qwen3.5-4B** (Alibaba)
- 4.7B dense hybrid, **262K native context**.
- Best quant: `Q4_K_M` (~2.5–3.0GB) or `Q6_K` (~3.8GB).
- Why it wins: hybrid attention/KV design keeps RAM low on multi-page docs.
  2026 CPU benchmarks for structured JSON extraction: best balance of valid
  schema adherence, low footprint (~4–5GB RSS at 8–32K ctx), ~12–13 tok/s.

### 3. High-accuracy / overnight batch: **Qwen3.5-9B** (Alibaba)
- 9.7B dense hybrid. Best quant: `Q4_K_M` (~5.2–5.8GB).
- Tradeoff: better for complex node/edge schemas (nested relationships,
  strict disambiguation), but **~6–8 tok/s** on this CPU. Keep chunks tight
  (2K–4K tokens) to avoid swap.

### 4. Honorable mentions (ultra-lean / niche)
- **Nanbeige4.2-3B** (`Q8_0`, ~3.4GB): r/LocalLLaMA favorite for clean data
  parsing. Prefers node/edge schema passed as a **function/tool definition**
  instead of `response_format` JSON mode.
- **MiniCPM5-2B** (`Q6_K`/`Q8_0`, ~2.2GB): OpenBMB edge tool-use/structured
  parsing, 128K context — for ultra-fast background processing while
  multitasking.

## 2. Bake-off harness (what to measure when trying a candidate)

Current default in `knobs.json` is `qwen3:4b` (chosen for registry
verifiability, not because it outranks the above — see techREADME §6 note).

When testing a new model on this box, measure on the same `testdata/` set:

1. **JSON validity rate** — `%` of `qa_text()` responses that parse against
   the strict schema (bake-off metric #1; the QA pass is JSON-grade).
2. **Miss rate** — seeded-PII test docs: which model catches the semantic
   misses (person names in prose, addresses) the regex pass only catches
   partially.
3. **tok/s and wall-time per 2.5k-token chunk** (the real batch metric).
4. **RSS during run** — must not push the box into swap.

```powershell
# availability probe — run these first (specific tag names may differ)
ollama pull ling-3.0-tiny        # or: inclusionai/ling-3.0-tiny, ling-tiny
ollama pull qwen3.5:4b           # or: qwen3.5-4b
ollama pull qwen3.5:9b
```

If a tag fails, check `ollama.com/library` and `r/LocalLLaMA` for the right
name; candidates may also need LM Studio / llama.cpp direct GGUF rather than
Ollama — in that case point `llm.base_url` at whatever OpenAI-compatible
endpoint the runtime serves.

## 3. Decision rule

- Default stays `qwen3:4b` until a candidate beats it on JSON validity **and**
  miss-rate on the seeded set — then flip `llm.qa_model` in `knobs.json` (one
  string, no code change).
- Batch overnight runs (delta re-scan of whole Documents) may justify
  `qwen3.5:9b` regardless, since wall-time tolerance is higher.
