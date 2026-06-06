# TUI Master Agent

> Point it at a real GitHub TUI repo. It studies the code, figures out the framework, and generates a small **original** TUI in that same framework — then proves the result actually runs.

![CI](https://github.com/in5devilinspace/tui-master-agent/actions/workflows/ci.yml/badge.svg)
![license](https://img.shields.io/badge/license-MIT-blue)
![python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)

```bash
python tui_master.py https://github.com/Textualize/textual
# Cloning https://github.com/Textualize/textual
# Framework detected -> textual (signatures=3212, files=918)
# Generating with claude-opus-4-7 ...
# Wrote 1 file(s) to output/textual - "Pixel Pond"
# Verifying the generated TUI runs ...
# run_test headless -> exit 0
# OK - python main.py from output/textual
```

---

## The comeback arc

This project was **scoped on January 23, 2026** as an ambitious multi-agent
system — three sub-agents, a compounding learning database, six frameworks, a
Termux converter. The full spec is preserved, untouched, in
[`ARCHITECTURE.md`](./ARCHITECTURE.md), frozen at the
[`v0.0.1-before`](https://github.com/in5devilinspace/tui-master-agent/releases/tag/v0.0.1-before)
tag.

Then it hit a wall. The hard part was designing "patterns as a data structure,"
the scope was wide, and it sat dormant for four and a half months — an
architecture spec and zero implementation.

The [GitHub Finish-Up-A-Thon](https://dev.to/challenges/github-2026-05-21) was
the forcing function. In the final sprint I deliberately **cut the scope to the
spine** and shipped the one thing that makes the whole idea real: a working
single-agent generator. The sub-agents, learning DB, and Termux converter are
honest roadmap items (see below), not claims.

This isn't the finished vision. It's the start of finishing.

## What it actually does (today)

A single-file orchestrator, [`tui_master.py`](./tui_master.py), runs the whole
pipeline inline:

1. **Clone** the given GitHub repo (shallow).
2. **Detect** the TUI framework with *heuristics, not AI* — file-extension
   counts plus import-signature grep. A Rich-only repo is never mistaken for
   Textual; a Go repo is recognized as Bubble Tea.
3. **Gather** the README plus the few most framework-dense source files.
4. **Generate** a small, original TUI in the same framework in a single
   `claude-opus-4-7` call.
5. **Write** it to `output/<framework>/`.
6. **Verify** it runs — framework-native and headless, no TTY required:
   Textual via its official `run_test()` pilot, Bubble Tea via `go build`.

### Detected vs verified

| Framework | Language | Detection | Generation | Headless run-verification |
|---|---|:---:|:---:|:---:|
| **Textual** | Python | ✅ | ✅ | ✅ `run_test()` |
| **Bubble Tea** | Go | ✅ | ✅ | ✅ `go build` |
| Rich | Python | ✅ | ✅ | best-effort |
| Ratatui | Rust | ✅ | ✅ | not yet |
| Ink | JS/TS | ✅ | ✅ | not yet |
| Cursive | Rust | ✅ | ✅ | not yet |

Two frameworks across two languages are wired end-to-end with automated
run-verification. The detector covers all six.

## Quickstart

```bash
uv venv && uv pip install -e ".[dev]"        # or: pip install -e ".[dev]"

# Anthropic SDK creds (ANTHROPIC_API_KEY; ANTHROPIC_BASE_URL if self-routed)
export ANTHROPIC_API_KEY=sk-...

python tui_master.py https://github.com/Textualize/textual
python tui_master.py https://github.com/charmbracelet/bubbletea
```

Useful flags: `--framework {textual,rich,bubbletea,...}` to force one,
`--out DIR`, `--max-files N`, `--dry-run` (clone + detect only, no API call),
`--no-verify`, `--local PATH` (skip cloning).

See [`examples/`](./examples/) for sample generated TUIs (a Textual "Pixel Pond"
and a Bubble Tea Pomodoro timer) — committed verbatim as the model produced them.

## Roadmap

The original [`ARCHITECTURE.md`](./ARCHITECTURE.md) vision, tracked as issues and
explicitly **not built yet**:

- Pattern Learner sub-agent — extract reusable UX primitives across studied repos
- TUI Validator sub-agent — score output against an "awesome-tuis" quality bar
- Termux Converter sub-agent — Android-friendly variant of each generated TUI
- `learning_db.json` — compounding symbolic memory across study sessions
- Headless run-verification for Rust / JS frameworks (Ratatui, Ink, Cursive)

## Built with

Architecture, orchestration, and the verification harness: Claude Code
(`claude-opus-4-7`). Generation calls go through the Anthropic Python SDK.
Conventional Commits; MIT licensed.

## Acknowledgements

Frameworks studied and credited: [Textualize/textual](https://github.com/Textualize/textual),
[charmbracelet/bubbletea](https://github.com/charmbracelet/bubbletea),
[Textualize/rich](https://github.com/Textualize/rich),
[ratatui/ratatui](https://github.com/ratatui/ratatui),
[vadimdemedes/ink](https://github.com/vadimdemedes/ink),
[gyscos/cursive](https://github.com/gyscos/cursive).

## License

MIT. See [`LICENSE`](./LICENSE).
