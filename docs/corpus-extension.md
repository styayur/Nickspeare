# Adding a play or corpus

Nickspeare accepts new source material only when provenance, rights, extraction, and publication boundaries are explicit. The current committed atlas covers three plays and 195 indexed words; it should not be described as a general Early Modern corpus.

## Stable workflow

1. Read [DATA_SOURCES.md](../DATA_SOURCES.md) and [METHODOLOGY.md](METHODOLOGY.md).
2. Add the source to the source manifest with a stable identifier, edition, URL, license/copyright status, and SHA-256.
3. Keep full source files in ignored `.cache/`; do not commit copyrighted editions unless redistribution is permitted.
4. Define exclusions and speaker cohorts before extracting features.
5. Run:

```sh
python -m nickspeare data
python scripts/build_features.py
python scripts/build_atlas.py
python -m unittest discover -s tests -v
python -m build
```

6. Review both Python and browser atlas copies, source hashes, cohort counts, evidence labels, chronology, and generated provenance.
7. Update [METHODOLOGY.md](METHODOLOGY.md), [DATA_SOURCES.md](../DATA_SOURCES.md), and the changelog when coverage or interpretation changes.

## Acceptance rules

- A missing or changed source hash fails the build.
- Source evidence must point to the actual play, speaker identity, line label/XML identifier, and source hash.
- Generated names remain labelled as new coinages.
- Supplemental corpora can train a model but do not silently extend the committed source-evidence index.
- New sources must not leak private files, inaccessible editions, or unlicensed text into releases.

Maintainers decide when a corpus expansion is large enough to warrant a release and version bump.
