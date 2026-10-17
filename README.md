# Reverse Engineering Anything: 125B Rebuilds 4 Apps on a 16GB GPU

![GPU](https://img.shields.io/badge/Tested%20on-RTX%205060%20Ti%2016GB-76b900?style=for-the-badge&logo=nvidia&logoColor=white)
![Model](https://img.shields.io/badge/Model-Qwen3.8--Flash--Next%20125B%20MoE-06b6d4?style=for-the-badge)
![Engine](https://img.shields.io/badge/Engine-Strata-f59e0b?style=for-the-badge)
![Cost](https://img.shields.io/badge/Cost-Free-brightgreen?style=for-the-badge)
![Cloud](https://img.shields.io/badge/Cloud-Not%20Required-red?style=for-the-badge)
![API](https://img.shields.io/badge/API-OpenAI%20Compatible-black?style=for-the-badge)

▶️ **Watch the video:** https://www.youtube.com/watch?v=VwUz8rx8kJo

A 125B mixture-of-experts model running on a **16GB consumer GPU**, driving an
agent through **REA** + **Ghidra** to rebuild four compiled binaries from
scratch. No source code was available. Three of the four were stripped. On one
of them the agent found a hidden cheat code that wasn't on my answer key.

```
source code  --[deleted]-->  binary --[strip]-->  REA + Ghidra + agent  -->  working rebuild
```

The rebuilds run **natively** — no DOSBox, no emulator, no wrapper. The
interesting part wasn't reversing anything, it was the two ways the agent
failed before it worked. Both are written up in
[`docs/failures.md`](docs/failures.md).

## Hardware

| Part | Spec |
|---|---|
| GPU | RTX 5060 Ti 16GB |
| System RAM | 64 GB |
| CPU | multi-core; **24 pool workers** tuned optimal |
| OS | Ubuntu 24.04, CUDA 13 |

> ⚠️ **RAM is the real requirement, not VRAM.** ~47 GB of experts live in system
> RAM; only ~8.6 GB of hot experts get cached on the GPU. Viewers have since
> confirmed 32 GB system RAM + 24 GB VRAM also runs fine, so 64 GB is what
> *this* box needed, not a hard floor.

## Speed

| Test | Result |
|---|---|
| Chat decode | **69.7 tok/s** (65.5–90.5) |
| Chat first token | 0.50 s |
| Prefill 4K | 1,125 tok/s (3.60 s to first token) |
| Prefill 16K | 1,634 tok/s (9.87 s to first token) |
| Agent decode | **74.2 tok/s** (42.6–105.0) |
| Agent cache hit rate | 68.78% |
| Auto-tune best | **77.7 tok/s** |
| Context | 128K, 16,384 output, KV int8 |

Auto-tune is the cheapest win here — it restarts the engine repeatedly,
measuring every setting:

| CPU pool workers | Throughput |
|---|---|
| 47 | 39.0 tok/s |
| 31 | 57.8 tok/s |
| **24** | **73.5 tok/s** |
| final tuned config | **77.7 tok/s** |

More threads made it *slower* — they were fighting over memory.

## Results

| Level | Target | Stripped | Tests | Build | Context |
|---|---|---|---|---|---|
| 1 | CLI calculator | no | **10/10** ✅ | 5m 41s | 67.5K (52%) |
| 2 | Notes app, scrambled DB | yes | **10/10** ✅ | 8m 39s | 81.4K (62%) |
| 3 | ncurses game, hidden cheat | yes | **10/10** ✅ | 10m 14s | 106.7K (81%) |
| 4 | `kilo` real text editor | yes | **8/10** ⚠️ | ~85 min | 82K |

**Total cloud spend: $0.00.**

Level 4 was stopped by choice — only cursor-position polish was still failing,
and it wasn't worth another hour.

Every secret the agent recovered from each binary — the scrambled file format,
the cheat code, the compiler's divide-by-five constant — is written up in
[`docs/answer-key.md`](docs/answer-key.md), so you can check any claim yourself.
Raw metrics: [`results.csv`](results.csv).

## The part that actually matters

Two runs failed completely before anything worked. Both were **memory**
failures, not model failures:

1. **170 tools ≈ 150K tokens of descriptions vs a 64K context.** It did not
   fit. The agent compacted forever and never progressed.
2. **Compaction destroyed the work it had just done.** After the tool fix it
   decompiled the binary, thought for 3m29s, overflowed — and the summary
   threw away the decompiled output. Forever.

The fixes were boring and cheap:

| | Before | After |
|---|---|---|
| Tools enabled | 170 | **19** (151 disabled) |
| Context | 64K | **128K** |
| Reasoning budget | uncapped | **8,000 tokens/turn** |

128K cost ~60 hot experts (8.76 → 8.65 GiB). A rounding error against a total
failure.

> **Local AI doesn't fail because the model is dumb. It fails because the
> memory budget is wrong.**

## The tool filter

This was the most requested thing after the video, so it's all here.

REA exposes ~170 MCP tools, and every tool description is permanently resident
in the agent's prompt. [`config/opencode.json`](config/opencode.json) is the
verified working config: **151 tools disabled, 19 enabled.** It holds both
halves in one file — the local model endpoint *and* the REA MCP server.

```jsonc
"tools": {
  "rea_open_binary": true,             // the 19 kept tools are simply
  "rea_list_procedures": true,         // absent from this block
  ...
  "rea_capture_adb_screen": false,     // 151 explicitly disabled
  "rea_inspect_evm_interface": false,
}
```

Nothing was missed. To rebuild or curate it:

```bash
./scripts/rea-tool-filter.py --list                    # what's available
./scripts/rea-tool-filter.py --derive --apply          # reproduce this config
./scripts/rea-tool-filter.py --apply --keep-list mine.txt   # curate by hand
```

### Proof it didn't cost anything

Parsed out of the session recording — real counts, not estimates:

| REA tool | Calls | Output tokens |
|---|---|---|
| `rea_batch_decompile` | 7 | 20,782 |
| `rea_read_bytes` | 6 | 17,784 |
| `rea_procedure_pseudo_code` | 4 | 8,414 |
| `rea_list_procedures` | 2 | 117 |
| `rea_open_binary` | 1 | 94 |
| **total** | **20** | **47,191** |

**Five of the 170 tools ever fired.** The other 165 sat in the prompt
consuming context the whole run.

`rea_read_bytes` is the one worth noting: 6 calls, but **37% of all REA output
tokens** — and it produced the Level 3 cheat code. It reads raw data sections,
including the gaps between normal strings, which is exactly where the five
secret bytes were hiding.

For scale, the agent made **2,073 calls to its own shell tools** in the same
run. REA told it what the binary *was*; the shell is what it used to write the
rebuild, run both versions, and diff them. The byte-identical results are
believable because the agent wasn't guessing — it was testing, thousands of
times.

## Setup

```bash
git clone <this-repo> && cd <this-repo>
./scripts/setup.sh
```

Or step by step:

1. **Strata** — inference engine + model
   ```bash
   git clone https://github.com/Niko1221/Strata.git
   cd Strata && ./setup.sh --port 8082
   ```
   Menu: Qwen3.8-Flash-Next → IQ3_S → 64K → KV int8. Let it auto-tune once.
2. **OpenCode** — the agent
   ```bash
   npm install -g opencode-ai
   ```
3. **REA** — reverse-engineering tools + Ghidra
   ```bash
   npx -y rea-agents@6.4.0 setup     # detects OpenCode, points at Ghidra
   npx -y rea-agents@6.4.0 doctor    # expect healthy: true
   ```
   Verified against Ghidra 12.1.4 on Java 21.
4. **Cut the tool list — don't skip this**
   ```bash
   python3 scripts/rea-tool-filter.py --derive --apply
   ```
5. **Point the agent at the local endpoint and give it a stripped binary**

The tuned engine flags from this run are in
[`config/strata-iq3_s.json`](config/strata-iq3_s.json), and the full benchmark
output is in [`docs/strata-benchmark.txt`](docs/strata-benchmark.txt).

## Legal

Use this only on software you own, or software you have clear permission to
inspect. Many licences forbid reverse engineering and the law differs by
country. Note that re-implementing an app you own is a different activity
from defeating a licence check — the latter is cracking regardless of whether
you paid.

Sensible uses: your own lost code, unmaintained internal tools, authorised
security research, and learning.

## Files

| File | What's in it |
|---|---|
| [`config/opencode.json`](config/opencode.json) | The 151→19 tool filter + local endpoint + REA MCP server |
| [`config/strata-iq3_s.json`](config/strata-iq3_s.json) | Tuned engine flags from this run |
| [`scripts/rea-tool-filter.py`](scripts/rea-tool-filter.py) | Rebuilds/curates the tool allowlist |
| [`scripts/setup.sh`](scripts/setup.sh) | Full headless setup, all 9 steps |
| [`docs/failures.md`](docs/failures.md) | The two failures, and the fixes |
| [`docs/answer-key.md`](docs/answer-key.md) | Every secret hidden in the four binaries |
| [`docs/strata-benchmark.txt`](docs/strata-benchmark.txt) | Raw benchmark output |
| [`results.csv`](results.csv) | 48 metrics |
