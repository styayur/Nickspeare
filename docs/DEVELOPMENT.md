# Development

Start with [English](../README.md) or [简体中文](../README.zh-CN.md) for installation and the existing test commands. The Python package, browser engine and R analysis have distinct roles; their outputs are not interchangeable.

## Corpus rebuild

From the repository root:

```sh
python -m nickspeare data
python scripts/build_features.py
python scripts/build_atlas.py
```

This fetches source texts and rebuilds features and the Python/browser atlas from cached Folger XML for `1H4`, `2H4` and `H5`. Full texts stay in ignored `.cache/`. The source manifest pins input bytes with SHA-256; missing source files fail the build. Review changes to both atlas copies, source hashes, cohort counts and exclusions before committing.

The published index has 195 words across three plays. Supplemental `--corpus PATH` inputs train the word Markov model from Folger XML or line-oriented text; they do not silently extend the source-evidence index. Word Markov otherwise trains on individual quotes. Adding a play follows the [corpus extension workflow](corpus-extension.md), including source rights and acceptance rules.

## R / RStudio

R is optional for generation. In RStudio, run `source("R/setup.R")` from the repository root to install missing `xml2` and `jsonlite` packages. Then run in a terminal:

```sh
Rscript R/extract_features.R --out work/r-features
```

The R pass uses shared exclusions and speaker cohorts and the same add-half smoothed log-odds formula for characteristic words. Exploratory R output stays separate from the published atlas; the Python builder adds evidence records and source hashes. Compare results before promoting data, and update `nickspeare/data/extraction.json` when changing Python exclusions or cohorts.

## Project map

| Path | Responsibility |
|---|---|
| `nickspeare/generator.py` | Generation, suffixes and structured records |
| `nickspeare/corpus.py` | Markov engines and TEI parsing |
| `nickspeare/provenance.py` | Evidence lookup, blend ranking and date explanations |
| `nickspeare/data/provenance.json` | Packaged evidence atlas |
| `scripts/build_atlas.py` | Reproducible source-evidence build |
| `R/` | RStudio setup and feature extraction |
| `docs/` | Static UI, browser engine and shared atlas |
| `tests/` | Python and JavaScript regression tests |

Keep code and data rights distinct: [Sources and rights](../DATA_SOURCES.md) records the Folger edition and optional inputs. Follow [Contributing](../CONTRIBUTING.md) and [Security](../SECURITY.md). Release maintainers use the [release workflow](../.github/workflows/release.yml); a source version change alone does not publish a package.
