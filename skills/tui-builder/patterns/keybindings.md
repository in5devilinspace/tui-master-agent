# Pattern: Keybindings

> The unwritten contract of every shippable TUI: every action is reachable by keyboard, every binding is discoverable, and the most common keys mean the same thing across apps.

## The non-negotiables (apply to every TUI you ship)

| Key | Meaning | Why |
|---|---|---|
| `q` / `Ctrl+C` | Quit | Universal. Don't try to be clever. |
| `?` | Help overlay listing all bindings | Discoverability is the #1 TUI UX failure mode. |
| `Esc` | Dismiss modal / leave mode | Muscle memory across every modal app. |
| `Tab` / `Shift+Tab` | Move focus forward / back | Even single-pane TUIs benefit. |
| Arrow keys + `h j k l` | Navigate within current view | Vim users will thank you; arrow users will never notice. |
| `g` / `G` | Top / Bottom of list | Vim-flavored but universally adopted. |
| `/` | Filter / search the current view | High-leverage when present, expected if there's a list. |

If a TUI doesn't honor these, judges drop a quality point. So does every reviewer.

## Textual

```python
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Static


class App_(App):
    BINDINGS = [
        Binding("q",     "quit",      "Quit"),
        Binding("?",     "help",      "Help"),
        Binding("ctrl+r","reload",    "Reload",       show=True),
        Binding("/",     "filter",    "Filter",       show=True),
        Binding("g,g",   "to_top",    "Top",          show=True),  # vim-style chord
        Binding("shift+g","to_bottom","Bottom",       show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("press ? for help")
        yield Footer()
```

The `Footer` reads `BINDINGS` and renders the active key map automatically. `?` triggers `action_help`, which Textual auto-implements to show the bindings overlay.

## Bubble Tea — `bubbles/key` + `bubbles/help`

```go
package main

import (
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/bubbles/key"
	"github.com/charmbracelet/bubbles/help"
)

type keyMap struct {
	Up     key.Binding
	Down   key.Binding
	Filter key.Binding
	Help   key.Binding
	Quit   key.Binding
}

func (k keyMap) ShortHelp() []key.Binding { return []key.Binding{k.Up, k.Down, k.Filter, k.Help, k.Quit} }
func (k keyMap) FullHelp() [][]key.Binding {
	return [][]key.Binding{
		{k.Up, k.Down},
		{k.Filter, k.Help, k.Quit},
	}
}

var keys = keyMap{
	Up:     key.NewBinding(key.WithKeys("up", "k"),       key.WithHelp("↑/k", "up")),
	Down:   key.NewBinding(key.WithKeys("down", "j"),     key.WithHelp("↓/j", "down")),
	Filter: key.NewBinding(key.WithKeys("/"),             key.WithHelp("/",   "filter")),
	Help:   key.NewBinding(key.WithKeys("?"),             key.WithHelp("?",   "toggle help")),
	Quit:   key.NewBinding(key.WithKeys("q", "ctrl+c"),   key.WithHelp("q",   "quit")),
}

type model struct{ help help.Model }

func (m model) Init() tea.Cmd { return nil }
func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	if k, ok := msg.(tea.KeyMsg); ok {
		switch {
		case key.Matches(k, keys.Quit):
			return m, tea.Quit
		case key.Matches(k, keys.Help):
			m.help.ShowAll = !m.help.ShowAll
		}
	}
	return m, nil
}
func (m model) View() string { return "press ? for help\n\n" + m.help.View(keys) }

func main() { _, _ = tea.NewProgram(model{help: help.New()}).Run() }
```

The `key.Matches` function is what makes this robust — it compares against a `KeyBinding`'s registered keys, so you can rebind via config without touching the switch.

## Ratatui — own your own map

Ratatui doesn't ship a help widget. Build a small abstraction:

```rust
struct Binding { keys: &'static [&'static str], desc: &'static str }

const BINDINGS: &[Binding] = &[
    Binding { keys: &["q", "Ctrl+C"], desc: "Quit" },
    Binding { keys: &["?"],           desc: "Help" },
    Binding { keys: &["/"],           desc: "Filter" },
    Binding { keys: &["k", "↑"],      desc: "Up" },
    Binding { keys: &["j", "↓"],      desc: "Down" },
];

fn help_lines() -> Vec<ratatui::text::Line<'static>> {
    BINDINGS.iter().map(|b| {
        ratatui::text::Line::from(format!("{:>10}  {}", b.keys.join("/"), b.desc))
    }).collect()
}
```

Render `help_lines()` in a `Paragraph` inside a modal (see [`./modals.md`](./modals.md)) when `?` is pressed.

## Discoverability checklist (apply to every TUI)

- [ ] Footer or header always shows the 3–5 most relevant bindings for the current screen.
- [ ] `?` opens a full overlay listing every binding.
- [ ] Bindings change with focus — when a modal is open, the footer reflects the modal's keys, not the underlying screen's.
- [ ] Chord bindings (`g g`) display as `gg` in the help, not `g, g`.
- [ ] Mouse bindings, if any, are listed in the help text too.

## Cross-framework notes

- **Don't override `Ctrl+Z` or `Ctrl+S`.** They are terminal-level controls (suspend, flow-control). Hijacking them surprises users.
- **`Esc` has a delay in many terminals.** A 100ms timeout to disambiguate from alt-prefixed keys is standard. Most frameworks handle this; don't reinvent.
- **Vim keys are a superset, not a substitute.** Always ship arrow keys alongside `h j k l`.
- **Document binding conflicts.** If `/` filters and the user is inside a search box, `/` should type a literal slash — not trigger filter mode again. Use input contexts.

In Ink, register key handlers with `useInput((input, key) => { ... })`. In Cursive, use `siv.add_global_callback(Event::Char('q'), |s| s.quit())`. In Rich (non-interactive), there are no key bindings to ship.
