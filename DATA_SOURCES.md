# Sources and rights

The code is AGPL-3.0-or-later. This does not relicense third-party editions.

## Evidence atlas

The committed atlas is derived from the locally cached Folger Digital Texts
XML edition of *Henry IV, Part 1*, *Henry IV, Part 2* and *Henry V*.
Each source file's SHA-256 hash is recorded in the atlas. Its XML header identifies
the license as [CC BY-NC 3.0](https://creativecommons.org/licenses/by-nc/3.0/).
Retain that attribution and noncommercial restriction for these derived data.

Credit: William Shakespeare; editors Barbara A. Mowat and Paul Werstine;
XML editing and encoding by Michael Poston and Rebecca Niles;
publisher Folger Shakespeare Library. Changes made here: token normalization,
exclusion of stage directions/speaker labels, counting, speaker-cohort scoring,
and selection of representative word locations. The full XML is not committed.

- [Read Henry IV, Part 1](https://www.folger.edu/explore/shakespeares-works/henry-iv-part-1/read/)
- [Read Henry IV, Part 2](https://www.folger.edu/explore/shakespeares-works/henry-iv-part-2/read/)
- [Read Henry V](https://www.folger.edu/explore/shakespeares-works/henry-v/read/)
- [Folger XML documentation](https://folgerdigitaltexts.org/download/FDT_documentation.pdf)
- [Current Folger copyright policy](https://www.folger.edu/copyright-policy/)

The license in the cached edition is recorded rather than silently substituting
the current site's license. Shakespeare's underlying works and a modern edited
digital edition should not be treated as the same rights object.

## Optional corpora and influences

The downloader also supports [Gutenberg #100](https://www.gutenberg.org/ebooks/100)
and [tiny Shakespeare](https://github.com/karpathy/char-rnn/tree/master/data/tinyshakespeare).
These are optional training inputs; the shipped three-play provenance index
does not claim to index them. Hyperbard is a related research resource, not an
input to the shipped atlas. Markov generation is inspired by
[markov_poem](https://github.com/devjason/markov_poem) and
[namemaker](https://github.com/Rickmsd/namemaker).
