"""Text extraction and Markov models.

Two engines inspired by the referenced projects:

* :class:`WordMarkov` — word-level Markov chain, the technique used by
  ``devjason/markov_poem`` (line-oriented reseeding included).
* :class:`CharMarkov` — character-level n-gram model, the technique used by
  ``Rickmsd/namemaker`` for name generation.

Both are dependency-free and train on any iterable of tokens.
"""

from __future__ import annotations

import random
import re
import xml.etree.ElementTree as ET
from pathlib import Path

_TEI = "{http://www.tei-c.org/ns/1.0}"
_TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")


def tokenize(text: str) -> list[str]:
    """Lower-case and split Early Modern English text into word tokens."""
    return [m.group(0) for m in _TOKEN_RE.finditer(text.lower())]


class CharMarkov:
    """Character-level n-gram Markov model for coinage-style name generation."""

    def __init__(self, order: int = 3):
        if int(order) != order or order < 1:
            raise ValueError("order must be a positive integer")
        self.order = order
        self._chain: dict[tuple[str, ...], list[str | None]] = {}

    def train(self, names: list[str]) -> "CharMarkov":
        for name in names:
            name = name.strip().lower()
            if not name:
                continue
            padded = ("^",) * self.order + tuple(name) + ("$",)
            for i in range(len(padded) - self.order):
                key = padded[i:i + self.order]
                nxt = padded[i + self.order]
                self._chain.setdefault(key, []).append(nxt)
        return self

    def generate(self, rng: random.Random, seed: str | None = None,
                 min_len: int = 4, max_len: int = 12, max_tries: int = 500) -> str:
        """Sample a name.  ``seed`` seeds the start n-gram when possible."""
        if not self._chain:
            return seed or ""
        for _ in range(max_tries):
            key: tuple[str, ...]
            if seed:
                pad = ("^",) * self.order
                seeded = pad + tuple(seed.lower())
                key = seeded[:self.order]
                if key not in self._chain:
                    key = rng.choice([k for k in self._chain if k[0] == "^"])
            else:
                key = rng.choice([k for k in self._chain if k[0] == "^"])

            out: list[str] = []
            for _ in range(max_len + self.order + 2):
                options = self._chain.get(key)
                if not options:
                    break
                nxt = rng.choice(options)
                if nxt == "$" or nxt is None:
                    break
                out.append(nxt)
                key = key[1:] + (nxt,)
            name = "".join(out)
            if min_len <= len(name) <= max_len:
                return name
        return seed or ""


class WordMarkov:
    """Word-level Markov chain for epithet/phrase generation (markov_poem style)."""

    def __init__(self, order: int = 2):
        self.order = max(1, int(order))
        self._db: dict[tuple[str, ...], list[str]] = {}
        self._starts: list[tuple[str, ...]] = []

    def train(self, tokens: list[str]) -> "WordMarkov":
        if len(tokens) <= self.order:
            return self
        for i in range(len(tokens) - self.order):
            key = tuple(tokens[i:i + self.order])
            nxt = tokens[i + self.order]
            self._db.setdefault(key, []).append(nxt)
            if key[0].istitle() or key[0][0].isupper():
                self._starts.append(key)
        if not self._starts:
            self._starts = [tuple(tokens[:self.order])]
        return self

    def generate(self, rng: random.Random, n_words: int = 4, max_words: int = 8) -> str:
        if not self._db:
            return ""
        current = list(rng.choice(self._starts))
        out: list[str] = []
        for _ in range(max_words):
            out.append(current[0])
            options = self._db.get(tuple(current))
            if not options:
                break
            nxt = rng.choice(options)
            current = current[1:] + [nxt]
        return " ".join(out[:n_words])


def load_text(path: str | Path) -> str:
    """Read a plain-text corpus file with encoding fallbacks."""
    p = Path(path)
    for enc in ("utf-8", "latin-1"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return p.read_text(encoding="utf-8", errors="ignore")


def load_tiny_shakespeare(path: str | Path) -> list[str]:
    """Load Karpathy's tiny Shakespeare ``input.txt`` and tokenize it."""
    return tokenize(load_text(path))


def load_gutenberg(path: str | Path) -> list[str]:
    """Load Gutenberg's complete works and strip the header/footer boilerplate."""
    text = load_text(path)
    # Project Gutenberg texts are bracketed by these markers.
    start = text.find("*** START")
    end = text.find("*** END")
    if start != -1:
        start = text.find("\n", start) + 1
    if end != -1:
        text = text[start:end]
    else:
        text = text[start:]
    return tokenize(text)


def parse_folger(path: str | Path) -> dict[str, object]:
    """Parse a Folger TEI Simple XML play.

    Returns ``{"title": str, "speeches": [{"speaker": str, "words": [str]}]}``.
    Stage-direction words are captured separately as ``"stage_words"``.
    """
    root = ET.parse(str(path)).getroot()
    title = ""
    for el in root.iter(f"{_TEI}title"):
        if el.text and el.text.strip():
            title = el.text.strip()
            break

    speeches: list[dict[str, object]] = []
    stage_words: list[str] = []
    for sp in root.iter(f"{_TEI}sp"):
        who = sp.attrib.get("who", "")
        speaker_ids = [s.strip() for s in who.split("#") if s.strip()]
        primary = speaker_ids[0] if speaker_ids else ""
        words: list[str] = []
        for w in sp.iter(f"{_TEI}w"):
            if w.text and w.text.strip():
                words.append(w.text.strip())
        if words:
            speeches.append(
                {"speaker": primary, "speakers": speaker_ids, "words": words}
            )
    for st in root.iter(f"{_TEI}stage"):
        for w in st.iter(f"{_TEI}w"):
            if w.text and w.text.strip():
                stage_words.append(w.text.strip())
    return {"title": title, "speeches": speeches, "stage_words": stage_words}