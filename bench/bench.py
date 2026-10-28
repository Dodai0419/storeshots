"""Reproduce the README benchmark: 3 screens x 4 store sizes + feature graphic (13 PNGs), 3 runs."""
import sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import storeshots as s

cfg = Path(__file__).resolve().parent.parent / 'examples' / 'set.json'
times = []
for _ in range(3):
    with tempfile.TemporaryDirectory() as out:
        t = time.perf_counter(); n = len(s.render(cfg, list(s.SIZES), feature=True, out_dir=out)); times.append(time.perf_counter() - t)
print(f'{n} PNGs per run; runs: ' + ', '.join(f'{x:.2f} s' for x in times) + f'; min {min(times):.2f} s, max {max(times):.2f} s')
