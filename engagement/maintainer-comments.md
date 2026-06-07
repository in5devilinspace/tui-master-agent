Maintainer credit comments — post these as COMMENTS (e.g. under the DEV.to post, or as replies on relevant threads), NOT as the post body. Tasteful, specific, non-spammy. Each credits the framework honestly and tags the right maintainers.

Replace handles if you post on a platform where the canonical handle differs (e.g. GitHub @ vs. X @).

---

## Comment 1 — Textualize / Textual

Wanted to give credit where it's due: the Textual path in this only works because @textualize built `run_test()`. Being able to mount an app, drive it, and assert on it headlessly is exactly what let me put a real "did it actually run" gate on generated code instead of just checking that it imports. The README + a couple of source files were enough context for the model to produce a working app in your framework — which says a lot about how legible Textual's API is. The "Pixel Pond" example came straight out of that loop. Thank you for the framework and for making it testable by default. ({{DEVTO_URL}})

---

## Comment 2 — Charm / Bubble Tea

Credit to the @charmcli / @charmbracelet team — the Bubble Tea target here leans entirely on how clean the Elm-style Model/Update/View structure is. The model was able to produce an original, compiling Bubble Tea program (a Pomodoro timer) from just the README and a few source files, and I gate it on `go build` so nothing ships unless it actually compiles against your API. That it does, reliably, is a testament to how consistent the framework's shape is. Genuinely grateful for Bubble Tea — it made the cross-language half of this project the easy half. ({{DEVTO_URL}})
