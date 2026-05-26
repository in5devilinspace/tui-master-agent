# Ratatui (Rust)

> Immediate-mode TUI framework for Rust. The default pick when the TUI is performance-critical or the team is Rust-shop.

- Repo: https://github.com/ratatui-org/ratatui
- License: MIT
- Status (May 2026): mature, post-tui-rs renaming (since 2023), active monthly releases
- Backends: `crossterm` (default, cross-platform), `termion`, `termwiz`

## When to choose Ratatui

Pick Ratatui when **any one** of these is true:

- The team writes Rust.
- You're embedding a TUI inside an existing Rust application (where reaching for Go or Python would add a runtime).
- You need 60 fps rendering (visualizers, monitors, real-time data).
- You want one static binary distributable.

Skip Ratatui if the project is one-off and the team isn't already Rust-fluent — the ergonomic overhead doesn't pay back at small scale.

## Install

```bash
cargo new myapp && cd myapp
cargo add ratatui crossterm
```

`Cargo.toml` snippet (the defaults Ratatui picks are usually right):

```toml
[dependencies]
ratatui = "0.27"
crossterm = "0.27"
```

## Hello world

```rust
use std::io;

use crossterm::event::{self, Event, KeyCode};
use crossterm::terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen};
use crossterm::ExecutableCommand;
use ratatui::backend::CrosstermBackend;
use ratatui::widgets::{Block, Borders, Paragraph};
use ratatui::Terminal;

fn main() -> io::Result<()> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    stdout.execute(EnterAlternateScreen)?;
    let mut term = Terminal::new(CrosstermBackend::new(stdout))?;

    loop {
        term.draw(|f| {
            let block = Block::default().title("hello").borders(Borders::ALL);
            let para = Paragraph::new("Hello, terminal.\n(press q to quit)").block(block);
            f.render_widget(para, f.size());
        })?;

        if let Event::Key(key) = event::read()? {
            if key.code == KeyCode::Char('q') {
                break;
            }
        }
    }

    disable_raw_mode()?;
    term.backend_mut().execute(LeaveAlternateScreen)?;
    Ok(())
}
```

Note the lifecycle: enable raw mode → enter alt screen → loop → leave alt screen → disable raw mode. Ratatui is **immediate-mode** — you redraw everything each frame. There is no widget tree to retain.

## One production pattern — frame budget with `tokio::select!`

Real Ratatui apps drive rendering from an event loop that selects between input events, tick events, and async messages. This is the Rust analog of [Bubble Tea's `Cmd`](./bubbletea.md).

```rust
use std::time::Duration;

use crossterm::event::{self, Event, KeyCode};
use ratatui::widgets::{Block, Borders, Paragraph};
use tokio::time::{interval, MissedTickBehavior};

#[derive(Default)]
struct App { ticks: u64 }

#[tokio::main]
async fn main() -> std::io::Result<()> {
    // (raw mode / alt screen / Terminal setup omitted for brevity — see hello world)
    let mut term = setup_terminal()?;
    let mut app = App::default();
    let mut tick = interval(Duration::from_millis(250));
    tick.set_missed_tick_behavior(MissedTickBehavior::Skip);
    let (key_tx, mut key_rx) = tokio::sync::mpsc::unbounded_channel();
    std::thread::spawn(move || loop {
        if let Ok(Event::Key(k)) = event::read() { let _ = key_tx.send(k); }
    });

    loop {
        tokio::select! {
            _ = tick.tick() => { app.ticks += 1; }
            Some(key) = key_rx.recv() => {
                if key.code == KeyCode::Char('q') { break; }
            }
        }

        term.draw(|f| {
            let para = Paragraph::new(format!("ticks: {}\n(press q to quit)", app.ticks))
                .block(Block::default().borders(Borders::ALL));
            f.render_widget(para, f.size());
        })?;
    }
    teardown_terminal(term)?;
    Ok(())
}
```

This separates concerns: ticks bump state, keys mutate state, the draw call reads state. No locking, no shared mutability across threads.

## Gotchas

1. **Immediate-mode means you redraw the world.** Don't try to "update one widget" — re-render the frame. State diffs are *your* job, not the framework's.
2. **Raw mode + alt screen are stateful at the OS level.** If your app panics without `disable_raw_mode`, the terminal is wrecked. Wrap setup/teardown in RAII or a `Drop` guard.
3. **`event::read()` blocks the thread.** Move it to a thread or use `event::poll(Duration)` for non-blocking checks.
4. **Borrow checker on widgets.** Some widgets (like `Table`) hold borrows on their input — bind them to a `let` before passing to `f.render_widget`.
5. **Don't mix `crossterm` and `termion` backends in the same app.** Pick one.

## Termux verdict

⚠️ Cross-compile from a desktop. Rust toolchain on Termux is heavy and slow; use `cargo zigbuild` or the Android NDK toolchain to produce a `arm64-android` binary, then `scp`/`adb push` into Termux. See [`../termux/conversion-recipes.md`](../termux/conversion-recipes.md).

## Useful primitives

- `Terminal<Backend>` — owns the screen
- `Frame` — given to your closure, you render into it
- `Widget` trait — implement to define custom rendering
- `Layout` + `Constraint` — split a `Rect` into sub-rects
- `Block`, `Paragraph`, `List`, `Table`, `Chart`, `Gauge` — built-in widgets
- [`crossterm::event`](https://docs.rs/crossterm/) — key + mouse input
