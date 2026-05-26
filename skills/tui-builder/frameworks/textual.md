# Textual (Python)

> Modern, async-first, batteries-included. The default pick for any non-trivial Python TUI.

- Repo: https://github.com/Textualize/textual
- Docs: https://textual.textualize.io
- License: MIT
- Status (May 2026): stable, actively developed
- Underlying renderer: [Rich](./rich.md)

## When to choose Textual

Pick Textual when **any one** of these is true:

- The team's primary language is Python.
- The TUI has more than one screen, or any kind of routing.
- The TUI does async I/O (network, subprocess, filesystem watch).
- You want CSS-like styling and don't want to invent a theming system.
- You need first-class mouse support, not as an afterthought.

Skip Textual if the surface is genuinely render-only (a static dashboard panel) — in that case [`rich`](./rich.md) is half the code and zero of the lifecycle.

## Install

```bash
python -m pip install --upgrade textual textual-dev
textual --version  # verify
```

Project scaffold:

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install textual textual-dev
mkdir -p src/myapp tests
touch src/myapp/__init__.py src/myapp/app.py
```

## Hello world

```python
# src/myapp/app.py
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static


class HelloApp(App):
    CSS = """
    Static {
        content-align: center middle;
        height: 100%;
    }
    """
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("[b]Hello, terminal.[/b]")
        yield Footer()


if __name__ == "__main__":
    HelloApp().run()
```

Run with `python -m myapp.app`. Resize the window; the text re-centers. Hit `q` to quit. Hit `?` and you see all bindings — Textual builds the help overlay for free.

## One production pattern — reactive state with declarative re-render

The reason to learn Textual is the **reactive attribute + watch + render** triple. State changes flow through declared attributes; the UI re-renders the dependents, not the world.

```python
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static
from textual.containers import Vertical


class Counter(Static):
    value: reactive[int] = reactive(0)

    def render(self) -> str:
        return f"[b]count:[/b] {self.value}"

    def watch_value(self, old: int, new: int) -> None:
        # Side-effects that follow state, not race with it.
        self.refresh()


class CounterApp(App):
    BINDINGS = [
        ("+", "inc", "Increment"),
        ("-", "dec", "Decrement"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(Counter(id="c"))
        yield Footer()

    def action_inc(self) -> None:
        self.query_one("#c", Counter).value += 1

    def action_dec(self) -> None:
        self.query_one("#c", Counter).value -= 1
```

What you get for free:

- `+` / `-` show up in the footer immediately (Textual reads `BINDINGS`).
- `render()` is only called when `value` actually changes.
- `watch_value` runs **after** the change, so logging or persistence is race-free.

## Gotchas

1. **Don't `print()` from inside the app.** Use `self.log()` or the textual devtools console (`textual console`, separate terminal).
2. **CSS is selector-scoped, not global.** Two widgets both named `Static` will share rules; use `id` or class selectors to disambiguate.
3. **The event loop is asyncio.** Long synchronous work blocks the UI — wrap in `await asyncio.to_thread(...)` or `run_worker`.
4. **`compose` yields once.** Don't expect it to be called on every state change. State drives existing widgets; structure drives layout.
5. **Terminal-emulator quirks.** Truecolor works in iTerm2, WezTerm, Kitty, Alacritty, modern Windows Terminal, and Termux. Older `xterm` builds may not — declare a fallback palette.

## Termux verdict

✅ Native. `pkg install python && pip install textual` works out of the box. Constraints: small screen → keep panels collapsible, avoid grids deeper than 2 levels. See [`../termux/compatibility-matrix.md`](../termux/compatibility-matrix.md).

## Useful primitives

- `App` / `Screen` — top-level lifecycle + routing
- `Widget` + `reactive` — state-driven render
- `Vertical` / `Horizontal` / `Grid` — layout
- `DataTable` — see [`../patterns/tables.md`](../patterns/tables.md)
- `Modal` — see [`../patterns/modals.md`](../patterns/modals.md)
- `TabbedContent` — see [`../patterns/tabs.md`](../patterns/tabs.md)
- `Worker` / `@work` — async tasks without blocking the UI
