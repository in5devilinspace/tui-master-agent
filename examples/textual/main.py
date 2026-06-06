"""
Pixel Pond - A small interactive TUI built with Textual.

A tranquil pond where you can drop pebbles (click) to create ripples,
feed the fish (press F), toggle day/night (D), and watch lilies bloom (L).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from rich.segment import Segment
from rich.style import Style

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.geometry import Size
from textual.reactive import reactive
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Footer, Header, Static


@dataclass
class Ripple:
    x: int
    y: int
    age: int = 0
    max_age: int = 12


@dataclass
class Fish:
    x: float
    y: float
    vx: float
    vy: float
    color: str
    glyph: str = "°⡤─"
    target: tuple[float, float] | None = None


@dataclass
class Lily:
    x: int
    y: int
    bloom: int = 0  # 0..3


@dataclass
class Food:
    x: float
    y: float
    life: int = 80


class Pond(Widget, can_focus=True):
    """The pond surface where everything happens."""

    DEFAULT_CSS = """
    Pond {
        width: 1fr;
        height: 1fr;
        border: round $primary;
    }
    """

    night: reactive[bool] = reactive(False)
    fish_count: reactive[int] = reactive(0)
    ripple_count: reactive[int] = reactive(0)
    lily_count: reactive[int] = reactive(0)

    def __init__(self) -> None:
        super().__init__()
        self.ripples: list[Ripple] = []
        self.fishes: list[Fish] = []
        self.lilies: list[Lily] = []
        self.foods: list[Food] = []
        self.tick = 0
        self._cached_size: Size = Size(0, 0)

    def on_mount(self) -> None:
        self.set_interval(1 / 15, self.advance)
        # Seed with some fish and lilies
        for _ in range(4):
            self._spawn_fish()
        self.focus()

    def _spawn_fish(self) -> None:
        w = max(self.size.width - 2, 10)
        h = max(self.size.height - 2, 5)
        colors = ["#ff8c42", "#ffd166", "#ef476f", "#06d6a0", "#118ab2"]
        f = Fish(
            x=random.uniform(2, w - 2),
            y=random.uniform(2, h - 2),
            vx=random.choice([-0.6, -0.4, 0.4, 0.6]),
            vy=random.uniform(-0.15, 0.15),
            color=random.choice(colors),
        )
        self.fishes.append(f)
        self.fish_count = len(self.fishes)

    def add_lily(self) -> None:
        w = max(self.size.width - 4, 5)
        h = max(self.size.height - 4, 3)
        self.lilies.append(
            Lily(x=random.randint(2, w), y=random.randint(2, h))
        )
        self.lily_count = len(self.lilies)

    def feed(self) -> None:
        w = max(self.size.width - 2, 5)
        h = max(self.size.height - 2, 3)
        for _ in range(3):
            self.foods.append(
                Food(
                    x=random.uniform(2, w - 2),
                    y=random.uniform(2, h - 2),
                )
            )

    def clear_pond(self) -> None:
        self.ripples.clear()
        self.foods.clear()
        self.lilies.clear()
        self.lily_count = 0
        self.ripple_count = 0

    def advance(self) -> None:
        self.tick += 1
        # Age ripples
        for r in self.ripples:
            r.age += 1
        self.ripples = [r for r in self.ripples if r.age < r.max_age]
        self.ripple_count = len(self.ripples)

        # Age food
        for f in self.foods:
            f.life -= 1
            f.y += 0.05  # sinks slowly
        self.foods = [f for f in self.foods if f.life > 0]

        w = max(self.size.width - 2, 10)
        h = max(self.size.height - 2, 5)

        # Move fish
        for fish in self.fishes:
            # Seek nearest food
            if self.foods:
                nearest = min(
                    self.foods,
                    key=lambda f: (f.x - fish.x) ** 2 + (f.y - fish.y) ** 2,
                )
                dx = nearest.x - fish.x
                dy = nearest.y - fish.y
                dist = (dx * dx + dy * dy) ** 0.5 or 1.0
                fish.vx = 0.6 * dx / dist
                fish.vy = 0.3 * dy / dist
                if dist < 1.2:
                    self.foods.remove(nearest)
            else:
                # Wander
                if random.random() < 0.05:
                    fish.vy += random.uniform(-0.2, 0.2)
                fish.vy = max(-0.3, min(0.3, fish.vy))

            fish.x += fish.vx
            fish.y += fish.vy

            # Bounce off walls
            if fish.x <= 1:
                fish.x = 1
                fish.vx = abs(fish.vx)
            elif fish.x >= w:
                fish.x = w
                fish.vx = -abs(fish.vx)
            if fish.y <= 1:
                fish.y = 1
                fish.vy = abs(fish.vy)
            elif fish.y >= h:
                fish.y = h
                fish.vy = -abs(fish.vy)

            fish.glyph = "─⡤°" if fish.vx < 0 else "°⡤─"

        # Slowly bloom lilies
        if self.tick % 20 == 0:
            for lily in self.lilies:
                if lily.bloom < 3:
                    lily.bloom += 1

        self.refresh()

    def on_click(self, event) -> None:
        # Drop a pebble -> ripple, and scatter fish briefly
        x = event.x
        y = event.y
        self.ripples.append(Ripple(x=x, y=y))
        for fish in self.fishes:
            dx = fish.x - x
            dy = fish.y - y
            d = (dx * dx + dy * dy) ** 0.5 or 1.0
            fish.vx += 0.8 * dx / d
            fish.vy += 0.4 * dy / d

    def _water_color(self, x: int, y: int) -> str:
        if self.night:
            base = 18
            shimmer = (x * 3 + y * 5 + self.tick) % 11
            r = 8 + shimmer // 3
            g = 18 + shimmer // 2
            b = 48 + shimmer
            return f"#{r:02x}{g:02x}{b:02x}"
        else:
            shimmer = (x * 3 + y * 5 + self.tick) % 11
            r = 60 + shimmer * 2
            g = 130 + shimmer * 3
            b = 180 + shimmer * 4
            return f"#{r:02x}{min(g,255):02x}{min(b,255):02x}"

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if width == 0:
            return Strip.blank(0)

        # Build a row of characters and styles
        chars: list[str] = [" "] * width
        fgs: list[str | None] = [None] * width

        # Ripples
        for r in self.ripples:
            radius = r.age
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    # Approximate circle
                    if abs(dx * dx + dy * dy - radius * radius) <= radius:
                        px, py = r.x + dx, r.y + dy
                        if py == y and 0 <= px < width:
                            fade = 1.0 - (r.age / r.max_age)
                            if fade > 0.6:
                                chars[px] = "○"
                            elif fade > 0.3:
                                chars[px] = "·"
                            else:
                                chars[px] = "˙"
                            fgs[px] = "#e0f7ff" if not self.night else "#a0c8ff"

        # Lilies
        for lily in self.lilies:
            if lily.y == y and 0 <= lily.x < width:
                if lily.bloom >= 3:
                    chars[lily.x] = "✿"
                    fgs[lily.x] = "#ffb3d9"
                elif lily.bloom == 2:
                    chars[lily.x] = "❀"
                    fgs[lily.x] = "#ff80bf"
                else:
                    chars[lily.x] = "●"
                    fgs[lily.x] = "#2e7d32"
            # Lily pad next to flower
            pad_x = lily.x + 1
            if lily.y == y and 0 <= pad_x < width and chars[pad_x] == " ":
                chars[pad_x] = "◡"
                fgs[pad_x] = "#2e7d32"

        # Food
        for f in self.foods:
            fx, fy = int(f.x), int(f.y)
            if fy == y and 0 <= fx < width:
                chars[fx] = "•"
                fgs[fx] = "#fff59d"

        # Fish
        for fish in self.fishes:
            fy = int(fish.y)
            fx = int(fish.x)
            if fy == y:
                glyph = fish.glyph
                for i, ch in enumerate(glyph):
                    px = fx + i - 1
                    if 0 <= px < width:
                        chars[px] = ch
                        fgs[px] = fish.color

        # Build segments
        segments = []
        bg = "#0a1530" if self.night else "#1f5fa8"
        # Group adjacent cells by style for efficiency
        i = 0
        while i < width:
            j = i
            cur_fg = fgs[i] if fgs[i] else self._water_color(i, y)
            run = []
            while j < width:
                next_fg = fgs[j] if fgs[j] else self._water_color(j, y)
                if next_fg != cur_fg:
                    break
                run.append(chars[j])
                j += 1
            style = Style(color=cur_fg, bgcolor=bg)
            segments.append(Segment("".join(run), style))
            i = j

        return Strip(segments, width)


class StatusBar(Static):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $boost;
        color: $text;
        padding: 0 1;
    }
    """


class PixelPondApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    #main {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("f", "feed", "Feed fish"),
        Binding("l", "lily", "Add lily"),
        Binding("n", "new_fish", "New fish"),
        Binding("d", "toggle_day", "Day/Night"),
        Binding("c", "clear", "Clear"),
        Binding("q", "quit", "Quit"),
    ]

    TITLE = "Pixel Pond"
    SUB_TITLE = "click the water to drop a pebble"

    def compose(self) -> ComposeResult:
        yield Header()
        self.pond = Pond()
        yield self.pond
        self.status = StatusBar("Welcome to Pixel Pond.")
        yield self.status
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(0.5, self._update_status)

    def _update_status(self) -> None:
        phase = "🌙 night" if self.pond.night else "☀️  day"
        self.status.update(
            f"{phase}  |  fish: {self.pond.fish_count}  "
            f"lilies: {self.pond.lily_count}  ripples: {self.pond.ripple_count}"
        )

    def action_feed(self) -> None:
        self.pond.feed()

    def action_lily(self) -> None:
        self.pond.add_lily()

    def action_new_fish(self) -> None:
        self.pond._spawn_fish()

    def action_toggle_day(self) -> None:
        self.pond.night = not self.pond.night

    def action_clear(self) -> None:
        self.pond.clear_pond()


if __name__ == "__main__":
    PixelPondApp().run()
