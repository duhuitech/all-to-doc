#!/usr/bin/env python3
"""Configure the AppCode used by the Duhui all-to-doc skill."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from typing import Any

from duhui_config import (
    ALIYUN_MARKET_URL,
    APP_CODE_ENV,
    ConfigError,
    clear_saved_appcode,
    credential_status,
    save_appcode,
)


def emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Configure the AppCode used by the Duhui all-to-doc skill.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    set_parser = subparsers.add_parser("set", help="Save AppCode to the user config file")
    source_group = set_parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--stdin",
        action="store_true",
        help="Read AppCode from standard input; prompts securely when run in a terminal",
    )
    source_group.add_argument(
        "--from-env",
        action="store_true",
        help=f"Read AppCode from ${APP_CODE_ENV}",
    )

    subparsers.add_parser("status", help="Report whether AppCode is configured")
    subparsers.add_parser("clear", help="Remove the saved AppCode config file")
    return parser.parse_args(argv)


def read_stdin_appcode() -> str:
    if sys.stdin.isatty():
        return getpass.getpass("AppCode: ")
    return sys.stdin.read()


def configure_appcode(args: argparse.Namespace) -> int:
    if args.stdin:
        raw_appcode = read_stdin_appcode()
    else:
        raw_appcode = os.environ.get(APP_CODE_ENV, "")

    config_path = save_appcode(raw_appcode)
    emit_json(
        {
            "status": "configured",
            "config_path": str(config_path),
        }
    )
    return 0


def show_status() -> int:
    status = credential_status()
    status["market_url"] = ALIYUN_MARKET_URL
    emit_json(status)
    if status["status"] == "configured":
        return 0
    if status["status"] == "missing":
        return 3
    return 1


def clear_appcode() -> int:
    config_path, removed = clear_saved_appcode()
    emit_json(
        {
            "status": "cleared",
            "removed": removed,
            "config_path": str(config_path),
        }
    )
    return 0


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        if args.command == "set":
            return configure_appcode(args)
        if args.command == "status":
            return show_status()
        if args.command == "clear":
            return clear_appcode()
        raise AssertionError(f"Unhandled command: {args.command}")
    except (ConfigError, OSError) as exc:
        emit_json(
            {
                "status": "error",
                "reason": str(exc),
                "market_url": ALIYUN_MARKET_URL,
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
