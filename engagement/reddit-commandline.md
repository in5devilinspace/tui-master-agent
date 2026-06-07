Suggested subreddit: r/commandline

---

**Title:**
Point it at a TUI framework's repo and it generates + verifies an original TUI in that framework (Textual, Bubble Tea, and four more detected)

**Body:**

I built a small tool for people who live in the terminal and keep meaning to try the *next* TUI framework but never get past the blank `main`.

You give it a GitHub repo for a TUI framework. It shallow-clones, figures out which framework it is, and produces a small original TUI in that same framework — then checks the thing actually runs before handing it to you.

The pipeline, end to end:

- **Detect** the framework by counting file extensions and grepping imports. No model call here, just heuristics, so it's deterministic. It currently recognizes six: Textual, Rich, Bubble Tea, Ratatui, Ink, and Cursive.
- **Generate** by feeding the README plus a few key source files to the Claude API (claude-opus-4-7) and asking for an original app in that framework — not a copy of the repo's examples.
- **Verify** headlessly, per language. Textual apps get driven through `run_test()`; Bubble Tea apps have to pass `go build`. Output lands in `output/<framework>/`.

Two frameworks are verified all the way through across two languages right now: Textual (Python) and Bubble Tea (Go). The committed examples are a Textual "Pixel Pond" (drop pebbles, feed fish, day/night toggle) and a Bubble Tea Pomodoro timer. The other four frameworks are recognized by the detector but not yet wired to their own verify step — that's honest roadmap, filed as GitHub issues, not silently broken.

It's a single file, around 330 lines, mypy + ruff clean, with 17 offline tests.

What I'm curious about from this crowd: if you wanted to add a seventh framework, the work is (1) a detection signal and (2) a headless "did it run" check. For the TUIs you actually use, what's the cheapest reliable way to assert "this ran and rendered" from a script, with no human watching the terminal? That verify step is the whole ballgame and I'd rather steal a good pattern than invent a flaky one.

Repo link in a comment.
