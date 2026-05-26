# TUI Master Agent — Architecture

> Original spec drafted **2026-01-23**, materialized into this repo on **2026-05-26** as the `v0.0.1-before` exhibit for the GitHub Finish-Up-A-Thon comeback arc. **Frozen after `v0.0.1-before`** — subsequent design changes land in `docs/design-notes/`, not here.

---

## 1. Vision

An autonomous, multi-agent system that **studies real terminal user interfaces** in the wild and **generates new ones** — including stripped-down Android-friendly variants that run inside Termux.

The agent is not a chat front-end. It is a long-running operator that:

1. **Ingests a feed** of TUI repositories (URLs or local paths).
2. **Studies** each one — clones it, reads code, identifies the framework, extracts the UX primitives the project actually uses (event loops, layout, theming, key handling, async patterns).
3. **Compounds** what it learned into a persistent symbolic memory (`learning_db.json`), so the next study session starts from a richer baseline.
4. **Generates** a new TUI, picking the right framework for the requested category (dashboard, dev tool, monitoring panel, etc.) and producing source code, tests, and a README that meets an explicit "awesome-tuis caliber" quality bar.
5. Optionally **rewrites** the generated TUI into a **Termux-compatible** variant — no native deps, minimal terminal capability requirements, sane default key bindings for soft keyboards.

The point is *not* to ship one TUI. The point is to ship an agent that can ship many, and learn while it does.

## 2. Vocabulary

| Term | Meaning |
|---|---|
| **Master** | The orchestrator process (`tui_master.py`). Lives one per invocation, but its memory persists across runs via `learning_db.json`. |
| **Sub-agent** | A specialized Claude-driven worker the Master spawns to do one job well. There are three: Pattern Learner, TUI Validator, Termux Converter. |
| **Skill** | A Claude Code skill — a long-form, hand-curated prompt-with-attachments that the Master loads to make decisions about the TUI domain. There is exactly one in v1: `tui-builder`. |
| **Feed** | An input URL or local path pointing to a TUI repository to study. |
| **Study session** | One end-to-end invocation. Reads the feed, runs the sub-agents, updates `learning_db.json`, optionally produces a generated TUI in `study_sessions/<timestamp>/generated/`. |
| **Awesome-tuis caliber** | A measurable quality bar (see `skills/tui-builder/quality-bar/awesome-tuis-checklist.md`) the generated TUI must clear before the Master reports success. |

## 3. Top-level architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       tui_master.py  (orchestrator)                       │
│                                                                          │
│   ┌─────────────┐   ┌──────────────┐   ┌──────────────────────────────┐  │
│   │  CLI parse  │──▶│ Feed planner │──▶│   Study session scheduler    │  │
│   └─────────────┘   └──────────────┘   └──────────────┬───────────────┘  │
│                                                       │                  │
│        ┌──────────────────────────────────────────────┼───────────┐      │
│        ▼                                              ▼           ▼      │
│ ┌─────────────────┐                          ┌────────────┐  ┌────────┐  │
│ │ Pattern Learner │   reads cloned source    │ Validator  │  │ Termux │  │
│ │  (sub-agent)    │──▶ writes JSON deltas ──▶│ (sub-agent)│─▶│ (sub-  │  │
│ │                 │                          │            │  │ agent) │  │
│ └────────┬────────┘                          └─────┬──────┘  └────┬───┘  │
│          │                                         │              │      │
│          ▼                                         ▼              ▼      │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │                       learning_db.json                              │  │
│ │  (frameworks, patterns, gotchas, framework × pattern quality grid) │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │           skills/tui-builder  (read-only knowledge layer)      │    │
│   │   framework selector · scaffolding · patterns · termux subset   │    │
│   │              quality bar (awesome-tuis checklist)               │    │
│   └────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

## 4. The Master (`tui_master.py`)

### 4.1 CLI surface

```bash
python tui_master.py \
  --feed <url_or_path>              # repeatable; ≥1 required
  [--termux]                        # also emit a Termux variant per generated TUI
  [--categories "<csv>"]            # e.g. "Dashboards,Development,Monitoring"
  [--framework <name>]              # force a framework; default: agent picks
  [--max-feeds 10]                  # hard ceiling per session
  [--out study_sessions/]           # output root
  [--db learning_db.json]           # persistent symbolic memory
  [--model claude-opus-4-7]         # Anthropic model
  [--budget-usd 5.00]               # soft token budget
  [--dry-run]                       # plan-only, no API calls, no clones
  [--quiet | --verbose]
```

### 4.2 Run lifecycle

```
parse_args
  └─▶ load_or_init_db(learning_db.json)
       └─▶ for each feed:
            ├─▶ clone_to(study_sessions/<ts>/clones/<slug>)
            ├─▶ pattern_learner.run(slug) → patterns.json (delta)
            ├─▶ merge_into_db(delta)
            └─▶ if categories requested:
                 ├─▶ tui_builder.pick_framework(category, db) → fw
                 ├─▶ tui_builder.scaffold(fw, category) → generated/<slug>/
                 ├─▶ validator.run(generated/<slug>/) → quality_report.md
                 └─▶ if --termux:
                      └─▶ termux_converter.run(generated/<slug>/) → generated/<slug>-termux/
  └─▶ persist_db()
  └─▶ emit_session_summary(study_sessions/<ts>/summary.md)
```

### 4.3 `core/` package

```
core/
├── __init__.py
├── cli.py                    # argparse + dataclass config
├── config.py                 # pydantic v2 model of CLI + env + defaults
├── session.py                # StudySession context manager
├── feed.py                   # Feed dataclass + clone strategies (https, ssh, local)
├── db.py                     # LearningDB (loads / persists / merges deltas, schema versioned)
├── runner.py                 # async sub-agent dispatcher (one in-flight per type)
├── budget.py                 # token & USD budgeter
├── prompts.py                # composed prompts (uses skills/tui-builder/SKILL.md)
├── claude_client.py          # thin wrapper over anthropic SDK, retries, logs
└── exceptions.py             # CloneError, ValidationFailed, TermuxIncompatible, ...
```

### 4.4 Concurrency model

- One async event loop in the Master.
- Sub-agents are dispatched via `runner.dispatch(name, payload)` — each is an `async def` returning a JSON-serializable result.
- A single in-flight sub-agent at a time per type, but Pattern Learner / Validator / Termux Converter can interleave across feeds.
- The LearningDB is a singleton inside the process, persisted atomically (write-temp-then-rename) at the end of each feed.

### 4.5 Error handling

Three failure tiers:

| Tier | Example | Behavior |
|---|---|---|
| Recoverable | Anthropic 429, git clone retryable | Exponential backoff, max 3 attempts, then escalate |
| Skippable | Single feed clone fails permanently | Log, mark feed skipped, continue session |
| Fatal | DB corrupt, model unavailable, no feeds | Abort session, exit non-zero, dump diagnostic |

## 5. Sub-agents

Each sub-agent is a Claude conversation seeded with a role-specific system prompt, plus a tool surface tailored to its job. They do not share state directly — they exchange JSON through the Master.

### 5.1 Pattern Learner — `sub_agents/pattern_learner.py`

**Purpose:** Read a cloned source tree and emit a structured `patterns.json` describing what the project does and how.

**Inputs:**
- Path to cloned repo
- Current `learning_db.json` (read-only, for context)

**Outputs:** `patterns.json` with this shape (pydantic-validated):

```json
{
  "feed_url": "https://github.com/Textualize/textual",
  "repo_slug": "textualize-textual",
  "language": "python",
  "framework": "textual",
  "framework_confidence": 0.97,
  "ui_primitives": ["app", "screen", "widget", "binding", "reactive"],
  "event_loop_style": "asyncio",
  "state_management": "reactive_attributes",
  "layout_primitives": ["grid", "vertical", "horizontal", "dock"],
  "color_strategy": "css_themed",
  "keyboard_scheme": "vim_friendly_with_chord_support",
  "test_runner": "pytest",
  "notable_patterns": [
    {"name": "screen_stack", "evidence_paths": ["src/textual/screen.py:42"], "summary": "..."},
    {"name": "css_widget_styling", "evidence_paths": ["..."], "summary": "..."}
  ],
  "gotchas": [
    {"summary": "...", "severity": "medium", "evidence": "..."}
  ],
  "termux_compatibility": {
    "verdict": "needs_truecolor_fallback",
    "blockers": ["truecolor assumed in css palette"]
  }
}
```

**Method:**
1. File-extension distribution → language guess.
2. Top-level package or `Cargo.toml`/`go.mod`/`package.json` parse → framework guess.
3. Walk source, sample 12–30 representative files, hand them to Claude with a structured-extraction prompt.
4. Validate output against pydantic schema, retry on shape mismatch (max 2).

### 5.2 TUI Validator — `sub_agents/validator.py`

**Purpose:** Score a candidate (generated or studied) TUI against the awesome-tuis quality bar; emit a `quality_report.md`.

**Inputs:**
- Path to TUI source (generated or cloned)
- The current quality bar (`skills/tui-builder/quality-bar/awesome-tuis-checklist.md`)

**Outputs:** `quality_report.md` plus a structured `score.json`:

```json
{
  "criteria_total": 12,
  "criteria_passed": 9,
  "criteria_failed": ["accessible_color_palette", "discoverable_keyboard_help", "stable_resize_behavior"],
  "verdict": "promising_but_not_shippable",
  "recommendations": ["add ? help screen", "add --no-color flag", "test under 80x24"]
}
```

**Method:** Static-grep checks for known anti-patterns (e.g., `print()` calls in event loop, hardcoded ANSI without truecolor detection), plus Claude judgment on subjective criteria (palette, README quality).

### 5.3 Termux Converter — `sub_agents/termux_converter.py`

**Purpose:** Take a generated TUI and produce a sibling tree that runs under Termux on Android — same UX intent, conservative terminal capabilities, no native deps.

**Inputs:**
- Path to generated TUI source
- Compatibility matrix (`skills/tui-builder/termux/compatibility-matrix.md`)
- Conversion recipes (`skills/tui-builder/termux/conversion-recipes.md`)

**Outputs:** Sibling directory `<orig>-termux/` containing the rewritten source plus a `TERMUX.md` describing what changed and why.

**Method:**
1. Detect native-dep imports and replace with pure-Python (or pure-Go, etc.) equivalents per the recipes.
2. Cap color usage to 256-color safe palette unless `TERM=xterm-truecolor` confirmed.
3. Replace chord-heavy key bindings with discoverable, soft-keyboard-friendly single keys + a `?` help overlay.
4. Validate via the TUI Validator with a Termux-stricter checklist subset.

## 6. The Skill — `skills/tui-builder/`

A Claude Code skill is a structured, hand-curated knowledge dump that the Master loads into its prompt context. It is the agent's read-only **expertise**, separate from the read-write **memory** (`learning_db.json`).

```
skills/tui-builder/
├── SKILL.md                          # top-level, lists what's inside
├── frameworks/
│   ├── textual.md                    # when to choose, install, hello world, 1 production pattern
│   ├── bubbletea.md
│   ├── ratatui.md
│   ├── ink.md
│   ├── cursive.md
│   └── rich.md
├── patterns/
│   ├── tabs.md                       # copy-paste implementations in ≥3 frameworks
│   ├── modals.md
│   ├── tables.md
│   ├── keybindings.md
│   └── async-events.md
├── termux/
│   ├── compatibility-matrix.md       # framework × {install, run, render, keybinds, perf}
│   └── conversion-recipes.md
└── quality-bar/
    └── awesome-tuis-checklist.md     # ≥12 measurable criteria
```

The skill is **declarative** and **versioned with the repo**. Updates to it are intentional, reviewed PRs — not something the agent rewrites itself. (Self-evolving skills are tracked as a v2 idea in `docs/design-notes/`.)

## 7. Persistent memory — `learning_db.json`

A single, hand-readable JSON file. The agent treats it as append-mostly: deltas merge into it, conflicts resolve newer-wins-with-history.

```json
{
  "schema_version": 1,
  "frameworks": {
    "textual": {
      "studied_count": 7,
      "production_patterns_observed": {
        "tabs": {"count": 5, "exemplars": ["..."]},
        "modals": {"count": 4, "exemplars": ["..."]},
        "tables": {"count": 6, "exemplars": ["..."]}
      },
      "common_gotchas": [...],
      "termux_verdict": "needs_truecolor_fallback"
    },
    "bubbletea": { ... },
    "ratatui": { ... }
  },
  "cross_framework_insights": [
    "every shippable TUI implements ? help",
    "all 3 mature frameworks separate model from render"
  ],
  "history": [
    {"ts": "2026-05-30T12:14:00Z", "session": "...", "delta_summary": "..."}
  ]
}
```

Why JSON and not SQLite? Hand-readable. Diff-able in git history. The whole point of compounding memory is being able to **see** what the agent knows. SQLite hides that behind a query layer.

## 8. Study session layout (per run)

```
study_sessions/2026-05-30T12-14-00/
├── feeds.json                          # what was requested
├── clones/
│   ├── textualize-textual/             # shallow clone, removed at end of session unless --keep
│   ├── charmbracelet-bubbletea/
│   └── ratatui-org-ratatui/
├── patterns/
│   ├── textualize-textual.json
│   ├── charmbracelet-bubbletea.json
│   └── ratatui-org-ratatui.json
├── generated/
│   ├── dashboards-textual/             # if --categories included Dashboards
│   │   ├── pyproject.toml
│   │   ├── src/.../app.py
│   │   ├── tests/test_app.py
│   │   ├── README.md
│   │   └── quality_report.md
│   └── dashboards-textual-termux/
├── logs/
│   ├── master.log
│   ├── pattern_learner.log
│   ├── validator.log
│   └── termux_converter.log
└── summary.md                          # rendered human report
```

## 9. Quality bar — what "awesome-tuis caliber" means

The `awesome-tuis-checklist.md` enumerates ≥12 measurable criteria, each of which is either a static check (grep or AST) or a model-judged binary. Examples:

1. README has install, run, screenshot, key map.
2. `--help` exists and lists every keybinding.
3. `?` shows in-app help.
4. Survives 80×24 — no clipping, no scrolling artifacts on default size.
5. Survives resize during use.
6. Uses fewer than 24 distinct colors *or* declares truecolor explicitly.
7. No raw `print()` calls outside the event loop.
8. Has at least one `pytest` (or framework-equivalent) test covering startup.
9. CI workflow exists.
10. License file present.
11. Documents async behavior if any operation > 100ms.
12. Names every panel/screen in a single style (Pascal, kebab, snake — pick one).

A generated TUI must pass ≥10 of these before the Master reports success.

## 10. Framework support matrix (v1)

| Framework | Language | Termux native | Termux via recipe | Primary use-case |
|---|---|---|---|---|
| Textual | Python | ✅ | n/a | rich, modern, async-first apps |
| Rich | Python | ✅ | n/a | render-only / non-interactive panels |
| Bubble Tea | Go | ⚠️ (needs static build) | ✅ | minimalist Elm-arch apps |
| Ratatui | Rust | ⚠️ (cross-compile) | ✅ | performance-critical TUIs |
| Cursive | Rust | ⚠️ | ⚠️ | classic widget TUIs (low priority for v1) |
| Ink | TypeScript | ⚠️ (Node on Termux) | ✅ | JS-shop dev tools |

## 11. Testing strategy

- **Unit tests** for `core/` modules — `pytest`, ≥80% line coverage, enforced in CI.
- **Integration tests** that spin up the Master with `--dry-run` and assert the plan it produces.
- **Contract tests** for sub-agents: each is run against a fixture repo, output validated against pydantic schema.
- **Golden tests** for generated TUIs: a small fixture category produces a deterministic-enough output (with model temperature 0) that a snapshot test can catch regressions in the prompts.

CI matrix:

```yaml
matrix:
  python: ["3.11", "3.12", "3.13"]
  os: [ubuntu-latest, macos-latest]
```

## 12. What is explicitly out of scope (v1)

- Windows-native terminal hosts (the agent runs in WSL / macOS / Linux / Termux only).
- Web-based TUI emulation (xtermjs glue).
- Fine-tuning loops — all learning is symbolic, stored in `learning_db.json`. The model itself is inference-only.
- Self-modifying skills. The `tui-builder/` skill is changed by humans via PR; the agent can *propose* changes in `docs/design-notes/` but cannot apply them.
- Pricing / cost dashboards. `--budget-usd` is a soft ceiling, not a billing surface.

## 13. Future / v2 ideas (deferred)

- Self-evolving skills under explicit `--skill-mutate` flag.
- A web dashboard rendering `learning_db.json` as a knowledge graph.
- Cross-language pattern translation (e.g., "express this Textual tab as Bubble Tea").
- Auto-PR back to studied repos with small ergonomic fixes the Validator finds.
- A `--watch` mode that monitors a feed list for new repos and runs sessions automatically.

## 14. Decision log (Jan 23, 2026)

Recorded inline to preserve the original reasoning:

- **Why three sub-agents and not one mega-agent?** Separation of concerns: learning, validating, and porting are distinct evaluation criteria. Easier to swap any one. Easier to test in isolation.
- **Why JSON memory, not a vector DB?** Compounding memory should be auditable. A vector DB hides the model from the operator. v1 stays symbolic.
- **Why Python for the Master?** The ecosystem of TUI tooling Python touches (Textual, Rich) plus pydantic for schema discipline plus the official `anthropic` SDK. Go would be tempting; Python wins on the schema layer.
- **Why six frameworks and not three?** Three is what we'd ship if we were demoing. Six is what we need to be useful — different shops need different output languages. Two per major language family (Python, Go+Rust+TS).
- **Why Termux at all?** Because the most underserved TUI surface in 2026 is the phone-as-laptop case. Termux is where the agent earns its keep — anyone can scaffold a desktop TUI; few think about what "responsive TUI" means on a 6-inch screen with a soft keyboard.

---

*End of frozen spec. Anything past v0.0.1-before is in `docs/design-notes/`.*
