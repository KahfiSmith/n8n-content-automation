#!/usr/bin/env python3
"""Shared utilities for scripts that read .env files."""

from __future__ import annotations

from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict. Ignores comments and blank lines."""
    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def to_bool(value: str | None, default: bool) -> bool:
    """Convert a string value to boolean."""
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}
