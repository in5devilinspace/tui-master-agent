# Rich (Python)

> Render-only library for stunning terminal output. The default pick when the surface is non-interactive — dashboards, reports, progress bars, syntax-highlighted dumps.

- Repo: https://github.com/Textualize/rich
- License: MIT
- Status (May 2026): stable, post-3.0, the base renderer underneath [Textual](./textual.md)

## When to choose Rich

Pick Rich when **all** of these are true:

- The output is **not interactive** — no key handling, no focus.
- You want it to look great with effectively zero ceremony.
- The surface is one screen or a scrolling log, not a router-shaped app.

If the user can press a key and the app reacts, you want Textual or one of the others. Rich is the renderer; Textual is the app shell.

## Install

```bash
python -m pip install --upgrade rich
python -m rich  # demo
```

## Hello world

```python
from rich import print
print("[b magenta]Hello, terminal.[/]  [dim](this is rich)[/]")
```

That's it. One line. Reflows on resize. Truecolor where available, gracefully degrades elsewhere.

## One production pattern — Live dashboard

The single highest-leverage Rich pattern is `Live` — a context manager that mutably refreshes a renderable in place. Layout splits the screen, panels fill it, your loop updates the panels, Rich diffs and redraws.

```python
import time, random
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

console = Console()
layout = Layout()
layout.split_column(
    Layout(name="header", size=3),
    Layout(name="body", ratio=1),
    Layout(name="footer", size=5),
)
layout["body"].split_row(Layout(name="left"), Layout(name="right"))


def render_header() -> Panel:
    return Panel("[b]process monitor[/]  ·  q to quit", style="cyan")


def render_table() -> Table:
    t = Table(title="Top processes", expand=True)
    t.add_column("PID"); t.add_column("Name"); t.add_column("CPU %")
    for i in range(8):
        t.add_row(str(1000 + i), f"proc-{i}", f"{random.uniform(0, 100):.1f}")
    return t


def render_progress() -> Progress:
    p = Progress(SpinnerColumn(), TextColumn("[bold]{task.description}"), BarColumn())
    p.add_task("downloading", total=100, completed=random.randint(0, 100))
    p.add_task("indexing",    total=100, completed=random.randint(0, 100))
    return p


with Live(layout, console=console, refresh_per_second=4, screen=True):
    while True:
        layout["header"].update(render_header())
        layout["left"].update(render_table())
        layout["right"].update(Panel(render_progress(), title="jobs"))
        layout["footer"].update(Panel("CPU avg: …  ·  mem: …  ·  net: …", style="dim"))
        time.sleep(0.25)
```

That's a complete monitor: 3 regions, a live table, a progress panel. ~40 lines.

## Gotchas

1. **Rich is not interactive.** No key bindings, no focus, no mouse routing. If you need any of those, stop and pick Textual.
2. **`Live` plays badly with `print()`.** Anything you write outside `Live`'s context will trash the rendering. Use `Live.console.print(...)` or queue lines through a panel.
3. **Markup is bracket-based, not Markdown.** `[b]bold[/]`, `[red]red[/]`, `[link=https://...]label[/link]`. Don't try to use `**bold**` — Rich's `Markdown` renderable handles that, but inline `print()` doesn't.
4. **Tables auto-size by terminal width.** That's usually what you want, but for fixed-width reports pass `width=...` explicitly.
5. **Logging integration is its own opinion.** `from rich.logging import RichHandler` — great for ad-hoc CLIs, sometimes overkill in production where structured logs win.

## Termux verdict

✅ Native. `pkg install python && pip install rich` works out of the box. Pure Python. No native deps. Excellent fit for Android terminal dashboards.

## Useful primitives

- `print` / `console.print` — the entry point
- `Table`, `Tree`, `Syntax`, `Markdown`, `Panel`, `Columns` — renderables
- `Layout` — split the screen into regions
- `Live` — mutate a layout in place over time
- `Progress` — bars, spinners, multi-task
- `Console` — the renderer; supports recording (`record=True`, then `export_svg`)
