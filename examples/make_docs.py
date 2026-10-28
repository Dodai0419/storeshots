"""Build the README pictures from a real `python storeshots.py --demo` run (run from the repo root)."""
import subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw

subprocess.run([sys.executable, 'storeshots.py', '--demo', '--out', 'stores-demo'], check=True, stdout=subprocess.DEVNULL)
S, D = Path('stores-demo'), Path('docs'); D.mkdir(exist_ok=True)

def row(paths, h, gap=24, bg=(246, 244, 239)):
    ims = [Image.open(p).convert('RGB') for p in paths]
    ims = [i.resize((round(i.width * h / i.height), h), Image.LANCZOS) for i in ims]
    out = Image.new('RGB', (sum(i.width for i in ims) + gap * (len(ims) + 1), h + 2 * gap), bg)
    x = gap
    for i in ims: out.paste(i, (x, gap)); x += i.width + gap
    return out

iphone = S / 'iphone-6.9in_1320x2868'
row(sorted(iphone.glob('*.png')), 900).save(D / 'hero.png')
row([Path('examples/raw/home.png'), iphone / '01-today.png'], 900).save(D / 'before-after.png')
row([S / f / '01-today.png' for f in ('iphone-6.9in_1320x2868', 'ipad-13in_2048x2732', 'android-phone_1080x1920', 'android-tab-7in_1200x1920')], 700).save(D / 'sizes.png')
Image.open(S / 'feature-graphic_1024x500.png').save(D / 'feature-graphic.png')
for p in sorted(D.glob('*.png')): print(p, Image.open(p).size)
