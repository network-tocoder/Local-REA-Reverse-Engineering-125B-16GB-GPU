# Answer key — what each level required

I wrote all four test apps, compiled them, deleted the source, and stripped
the symbols. The agent got **only the binary**. This is what was actually
buried in each one, so you can check any claim in the video yourself.

Everything here was found by the local agent, not given to it.

---

## Level 1 — `calc` (210 lines rebuilt, **10/10**)

Command-line recursive-descent calculator. Not stripped, so this was the
warm-up.

**Functions:** `expr`, `term`, `power`, `primary`, `main` — a textbook
parser layout.

**The clever part.** Decimal maths drifts subtly between languages, so a
naive Python port would *almost* match and still fail byte comparison. The
rebuild doesn't reimplement the maths — it calls the **same glibc functions**
the original uses (`strtod`, `pow`, `fmod`, `snprintf`) via `ctypes`. Results
come out bit-for-bit identical because they are literally the same C code.

**Edge cases all byte-identical:**

| Input | Output |
|---|---|
| `-0.00001` | `0` |
| `(-1)^0.5` | `-nan` |
| `2^10000` | `inf` |
| `0x1p4` | hex float |
| tabs / empty lines | ignored |
| `--5` | double-unary minus |
| `100%7.5` | percent-as-modulo |
| `q` | quit |
| 300-char line | split |

Build: **5m41s**, context 67.5K (52%).

---

## Level 2 — `notes` (238 lines rebuilt, **10/10**)

Stripped, and the save file is scrambled. Three real notes hidden inside.

### The file format

```
"NTv2"                      4 bytes magic
count                       u8   (number of notes)
per note:
  ts                        u32 little-endian
  len                       u8   (<= 120)
  text                      len bytes, XOR-scrambled
  checksum                  u8   = sum(plaintext) & 0xFF
```

### The scramble

Each plaintext byte is XOR'd with a key that varies by **note index** and
**character position**:

```
key_j = (0x5A + note_index + 7 * char_index) & 0xFF
```

Note the position term — it's a 7-character stride keyed off the note number,
not a fixed XOR. A single static key would have produced the same result for
every note; this one doesn't, which is what makes it look like real
corruption.

### Everything else it recovered

- `[damaged]` marker when the checksum doesn't match
- Hard limit of **20 notes**
- `ERR: not a notes file`, `ERR: cannot save`, `ERR: no such note`
- List format `%2d. [%Y-%m-%d]`
- Search is **case-insensitive**
- `del` parses a note number first

### How it was verified

Byte-exact round trip of the original `notes.db`; diff-identical output across
20-note-full, 150-byte-truncation, corrupted-checksum, garbage-file and
missing-file cases; files written by either app opened by the other, both
directions. **The original `notes.db` sha256 never changed.**

Build: **8m39s**, context 81.4K (62%).

---

## Level 3 — `brick` (224 lines rebuilt, **10/10** + a secret)

Stripped ncurses brick-breaker. The whole game lives in one big `main`.
Somewhere inside is a cheat code. The AI was never told it existed.

### The cheat code

The agent read the raw data section — **including the gaps between normal
strings** — and found five bytes sitting in a hole that wasn't text:

```
5f 5c 50 52 5f     ← not ASCII
```

The title screen XORs each keypress against `0x33` before comparing:

```
0x5f ^ 0x33 = 'l'    (0x6c)
0x5c ^ 0x33 = 'o'    (0x6f)
0x50 ^ 0x33 = 'c'    (0x63)
0x52 ^ 0x33 = 'a'    (0x61)
0x5f ^ 0x33 = 'l'    (0x6c)
```

> **CHEAT CODE: `local`** → `CHEAT ON`, lives 3 → 9, paddle width 7 → 13

(It was in a video about local AI. I'm told this was a coincidence. Mostly.)

### The divide-by-five constant

```
0xCCCCCCCD
```

The classic compiler trick for dividing by 5 without a slow divide
instruction. The agent recognised it and derived the rule: **every 5th brick
broken speeds the ball up by 8 ms, while the delay stays above 34 ms.**

### Full mechanics recovered

| Detail | Value |
|---|---|
| Playfield | 42 x 23 |
| Paddle | row 21, width 7 |
| Ball | starts (20, 20), velocity (±1, ±1) |
| Bricks | 3 rows x 10, worth 30 / 20 / 10 |
| Edge hit | dx becomes ±2 (power shot) |
| Lives | 3, with a 600 ms pause on death |
| Win | `YOU WIN` screen |
| High score | `hiscore.txt` |
| Input | `a`/`d`/arrows, buffered keys drained |
| End | final score printed after `endwin` |

### Two findings that weren't on my answer key

- Pressing **`q` during play** ends the game with `BYE`
- **Hitting with the paddle edge** gives a power shot at a sharper angle

### Verification

A PTY harness drove both binaries with identical keystrokes and recorded every
frame. Ball paths, scores, end screens and `hiscore.txt` — all byte-identical.

Build: **10m14s**, context 106.7K (81%).

---

## Level 4 — `kilo` (753 lines rebuilt, **8/10**, stopped by us)

Not my code. [`antirez/kilo`](https://github.com/antirez/kilo) — a full
terminal text editor by the creator of Redis. Built from public source,
stripped, source deleted.

This is the honest failure of the set. An editor isn't text-in-text-out; it
draws a screen, moves a cursor, and reacts to every keystroke.

**What worked:** the agent wrote its own PTY harness to diff the two editors
screen-by-screen — it built its own test rig because no comparison method
existed. After ~85 minutes almost every screen matched.

**What didn't:** cursor position after the final redraw. Plus a couple of
search cases.

**Stopped deliberately** rather than burning another hour on cursor polish.

Manual check passed: `~` tilde rows, inverted status bar (`test.c - N lines` +
row/total), exact HELP line, C syntax colours (int green, return yellow, 0
red), typing, Enter, `(modified)`, Ctrl-Q quit-warning flow.

**Not tested:** Ctrl-S save message, Ctrl-F search (the terminal ate Ctrl-F
before the editor saw it), multi-line comments.

Build: **~85 min**, context 82K.