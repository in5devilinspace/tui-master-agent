# Pattern: Tabs

> A horizontal strip of labels; one is active; the body renders the active tab's content. Tabs is one of the highest-value TUI primitives because it scales information density without scrolling.

## When to use

- The UI has 2–7 distinct views of the same domain (e.g., logs / metrics / config / about).
- Switching between them should be cheap and discoverable (tab key, arrow keys, mouse click).
- The views are logically equal — none of them is "primary."

If one view is the primary and the others are details, use a master-detail split instead.

## Textual

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, Static


class TabsApp(App):
    BINDINGS = [
        ("1", "show_tab('logs')",   "Logs"),
        ("2", "show_tab('stats')",  "Stats"),
        ("3", "show_tab('about')",  "About"),
        ("q", "quit",               "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="logs"):
            with TabPane("Logs", id="logs"):
                yield Static("[b]live log feed here[/]")
            with TabPane("Stats", id="stats"):
                yield Static("[b]metrics here[/]")
            with TabPane("About", id="about"):
                yield Static("[b]about this tool[/]")
        yield Footer()

    def action_show_tab(self, name: str) -> None:
        self.query_one(TabbedContent).active = name


if __name__ == "__main__":
    TabsApp().run()
```

Textual's `TabbedContent` does keyboard nav, focus management, mouse clicks, and styling out of the box. Numeric shortcuts via `BINDINGS` make jumping cheap.

## Bubble Tea

```go
package main

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

var (
	active   = lipgloss.NewStyle().Bold(true).Underline(true).Padding(0, 1)
	inactive = lipgloss.NewStyle().Faint(true).Padding(0, 1)
)

type model struct {
	tabs    []string
	bodies  []string
	current int
}

func (m model) Init() tea.Cmd { return nil }

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	if k, ok := msg.(tea.KeyMsg); ok {
		switch k.String() {
		case "right", "l", "tab":
			m.current = (m.current + 1) % len(m.tabs)
		case "left", "h", "shift+tab":
			m.current = (m.current - 1 + len(m.tabs)) % len(m.tabs)
		case "q", "ctrl+c":
			return m, tea.Quit
		}
	}
	return m, nil
}

func (m model) View() string {
	var bar strings.Builder
	for i, t := range m.tabs {
		if i == m.current {
			bar.WriteString(active.Render(t))
		} else {
			bar.WriteString(inactive.Render(t))
		}
	}
	return fmt.Sprintf("%s\n\n%s\n\n(h/l or tab to switch, q to quit)", bar.String(), m.bodies[m.current])
}

func main() {
	_, _ = tea.NewProgram(model{
		tabs:   []string{"Logs", "Stats", "About"},
		bodies: []string{"live log feed", "metrics here", "about this tool"},
	}).Run()
}
```

Bubble Tea has no built-in tab widget — you compose the bar yourself with lipgloss. That's idiomatic; the framework expects you to own layout.

## Ratatui

```rust
use ratatui::layout::{Constraint, Direction, Layout};
use ratatui::style::{Modifier, Style};
use ratatui::text::Line;
use ratatui::widgets::{Block, Borders, Paragraph, Tabs};

fn render(f: &mut ratatui::Frame, current: usize) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(3), Constraint::Min(0)])
        .split(f.size());

    let titles: Vec<Line> = ["Logs", "Stats", "About"].iter().map(|t| Line::from(*t)).collect();
    let tabs = Tabs::new(titles)
        .select(current)
        .block(Block::default().borders(Borders::ALL))
        .highlight_style(Style::default().add_modifier(Modifier::BOLD | Modifier::UNDERLINED));
    f.render_widget(tabs, chunks[0]);

    let body = match current {
        0 => "live log feed",
        1 => "metrics here",
        _ => "about this tool",
    };
    f.render_widget(Paragraph::new(body).block(Block::default().borders(Borders::ALL)), chunks[1]);
}
```

Ratatui ships a `Tabs` widget; you supply the index and the highlight style. Pair with the `tokio::select!` event loop from the framework page.

## Cross-framework notes

- **Discoverability:** always show all tab labels at once; never hide them behind a menu. The whole point is parallel visibility.
- **Active indicator:** bold + underline is the most universally supported (no truecolor required). Color-only indicators fail on monochrome terminals.
- **Keyboard:** `Tab` / `Shift+Tab` for sequential, `1`–`9` for direct jump. Don't make users hunt.
- **Mouse:** every modern terminal supports mouse clicks on tabs — Textual handles it, Bubble Tea/Ratatui require you to handle `tea.MouseMsg` / `crossterm::event::MouseEvent`.

In Rich and Cursive, build tabs from `Columns` + `Panel` and `LinearLayout` + `Button` respectively — neither ships a dedicated tab primitive, but the building blocks are there.
