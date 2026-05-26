# Bubble Tea (Go)

> Minimalist Elm architecture for the terminal. The default pick for any non-trivial Go TUI.

- Repo: https://github.com/charmbracelet/bubbletea
- Companion libs: [`bubbles`](https://github.com/charmbracelet/bubbles) (widgets), [`lipgloss`](https://github.com/charmbracelet/lipgloss) (styling)
- License: MIT
- Status (May 2026): stable, the de-facto Go TUI standard

## When to choose Bubble Tea

Pick Bubble Tea when **any one** of these is true:

- The team writes Go.
- You value a tiny, explicit core (one `Model`, one `Update`, one `View`) over a feature buffet.
- You want a single static binary distributable — including Termux as a stretch target.
- You like Elm and want that mental model without the JS.

Skip Bubble Tea if the team is Python-shop (use [Textual](./textual.md)) or the project is render-only (use [Rich](./rich.md)).

## Install

```bash
go install github.com/charmbracelet/bubbletea@latest
mkdir myapp && cd myapp
go mod init github.com/you/myapp
go get github.com/charmbracelet/bubbletea github.com/charmbracelet/bubbles github.com/charmbracelet/lipgloss
```

## Hello world

```go
package main

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
)

type model struct{ greeting string }

func (m model) Init() tea.Cmd { return nil }

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.String() == "q" || msg.String() == "ctrl+c" {
			return m, tea.Quit
		}
	}
	return m, nil
}

func (m model) View() string { return m.greeting + "\n\n(q to quit)" }

func main() {
	if _, err := tea.NewProgram(model{greeting: "Hello, terminal."}).Run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
```

Run with `go run .`. Three functions, one struct, total program. That tiny surface is the point.

## One production pattern — async work via `tea.Cmd`

The Elm architecture sends messages to drive state. Side effects return `tea.Cmd`. Long-running work — HTTP, subprocess, disk — is wrapped in a `Cmd` and produces a `Msg` when it finishes.

```go
package main

import (
	"fmt"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

type tickMsg time.Time

type model struct{ count int }

func tickEvery() tea.Cmd {
	return tea.Tick(time.Second, func(t time.Time) tea.Msg { return tickMsg(t) })
}

func (m model) Init() tea.Cmd { return tickEvery() }

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tickMsg:
		m.count++
		return m, tickEvery()
	case tea.KeyMsg:
		if msg.String() == "q" {
			return m, tea.Quit
		}
	}
	return m, nil
}

func (m model) View() string {
	return fmt.Sprintf("ticks: %d  (q to quit)\n", m.count)
}

func main() {
	_, _ = tea.NewProgram(model{}).Run()
}
```

What you get:

- The UI never blocks — `tea.Cmd` runs on a goroutine.
- No mutable globals; the model is the only state.
- Replayable: every state transition is `(prev_model, msg) → (next_model, cmd)`.

## Gotchas

1. **Don't mutate `m` in place inside `Update`.** Bubble Tea's contract is value-typed updates: copy, modify, return the copy. Mutating a pointer field works but breaks the replay model.
2. **`tea.Cmd` runs *outside* the update loop.** Don't capture pointers into `m` from inside a `Cmd` closure — race city.
3. **Rendering is straight-string concatenation.** Use [`lipgloss`](https://github.com/charmbracelet/lipgloss) for styling and layout; avoid hand-rolled ANSI escapes.
4. **`tea.Program.Run()` blocks.** Anything you need to do before it returns must be in a `Cmd`.
5. **Alt screen mode** (`tea.WithAltScreen()`) clears the terminal on exit — toggle off if you want output to remain.

## Termux verdict

⚠️ Needs static build. Compile on Linux/Mac with `CGO_ENABLED=0 GOOS=android GOARCH=arm64 go build`, scp the binary into Termux, and run. See [`../termux/conversion-recipes.md`](../termux/conversion-recipes.md) for the build command and known-good combinations.

## Useful primitives

- `tea.Model` — the state struct (your domain object)
- `tea.Msg` — events flowing into `Update`
- `tea.Cmd` — side-effect declarations
- `bubbles/list`, `bubbles/table`, `bubbles/textinput`, `bubbles/spinner` — drop-in widgets
- `lipgloss.Style` — theming primitives
- `bubbles/help` — see [`../patterns/keybindings.md`](../patterns/keybindings.md) for the help overlay pattern
