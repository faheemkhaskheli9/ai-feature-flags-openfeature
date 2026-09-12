"""CLI entry point.

    python -m ai_feature_flags.cli show-examples
    python -m ai_feature_flags.cli validate examples/flags/rag_enabled.json
    python -m ai_feature_flags.cli flag create --key rag.enabled --type boolean \\
        --default true --description "Toggle RAG" --owner platform-team
    python -m ai_feature_flags.cli flag list --json
    python -m ai_feature_flags.cli flag update --key rag.enabled --default false
    python -m ai_feature_flags.cli flag delete --key rag.enabled

``flag`` subcommands talk to the config store (Redis if `$REDIS_URL`/--redis-url
resolves and is reachable, else the local JSON-file fallback under
``configs/flags`` -- see ``config_store.get_config_store``). Every write is
validated against the ``FlagDefinition`` schema before it reaches the store,
so a malformed flag never gets persisted.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from pydantic import ValidationError

from ai_feature_flags.config_store import ConfigStore, get_config_store
from ai_feature_flags.examples import example_flags
from ai_feature_flags.schema import FlagDefinition, FlagType, now_utc


def _run_show_examples() -> int:
    for flag in example_flags():
        print(flag.to_json())
    return 0


def _run_validate(path: str) -> int:
    try:
        raw = open(path, encoding="utf-8").read()
        FlagDefinition.from_json(raw)
    except FileNotFoundError:
        print(f"error: no such file {path!r}", file=sys.stderr)
        return 2
    except (ValidationError, json.JSONDecodeError) as exc:
        print(f"invalid flag definition: {exc}", file=sys.stderr)
        return 1
    print(f"{path}: valid flag definition")
    return 0


class FlagValueError(ValueError):
    """A --default value couldn't be parsed as the requested flag type."""


def _parse_default_value(flag_type: FlagType, raw: str) -> Any:
    if flag_type is FlagType.BOOLEAN:
        lowered = raw.strip().lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no"):
            return False
        raise FlagValueError(f"cannot parse {raw!r} as a boolean (use true/false)")
    if flag_type is FlagType.NUMBER:
        try:
            return int(raw) if raw.strip().lstrip("-").isdigit() else float(raw)
        except ValueError as exc:
            raise FlagValueError(f"cannot parse {raw!r} as a number") from exc
    if flag_type is FlagType.STRING:
        return raw
    if flag_type is FlagType.OBJECT:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FlagValueError(f"cannot parse {raw!r} as JSON for an object flag") from exc
        if not isinstance(parsed, dict):
            raise FlagValueError(f"object flag default must be a JSON object, got {raw!r}")
        return parsed
    raise FlagValueError(f"unknown flag type {flag_type!r}")  # pragma: no cover - exhaustive enum


def _print_flags(flags: list[FlagDefinition], as_json: bool) -> None:
    if as_json:
        print(json.dumps([json.loads(f.to_json()) for f in flags], indent=2))
        return
    if not flags:
        print("(no flags)")
        return
    key_width = max(len("key"), *(len(f.key) for f in flags))
    type_width = max(len("type"), *(len(f.type.value) for f in flags))
    print(f"{'key'.ljust(key_width)}  {'type'.ljust(type_width)}  default  owner")
    for f in flags:
        print(
            f"{f.key.ljust(key_width)}  {f.type.value.ljust(type_width)}  "
            f"{json.dumps(f.default_value)}  {f.owner}"
        )


def _run_flag_create(store: ConfigStore, args: argparse.Namespace) -> int:
    if store.get(args.key) is not None:
        print(f"error: flag {args.key!r} already exists (use 'flag update')", file=sys.stderr)
        return 1
    try:
        default_value = _parse_default_value(FlagType(args.type), args.default)
        timestamp = now_utc()
        flag = FlagDefinition(
            key=args.key,
            type=FlagType(args.type),
            default_value=default_value,
            description=args.description,
            owner=args.owner,
            created_at=timestamp,
            updated_at=timestamp,
        )
    except (FlagValueError, ValidationError) as exc:
        print(f"invalid flag definition: {exc}", file=sys.stderr)
        return 1
    store.set(flag)
    _print_flags([flag], args.json)
    return 0


def _run_flag_list(store: ConfigStore, args: argparse.Namespace) -> int:
    _print_flags(store.list(), args.json)
    return 0


def _run_flag_update(store: ConfigStore, args: argparse.Namespace) -> int:
    existing = store.get(args.key)
    if existing is None:
        print(f"error: no such flag {args.key!r} (use 'flag create')", file=sys.stderr)
        return 1
    try:
        default_value = (
            _parse_default_value(existing.type, args.default)
            if args.default is not None
            else existing.default_value
        )
        candidate = existing.model_copy(
            update={
                "default_value": default_value,
                "description": args.description or existing.description,
                "owner": args.owner or existing.owner,
                "updated_at": now_utc(),
            }
        )
        updated = FlagDefinition.model_validate(candidate.model_dump())  # re-run all validators
    except (FlagValueError, ValidationError) as exc:
        print(f"invalid flag definition: {exc}", file=sys.stderr)
        return 1
    store.set(updated)
    _print_flags([updated], args.json)
    return 0


def _run_flag_delete(store: ConfigStore, args: argparse.Namespace) -> int:
    if not store.delete(args.key):
        print(f"error: no such flag {args.key!r}", file=sys.stderr)
        return 1
    print(f"deleted {args.key}")
    return 0


def _add_store_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--redis-url", default=None, help="overrides $REDIS_URL")
    parser.add_argument("--file-dir", default=None, help="local JSON-file store dir fallback")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai_feature_flags", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show-examples", help="print one example FlagDefinition per type")
    p = sub.add_parser("validate", help="validate a JSON flag definition file")
    p.add_argument("path")

    flag = sub.add_parser("flag", help="CRUD operations against the config store")
    flag_sub = flag.add_subparsers(dest="flag_command", required=True)

    create = flag_sub.add_parser("create", help="create a new flag")
    create.add_argument("--key", required=True)
    create.add_argument("--type", required=True, choices=[t.value for t in FlagType])
    create.add_argument("--default", required=True)
    create.add_argument("--description", required=True)
    create.add_argument("--owner", required=True)
    _add_store_args(create)

    listp = flag_sub.add_parser("list", help="list all flags")
    _add_store_args(listp)

    update = flag_sub.add_parser("update", help="update an existing flag")
    update.add_argument("--key", required=True)
    update.add_argument("--default", default=None)
    update.add_argument("--description", default=None)
    update.add_argument("--owner", default=None)
    _add_store_args(update)

    delete = flag_sub.add_parser("delete", help="delete a flag")
    delete.add_argument("--key", required=True)
    _add_store_args(delete)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "show-examples":
        return _run_show_examples()
    if args.command == "validate":
        return _run_validate(args.path)
    if args.command == "flag":
        store_kwargs = {}
        if args.redis_url is not None:
            store_kwargs["redis_url"] = args.redis_url
        if args.file_dir is not None:
            store_kwargs["file_dir"] = args.file_dir
        store = get_config_store(**store_kwargs)
        if args.flag_command == "create":
            return _run_flag_create(store, args)
        if args.flag_command == "list":
            return _run_flag_list(store, args)
        if args.flag_command == "update":
            return _run_flag_update(store, args)
        if args.flag_command == "delete":
            return _run_flag_delete(store, args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
