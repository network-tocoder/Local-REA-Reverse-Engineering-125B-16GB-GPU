# The two failures (and why they matter more than the wins)

This is the part of the video I'd keep if I had to cut everything else, and
it's the part most people skip. Both failures were **memory failures, not
model failures**. The model never got dumber — the harness ran out of room.

---

## Failure 1 — 170 tools, 150K tokens of descriptions, 64K of context

REA exposes ~170 MCP tools. An agent must read a tool's description before it
can call it, so every tool is permanently resident in the prompt.

```
170 tool descriptions   ≈ 150,000 tokens
model context window      64,000 tokens   ← it does not fit
```

OpenCode then does what any agent does when context fills: **compact**. It
summarises the conversation to make room. The summary is shorter, work
continues, context fills again, it compacts again. A loop, with the run never
actually progressing.

```
open binary → 170 schemas → overflow → compact → overflow → compact → ...
```

### Fix 1 — cut the tool list to what the job needs

Native-binary reconstruction needs a small, boring set of tools:

| Need | Purpose |
|---|---|
| open binary | load the ELF into Ghidra |
| list procedures | enumerate functions |
| search procedures | find them by name/pattern |
| decompile | batch + single-function pseudocode |
| read bytes | inspect raw data sections |
| read strings | pull `.rodata` / error messages |
| cross-references | find callers/callees |
| verify rebuild | compare rebuilt behaviour against the original |

Everything else — ADB, Android, Electron, JavaScript, Swift, EVM, evidence
bundles, managed/Apple/PE/Keynote paths — is real capability that this job
simply never touches. Disabling **151 of 170** tools took the prompt from
~150K tokens to something that fits.

The agent did not miss them. Level 3 found a hidden cheat code without any of
the disabled tools.

See [`../config/opencode.json`](../config/opencode.json) and
[`rea-tool-filter.py`](../scripts/rea-tool-filter.py).

---

## Failure 2 — compaction threw away the work it had just done

With fewer tools the agent got much further. It opened the binary,
decompiled, read the bytes. Then it thought for **3m29s** — and that thinking
filled the 64K context on its own. It compacted. The summary dropped the
decompiled output it had already gathered. It started the binary again, hit
the same wall, compacted again.

```
open → decompile → 3m29s of thinking → overflow → summary loses the
decompile → start over → ... (forever)
```

This is the nasty one: the agent had *already solved the problem* and lost it
to a summariser.

### Fix 2 — more context, and a cap on thinking

| Setting | Before | After |
|---|---|---|
| Context window | 64K | **128K** |
| Reasoning budget | uncapped | **8,000 tokens/turn** |

That is the whole fix. With room to hold both the work *and* the thinking,
the run completed: Level 1 finished in 5m41s using 67.5K (52%) of context.

Strata still fit it — 128K cost about sixty fewer hot experts on the GPU
(4,595 → 4,534, 8.76 → 8.65 GiB). A rounding error against a total failure.

---

## What this actually teaches

> **Local AI doesn't fail because the model is dumb. It fails because the
> memory budget is wrong.**

Both failures were invisible in advance and obvious afterwards. Neither would
have been caught by a smaller model, and neither would have been fixed by a
faster GPU. Context budget and tool surface are the two dials that decide
whether a local agent finishes or loops.

If you take one thing from this repo: check what your tool list costs in
tokens before you blame the model.