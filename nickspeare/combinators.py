"""Core logical combination rules (``he xin luo ji xing zu he`` / 核心逻辑性组合).

The stage after text extraction.  Three fusion strategies implement the brief:

1. **Rogue-to-king semantic fusion** — tavern vocabulary is ennobled by
   Agincourt vocabulary: ``sack + agincourt + 1415``.
2. **Quote splicing with phonetic fusion** — famous lines are stripped of
   stop-words and their content words blended.
3. **Archaic coinage with truncation/deformation** — Early Modern function
   words and Markov chain output are bent into invented proper names.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from . import phonetics as ph

_STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "is", "be", "am",
    "are", "was", "were", "not", "that", "this", "these", "those", "with",
    "for", "from", "my", "our", "your", "their", "his", "her", "its", "i",
    "you", "we", "he", "she", "it", "they", "o", "out", "all", "such", "by",
    "as", "if", "but", "so", "nor", "than", "then", "when", "what", "where",
    "why", "how", "shall", "will", "would", "could", "should", "may", "might",
    "have", "has", "had", "do", "does", "did", "no", "yes", "into", "upon",
}


@dataclass
class Fusion:
    """A single generated coinage plus its provenance."""
    text: str
    kind: str
    parts: list[str] = field(default_factory=list)
    description: str = ""
    trace: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "kind": self.kind,
            "parts": self.parts,
            "description": self.description,
        }


def _stem(word: str) -> str:
    return re.sub(r"[^a-z]", "", ph.normalize(word))


def _content_words(quote: str) -> list[str]:
    words = re.findall(r"[a-z]+(?:'[a-z]+)?", quote.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) >= 4]


def rogue_to_king(lex, rng: random.Random, year_theme: str | None = None,
                  royal_affinity: float = .65) -> Fusion:
    """Fuse a tavern/rogue word with a king/Agincourt word.

    The canonical case is ``sack + agincourt + 1415``.  We alternate between a
    hard bridge-blend and a syllable-boundary blend for variety.
    """
    tavern = rng.choice(lex.category("tavern") or ["sack"])
    from .provenance import atlas
    import math
    choices = lex.category("kings") or ["agincourt"]
    weights = [math.exp(max(-3, min(3, atlas()["words"].get(_stem(w), {}).get("log_odds", 0))) *
                       (2 * royal_affinity - 1)) for w in choices]
    kings = rng.choices(choices, weights=weights, k=1)[0]
    a, b = _stem(tavern), _stem(kings)
    from .provenance import rank_blends
    candidates = rank_blends(a, b)
    best = candidates[0]
    core = best["text"]
    return Fusion(
        text=core,
        kind="rogue_to_king",
        parts=[tavern, kings],
        description=f"{tavern} + {kings}",
        trace=[{"stage": "Eastcheap", "value": a},
               {"stage": "Royal encounter", "value": b},
               {"stage": "Fusion", "value": core, "candidates": candidates}],
    )


def quote_splice(lex, rng: random.Random) -> Fusion:
    """Blend content words drawn from a famous Shakespeare line."""
    quotes = lex.quotes
    if not quotes:
        return Fusion(text="", kind="quote_splice", parts=[], description="no quotes")
    quote = rng.choice(quotes)
    words = _content_words(quote["text"])
    if not words:
        words = re.findall(r"[a-z]+", quote["text"].lower())
    picks = [_stem(w) for w in rng.sample(words, k=min(3, len(words)))]
    if len(picks) == 1:
        core = ph.truncate(picks[0], rng.randint(5, 8))
    else:
        core = picks[0]
        for nxt in picks[1:]:
            core = ph.blend(core, nxt)
    return Fusion(
        text=core,
        kind="quote_splice",
        parts=picks,
        description=f'"{quote["text"]}" ({quote["play"]})',
    )


def archaic_coinage(lex, rng: random.Random, markov=None) -> Fusion:
    """Coin a new word from an archaic connective or from Markov output."""
    archaic = lex.category("archaic") or ["prithee"]
    if markov is not None and rng.random() < 0.5:
        seed = rng.choice(lex.all_seed_words() or archaic)
        raw = markov.generate(rng, seed=_stem(seed), min_len=4, max_len=10)
        base = raw or _stem(seed)
    else:
        base = _stem(rng.choice(archaic))
    affix = rng.choice(lex.category("affixes") or ["-eth"]).lstrip("-")
    style = rng.random()
    if style < 0.34:
        core = ph.truncate(base, rng.randint(3, max(3, len(base) - 1)), affix)
    elif style < 0.67:
        core = ph.deform(base, rng.randint(0, 10_000))
    else:
        core = base + affix.lstrip("-")
    return Fusion(
        text=core,
        kind="archaic_coinage",
        parts=[base],
        description=f"{base} -> {core}",
    )


def markov_coin(lex, rng: random.Random, markov) -> Fusion:
    """A bare character-Markov coinage seeded from the classified library."""
    seeds = lex.all_seed_words() or ["sack"]
    seed = rng.choice(seeds)
    name = markov.generate(rng, seed=_stem(seed), min_len=4, max_len=12)
    return Fusion(
        text=name or _stem(seed),
        kind="markov_coin",
        parts=[seed],
        description=f"markov seeded by {seed}",
    )


def _year_suffix(rng: random.Random, theme: str | None) -> str:
    from . import suffixes
    return suffixes.pick_year(rng, theme)


def markov_epithet(lex, rng: random.Random, word_markov) -> Fusion:
    """A word-level Markov epithet in the manner of devjason/markov_poem.

    Produces a short multi-word phrase (e.g. "the valiant rogue of agincourt")
    which downstream styling turns into a nickname.
    """
    phrase = ""
    if word_markov is not None:
        phrase = word_markov.generate(rng, n_words=rng.randint(2, 4), max_words=6)
    words = [w for w in phrase.split() if w]
    if not words:
        seeds = lex.all_seed_words() or ["sack", "agincourt"]
        words = rng.sample(seeds, k=min(3, len(seeds)))
    return Fusion(
        text=" ".join(words),
        kind="markov_epithet",
        parts=words,
        description="word-markov: " + (" ".join(words) if words else ""),
    )


def combine(lex, rng: random.Random, markov, word_markov=None) -> Fusion:
    """Randomly dispatch to one of the available combination rules."""
    rules = [rogue_to_king, quote_splice, archaic_coinage, markov_coin, markov_epithet]
    rule = rng.choice(rules)
    if rule is markov_coin:
        return rule(lex, rng, markov)
    if rule is archaic_coinage:
        return rule(lex, rng, markov)
    if rule is markov_epithet:
        return rule(lex, rng, word_markov)
    return rule(lex, rng)
