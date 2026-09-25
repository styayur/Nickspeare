"""Classified Shakespearean word library (``ci ku fen lei`` / 词库分类).

Every category is a curated, source-attributable word list drawn from the
public-domain corpora this project consumes:

* Project Gutenberg, *The Complete Works of William Shakespeare* (#100)
* Karpathy's *tiny Shakespeare* training set (char-rnn)
* Folger Shakespeare Digital Texts (TEI Simple XML)
* Hyperbard, an NLP/graph database of the plays built on Folger (stand-in for
  the "hisent" NLP resource the brief mentions)

The ``Lexicon`` class merges these curated seeds with machine-extracted
feature lists produced by ``scripts/build_features.py`` (or the R pipeline in
``R/extract_features.R``).
"""

from __future__ import annotations

import json
from pathlib import Path

TAVERN = [
    # Falstaff's Eastcheap / Boar's Head vocabulary (Henry IV 1 & 2, Henry V).
    "sack", "canakin", "tapster", "varlet", "rogue", "knave", "rascal",
    "wassail", "tavern", "ale", "boar", "drawer", "harlotry", "lewdster",
    "reveller", "roisterer", "ruffian", "miscreant", "cozener", "pickpurse",
    "flapdragon", "bombard", "quart", "pottle", "halfpenny", "dudgeon",
    "cudgel", "riot", "revel", "revelry", "humour", "belly", "docket",
    "counterfeit", "roguery", "brawler", "ribald", "gadshill", "eastcheap",
]

KINGS = [
    # Henry V / Agincourt martial-royal vocabulary.
    "agincourt", "harfleur", "crispin", "crispian", "saint", "honour",
    "valour", "crown", "majesty", "heraldry", "england", "harry", "monmouth",
    "leek", "banner", "battle", "triumph", "conquest", "sovereign", "royal",
    "sceptre", "throne", "gallant", "king", "glory", "victory", "sword",
    "standard", "horseman", "archer", "warrior", "chivalry", "armour",
    "regiment", "command", "empire", "realm", "diadem",
]

ARCHAIC_CONNECTIVES = [
    # High-frequency Early Modern English function words and interjections.
    "the", "thou", "thee", "thy", "thine", "ye", "anon", "prithee",
    "forsooth", "perchance", "wherefore", "alack", "alas", "hark", "whence",
    "betwixt", "ere", "dost", "doth", "hath", "shalt", "wilt", "art", "ay",
    "nay", "sirrah", "zounds", "marry", "beshrew", "gramercy", "certes",
    "sooth", "welladay", "god-den",
]

TITLES = [
    "king", "prince", "duke", "earl", "lord", "knight", "sir", "captain",
    "archbishop", "bishop", "herald", "squire", "page", "queen", "princess",
]

CHARACTERS = [
    "falstaff", "hal", "hotspur", "glendower", "pistol", "nimb", "bardolph",
    "poins", "john", "warwick", "westmoreland", "exeter", "fluellen", "montjoy",
    "hamlet", "ophelia", "macbeth", "lear", "othello", "desdemona", "romeo",
    "juliet", "mercutio", "puck", "ariel", "caliban", "prospero", "caesar",
    "brutus", "richard", "henry", "harry",
]

PLACES = [
    "england", "france", "agincourt", "harfleur", "london", "eastcheap",
    "windsor", "westminster", "wales", "scotland", "ireland", "denmark",
    "elsinore", "verona", "venice", "cyprus", "troy", "athens", "rome",
]

AFFIXES = [
    "-eth", "-est", "-ly", "-er", "-s", "-es", "-ion", "-age", "-ing",
    "-ous", "-al", "-ance", "-ent", "-ess", "-ish", "-ward", "-fold",
]

QUOTES = [
    {
        "key": "once_more_unto_the_breach",
        "text": "Once more unto the breach, dear friends, once more",
        "play": "Henry V",
        "speaker": "King Henry V",
    },
    {
        "key": "we_few_we_happy_few",
        "text": "We few, we happy few, we band of brothers",
        "play": "Henry V",
        "speaker": "King Henry V",
    },
    {
        "key": "cry_god_for_harry",
        "text": "Cry God for Harry, England, and Saint George",
        "play": "Henry V",
        "speaker": "King Henry V",
    },
    {
        "key": "to_be_or_not_to_be",
        "text": "To be, or not to be, that is the question",
        "play": "Hamlet",
        "speaker": "Hamlet",
    },
    {
        "key": "all_the_worlds_a_stage",
        "text": "All the world's a stage",
        "play": "As You Like It",
        "speaker": "Jaques",
    },
    {
        "key": "parting_is_such_sweet_sorrow",
        "text": "Parting is such sweet sorrow",
        "play": "Romeo and Juliet",
        "speaker": "Juliet",
    },
    {
        "key": "horse_my_kingdom",
        "text": "A horse, a horse, my kingdom for a horse",
        "play": "Richard III",
        "speaker": "Richard III",
    },
    {
        "key": "something_wicked",
        "text": "Something wicked this way comes",
        "play": "Macbeth",
        "speaker": "Second Witch",
    },
    {
        "key": "friends_romans_countrymen",
        "text": "Friends, Romans, countrymen, lend me your ears",
        "play": "Julius Caesar",
        "speaker": "Mark Antony",
    },
    {
        "key": "uneasy_lies_the_head",
        "text": "Uneasy lies the head that wears a crown",
        "play": "Henry IV, Part 2",
        "speaker": "King Henry IV",
    },
    {
        "key": "brave_new_world",
        "text": "O brave new world, that has such people in it",
        "play": "The Tempest",
        "speaker": "Miranda",
    },
    {
        "key": "rose_by_any_other_name",
        "text": "A rose by any other name would smell as sweet",
        "play": "Romeo and Juliet",
        "speaker": "Juliet",
    },
    {
        "key": "what_light_through_yonder",
        "text": "What light through yonder window breaks",
        "play": "Romeo and Juliet",
        "speaker": "Romeo",
    },
    {
        "key": "course_of_true_love",
        "text": "The course of true love never did run smooth",
        "play": "A Midsummer Night's Dream",
        "speaker": "Lysander",
    },
    {
        "key": "now_is_the_winter",
        "text": "Now is the winter of our discontent",
        "play": "Richard III",
        "speaker": "Richard III",
    },
    {
        "key": "out_damned_spot",
        "text": "Out, damned spot! out, I say",
        "play": "Macbeth",
        "speaker": "Lady Macbeth",
    },
]

CURATED = {
    "tavern": TAVERN,
    "kings": KINGS,
    "archaic": ARCHAIC_CONNECTIVES,
    "titles": TITLES,
    "characters": CHARACTERS,
    "places": PLACES,
    "affixes": AFFIXES,
    "quotes": QUOTES,
}


class Lexicon:
    """Merges curated seeds with extracted feature files.

    Feature files live in ``data/features/*.json`` and are produced by
    ``scripts/build_features.py`` (Python) or ``R/extract_features.R`` (R).
    Each file maps a category name to a list of word strings.
    """

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parent / "data"
        self.words: dict[str, list[str]] = {k: list(v) for k, v in CURATED.items() if k != "quotes"}
        self.quotes: list[dict] = [dict(q) for q in QUOTES]
        self._load_features()

    def _load_features(self) -> None:
        features_dir = self.data_dir / "features"
        if not features_dir.is_dir():
            return
        for path in sorted(features_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for category, items in payload.items():
                if not isinstance(items, list):
                    continue
                clean = [str(i) for i in items if isinstance(i, str) and i.strip()]
                bucket = self.words.setdefault(category, [])
                seen = set(bucket)
                for item in clean:
                    if item not in seen:
                        bucket.append(item)
                        seen.add(item)

    def category(self, name: str) -> list[str]:
        return self.words.get(name, [])

    def all_seed_words(self) -> list[str]:
        """Flatten every curated/feature word for Markov seeding."""
        seen: set[str] = set()
        out: list[str] = []
        for category in ("tavern", "kings", "archaic", "titles", "characters", "places"):
            for word in self.category(category):
                if word not in seen:
                    seen.add(word)
                    out.append(word)
        return out