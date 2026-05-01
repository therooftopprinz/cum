"""`cum-tools` / `python -m cum_tools` entry point."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from cum_tools.repo import REPO_ROOT, TARGET_PY3_DIR


def _run_sample2_py_test() -> int:
    script = TARGET_PY3_DIR / "test" / "sample2_test.py"
    env = os.environ.copy()
    pp = env.get("PYTHONPATH", "")
    root_py3 = str(TARGET_PY3_DIR)
    env["PYTHONPATH"] = root_py3 + (os.pathsep + pp if pp else "")
    r = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
    )
    return int(r.returncode if r.returncode is not None else 1)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="cum-tools",
        description="Python-side CUM tooling (codegen & tests).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    codegen = sub.add_parser("codegen", help="Regenerate Python output from .cum")
    csub = codegen.add_subparsers(dest="target", required=True)
    csub.add_parser("sample2", help="Write target_py3/test/sample2.py from sample2.cum")

    test = sub.add_parser("test", help="Run Python backend tests")
    tsub = test.add_subparsers(dest="which", required=True)
    tsub.add_parser(
        "sample2",
        help="Regenerate sample2.py and run the golden PER codec check",
    )

    args = p.parse_args(argv)

    if args.cmd == "codegen" and args.target == "sample2":
        from cum_tools.codegen_sample2 import run as codegen_run

        codegen_run()
        return 0

    if args.cmd == "test" and args.which == "sample2":
        from cum_tools.codegen_sample2 import run as codegen_run

        codegen_run()
        return _run_sample2_py_test()

    raise RuntimeError("unhandled command")


if __name__ == "__main__":
    raise SystemExit(main())
