#!/usr/bin/env python3
"""Build a reproducible evidence atlas from three locally cached Folger XML files."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nickspeare.lexicon import Lexicon
from nickspeare.suffixes import HISTORICAL_YEARS
from nickspeare.provenance import describe_year
from scripts.build_features import TAVERN_SPEAKERS, KINGS_SPEAKERS

NS = "{http://www.tei-c.org/ns/1.0}"
ID = "{http://www.w3.org/XML/1998/namespace}id"
PLAYS = {"1H4": "henry-iv-part-1", "2H4": "henry-iv-part-2", "H5": "henry-v"}


def build(source):
    lex = Lexicon()
    wanted = {re.sub('[^a-z]', '', w.lower()) for w in lex.all_seed_words()}
    examples = defaultdict(list)
    total = Counter()
    groups = {"tavern": Counter(), "kings": Counter()}
    manifest = []
    for code, slug in PLAYS.items():
        path = source / (code + ".xml")
        raw = path.read_bytes()  # missing source is a build failure, never an empty atlas
        root = ET.fromstring(raw)
        parents = {child: parent for parent in root.iter() for child in parent}
        title = root.find('.//' + NS + 'title').text
        people = {p.get(ID): ' '.join(''.join(p.find(NS + 'persName').itertext()).split())
                  for p in root.iter(NS + 'person') if p.find(NS + 'persName') is not None}
        manifest.append({"file": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
                         "title": title, "url": f"https://www.folger.edu/explore/shakespeares-works/{slug}/read/"})
        for sp in root.iter(NS + 'sp'):
            ids = [v.lstrip('#') for v in sp.get('who', '').split()]
            cohort = [name for name, members in (("tavern", TAVERN_SPEAKERS), ("kings", KINGS_SPEAKERS))
                      if any(s.split('_')[0] in members for s in ids)]
            for w in sp.iter(NS + 'w'):
                ancestor = parents[w]
                excluded = False
                while ancestor is not sp:
                    if ancestor.tag in (NS + 'stage', NS + 'speaker'):
                        excluded = True
                    ancestor = parents[ancestor]
                if excluded:
                    continue
                word = re.sub('[^a-z]', '', ''.join(w.itertext()).lower())
                if not word:
                    continue
                total[word] += 1
                for name in cohort:
                    groups[name][word] += 1
                if word not in wanted:
                    continue
                record = {"play": title, "code": code, "speakers": [people.get(s, s) for s in ids],
                          "speaker_ids": ids, "speech_id": sp.get(ID), "word_id": w.get(ID),
                          "line": w.get('n', ''), "url": manifest[-1]['url']}
                # Up to four examples, spanning speakers/plays rather than repeating a speech.
                key = (code, tuple(ids))
                if len(examples[word]) < 4 and all((e['code'], tuple(e['speaker_ids'])) != key for e in examples[word]):
                    examples[word].append(record)
    vocab = len(set(groups['tavern']) | set(groups['kings']))
    sizes = {k: sum(v.values()) for k, v in groups.items()}
    words = {}
    for word in sorted(wanted & total.keys()):
        a, b = groups['tavern'][word], groups['kings'][word]
        # Add-half smoothed log odds. Positive values favour royal speech.
        odds = math.log((b + .5) / (sizes['kings'] - b + .5 * (vocab - 1))) - math.log((a + .5) / (sizes['tavern'] - a + .5 * (vocab - 1)))
        words[word] = {"occurrences": examples[word], "counts": {"total": total[word], "tavern": a, "kings": b},
                       "log_odds": round(odds, 6), "affiliation": "royal" if odds > .5 else "tavern" if odds < -.5 else "shared"}
    return {"schema_version": 1, "method": "add-half smoothed log odds; royal minus tavern; editorial speaker cohorts",
            "sources": manifest, "cohort_tokens": sizes, "vocabulary_size": vocab,
            "license": "Folger Digital Texts XML: CC BY-NC 3.0; code: AGPL-3.0-or-later",
            "words": words, "lexicon": lex.words, "quotes": lex.quotes,
            "years": {k: describe_year(v, 'year') for k, v in HISTORICAL_YEARS.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folger-dir', type=Path, default=ROOT / '.cache/corpus/folger/FolgerDigitalTexts_XML_Complete')
    args = parser.parse_args()
    payload = json.dumps(build(args.folger_dir), ensure_ascii=False, indent=2) + '\n'
    for path in (ROOT / 'nickspeare/data/provenance.json', ROOT / 'docs/atlas.json'):
        path.write_text(payload, encoding='utf-8')
    print('Wrote shared Python/browser source atlas.')
