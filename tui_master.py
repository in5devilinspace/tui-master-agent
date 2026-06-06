#!/usr/bin/env python3
"""TUI Master Agent - single-agent orchestrator.

Pipeline (one GitHub repo in, one inspired TUI out):

    1. clone the repo (shallow)
    2. detect the TUI framework with heuristics (file extensions + import grep)
    3. feed the README + a few representative source files to Claude
    4. generate a small, original TUI in the same framework
    5. write it to output/<framework>/
    6. verify it runs (headless smoke test)

This is the scoped "spine" of the larger architecture in ARCHITECTURE.md. The
sub-agents, learning database, and Termux converter are on the roadmap, not here.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError
from rich.console import Console

MODEL = "claude-opus-4-7"
MAX_SOURCE_FILES = 5
MAX_FILE_BYTES = 12_000
MAX_README_BYTES = 6_000
MAX_OUTPUT_TOKENS = 16_000

console = Console()


# --------------------------------------------------------------------------- #
# Framework registry - detection is pure heuristics, no AI.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Framework:
    name: str
    language: str
    extensions: tuple[str, ...]
    # Substrings that, when found in a source file of a matching extension,
    # signal this framework. Specific markers ("import textual") beat generic
    # ones so a Rich-only repo is never mistaken for Textual.
    signatures: tuple[str, ...]
    entry: str
    install_cmd: str
    run_cmd: str
    smoke_cmd: tuple[str, ...]
    # Higher priority breaks ties toward the more specific framework.
    priority: int = 0
    verified: bool = False


FRAMEWORKS: dict[str, Framework] = {
    "textual": Framework(
        name="textual",
        language="python",
        extensions=(".py",),
        signatures=("import textual", "from textual"),
        entry="main.py",
        install_cmd="pip install textual",
        run_cmd="python main.py",
        smoke_cmd=("python", "main.py", "--smoke"),
        priority=5,
        verified=True,
    ),
    "rich": Framework(
        name="rich",
        language="python",
        extensions=(".py",),
        signatures=("import rich", "from rich"),
        entry="main.py",
        install_cmd="pip install rich",
        run_cmd="python main.py",
        smoke_cmd=("python", "main.py", "--smoke"),
        priority=1,
        verified=True,
    ),
    "bubbletea": Framework(
        name="bubbletea",
        language="go",
        extensions=(".go",),
        signatures=("charmbracelet/bubbletea", "tea.NewProgram", "tea.Model"),
        entry="main.go",
        install_cmd="go mod tidy",
        run_cmd="go run .",
        smoke_cmd=("go", "run", ".", "--smoke"),
        priority=4,
        verified=True,
    ),
    "ratatui": Framework(
        name="ratatui",
        language="rust",
        extensions=(".rs",),
        signatures=("use ratatui", "ratatui::", "tui::"),
        entry="src/main.rs",
        install_cmd="cargo build",
        run_cmd="cargo run",
        smoke_cmd=("cargo", "run", "--", "--smoke"),
        priority=3,
    ),
    "ink": Framework(
        name="ink",
        language="javascript",
        extensions=(".js", ".jsx", ".ts", ".tsx"),
        signatures=("from 'ink'", 'from "ink"', "require('ink')", 'require("ink")'),
        entry="cli.js",
        install_cmd="npm install",
        run_cmd="node cli.js",
        smoke_cmd=("node", "cli.js", "--smoke"),
        priority=2,
    ),
    "cursive": Framework(
        name="cursive",
        language="rust",
        extensions=(".rs",),
        signatures=("use cursive", "cursive::"),
        entry="src/main.rs",
        install_cmd="cargo build",
        run_cmd="cargo run",
        smoke_cmd=("cargo", "run", "--", "--smoke"),
        priority=3,
    ),
}

_SKIP_DIRS = {
    ".git", "node_modules", "vendor", "target", "dist", "build",
    "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", ".ruff_cache",
}


# --------------------------------------------------------------------------- #
# Generation contract.
# --------------------------------------------------------------------------- #
class GeneratedFile(BaseModel):
    path: str
    content: str


class Generation(BaseModel):
    framework: str = ""
    title: str = "Inspired TUI"
    files: list[GeneratedFile] = Field(min_length=1)
    install_cmd: str = ""
    run_cmd: str = ""
    smoke_cmd: str = ""
    notes: str = ""


@dataclass
class DetectionResult:
    framework: Framework | None
    scores: dict[str, int] = field(default_factory=dict)
    file_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class Context:
    readme: str
    files: list[dict[str, str]]


# --------------------------------------------------------------------------- #
# Pipeline steps.
# --------------------------------------------------------------------------- #
def clone_repo(url: str, dest: Path) -> Path:
    """Shallow-clone a GitHub URL into dest/repo."""
    if not (url.startswith("https://github.com/") or url.startswith("git@github.com:")):
        raise ValueError(f"refusing to clone non-GitHub URL: {url}")
    target = dest / "repo"
    subprocess.run(
        ["git", "clone", "--depth", "1", "--quiet", url, str(target)],
        check=True,
    )
    return target


def _iter_source_files(repo: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
        if len(files) >= 4000:
            break
    return files


def detect_framework(repo: Path) -> DetectionResult:
    """Heuristic detection: count framework import signatures per file extension."""
    scores: dict[str, int] = {name: 0 for name in FRAMEWORKS}
    file_counts: dict[str, int] = {name: 0 for name in FRAMEWORKS}

    for path in _iter_source_files(repo):
        suffix = path.suffix.lower()
        candidates = [fw for fw in FRAMEWORKS.values() if suffix in fw.extensions]
        if not candidates:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for fw in candidates:
            hits = sum(text.count(sig) for sig in fw.signatures)
            if hits:
                scores[fw.name] += hits
                file_counts[fw.name] += 1

    ranked = sorted(
        FRAMEWORKS.values(),
        key=lambda fw: (scores[fw.name], fw.priority),
        reverse=True,
    )
    best = ranked[0] if scores[ranked[0].name] > 0 else None
    return DetectionResult(framework=best, scores=scores, file_counts=file_counts)


def gather_context(repo: Path, fw: Framework, max_files: int) -> Context:
    """Collect the README plus the most framework-dense source files."""
    readme = ""
    for candidate in ("README.md", "README.rst", "README.txt", "readme.md"):
        p = repo / candidate
        if p.is_file():
            readme = p.read_text(encoding="utf-8", errors="ignore")[:MAX_README_BYTES]
            break

    scored: list[tuple[int, int, Path]] = []
    for path in _iter_source_files(repo):
        if path.suffix.lower() not in fw.extensions:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        hits = sum(text.count(sig) for sig in fw.signatures)
        if hits:
            scored.append((hits, -len(text), path))

    scored.sort(reverse=True)
    picked: list[dict[str, str]] = []
    for _hits, _neg_len, path in scored[:max_files]:
        text = path.read_text(encoding="utf-8", errors="ignore")[:MAX_FILE_BYTES]
        picked.append({"path": str(path.relative_to(repo)), "content": text})

    return Context(readme=readme, files=picked)


SYSTEM_PROMPT = """\
You are TUI Master Agent, a generator of terminal user interfaces.

You will be shown the README and a few representative source files from a real
open-source TUI project, plus the name of the framework it is built with. Study
how the project uses that framework, then design a SMALL, ORIGINAL TUI in the
SAME framework. Do not copy the source. Build something inspired by it - a
focused, self-contained little app that demonstrates the framework's idioms
(layout, event loop, key handling, theming) at a fraction of the size.

Hard requirements for the code you produce:
- Same framework and language as the source project.
- Small: 1-3 files, self-contained, no exotic third-party dependencies beyond
  the framework itself.
- It MUST run. So that it can be verified automatically (headless, no TTY):
    * Textual (Python): define your App subclass at MODULE level (so it can be
      imported and driven by Textual's `run_test()` pilot), and guard the
      interactive launch under `if __name__ == "__main__": <YourApp>().run()`.
    * Rich (Python): put the demo in a `main()` function guarded by
      `if __name__ == "__main__": main()`. Do not block on input at import time.
    * Bubble Tea (Go): `package main`, a standard `func main()`, must compile
      cleanly with `go build`. Use only the bubbletea/lipgloss/bubbles modules.
- No network access, no files written at runtime.

Return ONE JSON object and nothing else, wrapped in a ```json fenced block:

```json
{
  "framework": "<framework name>",
  "title": "<short name of your TUI>",
  "files": [{"path": "main.py", "content": "<full file source>"}],
  "install_cmd": "<one shell command to install deps>",
  "run_cmd": "<one shell command to run it>",
  "notes": "<one sentence on what it does and what inspired it>"
}
```
"""


def build_user_message(fw: Framework, context: Context, source_url: str) -> str:
    parts = [
        f"Framework: {fw.name} ({fw.language})",
        f"Source project: {source_url}",
        f"Entry file your generated app must use: {fw.entry}",
        "",
        "=== README (truncated) ===",
        context.readme or "(no README found)",
        "",
        "=== Representative source files ===",
    ]
    for f in context.files:
        parts.append(f"\n--- {f['path']} ---\n{f['content']}")
    parts.append(
        "\nNow design and return a small original TUI in this framework, "
        "following every hard requirement. JSON only."
    )
    return "\n".join(parts)


def call_claude(system: str, user: str, model: str) -> str:
    import anthropic

    client = anthropic.Anthropic()
    chunks: list[str] = []
    with client.messages.stream(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    ) as stream:
        for text in stream.text_stream:
            chunks.append(text)
    return "".join(chunks)


def parse_generation(text: str) -> Generation:
    """Extract the JSON object from the model output and validate it."""
    blob = _extract_json(text)
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as exc:
        raise ValueError(f"model did not return valid JSON: {exc}") from exc
    try:
        return Generation.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"generation failed schema validation: {exc}") from exc


def _extract_json(text: str) -> str:
    fence = "```json"
    if fence in text:
        start = text.index(fence) + len(fence)
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    first, last = text.find("{"), text.rfind("}")
    if first != -1 and last != -1 and last > first:
        return text[first : last + 1]
    raise ValueError("no JSON object found in model output")


def write_output(gen: Generation, out_dir: Path) -> Path:
    """Write generated files under out_dir, rejecting unsafe paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for gf in gen.files:
        rel = Path(gf.path)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"unsafe output path: {gf.path}")
        dest = out_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(gf.content, encoding="utf-8")
    return out_dir


# Headless Textual driver: import the generated entry, find its App subclass,
# and run it through Textual's official run_test() pilot - no TTY required.
_TEXTUAL_DRIVER = """\
import asyncio, importlib.util, inspect, sys
from textual.app import App

spec = importlib.util.spec_from_file_location("generated_app", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
sys.modules["generated_app"] = mod  # so @dataclass etc. can resolve the module
spec.loader.exec_module(mod)
app_cls = next(
    (o for o in vars(mod).values()
     if inspect.isclass(o) and issubclass(o, App) and o is not App),
    None,
)
if app_cls is None:
    print("no App subclass found", file=sys.stderr); raise SystemExit(3)

async def _run() -> None:
    async with app_cls().run_test() as pilot:
        await pilot.pause()

asyncio.run(_run())
print("TEXTUAL_SMOKE_OK")
"""


def _py_compile_all(out_dir: Path) -> tuple[bool, str]:
    py_files = list(out_dir.rglob("*.py"))
    for p in py_files:
        res = subprocess.run(
            [sys.executable, "-m", "py_compile", str(p)],
            capture_output=True, text=True,
        )
        if res.returncode != 0:
            return False, f"py_compile failed for {p.name}:\n{res.stderr}"
    return True, f"py_compile ok ({len(py_files)} file(s))"


def _verify_textual(fw: Framework, out_dir: Path) -> tuple[bool, str]:
    ok, msg = _py_compile_all(out_dir)
    if not ok:
        return False, msg
    entry = (out_dir / fw.entry).resolve()
    try:
        res = subprocess.run(
            [sys.executable, "-c", _TEXTUAL_DRIVER, str(entry)],
            cwd=out_dir, capture_output=True, text=True, timeout=90,
        )
    except subprocess.TimeoutExpired:
        return False, f"{msg}\nheadless run_test timed out"
    log = f"{msg}\nrun_test headless -> exit {res.returncode}"
    if res.returncode != 0:
        return False, log + "\n" + (res.stderr or res.stdout)[-800:]
    return True, log


def _verify_go(out_dir: Path) -> tuple[bool, str]:
    log: list[str] = []
    if not (out_dir / "go.mod").exists():
        subprocess.run(["go", "mod", "init", "inspired"], cwd=out_dir,
                       capture_output=True, text=True)
    tidy = subprocess.run(["go", "mod", "tidy"], cwd=out_dir,
                          capture_output=True, text=True, timeout=240)
    log.append(f"go mod tidy -> exit {tidy.returncode}")
    build = subprocess.run(["go", "build", "./..."], cwd=out_dir,
                           capture_output=True, text=True, timeout=240)
    log.append(f"go build ./... -> exit {build.returncode}")
    if build.returncode != 0:
        log.append((build.stderr or build.stdout)[-800:])
        return False, "\n".join(log)
    return True, "\n".join(log)


def _verify_generic(fw: Framework, out_dir: Path) -> tuple[bool, str]:
    if fw.language == "python":
        ok, msg = _py_compile_all(out_dir)
        return ok, msg + "\n(best-effort: no headless harness for this framework yet)"
    return True, "files written (no automated run-verification for this framework yet)"


def verify_runs(fw: Framework, gen: Generation, out_dir: Path) -> tuple[bool, str]:
    """Framework-native proof that the generated TUI actually runs."""
    if fw.name == "textual":
        return _verify_textual(fw, out_dir)
    if fw.name == "bubbletea":
        return _verify_go(out_dir)
    return _verify_generic(fw, out_dir)


# --------------------------------------------------------------------------- #
# Driver.
# --------------------------------------------------------------------------- #
def run(args: argparse.Namespace) -> int:
    source = args.feed
    out_root = Path(args.out)

    with tempfile.TemporaryDirectory(prefix="tui-master-") as tmp:
        tmpdir = Path(tmp)
        if args.local:
            repo = Path(args.local)
            console.print(f"[cyan]Using local repo[/] {repo}")
        else:
            console.print(f"[cyan]Cloning[/] {source}")
            repo = clone_repo(source, tmpdir)

        if args.framework:
            fw = FRAMEWORKS[args.framework]
            console.print(f"[cyan]Framework[/] forced -> [bold]{fw.name}[/]")
        else:
            det = detect_framework(repo)
            if det.framework is None:
                console.print("[red]No supported TUI framework detected.[/]")
                console.print(f"scores: {det.scores}")
                return 2
            fw = det.framework
            console.print(
                f"[cyan]Framework[/] detected -> [bold]{fw.name}[/] "
                f"(signatures={det.scores[fw.name]}, files={det.file_counts[fw.name]})"
            )

        context = gather_context(repo, fw, args.max_files)
        console.print(
            f"[cyan]Context[/] README={len(context.readme)}B, "
            f"files={len(context.files)}"
        )

        if args.dry_run:
            console.print("[yellow]--dry-run:[/] skipping generation.")
            return 0

        console.print(f"[cyan]Generating[/] with {args.model} ...")
        raw = call_claude(SYSTEM_PROMPT, build_user_message(fw, context, source), args.model)
        gen = parse_generation(raw)

        out_dir = out_root / fw.name
        write_output(gen, out_dir)
        console.print(
            f"[green]Wrote[/] {len(gen.files)} file(s) to {out_dir} - "
            f"\"{gen.title}\""
        )

    if args.no_verify:
        console.print("[yellow]--no-verify:[/] skipping run check.")
        return 0

    console.print("[cyan]Verifying[/] the generated TUI runs ...")
    ok, vlog = verify_runs(fw, gen, out_dir)
    console.print(vlog)
    if ok:
        console.print(f"[bold green]OK[/] - {fw.run_cmd} from {out_dir}")
        return 0
    console.print("[bold red]Verification failed.[/]")
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tui_master",
        description="Generate a small TUI inspired by a real GitHub TUI repo.",
    )
    p.add_argument("feed", nargs="?", default="",
                   help="GitHub URL of a TUI repo to study")
    p.add_argument("--local", help="path to an already-cloned repo (skips clone)")
    p.add_argument("--framework", choices=sorted(FRAMEWORKS),
                   help="force a framework instead of detecting")
    p.add_argument("--out", default="output", help="output root (default: output)")
    p.add_argument("--model", default=MODEL, help=f"Anthropic model (default: {MODEL})")
    p.add_argument("--max-files", type=int, default=MAX_SOURCE_FILES,
                   help="max source files to feed the model")
    p.add_argument("--dry-run", action="store_true",
                   help="clone + detect only, no API call")
    p.add_argument("--no-verify", action="store_true",
                   help="skip the run check after generation")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.feed and not args.local:
        console.print("[red]Provide a GitHub URL (or --local PATH).[/]")
        return 2
    try:
        return run(args)
    except (ValueError, subprocess.CalledProcessError) as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
