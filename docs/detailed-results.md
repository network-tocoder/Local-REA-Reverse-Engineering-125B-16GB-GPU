# REA local test results
## Level 1 calc (not stripped) — PASS
- Run 1 (64K ctx, no thinking budget): FAILED by compaction loop (150K tool schemas -> filtered 170->19 tools; then 63K context, 3m29s thinking, compaction lost work)
- Run 2 (128K ctx, thinking budget 8000): PASS. Build 5m 41s (final turn), context 67.5K (52%), $0.00
- 10/10 side-by-side identical + edge sweep byte-identical (-0.00001->0, (-1)^0.5->-nan, 2^10000->inf, 0x1p4, tabs, empty lines, --5, 100%7.5, q, 300-char line split)
- Approach: decompiled skip/primary/power/term/expr/main, read .rodata strings, probed original, rebuilt in Python calling same glibc strtod/pow/fmod/snprintf via ctypes for bit-identical floats
- Thinking: 1m54s probe plan, 1m35s confirm
- Independent check (outside AI): diff ./calc vs calc.py on 8 inputs -> IDENTICAL

## Level 2 notes (stripped, scrambled db) — PASS
- Build 8m 39s (final turn), context 81.4K (62% of 128K), $0.00
- Decoded format exactly: "NTv2" | count u8 | per note: ts u32le | len u8 (<=120) | text ^ ((0x5A + note_i + 7*char_j) & 0xFF) | checksum u8 = sum(plain)&0xFF
- Found: [damaged] on checksum mismatch, max 20 notes, ERR: not a notes file / cannot save / no such note, list format %2d. [%Y-%m-%d], case-insensitive find, del via number parse
- Verification: byte-exact round trip of original notes.db; diff-identical outputs on many scripts (20-note full, 150-byte truncation, corrupted checksum, garbage file, missing file); interop both ways; original notes.db sha256 unchanged
- Score vs answer key: 10/10
- Independent check: notes.py lists the 3 original notes from original notes.db

## Level 3 brick (stripped ncurses game, hidden cheat) — PASS
- Build 10m 14s (final turn), context 106.7K (81% of 128K), $0.00
- Recording: clips/57_L3_screenrec_677.mkv (10 min). L2 recording: clips/56_L2_screenrec_676.mkv (4 min)
- Found cheat: decoded bytes 5f 5c 50 52 5f XOR 0x33 -> "local" (title screen) -> CHEAT ON, lives 3->9, paddle 7->13
- Found GCC %5 magic constant 0xCCCCCCCD -> speed-up every 5th brick, -8ms while delay>34
- All mechanics: 42x23 field, controls a/d/arrows drain buffered keys, paddle row 21 width 7, ball (20,20) v(+-1,+-1), 3x10 bricks 30/20/10, edge dx=+-2, 3 lives 600ms pause, YOU WIN, hiscore.txt, prints final score after endwin
- Extra hidden findings: "BYE" ending when q in play; edge-hit power shots
- Verification: pty-driven A/B runs -> byte-identical ball traces, scores, end screens, hiscore.txt
- Score vs answer key: 10/10

## Level 4 kilo (real project, antirez/kilo, stripped) — PARTIAL (stopped by us)
- kilo.py ~719 lines written; help line + usage string exact; built own pty harness (harness.py) diffing screens vs original
- After ~85 min still failing only CURSOR DIFF cases (final cursor pos (23,0) vs rebuilt), some find TEXT DIFF; context 82K
- Decision: stopped; score by manual check
- Manual check of kilo.py: ~ rows, inverted status bar "test.c - N lines" + row/total, exact HELP line, C colours (int green/return yellow/0 red), typing + Enter, "(modified)", Ctrl-Q quit-warning flow worked
- Not tested: Ctrl-S message, Ctrl-F search (terminal intercepted Ctrl-F), multi-line comments
- Final: 8/10 confirmed (stopped early, cursor-position polish only)
