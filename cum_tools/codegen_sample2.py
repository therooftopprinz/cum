"""Emit `target_py3/test/sample2.py` from `sample2.cum` via the AST."""

from __future__ import annotations

import os
import subprocess
import sys

from cum_tools.repo import GENERATOR_DIR, REPO_ROOT, TARGET_PY3_DIR


def run(py_exe: str | None = None) -> None:
    """Pipe sample2.cum → AST → ast_to_py.py and write target_py3/test/sample2.py."""
    py = py_exe or os.environ.get("PYTHON", sys.executable)
    cum = REPO_ROOT / "sample2.cum"
    out = TARGET_PY3_DIR / "test" / "sample2.py"
    gen = str(GENERATOR_DIR)

    env = os.environ.copy()
    sep = os.pathsep
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = gen + (sep + prev if prev else "")

    ast = subprocess.run(
        [py, str(GENERATOR_DIR / "cum_to_ast.py"), str(cum)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if ast.returncode != 0:
        sys.stderr.write(ast.stderr or "")
        raise SystemExit(ast.returncode)

    py_out = subprocess.run(
        [py, str(GENERATOR_DIR / "ast_to_py.py")],
        cwd=str(REPO_ROOT),
        env=env,
        input=ast.stdout,
        capture_output=True,
        text=True,
        check=False,
    )
    if py_out.returncode != 0:
        sys.stderr.write(py_out.stderr or "")
        raise SystemExit(py_out.returncode)

    out.parent.mkdir(parents=True, exist_ok=True)
    data = py_out.stdout
    out.write_text(data, encoding="utf-8")
    sys.stderr.write(
        "wrote {} ({} bytes)\n".format(out, len(data.encode("utf-8")))
    )
