# Nickspeare

[![Verify](https://github.com/styayur/Nickspeare/actions/workflows/ci.yml/badge.svg)](https://github.com/styayur/Nickspeare/actions/workflows/ci.yml)

**Shakespearean nickname generator — from Eastcheap rogue to Agincourt king.**

[Open the composing room](https://styayur.github.io/Nickspeare/) · [Methodology](docs/METHODOLOGY.md) · [Contributing](CONTRIBUTING.md) · [Source attribution](DATA_SOURCES.md)

把 Eastcheap 的酒馆词汇与 Agincourt 的王权意象融合成网名。每个名字都可以追溯原词、人物、剧目、语义阵营、融合步骤与年代含义；生成词本身始终标明为新造词。

```text
sack + agincourt → sackagincourt → Sackagincourt1415
```

The browser is an Early Modern composing room: classical serif text, monospace
parameters and provenance, paper white, black ink and dark red. Use **FORGE NAME**,
inspect the paper trail, follow the four-stage formation, and export a JSON record.
Replay links preserve the settings and selected impression. Everything runs locally
in the browser; there is no generation API or API key.

## What is inside

- **Source evidence:** 195 indexed words in the current three-play atlas, with
  speaker identities, printed line labels, speech/word XML IDs and source hashes.
- **Semantic affiliation:** add-half smoothed log odds contrast selected tavern
  and royal speaker groups. Royal affinity controls weighted ingredient selection.
- **Ranked fusion:** compare overlap, concatenation and vowel-group cuts using
  explicit retention, consonant-cluster and length scores; inspect alternatives.
- **Character Markov:** order-three conditional generation with real prefix
  conditioning. Browser records include transitions, probabilities and fallbacks.
- **Chronology:** distinguish story history, biography, composition context and
  publication; 1413 is coronation, 1415 is Agincourt, 1623 is the First Folio.
- **Reproducibility:** seeded generation, structured provenance, Python/Node tests,
  browser integration checks, source manifests and a documented rebuild process.

This is a literary experiment, not a historical pronunciation model. Speaker groups
are editorial interpretations; rare-word associations are uncertain. Evidence attests
an ingredient, not the invented name. See [methodology](docs/METHODOLOGY.md).

## Install

Python 3.9+; no third-party runtime packages.

```sh
git clone https://github.com/styayur/Nickspeare.git
cd Nickspeare
python -m pip install -e .
```

## Generate

```sh
python -m nickspeare generate -n 10 --seed 42
python -m nickspeare generate -n 5 --rule rogue_to_king --style title --year-theme agincourt --royal-affinity 0.85 --json
python -m nickspeare generate -n 5 --rule markov_coin --suffix none --seed 42
python -m nickspeare generate -n 5 --rule markov_epithet --seed 42
```

Python offers `rogue_to_king`, `quote_splice`, `archaic_coinage`, `markov_coin`
and `markov_epithet`. Browser offers the first four. `--suffix none` never adds
a year; `number` denotes a nonhistorical ornament; `both` randomly chooses a
historical or numeric suffix. Styles: `lower`, `camel`, `title`, `snake`, `kebab`,
`upper`. Separators transform existing phrase boundaries, not guessed compound roots.

```python
from nickspeare import NicknameGenerator

engine = NicknameGenerator(seed=42, royal_affinity=0.85)
name = engine.generate_one(rule="rogue_to_king", year_theme="agincourt")
print(name.variant)
print(name.as_dict()["provenance"])
```

Python and browser share lexical/evidence data and blend scores but use different
RNGs and transformation rules. Seeds replay within an engine/version, not across
engines. Word Markov trains on individual quotes by default; add `--corpus PATH`
for Folger XML or line-oriented plain text. Supplemental corpora train the model
but do not silently extend the committed source-evidence index.

## Corpus and R / RStudio workflow

```sh
python -m nickspeare data
python scripts/build_features.py
python scripts/build_atlas.py
```

This rebuilds features and the identical Python/browser atlas from cached Folger
XML for `1H4`, `2H4`, `H5`. Full texts stay in ignored `.cache/`. The source manifest
pins input bytes with SHA-256. Missing source files fail the build.

In RStudio run `source("R/setup.R")` to install missing `xml2` and `jsonlite`
packages. Then run from a terminal:

```sh
Rscript R/extract_features.R --out work/r-features
```

The R pass uses shared exclusions and speaker cohorts and the same smoothed
log-odds formula for characteristic words. Its exploratory outputs are kept
separate from the published atlas. The Python atlas builder adds evidence records
and source hashes. R is optional for nickname generation.

## Development

```sh
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
npm test
python -m build
```

Serve the site with `python -m http.server 8765 --directory docs`. After
`python -m playwright install chromium`, run `python scripts/check_browser.py`
in another terminal. CI runs Python 3.9/3.12/3.14 and headless browser checks.
GitHub Pages publishes `main:/docs`.

## Project map

| Path | Responsibility |
| --- | --- |
| `nickspeare/generator.py` | Generation, suffixes and structured records |
| `nickspeare/corpus.py` | Markov engines and TEI parsing |
| `nickspeare/provenance.py` | Evidence lookup, blend ranking, date explanation |
| `nickspeare/data/provenance.json` | Packaged evidence atlas |
| `scripts/build_atlas.py` | Reproducible source evidence build |
| `R/` | RStudio dependency setup and extraction |
| `docs/` | Static Pages UI, browser engine and shared atlas |
| `tests/` | Python and JavaScript regression tests |

## License and acknowledgements

Code: **AGPL-3.0-or-later**, see [LICENSE](LICENSE). The cached Folger edition and
its derived data retain **CC BY-NC 3.0** attribution and restrictions; they are
not relicensed by the code license. See [DATA_SOURCES.md](DATA_SOURCES.md).

Thanks to the Folger Shakespeare Library and its editors/encoders. Optional
corpora include Project Gutenberg and Karpathy’s tiny Shakespeare. Markov
techniques are inspired by [markov_poem](https://github.com/devjason/markov_poem)
and [namemaker](https://github.com/Rickmsd/namemaker).
