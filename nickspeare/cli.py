"""Command-line interface for Nickspeare."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, data, generator


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    parser.add_argument("--corpus", action="append", default=None, metavar="PATH",
                        help="optional corpus file/dir (Folger XML, plain text) for richer output")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nickspeare",
        description="Generate Shakespearean nicknames (酒馆浪子 -> 王者阿金库尔).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    gen = sub.add_parser("generate", help="generate nicknames")
    gen.add_argument("-n", "--count", type=int, default=10)
    gen.add_argument("--rule", choices=sorted(generator._RULES) + ["all"],
                     default="all", help="combination rule (default: all)")
    gen.add_argument("--style", choices=generator._STYLES, default="camel",
                     help="output casing")
    gen.add_argument("--suffix", choices=("year", "number", "both", "none"),
                     default="year", help="numeric suffix family")
    gen.add_argument("--year-theme", default=None,
                     help="pin the historical year (e.g. agincourt, globe)")
    gen.add_argument("--digits", type=int, default=None, help="digit count for number suffix")
    gen.add_argument("--royal-affinity", type=float, default=.65,
                     help="royal log-odds weighting from 0 to 1 (default: .65)")
    gen.add_argument("--no-dedupe", action="store_true", help="allow duplicate results")
    gen.add_argument("--json", action="store_true", help="emit JSON with provenance")
    _add_common(gen)

    dl = sub.add_parser("data", help="download the public-domain corpora")
    dl.add_argument("--cache", default=None, help="cache directory")
    dl.add_argument("--complete", action="store_true", help="download the full Folger set")
    _add_common(dl)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "data":
        try:
            paths = data.ensure_all(args.cache)
            if args.complete:
                paths["folger"] = data.ensure_folger(args.cache, complete=True)
            for name, path in paths.items():
                print(f"{name}: {path}")
        except Exception as exc:  # pragma: no cover - network path
            print(f"error downloading corpora: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.command == "generate":
        rule = None if args.rule == "all" else args.rule
        suffix = None if args.suffix == "none" else args.suffix
        gen = generator.NicknameGenerator(seed=args.seed, corpus_paths=args.corpus, royal_affinity=args.royal_affinity)
        nicks = gen.generate(
            count=args.count,
            rule=rule,
            style=args.style,
            suffix=suffix,
            year_theme=args.year_theme,
            digits=args.digits,
            dedupe=not args.no_dedupe,
        )
        if args.json:
            print(json.dumps([n.as_dict() for n in nicks], ensure_ascii=False, indent=2))
        else:
            for n in nicks:
                line = n.variant
                if n.description:
                    line += f"\t# {n.description}"
                print(line)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
