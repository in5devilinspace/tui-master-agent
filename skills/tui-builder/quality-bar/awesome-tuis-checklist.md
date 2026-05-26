# Awesome-TUIs caliber — the quality bar

> 14 measurable criteria a generated TUI must clear before the Master reports success. The TUI Validator sub-agent runs these against the source tree and emits a `quality_report.md` + structured `score.json`. A generated TUI must pass **≥10 of 14** before the Master declares success. If it scores 8–9, the report flags it for human review. Below 8 = automatic regenerate.

Each criterion is either a **static check** (grep / AST / file presence) or a **model judgment** (Claude reads README and source, returns binary). Type is noted next to each.

---

## 1. README presence and structure  ·  *static*

The repo has a `README.md` at the root, and it contains, in any order:

- An install command (`pip install`, `go get`, `cargo add`, `npm install`).
- A run command (`python -m`, `go run`, `cargo run`, `npx`).
- A screenshot or asciinema link.
- A keyboard cheatsheet table or list.

Anything less than all four = fail.

## 2. `--help` lists every keybinding  ·  static

Invoking the binary with `--help` (or framework equivalent) prints a help section that mentions every key registered in the app's bindings table. Done programmatically by parsing the bindings table and grepping `--help` output.

## 3. `?` shows in-app help  ·  static + smoke

Either a `?` binding is registered, or the framework's built-in help overlay (Textual `Footer`, `bubbles/help`, Cursive's modal stack) is wired. Smoke-tested by sending `?` to a running PTY and asserting an overlay diff.

## 4. Survives 80×24 without clipping or wrap artifacts  ·  smoke

The TUI is launched in an 80×24 PTY (`pyte`, `vt100-emulator`, or `tmux new-session -d -x 80 -y 24`). After 2 render frames, no character is in the last column without an explicit `\n` after it, and no panel is cut mid-border.

## 5. Survives resize during use  ·  smoke

Same as #4, but mid-run the PTY is resized to 120×40 and then back to 80×24. The render does not corrupt, and the layout reflows. (Resize-corruption is a top-10 TUI bug; it's worth a dedicated criterion.)

## 6. Declared color usage  ·  static + judgment

Either:

- The source uses ≤24 distinct colors (counted by parsing style declarations), or
- The source explicitly checks `COLORTERM` / `TERM` / framework profile at startup and downgrades.

Truecolor-only TUIs without a declared fallback fail this criterion.

## 7. No raw `print` in the event loop  ·  static

`grep -nE '^[^#]*\bprint\b' src/` (or language equivalent) finds zero hits inside files that are part of the render path. Logging through the framework's log channel is exempt. The check is heuristic but cheap and catches the common bug.

## 8. ≥1 test covering startup  ·  static + run

A test file exists. It is registered with the project's test runner (`pytest`, `go test`, `cargo test`, `vitest`). It runs the app's entry point with a synthetic input (e.g., "press q immediately") and asserts a non-zero exit code is **not** emitted. Coverage is enforced ≥80% for the Master; for generated TUIs, the bar is "≥1 test" — proof-of-life, not full coverage.

## 9. CI workflow exists  ·  static

A `.github/workflows/` file exists, runs the test suite on push, and is YAML-valid. Multi-version matrix is a bonus, not required.

## 10. License file present and non-empty  ·  static

`LICENSE` or `LICENSE.md` exists. Non-zero size. Contains a recognized SPDX identifier in the header (MIT, Apache-2.0, BSD-3-Clause, GPL-3.0-or-later, etc.).

## 11. Async behavior documented if any op > 100ms  ·  judgment

If the source contains async / `tea.Cmd` / `tokio::spawn` / `useEffect`-with-async, the README has a sentence explaining what runs in the background and how it surfaces results. Model-judged binary: "would a new contributor understand the async path from the README?"

## 12. Consistent naming style  ·  static

All screen / panel / widget identifiers follow exactly one of: `PascalCase`, `snake_case`, `kebab-case`. Mixed styles fail. Detected by tokenizing the identifiers in the bindings table + the file/class names of screens.

## 13. Resize-safe at 50×20 (Termux portrait)  ·  smoke, optional

Same as #4 but at 50×20. Only required for TUIs marked `termux=true` in the session config. Generated desktop-only TUIs are exempt.

## 14. Exits cleanly on `Ctrl+C` and `q`  ·  smoke

Sending `Ctrl+C` to a running TUI causes it to exit with code 0 (or 130 for SIGINT, framework's choice — but consistent). Sending `q` does the same. No `^C^C` required (i.e., the framework's signal handling is wired).

---

## Scoring

| Pass count | Verdict |
|---|---|
| 13–14 | **shippable** — Master reports success |
| 10–12 | **shippable_with_caveats** — Master reports success, lists the failed criteria in the report |
| 8–9   | **needs_review** — Master pauses, asks the operator |
| 0–7   | **regenerate** — Master discards the candidate and re-runs with a stricter prompt |

The TUI Validator implements this as `score.json`:

```json
{
  "criteria_total": 14,
  "criteria_passed": 12,
  "criteria_failed": ["7_no_raw_print", "12_consistent_naming"],
  "verdict": "shippable_with_caveats",
  "recommendations": [
    "Wrap the two debug print() calls in src/utils.py with self.log() or remove them.",
    "Rename action_AddItem to action_add_item to match the rest of the bindings table."
  ]
}
```

A `quality_report.md` is generated alongside, intended for human reading, listing each criterion with pass/fail and the reasoning.

---

## What this checklist is NOT

- **Not a substitute for user testing.** A TUI that passes 14/14 can still be ugly or confusing. The bar is "shippable as a baseline," not "delightful."
- **Not a coverage gate.** That belongs in the agent's own test suite (`tests/`), not in generated TUIs. The agent enforces its own ≥80% line coverage independently.
- **Not framework-specific.** Every criterion is framework-agnostic. Framework-specific anti-patterns live in the framework page (e.g., "don't mix ncurses + crossterm" in [`../frameworks/cursive.md`](../frameworks/cursive.md)).
