Suggested subreddit: r/Python

---

**Title:**
I built a tool that reads a TUI framework's repo, then generates and headlessly verifies an original Textual app in that framework

**Body:**

I've been poking at a question for a while: can you point a script at a real TUI framework's GitHub repo and have it produce a *working* app in that framework, without hardcoding the framework's API in advance?

The result is a single-file Python orchestrator (~330 lines). You give it a repo URL and it:

1. Shallow-clones the repo.
2. Detects the framework with plain heuristics — file-extension counts plus an import grep. No AI in this step, just counting. Right now it recognizes six: Textual, Rich, Bubble Tea, Ratatui, Ink, Cursive.
3. Feeds the README plus a few key source files to the Claude API (claude-opus-4-7) and asks for a small *original* TUI in that same framework.
4. Writes it to `output/<framework>/` and verifies it actually runs headlessly. For Textual that means driving it through `run_test()`; the app has to mount and respond, not just import.

For the Textual path the committed example is "Pixel Pond" — you drop pebbles, feed fish, and toggle day/night. It's small but it's real, generated, and it passes the headless run.

The detection-by-counting part is what I'm least sure about. It's deliberately dumb (extension census + import grep) because I wanted the framework detection to be deterministic and explainable rather than another model call. It holds up for the six frameworks I've tried, but I'd expect it to get confused by polyglot repos or vendored deps.

So, two questions for the Textual / Python TUI folks here:

- For headless verification, is `run_test()` enough to call a generated app "working," or are there failure modes (timers, workers, async teardown) it won't catch that I should be asserting on?
- If you were detecting "is this a Textual repo" from the tree alone, what signal would you trust beyond `import textual` and `.py` density?

It's mypy + ruff clean with 17 offline tests. Repo link in a comment so this doesn't read as a drive-by — genuinely want the verification critique.
