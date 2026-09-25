"""Tests for Nickspeare.  Run with ``python -m unittest`` (no third-party deps)."""

import random
import unittest

from nickspeare import combinators, corpus, generator, phonetics, suffixes
from nickspeare.lexicon import Lexicon


class PhoneticsTest(unittest.TestCase):
    def test_blend_overlap(self):
        self.assertEqual(phonetics.blend("honour", "ourself"), "honourself")

    def test_blend_no_overlap(self):
        self.assertEqual(phonetics.blend("sack", "agincourt"), "sackagincourt")

    def test_estimate_syllables(self):
        self.assertGreaterEqual(phonetics.estimate_syllables("agincourt"), 2)

    def test_truncate_with_affix(self):
        self.assertEqual(phonetics.truncate("thou", 3, "eth"), "thoeth")


class SuffixesTest(unittest.TestCase):
    def test_historical_year(self):
        rng = random.Random(0)
        self.assertEqual(suffixes.pick_year(rng, "agincourt"), "1415")

    def test_number_digits(self):
        rng = random.Random(0)
        n = suffixes.pick_number(rng, 3)
        self.assertEqual(len(n), 3)
        self.assertTrue(n.isdigit())


class LexiconTest(unittest.TestCase):
    def test_categories_present(self):
        lex = Lexicon()
        self.assertIn("sack", lex.category("tavern"))
        self.assertIn("agincourt", lex.category("kings"))
        self.assertIn("thou", lex.category("archaic"))

    def test_quotes_present(self):
        lex = Lexicon()
        self.assertGreaterEqual(len(lex.quotes), 5)


class MarkovTest(unittest.TestCase):
    def test_char_markov(self):
        m = corpus.CharMarkov(order=3).train(["sack", "agincourt", "crispin"])
        rng = random.Random(1)
        name = m.generate(rng, seed="sack", min_len=4, max_len=12)
        self.assertGreaterEqual(len(name), 4)

    def test_word_markov(self):
        tokens = corpus.tokenize("we few we happy few band of brothers")
        m = corpus.WordMarkov(order=2).train(tokens)
        rng = random.Random(2)
        out = m.generate(rng, n_words=3)
        self.assertTrue(out.strip())


class CombinatorsTest(unittest.TestCase):
    def setUp(self):
        self.lex = Lexicon()
        self.rng = random.Random(3)
        self.markov = corpus.CharMarkov(order=3).train(self.lex.all_seed_words())

    def test_rogue_to_king_parts(self):
        f = combinators.rogue_to_king(self.lex, self.rng)
        self.assertEqual(f.kind, "rogue_to_king")
        self.assertTrue(f.parts)

    def test_quote_splice(self):
        f = combinators.quote_splice(self.lex, self.rng)
        self.assertEqual(f.kind, "quote_splice")
        self.assertTrue(f.text)


class GeneratorTest(unittest.TestCase):
    def test_generate_counts_and_styles(self):
        gen = generator.NicknameGenerator(seed=5)
        nicks = gen.generate(20, dedupe=True)
        self.assertEqual(len(nicks), 20)
        self.assertEqual(len(set(n.variant for n in nicks)), 20)

    def test_specific_rule(self):
        gen = generator.NicknameGenerator(seed=6)
        nicks = gen.generate(10, rule="rogue_to_king", style="lower", suffix="year")
        self.assertTrue(all(n.kind == "rogue_to_king" for n in nicks))

    def test_style_camel(self):
        gen = generator.NicknameGenerator(seed=7)
        nick = gen.generate_one(rule="rogue_to_king", style="camel")
        self.assertFalse(" " in nick.variant)


if __name__ == "__main__":
    unittest.main()