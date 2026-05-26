# Pattern: Modals

> A focused overlay layered above the main UI that captures input until dismissed. Used for confirmations, forms, full-screen pickers, and "are you sure?" prompts.

## When to use

- A workflow requires the user's full attention for ≤30 seconds (confirm delete, paste a token, choose from a long list).
- The result is a single value or yes/no, returned to the calling context.
- The main UI can pause without losing state.

Avoid modals for anything that takes longer than 30s — that's a new screen, not a popup.

## Textual

```python
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Vertical, Horizontal


class ConfirmQuit(ModalScreen[bool]):
    BINDINGS = [("escape", "dismiss", "Cancel"), ("y", "yes", "Yes"), ("n", "no", "No")]

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("[b]Really quit?[/]"),
            Horizontal(Button("Yes", id="yes", variant="error"), Button("No", id="no", variant="primary")),
            id="dialog",
        )

    def action_yes(self) -> None: self.dismiss(True)
    def action_no(self)  -> None: self.dismiss(False)
    def on_button_pressed(self, event: Button.Pressed) -> None: self.dismiss(event.button.id == "yes")


class App_(App):
    CSS = "#dialog { width: 40; padding: 1 2; border: thick $accent; background: $surface; }"
    BINDINGS = [("q", "ask_quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("press q to try to quit")
        yield Footer()

    async def action_ask_quit(self) -> None:
        if await self.push_screen_wait(ConfirmQuit()):
            self.exit()
```

`ModalScreen[T]` is generic in the return type. `push_screen_wait` returns the awaited result. Pattern works for any value, not just bools.

## Bubble Tea

```go
package main

import (
	"strings"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type confirmState int

const (
	stateMain confirmState = iota
	stateConfirm
)

type model struct {
	state    confirmState
	question string
}

func (m model) Init() tea.Cmd { return nil }

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	if k, ok := msg.(tea.KeyMsg); ok {
		switch m.state {
		case stateMain:
			if k.String() == "q" {
				m.state = stateConfirm
				m.question = "Really quit? (y/n)"
				return m, nil
			}
		case stateConfirm:
			switch k.String() {
			case "y":
				return m, tea.Quit
			case "n", "esc":
				m.state = stateMain
			}
		}
	}
	return m, nil
}

func (m model) View() string {
	body := "press q to try to quit"
	if m.state != stateConfirm {
		return body
	}
	dialog := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).Padding(1, 2).Render(m.question)
	return lipgloss.Place(80, 24, lipgloss.Center, lipgloss.Center,
		strings.Join([]string{body, dialog}, "\n\n"))
}

func main() { _, _ = tea.NewProgram(model{}).Run() }
```

Bubble Tea models modals as state machines — no separate window stack. `lipgloss.Place` centers the dialog in the viewport.

## Ratatui

```rust
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Style};
use ratatui::widgets::{Block, Borders, Clear, Paragraph};

fn render_modal(f: &mut ratatui::Frame, area: Rect, question: &str) {
    let block = Block::default()
        .title(" Confirm ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::Yellow));
    let para = Paragraph::new(question).alignment(Alignment::Center).block(block);
    let dialog_area = centered_rect(40, 20, area);
    f.render_widget(Clear, dialog_area); // CRITICAL: erase what's under the modal
    f.render_widget(para, dialog_area);
}

fn centered_rect(pct_x: u16, pct_y: u16, r: Rect) -> Rect {
    let v = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - pct_y) / 2),
            Constraint::Percentage(pct_y),
            Constraint::Percentage((100 - pct_y) / 2),
        ])
        .split(r);
    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - pct_x) / 2),
            Constraint::Percentage(pct_x),
            Constraint::Percentage((100 - pct_x) / 2),
        ])
        .split(v[1])[1]
}
```

The `Clear` widget is critical — Ratatui is immediate-mode, so without it the modal renders *on top of* the background characters rather than replacing them.

## Cross-framework notes

- **Always erase the background.** Textual handles it; Bubble Tea via `lipgloss.Place`; Ratatui via `Clear`. Skip it once, regret it forever.
- **Escape always dismisses.** This is non-negotiable for muscle-memory consistency.
- **Default focus on the safer option.** "No / Cancel" should be the highlighted button when the action is destructive.
- **Width caps.** Don't let modals fill the screen — a 40-column dialog inside an 80-column terminal is the sweet spot.
- **Don't stack modals.** If a modal needs to spawn another modal, you're building a wizard. Wizards are a separate screen, not a stack of overlays.

In Ink, model the modal as a conditional sub-tree rendered above the main `<Box>` with `position: absolute` style props. In Cursive, use `add_layer(Dialog::around(...))` — the layer stack does the modal semantics for free.
