"""Numeric suffix stage: historical years and ordinary numbers.

The "rogue to king" arc is anchored in dates.  ``sack`` + ``agincourt`` +
``1415`` is the canonical fusion: the tavern wit is ennobled on St Crispin's
Day.  We also support arbitrary 1--4 digit suffixes for everyday usernames.
"""

from __future__ import annotations

import random

#: Historically resonant dates for Shakespeare's world.
HISTORICAL_YEARS: dict[str, str] = {
    "agincourt": "1415",
    "harfleur": "1415",
    "st_crispin": "1415",
    "henry_v_crowned": "1413",
    "bosworth": "1485",
    "hastings": "1066",
    "globe": "1599",
    "shakespeare_born": "1564",
    "shakespeare_died": "1616",
    "hamlet": "1601",
    "macbeth": "1606",
    "first_folio": "1623",
    "spanish_armada": "1588",
    "gunpowder_plot": "1605",
}

#: Short tags that select the year family above.
_YEAR_KEYS = tuple(HISTORICAL_YEARS)


def pick_year(rng: random.Random, theme: str | None = None) -> str:
    """Return a historical year string, optionally pinned to a theme."""
    if theme and theme in HISTORICAL_YEARS:
        return HISTORICAL_YEARS[theme]
    return HISTORICAL_YEARS[rng.choice(_YEAR_KEYS)]


def pick_number(rng: random.Random, digits: int | None = None) -> str:
    """Return a random 2--4 digit number suitable as a username suffix."""
    digits = digits or rng.choice((2, 3, 4))
    low = 10 ** (digits - 1)
    high = 10 ** digits - 1
    return str(rng.randint(low, high))


def suffix(name: str, rng: random.Random, kind: str = "year",
           theme: str | None = None, digits: int | None = None,
           separator: str = "") -> str:
    """Append a numeric suffix to ``name``.

    kind: ``"year"`` uses a historically resonant date, ``"number"`` uses a
    plain random number, ``"both"`` picks one at random.
    """
    if kind == "number":
        tail = pick_number(rng, digits)
    elif kind == "both":
        tail = pick_year(rng, theme) if rng.random() < 0.5 else pick_number(rng, digits)
    else:
        tail = pick_year(rng, theme)
    return f"{name}{separator}{tail}"