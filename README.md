# Nickspeare

> 从酒馆浪子到王者阿金库尔 —— 用莎士比亚语料生成网名 / nickname 的 Python 程序。
> From tavern rogue to Agincourt king: a Python Shakespearean nickname generator.

**Nickspeare** fuses Early Modern English vocabulary with the semiotics of
Shakespeare's history plays to generate usernames.  On one side stands
Falstaff's Eastcheap tavern (`sack`, `canakin`, `varlet`, `rogue`); on the
other stands the martial kingship of Henry V (`agincourt`, `crispin`, `crown`,
`majesty`).  The generator's signature move is the *rogue-to-king* fusion:

```
sack + agincourt + 1415  ->  Sackagincourt1415
```

## Live demo

A browser demo is published on GitHub Pages:

**https://styayur.github.io/Nickspeare/**

## How it works — the five-stage pipeline

| Stage | Name | Meaning |
|------:|------|---------|
| 1 | 词库分类 | Classify Shakespearean words into tavern / kingly / archaic / quotes / titles / characters / places. |
| 2 | 文本抽取 | Extract token streams from the corpora; train character-level and word-level Markov models. |
| 3 | 核心逻辑性组合 | Logical fusion rules: rogue-to-king semantics, quote splicing, archaic coinage. |
| 4 | 音韵融合与截取 | Phonetic blending on syllable boundaries plus Early Modern affixation/truncation. |
| 5 | 历史年份/数字加缀 | Suffix with historical years (1415, 1564, 1599, 1616…) or plain numbers. |

### Combination rules

* **`rogue_to_king`** — blend a tavern word with a king/Agincourt word and
  (usually) anchor it with a year: `varlet + empire + 1415 → Varletempire1415`.
* **`quote_splice`** — strip stop-words from a famous line and blend the
  remaining content words: *"The course of true love never did run smooth"*
  → `trueneverlove`.
* **`archaic_coinage`** — truncate or deform a high-frequency Early Modern
  connective and add an affix: `thine → thhine`, `thou → thyage`.
* **`markov_coin`** — character-level Markov coinage seeded from the lexicon
  (the *namemaker* technique).
* **`markov_epithet`** — word-level Markov phrase in the manner of
  *markov_poem*: `quart argument chivalry → QuartArgumentChivalry`.

## Installation

Requires Python **3.9+**.  No third-party packages are needed at runtime.

```bash
git clone https://github.com/styayur/Nickspeare.git
cd Nickspeare
python -m pip install -e .
```

## Usage

```bash
# 20 default nicknames
python -m nickspeare generate -n 20

# reproducible run
python -m nickspeare generate -n 20 --seed 42

# rogue-to-king only, pinned to Agincourt, title case
python -m nickspeare generate -n 10 --rule rogue_to_king \
    --style title --year-theme agincourt

# lowercase usernames with a random numeric suffix
python -m nickspeare generate -n 10 --style lower --suffix number --digits 3

# JSON output with provenance
python -m nickspeare generate -n 5 --json

# feed a corpus (Folger XML dir or plain text) into the word-Markov engine
python -m nickspeare generate -n 10 --corpus .cache/corpus/folger/FolgerDigitalTexts_XML_Complete
```

Library API:

```python
from nickspeare import generate

for n in generate(5, seed=42):
    print(n.variant, "|", n.kind, "|", n.description)
```

Sample output (`--seed 42`):

```
varletempire1415     # varlet + empire + 1415
quartArgumentChivalry1415   # word-markov: quart argument chivalry
drawerstandard1616   # drawer + standard
trueneverlove1485    # "The course of true love never did run smooth" (A Midsummer Night's Dream)
flapdragonwork1588   # flapdragon + work + 1588
```

## Data sources & acknowledgements

All corpora are public-domain or open data, fetched on demand by
`python -m nickspeare data` (cached under `.cache/corpus`, git-ignored):

* **Project Gutenberg** — *The Complete Works of William Shakespeare* (#100),
  plain text UTF-8. <https://www.gutenberg.org/ebooks/100>
* **tiny Shakespeare** — Andrej Karpathy's 40k-line training set used in
  *"The Unreasonable Effectiveness of Recurrent Neural Networks"*.
  <https://github.com/karpathy/char-rnn/blob/master/data/tinyshakespeare/input.txt>
* **Folger Shakespeare Digital Texts** — TEI Simple XML, the annotated
  (character-attributed) database used for feature extraction.
  <https://folgerdigitaltexts.org/download/xml.html>
* **Hyperbard** — an NLP/graph database of the plays built on Folger,
  standing in for the "hisent" NLP resource named in the brief.
  <https://github.com/hyperbard/hyperbard>

The two generation engines are direct homages to:

* **devjason/markov_poem** — word-level Markov poem generation over the
  sonnets. <https://github.com/devjason/markov_poem>
* **Rickmsd/namemaker** — character-level Markov name generation.
  <https://github.com/Rickmsd/namemaker>

## R-assisted feature extraction

The brief calls for using **R** to pull play-feature words (Henry IV/V tavern
rogues, Agincourt royalty, high-frequency archaic connectives).  Because R is
not always installed, the Python pipeline is the default
(`scripts/build_features.py`) and its output is committed under
`nickspeare/data/features/`.  The equivalent R implementation lives at
`R/extract_features.R`:

```bash
install.packages(c("xml2", "jsonlite"))
Rscript R/extract_features.R
```

Both produce `{tavern,kings,archaic}.json`, which `Lexicon` merges into the
runtime word library.

## Project layout

```
nickspeare/
  cli.py          command-line interface
  corpus.py       tokenizer + CharMarkov + WordMarkov + Folger TEI parser
  lexicon.py      classified word library (curated seeds)
  phonetics.py    blending, syllabification, truncation, deformation
  combinators.py  fusion rules (rogue_to_king, quote_splice, ...)
  suffixes.py     historical-year / numeric suffix
  generator.py    the five-stage pipeline
  data/           committed feature files (tavern/kings/archaic)
  data.py         corpus downloader
R/extract_features.R   R feature-extraction pass
scripts/build_features.py  Python feature-extraction pass
scripts/fetch_corpus.py    corpus downloader entrypoint
tests/              unittest suite (run with `python -m unittest`)
docs/                GitHub Pages site source (docs/index.html)
```

## License

**GNU Affero General Public License v3.0 or later** — see [LICENSE](LICENSE).

The generated nicknames are not copyrightable by this project; the underlying
Shakespeare texts are public domain.  Nickspeare itself is AGPL-3.0-or-later.