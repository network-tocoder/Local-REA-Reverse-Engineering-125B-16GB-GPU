# What tools the agent actually used

Extracted from the recorded session (`rec/rea_full.cast`, 11,988 frames) by
parsing every `writing a tool call:` line. These are real counts from the run —
not a hand-picked selection.

## REA tools — 20 calls, ~47K tokens of tool output

| Tool | Calls | Output tokens | Seconds |
|---|---|---|---|
| `rea_batch_decompile` | 7 | 20,782 | 363 |
| `rea_read_bytes` | 6 | 17,784 | 278 |
| `rea_procedure_pseudo_code` | 4 | 8,414 | 131 |
| `rea_list_procedures` | 2 | 117 | 8 |
| `rea_open_binary` | 1 | 94 | 2 |
| **total** | **20** | **47,191** | **782** |

**Five distinct REA tools did the whole job.**

That's the justification for the tool filter, straight from the run. 170 tools
were on offer; five ever fired. And the shape of those five is exactly the
minimal set from the video: open → list → decompile → read pseudocode → read
bytes.

### What each one is for

| Tool | Role |
|---|---|
| `rea_open_binary` | Load the ELF into Ghidra. **Called once** — one binary, one open. |
| `rea_list_procedures` | Enumerate functions. 2 calls is enough to get bearings. |
| `rea_batch_decompile` | The workhorse. Decompile many functions in one call instead of 30 individual ones. |
| `rea_procedure_pseudo_code` | Re-read one function when the batch output was ambiguous. |
| `rea_read_bytes` | Where the secrets live — raw data sections, gaps between strings. Found the cheat code here. |

Note the token split: `rea_read_bytes` is only 6 calls but **37% of all REA
output tokens**, and it produced the Level 3 cheat code. Cheap to call,
enormously high value.

## The agent also used its own tools

REA wasn't the whole story. OpenCode's built-in tools did most of the work by
call count:

| Tool | Calls | Output tokens | Seconds |
|---|---|---|---|
| `exec_command` | 1,503 | 2,255,910 | 39,558 |
| `bash` | 202 | 217,248 | 3,742 |
| `write` | 179 | 875,568 | 11,973 |
| `write_stdin` | 60 | 124,652 | 2,817 |
| `edit` | 110 | 65,093 | 1,762 |
| `read` | 7 | 3,938 | 155 |
| `apply_patch` | 5 | 1,018 | 58 |
| `todowrite` | 3 | 844 | 24 |
| `skill` | 4 | 294 | 62 |
| **total** | **2,073** | **3,544,565** | **60,151** |

Two things worth internalising from this:

1. **REA is a specialist, not the whole toolkit.** 20 REA calls against 2,073
   native ones. Ghidra tells the agent what the binary *is*; the shell is what
   it uses to write the rebuild, run both versions, and diff them.

2. **`exec_command` at 1,503 calls is the real driver.** The verification loop
   — run the original, run the rebuild, compare — is the bulk of the work, and
   it needs a shell, not an MCP tool. This is why the byte-identical results
   are believable: the agent wasn't guessing, it was *testing*, thousands of
   times.

## Reproducing this analysis

```bash
python3 scripts/tool-usage.py rec/rea_full.cast
```

Add the session recording to `rec/` and rerun it against any run.

---

> **Note on prompts:** the exact prompt text typed into the agent is not in
> the files that backed this repo. What *is* here is what the agent actually
> did, call by call. Task prompts for all four levels are described in
> [`answer-key.md`](answer-key.md).