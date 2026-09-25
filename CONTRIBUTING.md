# Contributing

Use Python 3.9+ and Node 20+; the generators have no runtime dependencies.

```sh
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
npm test
python -m build
```

For browser checks, install Chromium with `python -m playwright install chromium`,
serve `docs` with `python -m http.server 8765 --directory docs`, and run
`python scripts/check_browser.py` in a second terminal.

For source changes, first fetch the corpus with `python -m nickspeare data`.
Run `python scripts/build_features.py` followed by `python scripts/build_atlas.py`.
Commit both atlas copies and review source hashes, cohort counts and evidence
changes. Do not fabricate speaker attributions or label generated words as quotes.
Check DATA_SOURCES.md before adding or redistributing a corpus.

R users can run `source('R/setup.R')` in RStudio, then
`Rscript R/extract_features.R --out work/r-features`. Keep exploratory output out
of packaged data until it has been compared with the Python build. Update
`nickspeare/data/extraction.json` when changing Python exclusions or cohorts.

Bug reports should include engine/version, seed, rule, suffix and exported JSON.
New algorithms should include deterministic regression tests and document their
limits. Browser and Python seeds are intentionally engine-specific.
