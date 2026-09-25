#!/usr/bin/env Rscript
# =============================================================================
# extract_features.R — extract play-feature words from the Folger Digital Texts
# -----------------------------------------------------------------------------
# The Python counterpart (scripts/build_features.py) produces the same output
# and is the default pipeline, so Nickspeare runs without R.  This script is
# provided because the brief asks for an R-assisted feature-extraction pass.
#
# Dependencies:
#   install.packages(c("xml2", "jsonlite"))
#
# Usage:
#   Rscript R/extract_features.R \
#     --folger-dir .cache/corpus/folger/FolgerDigitalTexts_XML_Complete \
#     --out data/features
# =============================================================================

suppressPackageStartupMessages({
  library(xml2)
  library(jsonlite)
})

# `%||%` helper (R >= 4.4 has it natively; keep a fallback for older versions)
if (!exists("%||%", envir = baseenv())) {
  `%||%` <- function(a, b) if (is.null(a)) b else a
}

# ---- CLI --------------------------------------------------------------------
args <- commandArgs(trailingOnly = TRUE)
parse_arg <- function(name, default) {
  idx <- match(name, args)
  if (!is.na(idx) && idx < length(args)) return(args[idx + 1L])
  default
}

script_path <- sub("^--file=", "", grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)[1])
repo <- normalizePath(file.path(dirname(script_path), ".."), mustWork = FALSE)
folger_dir <- parse_arg("--folger-dir",
                        file.path(repo, ".cache", "corpus", "folger", "FolgerDigitalTexts_XML_Complete"))
out_dir <- parse_arg("--out", file.path(repo, "nickspeare", "data", "features"))

# ---- Speaker classification --------------------------------------------------
TAVERN <- c("Falstaff", "Poins", "Bardolph", "Peto", "Gadshill", "MistressQuickly",
            "Vintner", "Francis", "DollTearsheet", "Pistol", "Nym", "Hostess")
KINGS  <- c("HenryV", "Chorus", "Exeter", "Westmoreland", "Fluellen")

STOPWORDS <- c("the", "and", "that", "this", "with", "for", "you", "your", "his",
  "her", "our", "their", "shall", "will", "would", "should", "could", "have",
  "has", "had", "but", "not", "nor", "from", "they", "them", "then", "than",
  "when", "what", "where", "which", "who", "whom", "whose", "all", "are", "was",
  "were", "be", "been", "being", "am", "is", "it", "its", "we", "us", "i", "my",
  "me", "he", "she", "him", "his", "so", "such", "as", "if", "of", "to", "in",
  "on", "at", "by", "a", "an", "do", "doth", "dost", "did", "does", "say", "said",
  "says", "now", "here", "there", "thus", "well", "good", "come", "go", "let",
  "make", "made", "take", "took", "give", "gave", "know", "think", "man", "men",
  "day", "night", "time", "life", "death", "world", "hand", "heart", "eyes",
  "head", "king", "prince", "lord", "lords", "sir", "o", "oh")

ARCHAIC <- c("the", "thou", "thee", "thy", "thine", "ye", "anon", "prithee",
  "forsooth", "perchance", "wherefore", "alack", "alas", "hark", "whence",
  "betwixt", "ere", "dost", "doth", "hath", "shalt", "wilt", "art", "ay", "nay",
  "sirrah", "zounds", "marry", "beshrew", "gramercy", "certes", "sooth", "welladay")

norm <- function(x) gsub("[^a-z]", "", tolower(x))

# Share exclusions and speaker cohorts with the Python implementation.
config <- fromJSON(file.path(repo, "nickspeare", "data", "extraction.json"))
STOPWORDS <- config$stopwords
PROPER_NAMES <- config$proper_names
TAVERN <- config$tavern_speakers
KINGS <- config$kings_speakers

speaker_matches <- function(ids, names) {
  any(vapply(names, function(n) any(ids == n | startsWith(ids, paste0(n, "_"))), logical(1)))
}

read_play <- function(path) {
  doc <- read_xml(path)
  xml_ns_strip(doc)
  sps <- xml_find_all(doc, "//sp")
  do.call(rbind, lapply(sps, function(sp) {
    who <- xml_attr(sp, "who")
    if (is.na(who)) who <- ""
    ids <- trimws(unlist(strsplit(who, "#", fixed = TRUE)))
    ids <- ids[nzchar(ids)]
    words <- xml_text(xml_find_all(sp, ".//w[not(ancestor::stage) and not(ancestor::speaker)]"))
    data.frame(
      speaker = if (length(ids)) ids[1] else "",
      speakers = I(list(ids)),
      words = I(list(words)),
      stringsAsFactors = FALSE
    )
  }))
}

# ---- Frequency + characteristic scoring -------------------------------------
freqs <- function(speeches, names) {
  counts <- list()
  for (i in seq_len(nrow(speeches))) {
    if (!speaker_matches(speeches$speakers[[i]], names)) next
    for (w in speeches$words[[i]]) {
      w <- norm(w)
      if (nchar(w) < 3 || w %in% STOPWORDS || w %in% PROPER_NAMES) next
      counts[[w]] <- (counts[[w]] %||% 0L) + 1L
    }
  }
  counts
}

top_characteristic <- function(target, other, n = 40) {
  words <- names(target)
  vocab <- length(union(names(target), names(other)))
  nt <- sum(unlist(target))
  no <- sum(unlist(other))
  score <- vapply(words, function(w) {
    cnt <- target[[w]]
    if (cnt < 2) return(-Inf)
    alt <- other[[w]] %||% 0L
    log((cnt + 0.5) / (nt - cnt + 0.5 * (vocab - 1))) -
      log((alt + 0.5) / (no - alt + 0.5 * (vocab - 1)))
  }, numeric(1))
  names(score) <- words
  counts <- vapply(words, function(w) as.numeric(target[[w]]), numeric(1))
  score <- score[order(score, counts, words, decreasing = TRUE)]
  head(names(score)[is.finite(score)], n)
}

# ---- Main -------------------------------------------------------------------
main <- function() {
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  plays <- list()
  for (code in c("1H4", "2H4", "H5")) {
    path <- file.path(folger_dir, paste0(code, ".xml"))
    if (!file.exists(path)) {
      stop("missing ", path)
    }
    plays[[code]] <- read_play(path)
  }
  all_sp <- do.call(rbind, unname(plays))
  tavern <- freqs(all_sp, TAVERN)
  kings <- freqs(all_sp, KINGS)

  writeLines(toJSON(list(tavern = top_characteristic(tavern, kings, 40)), auto_unbox = TRUE),
             file.path(out_dir, "tavern.json"))
  writeLines(toJSON(list(kings = top_characteristic(kings, tavern, 40)), auto_unbox = TRUE),
             file.path(out_dir, "kings.json"))

  arch_counts <- list()
  for (i in seq_len(nrow(all_sp))) {
    for (w in all_sp$words[[i]]) {
      w <- norm(w)
      if (w %in% ARCHAIC) arch_counts[[w]] <- (arch_counts[[w]] %||% 0L) + 1L
    }
  }
  arch_counts <- unlist(arch_counts)
  arch_counts <- sort(arch_counts, decreasing = TRUE)
  writeLines(toJSON(list(archaic = unname(head(names(arch_counts), 40))), auto_unbox = TRUE),
             file.path(out_dir, "archaic.json"))

  cat("wrote tavern/kings/archaic features to", out_dir, "\n")
  invisible(NULL)
}

if (!interactive()) main()
