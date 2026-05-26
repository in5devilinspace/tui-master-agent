# Pattern: Async events

> Long-running work — network calls, subprocesses, file watchers — must not block the render loop. Every TUI ships with at least one async path, even if it's just "load this list of items at startup."

## The universal shape

```
event loop  ───────────────────────────────────────────────▶
   │                  │                              │
   │ user presses /   │ background fetch ──▶ msg ───┤
   │ → enter filter   │                              │
   │   mode          ▼                              ▼
   │              update state                  update state
   │                  │                              │
   └─── render ──────▶│◀───── render ───────────────│
```

Three things are happening in parallel:

1. The render loop refreshes the screen at ~60 fps.
2. Input events arrive when the user presses keys.
3. Background work is in flight, eventually producing a state-changing message.

Each framework expresses this differently, but the contract is the same: **never block the render thread; deliver completion via a message**.

## Textual — `@work` + workers

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual import work
import httpx


class FetchApp(App):
    BINDINGS = [("r", "fetch", "Refresh"), ("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("press r to fetch", id="status")
        yield Footer()

    @work(exclusive=True)
    async def action_fetch(self) -> None:
        status = self.query_one("#status", Static)
        status.update("fetching…")
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("https://api.github.com")
            status.update(f"got {len(r.text)} bytes")
```

`@work` runs the action on a worker. `exclusive=True` cancels any in-flight invocation when a new one starts — exactly what you want for rapid `r` presses. UI never blocks.

## Bubble Tea — `tea.Cmd`

```go
package main

import (
	"fmt"
	"io"
	"net/http"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

type fetchOk struct{ size int }
type fetchErr struct{ err error }

func fetch() tea.Cmd {
	return func() tea.Msg {
		client := http.Client{Timeout: 5 * time.Second}
		r, err := client.Get("https://api.github.com")
		if err != nil { return fetchErr{err} }
		defer r.Body.Close()
		body, _ := io.ReadAll(r.Body)
		return fetchOk{size: len(body)}
	}
}

type model struct{ status string }

func (m model) Init() tea.Cmd { return nil }

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.String() == "r" {
			m.status = "fetching…"
			return m, fetch()
		}
		if msg.String() == "q" { return m, tea.Quit }
	case fetchOk:
		m.status = fmt.Sprintf("got %d bytes", msg.size)
	case fetchErr:
		m.status = "error: " + msg.err.Error()
	}
	return m, nil
}

func (m model) View() string { return m.status + "\n\n(r to fetch, q to quit)" }

func main() { _, _ = tea.NewProgram(model{status: "press r"}).Run() }
```

`tea.Cmd` runs the network call on its own goroutine. When it returns a `tea.Msg`, Bubble Tea queues the message and re-invokes `Update`. The model is never mutated from inside `fetch()`.

## Ratatui — channels + `tokio::select!`

Ratatui doesn't own the event loop — *you* do. The canonical pattern is `tokio::select!` between the input channel, the tick channel, and a worker-result channel.

```rust
use tokio::sync::mpsc;

enum Msg { Tick, Key(crossterm::event::KeyEvent), FetchOk(usize), FetchErr(String) }

#[tokio::main]
async fn main() -> std::io::Result<()> {
    let (tx, mut rx) = mpsc::unbounded_channel::<Msg>();
    spawn_input_thread(tx.clone());
    spawn_tick_loop(tx.clone());

    loop {
        match rx.recv().await {
            Some(Msg::Key(k)) if k.code == crossterm::event::KeyCode::Char('r') => {
                let tx2 = tx.clone();
                tokio::spawn(async move {
                    match reqwest::get("https://api.github.com").await {
                        Ok(r) => { let n = r.bytes().await.unwrap_or_default().len(); let _ = tx2.send(Msg::FetchOk(n)); }
                        Err(e) => { let _ = tx2.send(Msg::FetchErr(e.to_string())); }
                    }
                });
            }
            Some(Msg::Key(k)) if k.code == crossterm::event::KeyCode::Char('q') => break,
            // ... render + handle other msgs ...
            _ => {}
        }
    }
    Ok(())
}
```

This pattern scales to N workers and N message types without locking. Each worker `tokio::spawn`s, sends one message, exits.

## Cross-framework rules

1. **Never `time.sleep` / `time.Sleep` / `thread::sleep` in the render path.** Schedule a tick message instead.
2. **Cancel in-flight work on context change.** If the user moves to a different screen, the fetch for the old screen should be cancelled (Textual's `exclusive=True`, a `CancellationToken` in Rust, ctx-based cancellation in Go).
3. **Always show that something is happening.** A spinner, a "fetching…" string, a progress bar — silence after a key press feels like a freeze.
4. **Timeouts everywhere.** Set timeouts on HTTP calls (5s default), subprocess waits (30s default), file reads (no timeout but consider line-by-line streaming).
5. **Error states are first-class.** Treat `fetchErr` as a legitimate message variant, not an exception to swallow.

In Ink, use `useEffect` with a cleanup function; in Cursive, use `cb_sink` to post results back to the UI thread; in Rich (non-interactive), there's no event loop — just block synchronously.
