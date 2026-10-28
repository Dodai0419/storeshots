import contextlib, io, json, shutil, sys, tempfile, unittest
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import storeshots as ss

RAW = ROOT / 'examples' / 'raw'

def tmpdir(case):
    t = tempfile.TemporaryDirectory(); case.addCleanup(t.cleanup); return Path(t.name)

class Layout(unittest.TestCase):
    def test_screenshot_pixels_are_only_resized(self):
        shot = Image.open(RAW / 'home.png').convert('RGB')
        for size in [*ss.SIZES.values(), ss.FEATURE]:
            img, (x0, y0, x1, y1) = ss.compose(size, shot, dict(ss.THEME, bg='#22a88b'), 'Every habit,\n*one glance*')
            self.assertEqual(img.size, size); self.assertEqual(img.mode, 'RGB')
            self.assertTrue(0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1], 'phone must not be cropped')
            want = shot.resize((x1 - x0, y1 - y0), Image.LANCZOS)
            ih = round((y1 - y0) * 0.12)  # skip the dynamic island and rounded corners
            got = img.crop((x0, y0 + ih, x1, y1 - ih)); exp = want.crop((0, ih, x1 - x0, y1 - y0 - ih))
            diff = ImageStat.Stat(ImageChops.difference(got, exp)).mean
            self.assertLess(max(diff), 0.5, f'{size}: screen differs from the screenshot')

    def test_store_sizes_fit_store_rules(self):
        for name, (w, h) in ss.SIZES.items():
            if name.startswith('android'): self.assertTrue(ss.play_ok(w, h), name)
        self.assertFalse(ss.play_ok(1290, 2796))  # upstream note: 1290x2796 is too tall for Play

    def test_headline_markup(self):
        self.assertEqual(ss.parse_headline('Plan your day\n*in one tap*'), [[('Plan your day', False)], [('in one tap', True)]])
        self.assertEqual(ss.parse_headline('a *b* c'), [[('a ', False), ('b', True), (' c', False)]])

    def test_store_safe_text(self):
        found = ss.check_text([dict(out='1.png', headline='The #1 habit app'), dict(out='2.png', headline='Best value', sub='Only $4.99'),
                               dict(out='3.png', headline='Every habit,\n*one glance*')])
        self.assertEqual([o for o, _ in found], ['1.png', '2.png', '2.png'])

class Render(unittest.TestCase):
    def test_upstream_set_json_renders_same_job(self):
        """zaferayan's own set.example.json: same keys, scenes ignored, exact size, RGB, one file per image."""
        d = tmpdir(self)
        cfg = json.loads((ROOT / 'tests' / 'upstream' / 'zaferayan-set.example.json').read_text(encoding='utf-8'))
        for im, raw in zip(cfg['images'], ['home', 'streaks', 'stats']):
            shutil.copy(RAW / f'{raw}.png', d / f'{raw}.png'); im['screenshot'] = f'{raw}.png'
        (d / 'set.json').write_text(json.dumps(cfg), encoding='utf-8')
        outs = ss.render(d / 'set.json')
        self.assertEqual([p.name for p in outs], ['01-recipe.png', '02-day-plan.png', '03-today.png'])
        self.assertTrue(all(p.parent == d / 'stores' for p in outs))
        for p in outs:
            with Image.open(p) as im: self.assertEqual((im.size, im.mode), ((1290, 2796), 'RGB'))

    def test_every_store_and_feature_graphic(self):
        d = tmpdir(self)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(ss.main(['--demo', '--out', str(d)]), 0)
        self.assertEqual(len(list(d.rglob('*.png'))), 4 * 3 + 1)
        with Image.open(d / 'feature-graphic_1024x500.png') as im: self.assertEqual((im.size, im.mode), ((1024, 500), 'RGB'))
        self.assertNotIn('outside Play limits', out.getvalue())

    def test_strict_fails_on_risky_copy(self):
        d = tmpdir(self)
        shutil.copy(RAW / 'home.png', d / 'a.png')
        (d / 's.json').write_text(json.dumps(dict(images=[dict(screenshot='a.png', headline='The best habit app')])), encoding='utf-8')
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(ss.main([str(d / 's.json'), '--strict']), 1)
        self.assertIn('"best"', err.getvalue())

if __name__ == '__main__':
    unittest.main()
