import json
import random
import tempfile
import unittest
from pathlib import Path

from nickspeare.corpus import CharMarkov, parse_folger, load_gutenberg
from nickspeare.generator import NicknameGenerator, _RULES
from nickspeare.provenance import atlas, rank_blends, describe_year


class ProvenanceTests(unittest.TestCase):
    def test_downloader_is_not_shadowed_by_data_package(self):
        from nickspeare import data
        self.assertTrue(callable(data.ensure_all))

    def test_word_markov_uses_each_training_boundary(self):
        from nickspeare.corpus import WordMarkov
        m = WordMarkov().train(['sack','and','ale']).train(['honour','and','glory'])
        values = {m.generate(random.Random(i)) for i in range(30)}
        self.assertTrue(any(v.startswith('honour') for v in values))
        self.assertTrue(any(v.startswith('sack') for v in values))

    def test_no_suffix_means_no_digits_for_every_rule(self):
        for rule in _RULES:
            results = NicknameGenerator(seed=21).generate(20, rule=rule, suffix='none')
            self.assertTrue(all(not any(c.isdigit() for c in n.variant) for n in results), rule)
            self.assertTrue(all(n.suffix == '' for n in results))

    def test_pinned_year_is_always_applied_and_explained(self):
        results = NicknameGenerator(seed=5).generate(30, rule='rogue_to_king', year_theme='agincourt')
        self.assertTrue(all(n.suffix == '1415' and n.variant.endswith('1415') for n in results))
        self.assertIn('not the play', results[0].provenance['date']['explanation'])

    def test_number_is_not_interpreted_as_history(self):
        self.assertEqual(describe_year('1415', 'number')['kind'], 'number')

    def test_reproducible_full_records(self):
        a = [n.as_dict() for n in NicknameGenerator(seed=99).generate(25)]
        b = [n.as_dict() for n in NicknameGenerator(seed=99).generate(25)]
        self.assertEqual(a, b)
        json.dumps(a)

    def test_prefix_conditioning(self):
        model = CharMarkov(3).train(['sack', 'sacred', 'royal', 'roguery'])
        self.assertTrue(model.generate(random.Random(2), seed='sack').startswith('sa'))
        self.assertTrue(model.generate(random.Random(2), seed='royal').startswith('ro'))

    def test_missing_attestation_is_explicit(self):
        from nickspeare.provenance import evidence
        from nickspeare.lexicon import Lexicon
        self.assertEqual(evidence('inventedxyz', Lexicon())['status'], 'unverified seed or generated form')

    def test_atlas_shared_and_auditable(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual((root/'docs/atlas.json').read_bytes(), (root/'nickspeare/data/provenance.json').read_bytes())
        self.assertGreater(len(atlas()['words']), 100)
        self.assertTrue(atlas()['words']['sack']['occurrences'])
        self.assertTrue(all(len(s['sha256']) == 64 for s in atlas()['sources']))

    def test_best_candidate_and_retained_alternatives(self):
        ranked = rank_blends('counterfeit', 'majesty')
        self.assertGreater(len(ranked), 1)
        self.assertEqual(ranked[0]['score'], max(c['score'] for c in ranked))
        self.assertIn('honourself', [c['text'] for c in rank_blends('honour', 'ourself')])

    def test_input_validation(self):
        g = NicknameGenerator(4)
        for kwargs in ({'count':-1}, {'style':'wrong'}, {'suffix':'wrong'}, {'digits':0}, {'year_theme':'wrong'}):
            with self.assertRaises(ValueError):
                g.generate(**kwargs)

    def test_stage_and_speaker_labels_are_not_dialogue(self):
        xml = '''<TEI xmlns="http://www.tei-c.org/ns/1.0"><title>Fixture</title>
        <sp who="#Falstaff_1H4 #Poins_1H4"><speaker><w>FALSTAFF</w></speaker>
        <w>sack</w><stage><w>Exit</w></stage><w>hon<hi>our</hi></w></sp></TEI>'''
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'sample.xml'
            path.write_text(xml)
            speech = parse_folger(path)['speeches'][0]
            self.assertEqual(speech['words'], ['sack', 'honour'])
            self.assertEqual(speech['speakers'], ['Falstaff_1H4', 'Poins_1H4'])

    def test_plain_text_without_gutenberg_markers(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'sample.txt'; path.write_text('sack and honour')
            self.assertEqual(load_gutenberg(path), ['sack','and','honour'])
