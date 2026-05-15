"""CLI entrypoint: ``vs-show-variants``."""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

from vs_mod_tools.core.loader import load_vs_json
from vs_mod_tools.core.validation import extract_patterns, find_invalid_patterns
from vs_mod_tools.core.variants import generate_variants

# ── Help text constants ───────────────────────────────────────────────────────

_DESCRIPTION = (
    "Vintage Story variant generator and validator.\n\n"
    "Generates the effective variant list from a VS item JSON definition, with\n"
    "optional per-group filtering and pattern validation."
)

_EXAMPLES = (
    "examples:\n"
    "  vs-show-variants -f armor.json\n"
    "  vs-show-variants -f armor.json --bodypart legs --bodypart head\n"
    "  vs-show-variants -f armor.json --bodypart legs --construction jerkin\n"
    "  vs-show-variants -f armor.json --validate\n"
    "  vs-show-variants -f armor.json --bodypart legs --validate"
)

_DYNAMIC_ARGS_NOTE = (
    "variant group filter arguments:\n"
    "  When -f is provided, one --<group> flag is added per variantgroup\n"
    "  defined in the JSON file. Each flag may be repeated for OR logic\n"
    "  within that group; multiple distinct group flags are ANDed.\n"
    "  Example:  --bodypart legs --bodypart head --construction jerkin\n"
    "  Run with -f <file> --help to see the available groups and their states."
)

_HELP_FLAGS: frozenset[str] = frozenset({"-h", "--help"})
_FILE_FLAGS: frozenset[str] = frozenset({"-f", "--file"})


# ── Parser helpers ────────────────────────────────────────────────────────────


def _add_static_args(parser: argparse.ArgumentParser) -> None:
    """
    Add the fixed (non-dynamic) arguments to *parser*.

    :param parser: (argparse.ArgumentParser) The parser to add arguments to.

    :return: (None)
    """
    parser.add_argument(
        "-f",
        "--file",
        required=True,
        metavar="JSON_FILE",
        help="Path to the VS item definition JSON.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help=(
            "Check every wildcard-pattern string in the JSON against the "
            "processed variant list and report any that match nothing."
        ),
    )


def _build_parser(data: Dict[str, Any]) -> argparse.ArgumentParser:
    """
    Build and return the full argument parser, including dynamic group filter arguments based on the provided JSON data.

    :param data: (dict) The parsed VS item definition JSON.

    :return: (argparse.ArgumentParser) The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description=_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_EXAMPLES,
    )
    _add_static_args(parser)

    group_filters = parser.add_argument_group("variant group filter arguments")
    for group in data["variantgroups"]:
        code: str = group["code"]
        states: list[str] = group["states"]
        # dest uses underscores so getattr() works even when code contains hyphens.
        group_filters.add_argument(
            f"--{code}",
            action="append",
            dest=code.replace("-", "_"),
            choices=states,
            metavar=code.upper(),
            help=(
                f"Filter by {code} (repeat for OR logic within this group; "
                f"multiple distinct group flags are ANDed). "
                f"Choices: {{{', '.join(states)}}}"
            ),
        )

    return parser


# ── Entrypoint ────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    """
    Entrypoint for `vs-show-variants`.

    :param argv: (list[str] | None) Argument list to parse. Defaults to `sys.argv[1:]` when *None*, which is the normal runtime behaviour. Pass an explicit list when calling from tests to avoid touching the real process arguments.

    :return: (None)
    """
    argv_list: list[str] = argv if argv is not None else sys.argv[1:]
    argv_set: set[str] = set(argv_list)

    # If help is requested without a file we cannot build the dynamic group
    # args yet.  Show a static help page with a note explaining that group
    # filter flags will appear once -f is supplied.
    if _HELP_FLAGS & argv_set and not (_FILE_FLAGS & argv_set):
        static_parser = argparse.ArgumentParser(
            description=_DESCRIPTION,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=_DYNAMIC_ARGS_NOTE,
        )
        _add_static_args(static_parser)
        static_parser.parse_args(["--help"])
        return  # unreachable — parse_args exits via SystemExit

    # Pre-parse only the file path so we can load the JSON before building
    # the full (dynamically extended) argument parser.
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("-f", "--file", required=True)
    pre_args, _ = pre.parse_known_args(argv_list)

    json_path = Path(pre_args.file)
    if not json_path.is_file():
        raise SystemExit(f"error: file not found — {json_path}")

    data = load_vs_json(json_path)
    parser = _build_parser(data)
    args = parser.parse_args(argv_list)

    # Build per-group filter map:  group_code → [state, …]  or  []  (no filter)
    user_filters: Dict[str, List[str]] = {
        group["code"]: getattr(args, group["code"].replace("-", "_")) or [] for group in data["variantgroups"]
    }

    # ── Variant output ────────────────────────────────────────────────────────
    variants = generate_variants(data, user_filters)

    active_filters = {k: v for k, v in user_filters.items() if v}
    filter_note = "  Filters: " + ", ".join(f"--{k} {v}" for k, v in active_filters.items()) if active_filters else ""

    sep = "─" * 64
    print(sep)
    print(f"  Variants  ({len(variants)} total)")
    if filter_note:
        print(filter_note)
    print(sep)
    for v in variants:
        print(f"  {v}")
    print(sep)

    # ── Optional validation ───────────────────────────────────────────────────
    if args.validate:
        # Validate against the processed variant list (skipVariants removed,
        # allowedVariants applied) with no user filters.
        all_variants = generate_variants(data, {})
        patterns = extract_patterns(data)
        invalid = find_invalid_patterns(patterns, all_variants, data)

        print()
        print(sep)
        if invalid:
            print(f"  Validation — {len(invalid)} unmatched expansion(s)")
            print(sep)
            for field_path, original, expanded in invalid:
                if expanded != original:
                    print(f"  {field_path}")
                    print(f"    template : {original!r}")
                    print(f"    expanded : {expanded!r}")
                else:
                    print(f"  {field_path:<58}  →  {original!r}")
        else:
            print("  Validation — all patterns match at least one variant ✓")
        print(sep)


if __name__ == "__main__":
    main()
