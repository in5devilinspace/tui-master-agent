Suggested subreddit: r/golang

---

**Title:**
Cross-language TUI generator: it detects Bubble Tea from the repo tree, generates a Go TUI, and gates on `go build` before calling it done

**Body:**

I have a single-file Python orchestrator that points at a TUI framework's GitHub repo and tries to generate a small original app in that framework. The part that's relevant here is that it crosses the language boundary cleanly — the orchestrator is Python, but one of its two end-to-end-verified targets is Bubble Tea, so the thing it emits and checks is Go.

How it handles Go specifically:

- Framework detection is heuristic, not AI: it counts file extensions and greps imports. A repo full of `.go` files with `github.com/charmbracelet/bubbletea` in the import set reads as Bubble Tea. (The same detector also recognizes Ratatui, Textual, Rich, Ink, and Cursive — six total — so the Go path shares one code route with everything else.)
- It feeds the README plus a few key source files to the Claude API (claude-opus-4-7) and asks for an original Bubble Tea program following the Model/Update/View structure.
- Verification for the Go target is `go build` on the generated output in `output/bubbletea/`. If it doesn't compile, it doesn't count. The committed example is a Pomodoro timer.

I went with `go build` as the gate rather than trying to run the TUI in a pty because compilation already catches the failure mode I care about most from a model — plausible-looking code that references the wrong API or a non-existent field. For the Python/Textual target I do drive a headless run instead, since "imports fine" is weaker there.

Where I'd value Gophers' read:

- Is `go build` a reasonable "it works" bar for generated Bubble Tea, or is the interesting breakage downstream of compilation (Update loops that never quit, blocking `tea.Cmd`s) such that I should be running it under a test harness like `teatest`?
- For detection from the tree alone, would you trust the import path over `go.mod`, or check both? Vendored deps and monorepos are the cases I expect to fool the extension-count approach.

~330 lines, mypy + ruff clean on the Python side, 17 offline tests. Repo link in a comment rather than the title.
