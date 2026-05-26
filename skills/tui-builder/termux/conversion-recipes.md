# Termux conversion recipes

> Concrete steps the Termux Converter sub-agent applies to take a generated TUI and ship a Termux-friendly sibling. One recipe per axis × framework combination. Recipes are not exhaustive — they're the high-leverage 80%.

---

## Recipe 1 — Truecolor fallback

**Applies to:** every framework.

Detect color depth at startup; pick a palette that works either way.

### Python (Textual / Rich)

```python
import os
TRUECOLOR = os.environ.get("COLORTERM", "") in ("truecolor", "24bit")
PALETTE = {
    "accent":   "#7c3aed" if TRUECOLOR else "magenta",
    "warning":  "#facc15" if TRUECOLOR else "yellow",
    "danger":   "#ef4444" if TRUECOLOR else "red",
    "muted":    "#94a3b8" if TRUECOLOR else "bright_black",
}
```

### Go (Bubble Tea / lipgloss)

```go
import "github.com/charmbracelet/lipgloss"
var profile = lipgloss.ColorProfile()  // auto-detects truecolor / 256 / 16 / mono
var accent = lipgloss.NewStyle().Foreground(lipgloss.Color("#7c3aed"))
// lipgloss downgrades automatically based on profile — no extra work needed.
```

### Rust (Ratatui)

```rust
fn accent() -> ratatui::style::Color {
    if std::env::var("COLORTERM").map(|v| v == "truecolor" || v == "24bit").unwrap_or(false) {
        ratatui::style::Color::Rgb(0x7c, 0x3a, 0xed)
    } else {
        ratatui::style::Color::Magenta
    }
}
```

---

## Recipe 2 — Chord → single key remap

**Applies to:** Textual, Bubble Tea, Ratatui, Ink, Cursive.

Termux's soft keyboard makes chords expensive. Replace `g g` (top), `Ctrl+X` (action), etc., with discoverable single keys plus a `?` help overlay.

| Desktop binding | Termux binding | Rationale |
|---|---|---|
| `g g` (top)    | `t`            | Single tap; documented in `?` |
| `Shift+G`      | `b` (bottom)   | Lowercase pairs with `t`     |
| `Ctrl+R`       | `r`            | Same letter, no modifier     |
| `Ctrl+F`       | `/` (filter)   | Slash is universal           |
| `Ctrl+S` (save)| `s`            | No risk: TTY flow-control irrelevant when no terminal echo conflict |
| `Ctrl+Q` (quit)| `q`            | Same                         |
| `?`            | `?`            | Always preserved             |

The Termux Converter looks for chord patterns in the source TUI's bindings file (Textual `BINDINGS`, Bubble Tea `keyMap` struct, Ratatui `Binding` table) and rewrites them per this map, leaving a `# original: ctrl+r` comment so the change is reviewable.

---

## Recipe 3 — Drop ncurses, prefer crossterm

**Applies to:** Cursive (Rust), any C-extension Python lib (rare in scope).

```toml
# Cargo.toml — REMOVE
cursive = "0.21"

# Cargo.toml — ADD
cursive = { version = "0.21", default-features = false, features = ["crossterm-backend"] }
```

For Python: if a transitive dep needs `_curses` (very rare in the chosen frameworks), surface it as a Termux blocker in `TERMUX.md` and recommend the user swap libraries.

---

## Recipe 4 — Cross-compile Go binaries for Android

**Applies to:** Bubble Tea TUIs.

From a Linux or macOS desktop:

```bash
# arm64 Android
CGO_ENABLED=0 GOOS=android GOARCH=arm64 \
  go build -ldflags="-s -w" -o myapp-android-arm64 .

# arm (32-bit, older phones)
CGO_ENABLED=0 GOOS=android GOARCH=arm \
  go build -ldflags="-s -w" -o myapp-android-arm .

# transfer
scp myapp-android-arm64 phone:/data/data/com.termux/files/home/
# or
adb push myapp-android-arm64 /sdcard/Download/   # then move in Termux
```

In Termux: `chmod +x ./myapp-android-arm64 && ./myapp-android-arm64`. CGO must be off — the Android NDK toolchain is not present in Termux by default.

---

## Recipe 5 — Cross-compile Rust binaries for Android

**Applies to:** Ratatui, Cursive (with `crossterm-backend`).

Use `cargo zigbuild` (easier) or `cargo-ndk` (canonical).

### cargo zigbuild

```bash
cargo install cargo-zigbuild
rustup target add aarch64-linux-android
cargo zigbuild --target aarch64-linux-android --release
# binary at: target/aarch64-linux-android/release/myapp
```

### cargo-ndk

```bash
cargo install cargo-ndk
rustup target add aarch64-linux-android
# Requires Android NDK installed on the desktop side
cargo ndk -t arm64-v8a build --release
```

Transfer + chmod + run as in Recipe 4.

---

## Recipe 6 — Pin Node.js + ts-node for Ink

**Applies to:** Ink TUIs.

```bash
# in Termux
pkg install nodejs
node -v                                  # verify ≥ 20.x
npm install -g <package-name>
# OR ship a bundled binary via ncc / pkg / bun compile
```

`bun compile` (if your Ink app is bun-friendly) produces a single static-ish binary similar to Go/Rust — preferable when the target is "tap to launch" rather than "developer with `node` already installed."

---

## Recipe 7 — Replace `xdg-open` / `open` with `termux-open`

**Applies to:** any framework with "open URL" or "open file" actions.

```python
import shutil, subprocess
opener = shutil.which("termux-open-url") or shutil.which("xdg-open") or shutil.which("open")
subprocess.run([opener, url], check=False)
```

`termux-open-url` and `termux-open` come from the Termux:API package: `pkg install termux-api`.

---

## Recipe 8 — Layout for portrait 50×20

**Applies to:** every framework with multi-region layouts.

The Termux variant should add a layout breakpoint when `cols < 60` *or* `rows < 24`:

- Collapse horizontal grids to vertical stacks.
- Drop tertiary panels (footer hints, sidebar previews); promote them to the `?` overlay.
- Reduce padding (`Padding(0, 1)` instead of `Padding(1, 2)`).

```python
# Textual reactive layout
class App_(App):
    def on_resize(self, event: events.Resize) -> None:
        cls = "compact" if event.size.width < 60 or event.size.height < 24 else "regular"
        self.add_class(cls)
```

```css
.compact #sidebar { display: none; }
.compact #footer  { height: 1; }
```

---

## Recipe 9 — Smoke test under Termux's `python` / `node` / Go binary

**Applies to:** every framework.

Add a small smoke test that runs the app for 1 second with a tear-down hook to confirm startup works on Android. The Termux Converter adds a CI job that runs in a `termux-docker` image (or a self-hosted runner) so the variant doesn't drift from passing.

---

## Recipe 10 — Document changes in `TERMUX.md`

**Applies to:** every converted TUI.

Every recipe applied gets one entry in the generated `TERMUX.md`:

```markdown
# Termux variant — change log

- **Chord remap.** `g g` → `t`, `Shift+G` → `b`, `Ctrl+R` → `r`. See bindings table.
- **Truecolor fallback.** Palette downgraded to 16-color when `COLORTERM` is not `truecolor`.
- **Native dep dropped.** Replaced `cursive` default backend with `crossterm-backend`.
- **Cross-compile.** Build via `cargo zigbuild --target aarch64-linux-android --release`.
- **Help overlay added.** `?` opens a binding cheatsheet (was absent in desktop variant).
- **Layout breakpoint at 60×24.** Sidebar hides; padding shrinks; footer compacts.
```

The point: a human reviewing the Termux variant can audit *exactly* what was changed and why, in one file.
