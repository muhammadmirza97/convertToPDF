"""Command-line interface driven by the same tool registry as the GUI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.config import CATEGORIES, DEFAULT_OUTPUT_DIR
from src.converter import run_tool
from src.office_tools import find_libreoffice
from src.tool_registry import KIND_BOOL, find_tool, tools_in_category


def _print_tools() -> None:
    libreoffice = find_libreoffice()
    for category in CATEGORIES:
        tools = tools_in_category(category)
        if not tools:
            continue
        print(f"\n{category}")
        for tool in tools:
            flag = ""
            if tool.requires == "libreoffice" and not libreoffice:
                flag = "  [needs LibreOffice - not detected]"
            print(f"  {tool.id:<16} {tool.description}{flag}")


def _print_tool_help(tool_id: str) -> int:
    tool = find_tool(tool_id)
    if tool is None:
        print(f"Unknown tool: {tool_id}. Use --list to see the available tools.")
        return 2
    print(f"{tool.id} - {tool.label}")
    print(f"  Category: {tool.category}")
    print(f"  Accepts:  {tool.accepts_label}")
    print(f"  {tool.description}")
    if tool.hint:
        print(f"  Note: {tool.hint}")
    if not tool.options:
        print("  No options.")
        return 0
    print("  Options (--set key=value):")
    for option in tool.options:
        detail = f"    {option.key:<18} {option.label}"
        if option.choices:
            detail += f" [{' | '.join(option.choices)}]"
        if option.kind == KIND_BOOL:
            detail += " [true | false]"
        detail += f" (default: {option.default!r})"
        print(detail)
    return 0


def _parse_settings(pairs: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"Use --set key=value, not {pair!r}.")
        key, value = pair.split("=", 1)
        values[key.strip()] = value
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Local PDF Toolbox command line. All processing stays on this computer."
    )
    parser.add_argument("tool", nargs="?", help="Tool id, for example rotate_pdf. Use --list to see all.")
    parser.add_argument("input", nargs="*", help="One or more input files.")
    parser.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT_DIR), help="Output folder.")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="Tool option.")
    parser.add_argument("--list", action="store_true", help="List every tool and exit.")
    parser.add_argument("--help-tool", metavar="TOOL", help="Show the options for one tool and exit.")
    args = parser.parse_args(argv)

    if args.list:
        _print_tools()
        return 0
    if args.help_tool:
        return _print_tool_help(args.help_tool)
    if not args.tool:
        parser.print_help()
        return 2

    tool = find_tool(args.tool)
    if tool is None:
        print(f"Unknown tool: {args.tool}. Use --list to see the available tools.")
        return 2
    if not args.input:
        print(f"{tool.id} needs at least {tool.min_files} input file(s).")
        return 2

    files = [Path(item) for item in args.input]
    try:
        summary = run_tool(tool, files, args.output, _parse_settings(args.set), log_callback=print)
    except ValueError as exc:
        print(f"Could not start: {exc}")
        return 2

    for result in summary.results:
        for output in result.outputs:
            print(f"Created: {output}")
    return 0 if summary.ok else 1


if __name__ == "__main__":
    sys.exit(main())
