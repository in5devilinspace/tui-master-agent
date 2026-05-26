# Claude — TUI Master Agent project rules

This file is auto-loaded into every Claude Code session opened in this repo. Keep it lean.

## Project shape

`tui-master-agent` — an autonomous multi-agent system that ingests TUI repositories, learns patterns, and generates new TUIs (including Termux-compatible variants).

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the canonical design. **Never modify `ARCHITECTURE.md`** after the `v0.0.1-before` tag — it is the frozen "before" exhibit for the GitHub Finish-Up-A-Thon submission. Changes to the design land in `docs/design-notes/` instead.

## Stack

- Python 3.11+ (CI matrix: 3.11, 3.12, 3.13 × Ubuntu, macOS)
- `rich`, `textual`, `gitpython`, `anthropic` (model: `claude-opus-4-7`), `pydantic` v2, `pytest` (≥80% coverage)
- Output frameworks supported: Textual, Bubble Tea, Ratatui, Ink, Cursive, Rich
- MIT license

## Conventions

- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `ci:`)
  - When GitHub Copilot Workspace materially contributed to a commit, append a trailer:
    `Co-authored-by: GitHub Copilot <copilot@github.com>`
- **Branches:** use Linear's auto-generated `gitBranchName` (the9nine workspace, team `THE`) — PRs auto-link
- **Issue references in commit bodies:** `closes THE-N` (one per line for multiples)
- **`git add` by filename** — never `-A` / never `.`
- **No code comments** unless the *why* is non-obvious
- **No emoji in code** — they're fine in READMEs and DEV.to posts, not in docstrings or commit messages

## Layout

```
.
├── ARCHITECTURE.md           # frozen Jan 23 spec — DO NOT EDIT after v0.0.1-before
├── README.md
├── LICENSE                   # MIT
├── tui_master.py             # entry point (THE-135)
├── core/                     # orchestrator innards (THE-135)
├── sub_agents/               # pattern_learner, validator, termux_converter (THE-137)
├── skills/
│   └── tui-builder/          # THE-134: framework + pattern knowledge
├── study_sessions/           # per-run artifacts (gitignored runtime)
├── tests/                    # pytest, ≥80% coverage gate
├── .github/workflows/        # CI matrix
├── assets/
│   └── before/               # baseline screenshots for the submission post
└── docs/
    └── design-notes/         # post-v0.0.1-before design changes land here
```

## Superpowers skills to invoke (per the 1% rule)

| Trigger | Skill |
|---|---|
| Feature design / "let's build X" | `superpowers:brainstorming` (before code) |
| Any bug, failing test, unexpected behavior | `superpowers:systematic-debugging` |
| Multi-step spec | `superpowers:writing-plans` → `superpowers:executing-plans` |
| New module with tests | `superpowers:test-driven-development` |
| Before declaring done | `superpowers:verification-before-completion` |

## Linear ↔ this repo

- Project: **DEV.to Hackathon Push — Win $4K** (`https://linear.app/the9nine/project/devto-hackathon-push-win-dollar4k-e37e08954419`)
- Active issues: THE-132 through THE-144
- Update status via Linear MCP at issue boundaries: `Backlog → In Progress → In Review → Done`

## Out of scope (for v1)

- Windows-native TUI host (only WSL / macOS / Linux / Termux)
- Web-based TUI emulation (no xtermjs glue)
- LLM-fine-tuning loops (we stay inference-only; learning is symbolic, in `learning_db.json`)

## Style

Terse. Diff is the report. Don't summarize unless asked.
