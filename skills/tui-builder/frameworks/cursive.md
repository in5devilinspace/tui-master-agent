# Cursive (Rust)

> Classic, retained-mode widget-tree TUI library for Rust. The default pick when the target audience expects "old-school" TUI ergonomics — menus, dialog boxes, focus rings.

- Repo: https://github.com/gyscos/cursive
- License: MIT
- Status (May 2026): stable, slower release cadence than Ratatui
- Backends: `ncurses`, `pancurses`, `termion`, `crossterm`

## When to choose Cursive

Pick Cursive when **any one** of these is true:

- You're building something that resembles 1990s TUIs — `htop`, `mc`, `nano`, `dialog`. Menus, focus chains, modal dialogs.
- The team is Rust but prefers a higher-level API than [Ratatui](./ratatui.md).
- You want focus / tab order handled for you.

Skip Cursive if the project demands 60 fps rendering (use [Ratatui](./ratatui.md)) or the target includes Termux (native deps are painful on Android).

## Install

```bash
cargo new myapp && cd myapp
cargo add cursive --features crossterm-backend --no-default-features
```

`Cargo.toml`:

```toml
[dependencies]
cursive = { version = "0.21", default-features = false, features = ["crossterm-backend"] }
```

(Avoid the default ncurses backend on Termux — pick `crossterm-backend` for portability.)

## Hello world

```rust
use cursive::views::Dialog;
use cursive::Cursive;

fn main() {
    let mut siv = cursive::default();
    siv.add_layer(
        Dialog::around(cursive::views::TextView::new("Hello, terminal."))
            .title("hello")
            .button("Quit", |s: &mut Cursive| s.quit()),
    );
    siv.run();
}
```

`cursive::default()` picks a sensible backend; `run()` blocks until the user quits.

## One production pattern — focus chain + keyboard navigation

The headline reason to choose Cursive over Ratatui is that focus management is automatic. Tab cycles through interactive views; Enter activates; Escape backs out. You define the tree; Cursive runs the chain.

```rust
use cursive::views::{Dialog, EditView, LinearLayout, TextView, Button};
use cursive::traits::*;

fn main() {
    let mut siv = cursive::default();

    let layout = LinearLayout::vertical()
        .child(TextView::new("Login").center())
        .child(TextView::new("Username:"))
        .child(EditView::new().with_name("user").fixed_width(30))
        .child(TextView::new("Password:"))
        .child(EditView::new().secret().with_name("pass").fixed_width(30))
        .child(Button::new("Sign in", |s| {
            let user = s.call_on_name("user", |v: &mut EditView| v.get_content()).unwrap();
            let pass = s.call_on_name("pass", |v: &mut EditView| v.get_content()).unwrap();
            s.add_layer(Dialog::info(format!("Welcome, {} (len {})", user, pass.len())));
        }));

    siv.add_layer(Dialog::around(layout).title("Sign In").button("Cancel", |s| s.quit()));
    siv.run();
}
```

Tab cycles user → pass → Sign in → Cancel. Shift+Tab reverses. Enter on the button fires. Cursive owns all of that.

## Gotchas

1. **Cursive is retained-mode.** You build a tree and mutate it. Don't fight that with global state — name your views (`.with_name(...)`) and reach into them via `call_on_name`.
2. **The default ncurses backend has native deps.** `pkg-config`, `libncurses-dev`. On Termux, that's a fight. Prefer `crossterm-backend`.
3. **Callbacks are `Fn(&mut Cursive)`.** Inside, you can't easily share mutable state with the outer scope. Use `s.set_user_data(...)` to stash state on the siv.
4. **Layered modal dialogs stack.** `add_layer` pushes; the active layer captures input. Don't forget `pop_layer()` after a workflow completes.
5. **Cursive renders less often than Ratatui.** It's not for live tickers or visualizers — pick Ratatui for those.

## Termux verdict

⚠️ Works only with `crossterm-backend`. Default ncurses backend cannot link inside Termux without significant effort. Compile from a desktop with `cargo zigbuild --target aarch64-linux-android`. See [`../termux/conversion-recipes.md`](../termux/conversion-recipes.md).

## Useful primitives

- `Cursive` — the root object (mutable across callbacks)
- `Dialog`, `LinearLayout`, `Panel`, `ScrollView` — containers
- `TextView`, `EditView`, `SelectView`, `Checkbox`, `RadioButton` — interactive widgets
- `.with_name(...)` + `s.call_on_name(...)` — the canonical way to reach into widgets
- `set_user_data` / `user_data` / `take_user_data` — typed app-wide state slot
