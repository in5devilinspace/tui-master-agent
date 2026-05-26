# Termux compatibility matrix

> Termux is the Android terminal-emulator-plus-package-manager that hosts a near-complete Linux userland in a normal Android app. Anything we generate should run there — but the constraints are real. Below: framework × axis, with a single-cell verdict and a footnote when it's complicated.

Legend:

- ✅ — works out of the box, no recipe needed
- ⚠️ — works with a documented recipe (see [`./conversion-recipes.md`](./conversion-recipes.md))
- ❌ — not feasible at v1 (don't ship a Termux variant)
- 📱 — special Termux-only consideration

## The matrix

| Framework  | Install on Termux | Run on Termux | Render quality | Key bindings ergonomics | Performance (cold start → first frame) | Verdict |
|------------|-------------------|---------------|----------------|-------------------------|----------------------------------------|---------|
| Textual    | ✅ `pkg install python && pip install textual` | ✅ | ✅ truecolor since Termux ≥0.119 | ⚠️ chords (`g g`) painful on soft kb 📱 | ~250ms | **first pick** |
| Rich       | ✅ `pkg install python && pip install rich`    | ✅ | ✅ truecolor                       | n/a (render-only)                       | ~120ms | **first pick (read-only)** |
| Bubble Tea | ⚠️ cross-compile static binary, scp in        | ✅ | ✅                                 | ⚠️ chord penalty 📱                      | ~30ms  | **excellent** (after compile) |
| Ratatui    | ⚠️ cross-compile (`cargo zigbuild` or NDK)    | ✅ | ✅                                 | ⚠️ chord penalty 📱                      | ~25ms  | **excellent** (after compile) |
| Ink        | ⚠️ `pkg install nodejs` (~60 MB) + `npm i -g` | ✅ | ✅                                 | ⚠️ chord penalty + 300ms node boot 📱    | ~340ms | acceptable for interactive |
| Cursive    | ❌ default ncurses backend fails to link      | ⚠️ with `crossterm-backend` only | ✅ | ⚠️ chord penalty 📱                | ~30ms  | **avoid** in v1 |

## Axis details

### Install on Termux

Termux ships its own `pkg` package manager (apt under the hood, mirrors curated for Android). Python and Node install in one command; the Rust toolchain installs but compiling Ratatui inside Termux is slow and easily OOMs on small-RAM phones — cross-compile instead.

### Run on Termux

All six frameworks work *if* you can get a binary or runtime in there. The blocker is always install, never execution.

### Render quality

Termux's built-in terminal emulator supports truecolor since version 0.119 (mid-2024). Older Termux installs (which exist in the wild) fall back to 256-color — declare a `--no-truecolor` flag or detect `COLORTERM` at startup.

Special characters and box-drawing render correctly under the default Termux font (powerline-friendly). If users install a custom font, no guarantee — generated TUIs should not assume nerdfont symbols.

### Key bindings ergonomics 📱

This is where Termux is genuinely different from desktop:

- **Soft keyboard latency.** A chord like `g g` is ~600ms vs. ~60ms on a hardware keyboard. Discoverable single keys win.
- **No `Ctrl` on most virtual keyboards.** Termux maps Volume Down + key, which is unergonomic. Don't rely on `Ctrl+X` as the only way to do something.
- **Hardware keyboards do exist on Android.** Bluetooth keyboards, foldables, the Pixel Tablet keyboard case. The agent should not assume one or the other — provide both single keys and chords.

The Termux Converter sub-agent specifically remaps chord-heavy schemes to single keys when porting, and adds an explicit `?` help binding even if the source TUI didn't have one.

### Performance (cold start → first frame)

Measured on a Pixel 7 (Tensor G2, 8 GB), Termux 0.119:

- Static Go/Rust binaries are fastest (~25–30ms).
- Python with Textual is fast-enough for interactive use (~250ms).
- Node-based Ink pays the Node.js boot tax.

For a "tap launcher icon → see TUI" experience on Android, prefer static binaries when feasible.

## What "Termux variant" means concretely

When `tui_master.py --termux` is passed, the agent produces a sibling `<orig>-termux/` tree with the changes documented in `TERMUX.md`. Typical changes:

- Chord bindings → single keys + `?` help overlay
- Truecolor assumptions → palette declaration + `--no-truecolor` fallback
- Native deps → pure-language equivalents per [`./conversion-recipes.md`](./conversion-recipes.md)
- README updated with Termux install instructions
- Test runner verified under `pkg install python` (Python apps) or with a smoke-test in the static binary (Go/Rust)

## Don't-do-this list

- **Don't shell out to `xdg-open`, `gsettings`, or other desktop helpers.** Termux has its own intent-launching commands (`termux-open`, `termux-open-url`).
- **Don't read `~/.config/...` blindly.** Termux's `HOME` is `/data/data/com.termux/files/home`. Use `pathlib.Path.home()` / `os.UserHomeDir()` / `dirs::home_dir()` — not hard-coded `~/.config`.
- **Don't assume a 24-row tall terminal.** Termux portrait mode is often ~50 cols × 20 rows on a phone. Test at that size.
- **Don't grab `Ctrl+Z`.** Termux uses it to send SIGTSTP just like desktop terminals; users will hard-quit and report your app as crashy.
- **Don't depend on `bash` features inside Python `subprocess` calls.** Termux's default shell is `bash` only if installed; the actual default is often `sh`. Use full paths or `shutil.which`.
