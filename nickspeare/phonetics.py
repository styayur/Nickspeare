"""Phonetic helpers for the fusion-and-truncation stage.

These are intentionally lightweight, dependency-free heuristics.  They follow
the spirit of ``Rickmsd/namemaker.estimate_syllables``: enough signal to make
nicknames *sound* like Early Modern English without requiring a full
pronouncing dictionary.
"""

from __future__ import annotations

import re
import unicodedata

_VOWELS = "aeiouy"
_EARLY_MODERN_AFFIXES = (
    "-eth", "-est", "-ly", "-er", "-s", "-es", "-ion", "-age",
    "-ing", "-ous", "-al", "-ance", "-ent", "-ess",
)


def normalize(word: str) -> str:
    """Lower-case and strip diacritics/ligatures into ASCII-ish form."""
    word = word.lower().strip()
    word = unicodedata.normalize("NFKD", word)
    word = "".join(ch for ch in word if not unicodedata.combining(ch))
    return word


def vowels(word: str) -> list[int]:
    """Return the indices of vowel letters in ``word``."""
    return [i for i, ch in enumerate(word) if ch in _VOWELS]


def vowel_groups(word: str) -> list[tuple[int, int]]:
    """Return (start, end) spans of consecutive vowels."""
    groups: list[tuple[int, int]] = []
    start = None
    for i, ch in enumerate(word):
        if ch in _VOWELS:
            if start is None:
                start = i
        else:
            if start is not None:
                groups.append((start, i))
                start = None
    if start is not None:
        groups.append((start, len(word)))
    return groups


def estimate_syllables(word: str) -> int:
    """Approximate syllable count as the number of vowel groups."""
    word = normalize(word)
    if not word:
        return 0
    # A trailing silent-ish ``e`` should not count as a syllable of its own.
    groups = vowel_groups(word)
    count = len(groups)
    if count > 1 and word.endswith("e") and groups[-1] == (len(word) - 1, len(word)):
        count -= 1
    return max(1, count)


def split_onset(word: str) -> tuple[str, str]:
    """Split ``word`` into (consonant onset, remainder)."""
    word = normalize(word)
    for i, ch in enumerate(word):
        if ch in _VOWELS:
            return word[:i], word[i:]
    return word, ""


def blend(a: str, b: str) -> str:
    """Fuse two stems on the longest shared letter bridge.

    ``blend("sack", "agincourt")`` -> ``"sackincourt"`` (bridges nothing), while
    ``blend("honour", "ourbattle")`` would bridge on the shared ``our``.
    """
    a = normalize(a)
    b = normalize(b)
    if not a:
        return b
    if not b:
        return a
    limit = min(len(a), len(b))
    for n in range(limit, 1, -1):
        if a[-n:] == b[:n]:
            return a + b[n:]
    return a + b


def syllabic_blend(a: str, b: str) -> str:
    """Blend on a syllable boundary: keep a's onset-free tail and b's onset.

    This produces smoother coinages than raw overlap blending, e.g.
    ``syllabic_blend("agincourt", "crispin")`` -> ``"agincrispin"``.
    """
    a = normalize(a)
    b = normalize(b)
    if not a or not b:
        return a + b
    direct = blend(a, b)
    if direct not in (a + b,):
        return direct
    # Cut trailing consonant cluster of ``a`` so it runs into ``b``'s onset.
    tail = a.rstrip(_VOWELS + "wh")
    if tail and len(tail) < len(a):
        return tail[:-1] + b
    return a + b


def truncate(word: str, keep: int, affix: str | None = None) -> str:
    """Truncate ``word`` to ``keep`` letters and optionally append an affix."""
    word = normalize(word)
    core = word[:keep]
    if affix:
        core = core + affix
    return core


def deform(word: str, seed: int = 0) -> str:
    """Apply a small, deterministic Early-Modern-looking deformation.

    Doubles a consonant or swaps a vowel so a common word reads like a coined
    proper name ("kings" -> "kingz", "rose" -> "rosse").
    """
    word = normalize(word)
    if not word:
        return word
    import random
    rng = random.Random(seed)
    forms = []
    # Double a medial consonant.
    for i, ch in enumerate(word):
        if ch not in _VOWELS and i > 0 and ch not in "xy":
            forms.append(word[:i] + ch + word[i:])
    # Drop a trailing silent e.
    if word.endswith("e"):
        forms.append(word[:-1])
    # Replace terminal s with z.
    if word.endswith("s"):
        forms.append(word[:-1] + "z")
    if not forms:
        return word
    return rng.choice(forms)


def alliterate(*words: str) -> bool:
    """True when every non-empty word shares its initial letter."""
    initials = [normalize(w)[0] for w in words if w]
    return len(initials) > 1 and all(i == initials[0] for i in initials)


def assonate(a: str, b: str) -> bool:
    """True when two words share a dominant vowel."""
    va = {normalize(a)[i] for i in vowels(normalize(a))}
    vb = {normalize(b)[i] for i in vowels(normalize(b))}
    return bool(va & vb)


def title(word: str) -> str:
    """Title-case a possibly camel/snake/kebab word back into a display name."""
    word = re.sub(r"[_\-\s]+", " ", normalize(word))
    return "".join(p.capitalize() for p in word.split())


_EARLY_MODERN_SUFFIX_LIST = list(_EARLY_MODERN_AFFIXES)