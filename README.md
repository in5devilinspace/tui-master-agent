# TUI Master Agent

> An autonomous multi-agent system that learns from real GitHub TUI repositories and generates new ones — including Termux-friendly mobile variants.

![status: revival in progress](https://img.shields.io/badge/status-revival%20in%20progress-orange)
![license](https://img.shields.io/badge/license-MIT-blue)
![python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)

---

## Where this is in the comeback arc

This is the **`v0.0.1-before`** snapshot.

The repo currently contains:

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — the original architectural spec, drafted **January 23, 2026**, materialized verbatim into the repo today as the "before" exhibit
- `LICENSE` (MIT)
- This README

And nothing else. No orchestrator. No sub-agents. No skill. No tests. No demo.

That's the point. This commit is the **frozen "before"** — the moment the dormant idea became a repo so the comeback could be measured against something real.

The "after" lands on the [GitHub Finish-Up-A-Thon](https://dev.to/challenges/github-2026-05-21) submission post on **June 5, 2026**. By then, this README will look very different.

## What's coming (per the spec)

The full plan lives in [`ARCHITECTURE.md`](./ARCHITECTURE.md). Short version:

```
                ┌──────────────────────────┐
                │  TUI Master orchestrator │
                │     (tui_master.py)      │
                └─────────────┬────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌────────────────┐    ┌───────────────────┐
│ Pattern       │    │ TUI Validator  │    │ Termux Converter  │
│ Learner       │    │ (awesome-tuis  │    │ (Android-friendly │
│ (extracts UX  │    │  quality bar)  │    │  subset rewriter) │
│  primitives)  │    │                │    │                   │
└───────┬───────┘    └────────┬───────┘    └─────────┬─────────┘
        │                     │                      │
        └─────────────────────┼──────────────────────┘
                              ▼
                ┌──────────────────────────┐
                │   learning_db.json       │
                │  (compounding memory)    │
                └──────────────────────────┘
```

**Frameworks the agent targets:** Textual, Bubble Tea, Ratatui, Ink, Cursive, Rich.

**One CLI invocation:**

```bash
python tui_master.py \
  --feed https://github.com/Textualize/textual \
  --feed https://github.com/charmbracelet/bubbletea \
  --feed https://github.com/ratatui-org/ratatui \
  --termux \
  --categories "Dashboards,Development,Monitoring"
```

## Why the gap?

Drafted the architecture on a Sunday in late January, opened a Claude Code session the next day, got two paragraphs into the orchestrator stub and stopped. The "study session learning" abstraction was hard, the scope was wide, and life happened. Four months of nothing.

The [GitHub Finish-Up-A-Thon](https://dev.to/challenges/github-2026-05-21) announcement on May 21 was the kick.

## License

MIT. See [`LICENSE`](./LICENSE).

## Acknowledgements

Frameworks studied and credited in their own scaffold files: [Textualize/textual](https://github.com/Textualize/textual), [charmbracelet/bubbletea](https://github.com/charmbracelet/bubbletea), [ratatui-org/ratatui](https://github.com/ratatui-org/ratatui), [vadimdemedes/ink](https://github.com/vadimdemedes/ink), [gyscos/cursive](https://github.com/gyscos/cursive), [Textualize/rich](https://github.com/Textualize/rich).

---

_If you're a judge reading this on June 5 and the README is still this short — the project shipped at v0.0.1-before and nothing else. Tag was meant to be a baseline, not a milestone._
