# Pattern: Tables

> Aligned columnar data with headers, optional sort, optional selection, optional scroll. The single most common TUI primitive after text.

## When to use

- The data is a list of records with the same shape.
- Users will scan vertically and want columns to line up.
- ≥3 rows. (For ≤2 rows, just print them — a table is over-engineering.)

## Textual

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable


class TablesApp(App):
    BINDINGS = [("q", "quit", "Quit"), ("s", "sort", "Sort by CPU")]

    rows = [
        (1042, "claude",  17.3),
        (1056, "codex",    9.1),
        (1071, "hermes",  22.8),
        (1099, "gemini",   3.4),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        t = self.query_one(DataTable)
        t.add_columns("PID", "Name", "CPU %")
        for r in self.rows:
            t.add_row(*[str(c) for c in r])
        t.cursor_type = "row"

    def action_sort(self) -> None:
        self.query_one(DataTable).sort("CPU %", reverse=True)
```

Textual's `DataTable` handles cursor, scroll, sort, keyboard nav, and resize. Don't roll your own.

## Bubble Tea

Use the [`bubbles/table`](https://github.com/charmbracelet/bubbles/tree/master/table) widget — same architecture as the rest of Bubble Tea, but it owns column widths and cursor.

```go
package main

import (
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/lipgloss"
)

type model struct{ t table.Model }

func (m model) Init() tea.Cmd { return nil }
func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch k := msg.(type) {
	case tea.KeyMsg:
		if k.String() == "q" { return m, tea.Quit }
	}
	var cmd tea.Cmd
	m.t, cmd = m.t.Update(msg)
	return m, cmd
}
func (m model) View() string {
	return lipgloss.NewStyle().Padding(1, 2).Render(m.t.View())
}

func main() {
	cols := []table.Column{
		{Title: "PID", Width: 6},
		{Title: "Name", Width: 12},
		{Title: "CPU %", Width: 8},
	}
	rows := []table.Row{
		{"1042", "claude", "17.3"},
		{"1056", "codex", "9.1"},
		{"1071", "hermes", "22.8"},
		{"1099", "gemini", "3.4"},
	}
	t := table.New(table.WithColumns(cols), table.WithRows(rows), table.WithFocused(true), table.WithHeight(8))
	_, _ = tea.NewProgram(model{t: t}).Run()
}
```

## Ratatui

```rust
use ratatui::layout::Constraint;
use ratatui::style::{Color, Modifier, Style};
use ratatui::widgets::{Block, Borders, Row, Table, TableState};

fn render(f: &mut ratatui::Frame, state: &mut TableState) {
    let header = Row::new(vec!["PID", "Name", "CPU %"])
        .style(Style::default().add_modifier(Modifier::BOLD));
    let rows = vec![
        Row::new(vec!["1042", "claude", "17.3"]),
        Row::new(vec!["1056", "codex",  "9.1"]),
        Row::new(vec!["1071", "hermes", "22.8"]),
        Row::new(vec!["1099", "gemini", "3.4"]),
    ];
    let widths = [Constraint::Length(6), Constraint::Length(12), Constraint::Length(8)];
    let table = Table::new(rows, widths)
        .header(header)
        .block(Block::default().borders(Borders::ALL).title(" processes "))
        .highlight_style(Style::default().bg(Color::DarkGray));
    f.render_stateful_widget(table, f.size(), state);
}
```

`TableState` lives in your app model and survives across draws — that's how you persist the row cursor in immediate-mode rendering.

## Cross-framework notes

- **Right-align numeric columns.** Universally. No exceptions.
- **Header row gets bold; selected row gets a background tint.** Don't use color alone for selection — fails on monochrome.
- **Truncate, don't wrap.** A table with wrapped cells stops being a table. If a value overflows, ellipsize (`abc…`) and reveal full on selection.
- **Sort indicators belong in the header.** `Name ↓` is universally understood. `Name (sorted desc)` is clutter.
- **Big tables = paginate or scroll, never both.** Pick one. Mixing them confuses the keyboard model.

In Rich, build static tables with `Table()`; for live updating, swap to Textual's `DataTable`. In Ink, use [`ink-table`](https://github.com/maticzav/ink-table); in Cursive, use `SelectView` for single-column or compose a `LinearLayout` of rows for multi-column.
