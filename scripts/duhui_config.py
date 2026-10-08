#!/usr/bin/env python3
"""Shared AppCode configuration helpers for the Duhui all-to-doc skill."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

APP_CODE_ENV = "DUHUI_ALL_TO_DOC_APPCODE"
APP_CODE_FILE_ENV = "DUHUI_ALL_TO_DOC_APPCODE_FILE"
CONFIG_PATH_ENV = "DUHUI_ALL_TO_DOC_CONFIG"
ALIYUN_MARKET_URL = "https://market.aliyun.com/store/4721853/index.html"

CONFIG_SCHEMA_VERSION = 1
DEFAULT_CONFIG_PATH = Path.home() / ".duhui" / "all-to-doc" / "config.json"


class ConfigError(ValueError):
    """Raised when an explicit credential source is invalid."""


class MissingAppCodeError(ConfigError):
    """Raised when no supported credential source is configured."""


@dataclass(frozen=True)
class AppCodeCredential:
    value: str
    source: str
    location: str


def resolve_config_path() -> Path:
    raw_path = os.environ.get(CONFIG_PATH_ENV, "").strip()
    if raw_path:
        return Path(raw_path).expanduser().resolve()
    return DEFAULT_CONFIG_PATH


def normalize_appcode(raw_appcode: str, *, source: str) -> str:
    appcode = raw_appcode.strip()
    if not appcode:
        raise ConfigError(f"AppCode from {source} is empty")
    if "\n" in appcode or "\r" in appcode:
        raise ConfigError(f"AppCode from {source} cannot contain line breaks")
    return appcode


def read_appcode_file(path: Path) -> str:
    try:
        raw_appcode = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Could not read AppCode file {path}: {exc}") from exc
    return normalize_appcode(raw_appcode, source=str(path))


def read_config(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Could not read config file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file {path} is invalid JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ConfigError(f"Config file {path} must contain a JSON object")
    schema_version = payload.get("schema_version", CONFIG_SCHEMA_VERSION)
    if schema_version != CONFIG_SCHEMA_VERSION:
        raise ConfigError(
            f"Unsupported config schema_version {schema_version!r} in {path}; "
            f"expected {CONFIG_SCHEMA_VERSION}"
        )
    return payload


def resolve_appcode() -> AppCodeCredential:
    raw_environment_value = os.environ.get(APP_CODE_ENV, "")
    if raw_environment_value.strip():
        return AppCodeCredential(
            value=normalize_appcode(raw_environment_value, source=f"${APP_CODE_ENV}"),
            source="environment",
            location=APP_CODE_ENV,
        )

    raw_appcode_file = os.environ.get(APP_CODE_FILE_ENV, "").strip()
    if raw_appcode_file:
        appcode_path = Path(raw_appcode_file).expanduser().resolve()
        return AppCodeCredential(
            value=read_appcode_file(appcode_path),
            source="appcode_file",
            location=str(appcode_path),
        )

    config_path = resolve_config_path()
    if config_path.exists():
        payload = read_config(config_path)
        raw_appcode = payload.get("appcode")
        if not isinstance(raw_appcode, str):
            raise ConfigError(f"Config file {config_path} is missing string field: appcode")
        return AppCodeCredential(
            value=normalize_appcode(raw_appcode, source=str(config_path)),
            source="config_file",
            location=str(config_path),
        )

    raise MissingAppCodeError(
        f"No AppCode is configured in ${APP_CODE_ENV}, ${APP_CODE_FILE_ENV}, "
        f"or {config_path}"
    )


def credential_status() -> dict[str, Any]:
    config_path = resolve_config_path()
    try:
        credential = resolve_appcode()
    except MissingAppCodeError:
        return {
            "status": "missing",
            "configured": False,
            "config_path": str(config_path),
        }
    except ConfigError as exc:
        return {
            "status": "error",
            "configured": False,
            "config_path": str(config_path),
            "reason": str(exc),
        }
    return {
        "status": "configured",
        "configured": True,
        "source": credential.source,
        "location": credential.location,
        "config_path": str(config_path),
    }


def save_appcode(raw_appcode: str) -> Path:
    appcode = normalize_appcode(raw_appcode, source="configuration input")
    config_path = resolve_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    payload = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "appcode": appcode,
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    temp_path: Path | None = None
    try:
        file_descriptor, raw_temp_path = tempfile.mkstemp(
            prefix=f".{config_path.name}.",
            dir=config_path.parent,
            text=True,
        )
        temp_path = Path(raw_temp_path)
        try:
            if hasattr(os, "fchmod"):
                os.fchmod(file_descriptor, 0o600)
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as config_file:
                config_file.write(encoded)
                config_file.flush()
                os.fsync(config_file.fileno())
        except BaseException:
            try:
                os.close(file_descriptor)
            except OSError:
                pass
            raise
        temp_path.replace(config_path)
        try:
            config_path.chmod(0o600)
        except OSError:
            pass
        return config_path
    finally:
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def clear_saved_appcode() -> tuple[Path, bool]:
    config_path = resolve_config_path()
    try:
        config_path.unlink()
    except FileNotFoundError:
        return config_path, False
    return config_path, True
