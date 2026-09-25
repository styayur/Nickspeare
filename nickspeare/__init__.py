"""Nickspeare — a Shakespearean nickname/username generator.

The generator fuses Early Modern English vocabulary with the semiotics of
Shakespeare's history plays: tavern rogues (Falstaff, Eastcheap) on one side
and the martial kingship of Agincourt on the other.  It is inspired by
devjason/markov_poem (word-level Markov text generation) and Rickmsd/namemaker
(character-level Markov name generation).
"""

from .generator import NicknameGenerator, generate
from . import lexicon, corpus, phonetics, combinators, suffixes

__version__ = "1.1.0"
__all__ = ["NicknameGenerator", "generate", "lexicon", "corpus", "phonetics", "combinators", "suffixes"]
