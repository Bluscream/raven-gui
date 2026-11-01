"""File and function size limits, which no linter measures in lines."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE_LIMIT = 1000
FUNCTION_LIMIT = 200


def _sources() -> list[Path]:
    return sorted([*ROOT.glob("src/**/*.py"), *ROOT.glob("src/**/*.qml"), *ROOT.glob("tests/**/*.py")])


def test_the_glob_finds_the_sources() -> None:
    # Guards the guards: an empty match would make both limits pass vacuously.
    names = {path.name for path in _sources()}
    assert {"backend.py", "Main.qml", "test_size_limits.py"} <= names


def test_no_file_exceeds_the_limit() -> None:
    over = [
        f"{path.relative_to(ROOT)}: {count} lines"
        for path in _sources()
        if (count := len(path.read_text(encoding="utf-8").splitlines())) > FILE_LIMIT
    ]
    assert not over, f"files over {FILE_LIMIT} lines:\n" + "\n".join(over)


def test_no_function_exceeds_the_limit() -> None:
    over = []
    for path in (path for path in _sources() if path.suffix == ".py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.end_lineno is not None:
                length = node.end_lineno - node.lineno + 1
                if length > FUNCTION_LIMIT:
                    over.append(f"{path.relative_to(ROOT)}:{node.lineno} {node.name}: {length} lines")
    assert not over, f"functions over {FUNCTION_LIMIT} lines:\n" + "\n".join(over)
