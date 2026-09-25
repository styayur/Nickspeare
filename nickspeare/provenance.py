"""Auditable source evidence and deliberately modest orthographic scoring."""
import json
import re
from functools import lru_cache
from pathlib import Path

from . import phonetics as ph


@lru_cache(maxsize=1)
def atlas():
    path = Path(__file__).parent / "data" / "provenance.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"words": {}}


def rank_blends(a, b):
    """Rank spelling candidates; this is not reconstructed historical phonology."""
    candidates = [(ph.blend(a, b), "longest overlap"), (a + b, "concatenation")]
    groups = ph.vowel_groups(a)
    if len(groups) > 1:
        candidates.append((a[:groups[-1][0]] + b, "final vowel-group cut"))
    seen = set()
    ranked = []
    for text, method in candidates:
        if text in seen:
            continue
        seen.add(text)
        retention = min(1, len(text) / max(1, len(a + b)))
        clusters = sum(max(0, len(m) - 3) for m in re.findall(r"[^aeiouy]+", text))
        length_penalty = abs(len(text) - 12) / 12
        score = round(2 * retention - .35 * clusters - .3 * length_penalty, 4)
        ranked.append({"text": text, "method": method, "score": score,
                       "retention": round(retention, 4), "cluster_penalty": clusters})
    return sorted(ranked, key=lambda c: (-c["score"], c["text"]))


def evidence(part, lexicon):
    word = re.sub(r"[^a-z]", "", part.lower())
    item = atlas()["words"].get(word)
    factions = [k for k in ("tavern", "kings", "archaic") if part in lexicon.category(k)]
    return {"word": part, "editorial_categories": factions,
            "status": "attested" if item else "unverified seed or generated form",
            **(item or {"occurrences": [], "counts": {}, "log_odds": None})}


def describe_year(value, kind):
    if not value:
        return {"value": "", "kind": "none", "explanation": "No date appended."}
    if kind == "number":
        return {"value": value, "kind": "number", "explanation": "Random numeric ornament; no historical claim."}
    notes = {
        "1415": "Battle of Agincourt / Harfleur campaign: story-world history, not the play's composition date.",
        "1413": "Henry V's accession and coronation; the coronation precedes Agincourt by two years.",
        "1599": "The Globe opened; Henry V is generally dated around this year. Composition dates are approximate.",
        "1564": "Shakespeare's birth year; a biographical date.",
        "1616": "Shakespeare's death year; a biographical date.",
        "1623": "Publication of the First Folio; a publication date.",
        "1601": "Approximate dating of Hamlet; not an exact composition date.",
        "1606": "Approximate dating of Macbeth; not an exact composition date.",
        "1485": "Battle of Bosworth; story-world history.",
        "1066": "Battle of Hastings; a historical allusion, not a source date.",
        "1588": "Spanish Armada; an Elizabethan historical allusion.",
        "1605": "Gunpowder Plot; a Jacobean historical allusion.",
    }
    return {"value": value, "kind": "historical", "explanation": notes.get(value, "Historical allusion.")}
