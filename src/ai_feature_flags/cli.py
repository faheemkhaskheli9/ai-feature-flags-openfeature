"""CLI entry point.

    python -m ai_feature_flags.cli show-examples
    python -m ai_feature_flags.cli validate examples/flags/rag_enabled.json

Phase 1 only defines and validates the flag schema; storage/CRUD/evaluation
land in later phases behind the same ``FlagDefinition`` model.
"""

from __future__ import annotations

import argparse
import json
import sys

from pydantic import ValidationError

from ai_feature_flags.examples import example_flags
from ai_feature_flags.schema import FlagDefinition


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai_feature_flags", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show-examples", help="print one example FlagDefinition per type")
    p = sub.add_parser("validate", help="validate a JSON flag definition file")
    p.add_argument("path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "show-examples":
        return _run_show_examples()
    if args.command == "validate":
        return _run_validate(args.path)
    return 2


if __name__ == "__main__":
    sys.exit(main())
