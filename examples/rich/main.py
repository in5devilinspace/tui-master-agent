"""Mission Control TUI built with Rich.

Renders a live-updating fictional space mission dashboard using Layout,
Live, Progress, Panel, Table, and Syntax components from the rich library.
Runs for a fixed number of frames so it terminates cleanly in any env.
"""

from __future__ import annotations

import math
import random
from collections import deque
from datetime import datetime
from time import sleep

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

CONSOLE = Console()

MISSION_NAME = "ARTEMIS-RC / Flight 7"
EVENTS = [
    "Stage 1 ignition nominal",
    "Throttle up to 104%",
    "Max-Q passed",
    "MECO confirmed",
    "Stage separation",
    "Fairing jettison",
    "SECO-1 nominal",
    "Orbit insertion burn",
    "Solar arrays deployed",
    "Telemetry lock acquired",
    "Ground station handoff: Canberra",
    "Thermal control nominal",
]

COUNTDOWN_CODE = '''\
def countdown(seconds: int) -> None:
    """Simulate a launch countdown loop."""
    for t in range(seconds, 0, -1):
        broadcast(f"T-minus {t}")
        if t == 10:
            arm_autosequence()
        if t == 3:
            ignite_engines()
    broadcast("Liftoff!")
    release_clamps()
'''


def make_layout() -> Layout:
    layout = Layout(name="root")
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=8),
    )
    layout["body"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="center", ratio=2),
        Layout(name="right", ratio=1),
    )
    layout["left"].split_column(
        Layout(name="telemetry"),
        Layout(name="systems"),
    )
    return layout


def render_header(frame: int) -> Panel:
    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="center", ratio=1)
    grid.add_column(justify="right", ratio=1)
    status = "[bold green]NOMINAL[/]" if frame % 17 != 0 else "[bold yellow]CAUTION[/]"
    grid.add_row(
        f"[b cyan]{MISSION_NAME}[/]",
        f"Status: {status}",
        datetime.now().strftime("%H:%M:%S UTC"),
    )
    return Panel(grid, style="white on dark_blue", border_style="bright_blue")


def render_telemetry(frame: int) -> Panel:
    t = frame / 6.0
    altitude = max(0.0, 120.0 * (1 - math.exp(-t / 8)))
    velocity = 7.8 * (1 - math.exp(-t / 10))
    fuel = max(0.0, 100.0 - frame * 1.4)
    g_force = 1.0 + 2.2 * math.exp(-((t - 6) ** 2) / 18)

    progress = Progress(
        TextColumn("[b]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("{task.fields[value]}"),
        expand=True,
    )
    progress.add_task("Altitude", total=120, completed=altitude,
                      value=f"{altitude:6.2f} km")
    progress.add_task("Velocity", total=8, completed=velocity,
                      value=f"{velocity:5.2f} km/s")
    progress.add_task("Fuel    ", total=100, completed=fuel,
                      value=f"{fuel:5.1f} %")
    progress.add_task("G-force ", total=4, completed=g_force,
                      value=f"{g_force:4.2f} g")
    return Panel(progress, title="[b]Telemetry", border_style="green")


def render_systems(frame: int) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, expand=True, show_header=True,
                  header_style="bold magenta")
    table.add_column("System")
    table.add_column("State", justify="right")
    rng = random.Random(frame // 3)
    systems = [
        ("Guidance", "OK"),
        ("Avionics", "OK"),
        ("Comms", rng.choice(["OK", "OK", "LAG"])),
        ("Life Support", "OK"),
        ("Thermal", rng.choice(["OK", "OK", "WARM"])),
        ("Power", "OK"),
    ]
    for name, state in systems:
        color = {"OK": "green", "LAG": "yellow", "WARM": "yellow"}.get(state, "red")
        table.add_row(name, f"[{color}]{state}[/]")
    return Panel(table, title="[b]Subsystems", border_style="cyan")


def render_starfield(frame: int, width: int = 50, height: int = 14) -> Panel:
    rng = random.Random(42)
    stars = [(rng.randint(0, 9999), rng.randint(0, 9999), rng.choice("·.*+"))
             for _ in range(120)]
    rows = []
    for y in range(height):
        chars = [" "] * width
        for sx, sy, ch in stars:
            x = (sx + frame) % width
            yy = sy % height
            if yy == y:
                chars[x] = ch
        rows.append("".join(chars))
    text = Text("\n".join(rows), style="bright_white on black")
    # draw a small rocket marker
    return Panel(Align.center(text), title="[b]View Port",
                 border_style="bright_magenta")


def render_center(frame: int) -> Panel:
    syntax = Syntax(COUNTDOWN_CODE, "python", line_numbers=True,
                    theme="monokai", indent_guides=True)
    star = render_starfield(frame)
    group = Group(star, Panel(syntax, title="[b]Flight Software",
                              border_style="yellow"))
    return Panel(group, border_style="blue", title="[b]Mission View")


def render_log(log: deque) -> Panel:
    table = Table.grid(expand=True)
    table.add_column()
    for entry in log:
        table.add_row(entry)
    return Panel(table, title="[b]Event Log", border_style="red")


def main() -> None:
    layout = make_layout()
    log: deque = deque(maxlen=6)
    log.append("[dim]00:00[/] Mission control online")

    frames = 40
    with Live(layout, console=CONSOLE, refresh_per_second=8, screen=False):
        for frame in range(frames):
            if frame % 4 == 0:
                evt = EVENTS[(frame // 4) % len(EVENTS)]
                stamp = datetime.now().strftime("%M:%S")
                log.append(f"[dim]{stamp}[/] [green]>[/] {evt}")

            layout["header"].update(render_header(frame))
            layout["telemetry"].update(render_telemetry(frame))
            layout["systems"].update(render_systems(frame))
            layout["center"].update(render_center(frame))
            layout["right"].update(render_log(log))
            layout["footer"].update(
                Panel(
                    Align.center(
                        Text(
                            "ARTEMIS-RC  |  press Ctrl-C to abort  |  frame "
                            f"{frame + 1}/{frames}",
                            style="bold white",
                        )
                    ),
                    border_style="bright_blue",
                    style="on grey15",
                )
            )
            sleep(0.12)

    CONSOLE.print("[bold green]Mission complete. Splashdown nominal.[/]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        CONSOLE.print("[bold red]Mission aborted by operator.[/]")
