"""Orchestrates the five-stage pipeline.

Pipeline: 词库分类 -> 文本抽取 -> 核心逻辑性组合 -> 音韵融合与截取 -> 数字加缀
(lexicon classification -> text extraction -> logical combination ->
phonetic fusion & truncation -> numeric suffix).
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import combinators, corpus, phonetics as ph, suffixes
from .lexicon import Lexicon
from .provenance import evidence, describe_year, atlas

_RULES = {
    "rogue_to_king": combinators.rogue_to_king,
    "quote_splice": combinators.quote_splice,
    "archaic_coinage": combinators.archaic_coinage,
    "markov_coin": combinators.markov_coin,
    "markov_epithet": combinators.markov_epithet,
}

_STYLES = ("lower", "camel", "title", "snake", "kebab", "upper")


@dataclass
class Nickname:
    core: str
    variant: str
    kind: str
    parts: list[str] = field(default_factory=list)
    description: str = ""
    suffix: str = ""
    provenance: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "variant": self.variant,
            "core": self.core,
            "kind": self.kind,
            "parts": self.parts,
            "description": self.description,
            "suffix": self.suffix,
            "provenance": self.provenance,
        }


def _style_word(core: str, style: str) -> str:
    core = core.strip()
    if style == "lower":
        return core.lower()
    if style == "upper":
        return core.upper()
    if style == "camel":
        # Split on existing separators and boundaries between letter and digit.
        chunks = re.split(r"[\s_\-]+", core)
        pieces = []
        for ch in chunks:
            pieces.extend(re.findall(r"[A-Za-z]+|[0-9]+", ch) or [ch])
        out = ""
        for i, p in enumerate(pieces):
            if p.isdigit():
                out += p
            elif i == 0:
                out += p[0].lower() + p[1:]
            else:
                out += p[0].upper() + p[1:].lower()
        return out
    if style == "title":
        return ph.title(core)
    if style == "snake":
        return re.sub(r"[^a-z0-9]+", "_", core.lower()).strip("_")
    if style == "kebab":
        return re.sub(r"[^a-z0-9]+", "-", core.lower()).strip("-")
    raise ValueError(f"unknown style {style!r}")


class NicknameGenerator:
    def __init__(self, seed: int | None = None,
                 corpus_paths: list[str | Path] | None = None,
                 data_dir: str | Path | None = None,
                 markov_order: int = 3, royal_affinity: float = .65):
        if not 0 <= royal_affinity <= 1:
            raise ValueError("royal_affinity must be between 0 and 1")
        self.royal_affinity = royal_affinity
        self.corpus_paths = [str(p) for p in corpus_paths or []]
        self.rng = random.Random(seed)
        self.seed = seed
        self.sequence = 0
        self.lexicon = Lexicon(data_dir=data_dir)
        self.markov = corpus.CharMarkov(order=markov_order)
        self._train_markov()
        self.word_marks = self._train_word_markov(corpus_paths)

    def _train_markov(self) -> None:
        seeds = [ph.normalize(w) for w in self.lexicon.all_seed_words()]
        self.markov.train(seeds)

    def _train_word_markov(self, corpus_paths) -> corpus.WordMarkov:
        wm = corpus.WordMarkov(order=2)
        for quote in self.lexicon.quotes:
            wm.train(corpus.tokenize(quote["text"]))
        if corpus_paths:
            for path in corpus_paths:
                p = Path(path)
                try:
                    if p.is_dir():
                        for xml in sorted(p.glob("*.xml")):
                            parsed = corpus.parse_folger(xml)
                            for sp in parsed["speeches"]:
                                wm.train(corpus.tokenize(" ".join(sp["words"])))
                    elif p.suffix.lower() in (".xml",):
                        parsed = corpus.parse_folger(p)
                        for sp in parsed["speeches"]:
                            wm.train(corpus.tokenize(" ".join(sp["words"])))
                    else:
                        for line in corpus.load_text(p).splitlines():
                            wm.train(corpus.tokenize(line))
                except OSError as exc:
                    raise ValueError(f"cannot read corpus {p}") from exc
        return wm

    def generate_one(self, rule: str | None = None,
                     style: str = "camel",
                     suffix: str = "year",
                     year_theme: str | None = None,
                     digits: int | None = None) -> Nickname:
        rng = self.rng
        if style not in _STYLES:
            raise ValueError(f"unknown style {style!r}")
        if suffix not in (None, "none", "year", "number", "both"):
            raise ValueError(f"unknown suffix {suffix!r}")
        if year_theme and year_theme not in suffixes.HISTORICAL_YEARS:
            raise ValueError(f"unknown year theme {year_theme!r}")
        if digits is not None and (not isinstance(digits, int) or not 1 <= digits <= 8):
            raise ValueError("digits must be an integer between 1 and 8")
        if rule and rule not in _RULES:
            raise ValueError(f"unknown rule {rule!r}; choose from {sorted(_RULES)}")

        if rule == "markov_coin":
            fusion = combinators.markov_coin(self.lexicon, rng, self.markov)
        elif rule == "markov_epithet":
            fusion = combinators.markov_epithet(self.lexicon, rng, self.word_marks)
        elif rule == "archaic_coinage":
            fusion = combinators.archaic_coinage(self.lexicon, rng, self.markov)
        elif rule == "rogue_to_king":
            fusion = combinators.rogue_to_king(self.lexicon, rng, year_theme, self.royal_affinity)
        elif rule == "quote_splice":
            fusion = combinators.quote_splice(self.lexicon, rng)
        else:
            chosen = rng.choice(list(_RULES))
            return self.generate_one(chosen, style, suffix, year_theme, digits)

        core = fusion.text
        applied_suffix = ""
        suffix_kind = suffix
        if suffix in ("year", "number", "both") and not re.search(r"\d$", core):
            if suffix == "year":
                applied_suffix = suffixes.pick_year(rng, year_theme)
            elif suffix == "number":
                applied_suffix = suffixes.pick_number(rng, digits)
            else:
                suffix_kind = "year" if rng.random() < 0.5 else "number"
                applied_suffix = suffixes.pick_year(rng, year_theme) if suffix_kind == "year" else suffixes.pick_number(rng, digits)
            core = f"{core}{applied_suffix}"

        self.sequence += 1
        sources = [evidence(part, self.lexicon) for part in fusion.parts]
        quotes = [q for q in self.lexicon.quotes if fusion.kind == "quote_splice" and q["text"] in fusion.description]
        return Nickname(
            core=fusion.text,
            variant=_style_word(core, style),
            kind=fusion.kind,
            parts=fusion.parts,
            description=fusion.description,
            suffix=applied_suffix,
            provenance={"schema_version": 1, "engine": "python-1.1", "seed": self.seed,
                        "sequence": self.sequence, "sources": sources, "quotes": quotes,
                        "markov_order": self.markov.order,
                        "royal_affinity": self.royal_affinity,
                        "options": {"rule": rule, "style": style, "suffix": suffix, "year_theme": year_theme, "digits": digits},
                        "source_manifest": atlas().get("sources", []),
                        "additional_corpus_paths": self.corpus_paths,
                        "date": describe_year(applied_suffix, suffix_kind),
                        "trace": (fusion.trace or [{"stage": "Input", "value": " + ".join(fusion.parts)},
                                  {"stage": "Transformation", "value": fusion.text}]) +
                                 [{"stage": "Inscription", "value": _style_word(core, style)}],
                        "interpretation": "Semantic cohorts are editorial lenses; attestation belongs to input words, not the invented name."},
        )

    def generate(self, count: int = 10, rule: str | None = None,
                 style: str = "camel", suffix: str = "year",
                 year_theme: str | None = None, digits: int | None = None,
                 dedupe: bool = True) -> list[Nickname]:
        if style not in _STYLES:
            raise ValueError(f"unknown style {style!r}; choose from {_STYLES}")
        if not isinstance(count, int) or not 0 <= count <= 10000:
            raise ValueError("count must be an integer between 0 and 10000")
        out: list[Nickname] = []
        seen: set[str] = set()
        attempts = 0
        while len(out) < count and attempts < count * 40:
            attempts += 1
            nick = self.generate_one(rule, style, suffix, year_theme, digits)
            if dedupe and nick.variant in seen:
                continue
            seen.add(nick.variant)
            out.append(nick)
        if len(out) != count:
            raise RuntimeError(f"only {len(out)} distinct names found in {attempts} attempts; reduce count or disable dedupe")
        return out


def generate(count: int = 10, seed: int | None = None, **kwargs) -> list[Nickname]:
    """Convenience function: build a generator and emit ``count`` nicknames."""
    gen = NicknameGenerator(seed=seed)
    return gen.generate(count, **kwargs)
