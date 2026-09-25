#!/usr/bin/env python3
"""Download the public-domain Shakespeare corpora into ``.cache/corpus``."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nickspeare import data  # noqa: E402


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", default=None)
    parser.add_argument("--complete", action="store_true")
    args = parser.parse_args()
    paths = data.ensure_all(args.cache)
    if args.complete:
        paths["folger"] = data.ensure_folger(args.cache, complete=True)
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())