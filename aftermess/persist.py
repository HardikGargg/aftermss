"""Optional S3 copy of runtime.json so a live container keeps sitting state."""

from __future__ import annotations

import os
from pathlib import Path

from aftermess.paths import runtime_path


def bucket() -> str:
    return (os.environ.get("AFTERMESS_S3_BUCKET") or "").strip()


def key() -> str:
    prefix = (os.environ.get("AFTERMESS_S3_PREFIX") or "aftermess").strip().strip("/")
    return f"{prefix}/runtime.json"


def pull() -> None:
    name = bucket()
    if not name:
        return
    try:
        import boto3
    except ImportError:
        return
    path = runtime_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        boto3.client("s3").download_file(name, key(), str(path))
    except Exception:
        return


def push() -> None:
    name = bucket()
    if not name:
        return
    path = runtime_path()
    if not path.exists():
        return
    try:
        import boto3
    except ImportError:
        return
    boto3.client("s3").upload_file(str(path), name, key())
