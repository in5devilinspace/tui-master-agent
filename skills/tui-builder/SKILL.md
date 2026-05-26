---
name: tui-builder
description: Use when generating, evaluating, or porting Terminal User Interfaces (TUIs). Encodes framework selection, scaffolding, common UI patterns (tabs, modals, tables, keybindings, async events), Termux compatibility rules, and an "awesome-tuis caliber" quality bar across Textual, Bubble Tea, Ratatui, Ink, Cursive, and Rich.
---

# TUI Builder — Claude Code Skill

This skill is the **read-only expertise** of the TUI Master Agent. The agent's read-write **memory** lives separately in `learning_db.json`. Use this skill any time the task involves choosing a TUI framework, writing TUI code, evaluating a TUI for shippability, or porting one to Termux.

## When to invoke

- "Build a TUI for X" (dashboard, dev tool, monitor, picker, etc.)
- "Review this TUI"
- "Port this TUI to Termux"
- "Pick a framework for X"
- "What's the canonical way to do tabs / modals / tables / keybindings / async events in framework Y?"

If none of the above — skip this skill.

## How the skill is laid out

```
skills/tui-builder/
├── SKILL.md                          ← you are here (router)
├── frameworks/
│   ├── textual.md                    Python — async-first, modern, batteries-included
│   ├── bubbletea.md                  Go — minimalist Elm architecture
│   ├── ratatui.md                    Rust — performance-critical, immediate-mode
│   ├── ink.md                        TypeScript — React-for-the-terminal
│   ├── cursive.md                    Rust — classic widget-tree TUIs
│   └── rich.md                       Python — render-only / non-interactive panels
├── patterns/
│   ├── tabs.md                       3-framework implementations
│   ├── modals.md
│   ├── tables.md
│   ├── keybindings.md
│   └── async-events.md
├── termux/
│   ├── compatibility-matrix.md       framework × {install, run, render, keybinds, perf}
│   └── conversion-recipes.md         how to port each framework to Termux
└── quality-bar/
    └── awesome-tuis-checklist.md     12 measurable criteria for shippability
```

## Framework selector (decision tree)

Given (target_lang, target_platform, complexity, team_familiarity):

```
                  target_lang
                       │
       ┌───────────────┼───────────────┬──────────────┐
       ▼               ▼               ▼              ▼
    Python            Go             Rust         TypeScript
       │              │               │              │
   need ANY      always pick     need OOP-style    always pick
   interaction?  bubbletea       widget tree?      ink
       │                              │
   ┌───┴───┐                      ┌───┴───┐
   ▼       ▼                      ▼       ▼
  yes     no                     yes      no
   │       │                      │       │
 textual  rich                  cursive ratatui
```

Tie-breakers:

- **target_platform = Termux** → favor Textual (Python) or Bubble Tea (Go static-build). Avoid Cursive (native deps painful on Android).
- **complexity = high (many screens, async, themes)** → Textual > Bubble Tea > Ratatui > Ink > Cursive > Rich.
- **complexity = low (one screen, render-only panel)** → Rich (Python) > Bubble Tea > Textual.
- **team_familiarity matters more than the chart.** A team that knows Go ships a worse TUI in Textual than a good one in Bubble Tea.

## Output discipline

Every generated TUI must clear the `quality-bar/awesome-tuis-checklist.md` (≥10 of 12 criteria) before the Master reports success. If fewer than 10 pass, the agent surfaces the gaps and asks before declaring done.

## Invariants the agent enforces

1. **No raw `print()` in the event loop.** Every framework has a render path; use it.
2. **Every TUI ships a `?` help overlay.** Keyboard discoverability is the single highest-impact UX choice.
3. **Color usage is declared.** Either ≤24 distinct colors or `TERM=xterm-truecolor` confirmed at startup.
4. **Survives 80×24.** Smaller is welcome, bigger is fine, but the 80×24 baseline is non-negotiable.
5. **Names are consistent.** Pick `PascalCase` for screens, `snake_case` for actions, and don't mix.
6. **One framework per project.** Never mix Textual + Rich-the-interactive-app; Rich is a renderer Textual already uses.

## What this skill is NOT

- Not a chat front-end builder. For LLM-chat TUIs, the agent still uses one of these six frameworks; the chat is a feature, not a category.
- Not a Windows-native terminal toolkit. Output runs on WSL / macOS / Linux / Termux.
- Not self-modifying. The agent can propose updates to this skill in `docs/design-notes/`, but never edit it autonomously.
