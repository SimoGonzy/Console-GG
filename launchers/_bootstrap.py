"""Shared path setup for direct game launchers."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_root_on_path() -> None:
    """Allow `python launchers/play_*.py` to import the local package."""
    project_root = Path(__file__).resolve().parents[1]
    root = str(project_root)
    if root not in sys.path:
        sys.path.insert(0, root)
