"""Repository paths for cum_tools."""

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

REPO_ROOT: Path = _REPO_ROOT
GENERATOR_DIR: Path = REPO_ROOT / "generator"
TARGET_PY3_DIR: Path = REPO_ROOT / "target_py3"
