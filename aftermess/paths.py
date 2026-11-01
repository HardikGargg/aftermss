"""Filesystem locations. Runtime JSON is separate from the static directory."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    override = os.environ.get("AFTERMESS_DATA_DIR")
    if override:
        return Path(override)
    return ROOT / "data" / "aftermess"


def runtime_dir() -> Path:
    override = os.environ.get("AFTERMESS_RUNTIME_DIR") or os.environ.get("AFTERMESS_DATA_DIR")
    if override:
        return Path(override)
    return ROOT / "data" / "aftermess"


def directory_path() -> Path:
    return data_dir() / "directory.json"


def config_path() -> Path:
    return data_dir() / "config.json"


def runtime_path() -> Path:
    return runtime_dir() / "runtime.json"


def accounts_path() -> Path:
    return data_dir() / "accounts.json"
