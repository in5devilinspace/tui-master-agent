"""Offline tests for the orchestrator: detection, parsing, output, guards.

No network and no API calls - every test runs against synthetic repos in
tmp_path so the suite is fast and CI-safe.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tui_master as tm


def _make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    for rel, content in files.items():
        dest = repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    return repo


# --------------------------------------------------------------------------- #
# detect_framework
# --------------------------------------------------------------------------- #
def test_detect_textual(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {
        "app.py": "from textual.app import App\nimport textual\n",
        "widget.py": "from textual.widget import Widget\n",
    })
    result = tm.detect_framework(repo)
    assert result.framework is not None
    assert result.framework.name == "textual"


def test_detect_rich_not_textual(tmp_path: Path) -> None:
    # A Rich-only project must never be misread as Textual.
    repo = _make_repo(tmp_path, {
        "report.py": "from rich.console import Console\nimport rich\nConsole()\n",
    })
    result = tm.detect_framework(repo)
    assert result.framework is not None
    assert result.framework.name == "rich"
    assert result.scores["textual"] == 0


def test_detect_bubbletea(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {
        "main.go": (
            'package main\n'
            'import tea "github.com/charmbracelet/bubbletea"\n'
            'func main() { tea.NewProgram(nil) }\n'
        ),
    })
    result = tm.detect_framework(repo)
    assert result.framework is not None
    assert result.framework.name == "bubbletea"


def test_detect_none_for_plain_repo(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {
        "README.md": "# just docs\n",
        "notes.txt": "nothing to see here\n",
    })
    result = tm.detect_framework(repo)
    assert result.framework is None


def test_detect_skips_vendor_dirs(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {
        "app.py": "from textual.app import App\n",
        "node_modules/pkg/index.js": "from 'ink'\n" * 50,
    })
    result = tm.detect_framework(repo)
    assert result.framework is not None
    assert result.framework.name == "textual"


# --------------------------------------------------------------------------- #
# JSON extraction / generation parsing
# --------------------------------------------------------------------------- #
def test_extract_json_fenced() -> None:
    text = 'blah\n```json\n{"a": 1}\n```\ntrailing'
    assert tm._extract_json(text) == '{"a": 1}'


def test_extract_json_bare_object() -> None:
    text = 'here you go: {"a": 1, "b": [2, 3]} done'
    assert tm._extract_json(text) == '{"a": 1, "b": [2, 3]}'


def test_extract_json_missing_raises() -> None:
    with pytest.raises(ValueError):
        tm._extract_json("no json at all here")


def test_parse_generation_valid() -> None:
    raw = (
        '```json\n'
        '{"framework": "textual", "title": "Demo", '
        '"files": [{"path": "main.py", "content": "print(1)"}], '
        '"run_cmd": "python main.py"}\n'
        '```'
    )
    gen = tm.parse_generation(raw)
    assert gen.framework == "textual"
    assert gen.files[0].path == "main.py"
    assert gen.run_cmd == "python main.py"


def test_parse_generation_invalid_json_raises() -> None:
    with pytest.raises(ValueError):
        tm.parse_generation("```json\n{not valid json}\n```")


def test_parse_generation_requires_files() -> None:
    with pytest.raises(ValueError):
        tm.parse_generation('{"framework": "textual", "files": []}')


def test_generation_defaults() -> None:
    gen = tm.Generation(files=[tm.GeneratedFile(path="main.py", content="x")])
    assert gen.framework == ""
    assert gen.title == "Inspired TUI"


# --------------------------------------------------------------------------- #
# write_output guards
# --------------------------------------------------------------------------- #
def test_write_output_writes_files(tmp_path: Path) -> None:
    gen = tm.Generation(files=[
        tm.GeneratedFile(path="main.py", content="print('hi')"),
        tm.GeneratedFile(path="pkg/util.py", content="X = 1"),
    ])
    out = tmp_path / "out" / "textual"
    tm.write_output(gen, out)
    assert (out / "main.py").read_text() == "print('hi')"
    assert (out / "pkg" / "util.py").read_text() == "X = 1"


def test_write_output_rejects_parent_escape(tmp_path: Path) -> None:
    gen = tm.Generation(files=[tm.GeneratedFile(path="../evil.py", content="x")])
    with pytest.raises(ValueError):
        tm.write_output(gen, tmp_path / "out")


def test_write_output_rejects_absolute_path(tmp_path: Path) -> None:
    gen = tm.Generation(files=[tm.GeneratedFile(path="/etc/evil.py", content="x")])
    with pytest.raises(ValueError):
        tm.write_output(gen, tmp_path / "out")


# --------------------------------------------------------------------------- #
# clone guard / context gathering
# --------------------------------------------------------------------------- #
def test_clone_repo_rejects_non_github(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        tm.clone_repo("https://gitlab.com/foo/bar", tmp_path)


def test_gather_context_picks_dense_files_and_truncates(tmp_path: Path) -> None:
    big = "from textual.app import App\n" + ("# pad\n" * 5000)
    repo = _make_repo(tmp_path, {
        "README.md": "R" * 20_000,
        "dense.py": "from textual.app import App\n" * 8,
        "sparse.py": "from textual.widget import Widget\n",
        "huge.py": big,
    })
    fw = tm.FRAMEWORKS["textual"]
    ctx = tm.gather_context(repo, fw, max_files=2)
    assert len(ctx.readme) <= tm.MAX_README_BYTES
    assert len(ctx.files) == 2
    # The densest file (most signature hits) must be selected first.
    assert ctx.files[0]["path"] == "dense.py"
    for f in ctx.files:
        assert len(f["content"]) <= tm.MAX_FILE_BYTES
