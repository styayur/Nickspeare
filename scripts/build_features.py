#!/usr/bin/env python3
"""Extract play-feature words from the Folger Digital Texts.

This is the Python counterpart to ``R/extract_features.R``.  It reads the TEI
Simple XML plays, attributes speeches to speakers, and extracts:

* ``tavern``  — characteristic words of Falstaff's Eastcheap crew (Henry IV).
* ``kings``   — characteristic words of Henry V / the Chorus (Agincourt).
* ``archaic`` — high-frequency Early Modern function words, ranked.

Output is written to ``data/features/*.json`` and merged by ``Lexicon`` at
runtime, so the generator keeps working even without R installed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from nickspeare import corpus  # noqa: E402
from nickspeare.lexicon import ARCHAIC_CONNECTIVES  # noqa: E402

TAVERN_SPEAKERS = {
    "Falstaff", "Poins", "Bardolph", "Peto", "Gadshill", "MistressQuickly",
    "Vintner", "Francis", "DollTearsheet", "Pistol", "Nym", "Hostess",
}
KINGS_SPEAKERS = {"HenryV", "Chorus", "Exeter", "Westmoreland", "Fluellen"}

STOPWORDS = {
    "the", "and", "that", "this", "with", "for", "you", "your", "his", "her",
    "our", "their", "shall", "will", "would", "should", "could", "have", "has",
    "had", "but", "not", "nor", "from", "they", "them", "then", "than", "when",
    "what", "where", "which", "who", "whom", "whose", "all", "are", "was",
    "were", "be", "been", "being", "am", "is", "it", "its", "we", "us", "our",
    "i", "my", "me", "he", "she", "him", "himself", "herself", "myself",
    "thyself", "thy", "thine", "thee", "thou", "so", "such", "as", "if", "of",
    "to", "in", "on", "at", "by", "a", "an", "do", "doth", "dost", "did",
    "does", "say", "said", "says", "now", "here", "there", "thus", "well",
    "good", "come", "go", "let", "make", "made", "take", "took", "give",
    "gave", "know", "think", "man", "men", "day", "night", "time", "life",
    "death", "world", "hand", "heart", "eyes", "head", "king", "king's",
    "prince", "lord", "lords", "sir", "sirs", "o", "oh", "ha", "come",
}


def _norm(word: str) -> str:
    return re.sub(r"[^a-z]", "", word.lower())


# Character/proper names that should not leak into the feature lists.
PROPER_NAMES = {
    "hal", "nym", "falstaff", "hostess", "pistol", "doll", "shallow",
    "bardolph", "poins", "gadshill", "wart", "shadow", "robert", "feeble",
    "mouldy", "bullcalf", "francis", "peto", "kate", "katherine", "fluellen",
    "westmoreland", "exeter", "henry", "vintner", "chamberlain", "davy",
    "fang", "snare", "cole", "monmouth", "dauphin", "cambridge", "scroop",
    "grey", "montjoy", "bourbon", "orleans", "rambures", "constable", "jamy",
    "macmorris", "gower", "canterbury", "ely", "alice", "burgundy", "bedford",
    "gloucester", "clarence", "warwick", "harcourt", "salisbury", "york",
    "lancaster", "douglas", "hotspur", "glendower", "worcester", "vernon",
    "mortimer", "northumberland", "blunt", "sheriff", "ostler", "carriers",
    "john", "thomas", "francisco", "michael", "bates", "williams", "court",
}


def _speaker_matches(speaker_ids: list[str], names: set[str]) -> bool:
    for sid in speaker_ids:
        for name in names:
            if sid == name or sid.startswith(name + "_"):
                return True
    return False


def _freqs(speeches, names: set[str]) -> Counter:
    counter: Counter = Counter()
    for sp in speeches:
        if not _speaker_matches(sp["speakers"], names):
            continue
        for w in sp["words"]:
            w = _norm(w)
            if len(w) < 3 or w in STOPWORDS or w in PROPER_NAMES:
                continue
            counter[w] += 1
    return counter


def top_characteristic(target: Counter, other: Counter, n: int = 40) -> list[str]:
    ranked = []
    for word, count in target.items():
        score = count / (1 + other.get(word, 0))
        if count < 2:
            continue
        ranked.append((score, count, word))
    ranked.sort(reverse=True)
    return [w for _, _, w in ranked[:n]]


def archaic_ranking(speeches, n: int = 40) -> list[str]:
    counts: Counter = Counter()
    for sp in speeches:
        for w in sp["words"]:
            w = _norm(w)
            if w in ARCHAIC_CONNECTIVES:
                counts[w] += 1
    return [w for w, _ in counts.most_common(n)]


def build(folger_dir: Path, out_dir: Path) -> None:
    plays: dict[str, list[dict]] = {}
    for code in ("1H4", "2H4", "H5"):
        path = folger_dir / f"{code}.xml"
        if not path.exists():
            print(f"warning: missing {path}", file=sys.stderr)
            continue
        parsed = corpus.parse_folger(path)
        plays[code] = parsed["speeches"]

    tavern = Counter()
    kings = Counter()
    all_speeches: list[dict] = []
    for code, speeches in plays.items():
        all_speeches.extend(speeches)
        tavern.update(_freqs(speeches, TAVERN_SPEAKERS))
        kings.update(_freqs(speeches, KINGS_SPEAKERS))

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tavern.json").write_text(
        json.dumps({"tavern": top_characteristic(tavern, kings, 40)}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "kings.json").write_text(
        json.dumps({"kings": top_characteristic(kings, tavern, 40)}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "archaic.json").write_text(
        json.dumps({"archaic": archaic_ranking(all_speeches, 40)}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote tavern/kings/archaic features to {out_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folger-dir", type=Path,
                        default=REPO / ".cache" / "corpus" / "folger" / "FolgerDigitalTexts_XML_Complete")
    parser.add_argument("--out", type=Path, default=REPO / "nickspeare" / "data" / "features")
    args = parser.parse_args()
    build(args.folger_dir, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())