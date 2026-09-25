# A name with a paper trail

## Evidence and semantic affiliation

The atlas indexes normalized dialogue tokens in three Folger XML plays. It
excludes speaker labels and stage directions, records word/speech XML IDs and
printed line labels, and retains up to four distinct play/speaker examples per
word. The interface shows two examples; JSON preserves the remainder. Source
links open the whole play: XML IDs are evidence locators, not web-page anchors.

Tavern speakers include Falstaff, Poins, Bardolph and the Eastcheap circle;
royal speakers include Henry V, Chorus, Exeter, Westmoreland and Fluellen.
These are editorial cohorts, not exhaustive or mutually exclusive moral labels.
Prince Hal's transformation is not modeled as a historically measured variable.

For royal count `r`, tavern count `t`, group totals `R`, `T`, and union vocabulary
size `V`, the atlas stores:

```
log((r + 0.5) / (R - r + 0.5*(V-1)))
  - log((t + 0.5) / (T - t + 0.5*(V-1)))
```

Positive values lean royal; negative values lean tavern. Values between -0.5
and +0.5 are displayed as shared. A word can be a curated royal ingredient but
have tavern-leaning corpus evidence. Both are shown instead of concealing the
difference. Rare-word scores have high uncertainty; this is an exploratory
association statistic, not significance testing or an NLP classifier.

Royal affinity `a` in [0,1] weights the royal ingredient pool by
`exp(clamp(log_odds,-3,3)*(2*a-1))`. At 0.5 selection is uniform; higher values
prefer words leaning royal in these groups. Unattested words receive neutral
weight and an explicit unverified label. The tavern ingredient stays in its
editorial pool at every setting.

## Candidate ranking

Rogue-to-king tries longest letter overlap, concatenation, and (when available)
a cut before the first ingredient's final vowel group. Duplicate candidates
are removed. The deterministic score is:

```
2 * retained_length_fraction
  - 0.35 * sum(max(0, consonant_cluster_length - 3))
  - 0.3 * abs(candidate_length - 12) / 12
```

The maximum wins, with lexical ordering for ties. These coefficients are design
heuristics, not trained or validated quality estimates. They approximate spelling
readability, not Early Modern pronunciation. Browser quote splicing applies the
same ranking pairwise; its candidate panel shows the final pairwise step.

## Markov and replay

Character mode trains order-three transition frequencies on the deduplicated
lexicon. It conditions on the selected seed's first two letters and samples
observed continuations. Whole seed words can be reproduced; novelty is not
guaranteed. Browser output records conditional transitions and any bounded-retry
fallback. Python additionally offers word Markov, trained on individual quotes
or supplied corpus speeches/lines, never on alphabetically adjacent dictionary
words or cross-speech boundaries.

Both engines are reproducible within their version and data revision. They use
different RNGs and have different transformation rules, so equal seeds do not
promise equal output across Python and JavaScript. Browser links save settings
and the selected impression. Pressing FORGE NAME with unchanged settings advances
the seed by one; an exported record always retains the actual seed used. Python
records initial seed and sequence; replay requires the same call sequence and
external corpus contents. External corpus paths are recorded, not bundled or hashed.

## Chronology and interpretation

1413 denotes Henry V's accession/coronation; 1415 denotes the Agincourt campaign.
1599 is a theatre-history allusion and approximate composition context for
*Henry V*. 1623 denotes the First Folio's publication. A suffix is an independent
allusion, not the date a source word was first used. The visual coronation is a
literary journey; it does not move the historical coronation to Agincourt.

Generated names are inventions. An attestation applies only to an ingredient;
curated quotation attributions are shown separately from the three-play index.
See [Folger's Henry V introduction](https://www.folger.edu/explore/shakespeares-works/henry-v/)
and [Shakespeare's works](https://www.folger.edu/explore/shakespeares-works/) for context.

## Rebuild and assess

Run `python scripts/build_features.py` and `python scripts/build_atlas.py` against
the cached XML. The two atlas copies must match byte-for-byte. Tests exercise
deterministic generation, prefix conditioning, stage exclusion, suffix semantics,
invalid inputs, UI replay/export, responsive layout and unavailable data.
They establish implementation behavior, not literary quality. Any claim of better
names would require a blinded human evaluation; none is claimed here.
