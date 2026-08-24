"""Command-line interface for gnome-windeploy."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pefile

from gnome_windeploy import __version__
from gnome_windeploy.engine import DeployError, DeployOptions, DeployReport, deploy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gnome-windeploy",
        description=(
            "Deploy GNOME-platform desktop apps on Windows: gather the transitive "
            "DLL closure and all required runtime data into a relocatable bundle."
        ),
    )
    parser.add_argument("exes", nargs="+", metavar="EXE", help="compiled .exe file(s) to deploy")
    parser.add_argument(
        "--destdir",
        required=True,
        type=Path,
        metavar="DIR",
        help="output directory for the bundle (must not exist or be empty)",
    )
    parser.add_argument(
        "--dll-dir",
        action="append",
        type=Path,
        default=[],
        metavar="DIR",
        help="extra DLL search directory (repeatable)",
    )
    parser.add_argument(
        "--app-tree",
        type=Path,
        metavar="DIR",
        help="'meson install --destdir' tree merged into the bundle before "
        "dependency staging (app files win on collision)",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="RELDIR",
        help="force-mirror an extra prefix-relative directory (repeatable)",
    )
    parser.add_argument(
        "--icons",
        choices=("full", "scalable", "symbolic"),
        default="full",
        help="icon theme policy (default: full)",
    )
    parser.add_argument(
        "--locale-mode",
        choices=("deps", "full", "none"),
        default="deps",
        help="locale mirroring mode (default: deps)",
    )
    parser.add_argument(
        "--locale-langs",
        metavar="LIST",
        help="comma-separated language filter for deps locale mode, e.g. zh_CN,de",
    )
    parser.add_argument(
        "--gettext-domain",
        action="append",
        default=[],
        metavar="NAME",
        help="additional gettext domain to mirror locales for (repeatable)",
    )
    parser.add_argument("--zip", action="store_true", help="also create <destdir>.zip")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _validate(parser: argparse.ArgumentParser, args: argparse.Namespace) -> list[Path]:
    exes = []
    for raw in args.exes:
        exe = Path(raw)
        if not exe.is_file():
            parser.error(f"executable not found: {raw}")
        exes.append(exe)
    if args.destdir.exists():
        if not args.destdir.is_dir():
            parser.error(f"--destdir {args.destdir} exists and is not a directory")
        elif any(args.destdir.iterdir()):
            parser.error(f"--destdir {args.destdir} exists and is not empty")
    for dll_dir in args.dll_dir:
        if not dll_dir.is_dir():
            parser.error(f"--dll-dir directory not found: {dll_dir}")
    if args.app_tree is not None and not args.app_tree.is_dir():
        parser.error(f"--app-tree directory not found: {args.app_tree}")
    return exes


def _format_size(num: int) -> str:
    value = float(num)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            break
        value /= 1024
    return f"{num} B" if unit == "B" else f"{value:.1f} {unit}"


def _print_summary(report: DeployReport, verbose: bool) -> None:
    print("gnome-windeploy summary")
    print(f"  exes ({len(report.exes)}): {', '.join(report.exes)}")
    print(f"  DLLs: {len(report.dlls)}")
    if verbose:
        for name, origin in report.dlls.items():
            print(f"    {name} <- {origin}")
    print("  prefixes:")
    for prefix in report.prefixes:
        print(f"    {prefix}")
    print(f"  descriptors: {', '.join(report.descriptors)}")
    print(f"  staged files: {report.staged_files}")
    print(f"  output size: {_format_size(report.output_size)}")
    if report.zip_path is not None:
        print(f"  zip: {report.zip_path}")
    for line in report.overrides:
        print(f"  override: {line}")
    for line in report.collisions:
        print(f"  collision: {line}")
    for line in report.warnings:
        print(f"  warning: {line}")


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point; return 0 on success, 1 on any handled deployment error."""
    parser = build_parser()
    args = parser.parse_args(argv)
    exes = _validate(parser, args)
    langs = None
    if args.locale_langs:
        langs = [item.strip() for item in args.locale_langs.split(",") if item.strip()]
    options = DeployOptions(
        exes=exes,
        destdir=args.destdir,
        dll_dirs=[Path(directory) for directory in args.dll_dir],
        app_tree=args.app_tree,
        includes=list(args.include),
        icons=args.icons,
        locale_mode=args.locale_mode,
        locale_langs=langs,
        gettext_domains=list(args.gettext_domain),
        zip=args.zip,
    )
    try:
        report = deploy(options)
    except pefile.PEFormatError as exc:
        print(f"gnome-windeploy: error: not a valid PE binary: {exc}", file=sys.stderr)
        return 1
    except DeployError as exc:
        print(f"gnome-windeploy: error: {exc}", file=sys.stderr)
        return 1
    _print_summary(report, args.verbose)
    return 0
