"""Allow ``python -m nickspeare`` to behave like the CLI."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())