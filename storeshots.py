#!/usr/bin/env python3
"""storeshots: turn raw app screenshots into store-ready App Store and Google Play images.

Reads the set.json format of zaferayan/app-store-screenshot-skill (MIT) and exports every store
size of 7ANV1R/Store-Screenshot-Studio (MIT), plus a Play feature graphic and a store-safe text check.
Pillow only: no Chrome, no Node, no network.
"""
import argparse, json, math, re, sys
from pathlib import Path
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont

SIZES = {  # Store-Screenshot-Studio's store specs
    'iphone-6.9in': (1320, 2868), 'ipad-13in': (2048, 2732),
    'android-phone': (1080, 1920), 'android-tab-7in': (1200, 1920),
}
GROUPS = {'ios': ['iphone-6.9in', 'ipad-13in'], 'play': ['android-phone', 'android-tab-7in'], 'all': list(SIZES)}
FEATURE = (1024, 500)
THEME = dict(bg='#15151c', bg2=None, accent='#6d5efc', accent2=None, text=None, platform='ios', cutout=True,
             frame='black', headline_lines=2, device_max_w=0.73, pattern='none', sub=None)
FRAMES = {'black': '#111114', 'white': '#f2f2f4', 'silver': '#c9cbd1', 'gold': '#d8c4a0'}
# Store-safe text: claims both stores reject unless proven (Store-Screenshot-Studio's copy rules)
RISKY = re.compile(r'#\s*1\b|\bnumber one\b|\bbest\b|\btop[- ]rated\b|\b100\s*%|\bguarantee\w*|\baward[- ]winning\b|'
                   r'\bfree\b|[$€£¥]\s*\d|\bcheapest\b|\bfastest\b|\bapp of the (?:day|year)\b', re.I)
BOLD_FONTS = ['segoeuib.ttf', 'arialbd.ttf', 'DejaVuSans-Bold.ttf', 'LiberationSans-Bold.ttf', 'Helvetica.ttc', 'Arial Bold.ttf']
REG_FONTS = ['segoeui.ttf', 'arial.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf', 'Helvetica.ttc', 'Arial.ttf']

def rgb(c): return ImageColor.getrgb(c)[:3]

def luminance(c):
    r, g, b = (v / 255 for v in rgb(c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def font(names, size, cache={}):
    key = (tuple(names), size)
    if key not in cache:
        for n in names:
            try: cache[key] = ImageFont.truetype(n, size); break
            except OSError: pass
        else: cache[key] = ImageFont.load_default(size)
    return cache[key]

def parse_headline(text):
    """'Plan your day\\n*in one tap*' -> [[('Plan your day', False)], [('in one tap', True)]]"""
    return [[(part, i % 2 == 1) for i, part in enumerate(line.split('*')) if part] for line in text.split('\n')]

def check_text(images):
    """Store-safe copy: return [(out, phrase)] for claims the stores reject without proof."""
    return [(im.get('out', '?'), m.group(0)) for im in images for key in ('headline', 'sub') for m in RISKY.finditer(im.get(key) or '')]

def gradient(size, c1, c2):
    w, h = size
    mask = Image.linear_gradient('L').resize((1, h)).resize((w, h), Image.NEAREST)  # vertical: one column is enough
    return Image.composite(Image.new('RGB', size, rgb(c2 or c1)), Image.new('RGB', size, rgb(c1)), mask)

def pattern(img, kind, color):
    if kind in (None, 'none'): return
    w, h = img.size
    layer = Image.new('L', img.size, 0); d = ImageDraw.Draw(layer)
    s = max(w, h)
    if kind == 'rings':
        cx, cy = w * 0.85, h * 0.12
        for r in range(int(s * 0.08), int(s * 1.2), int(s * 0.07)): d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=40, width=max(2, w // 300))
    elif kind == 'dots':
        step = w // 18
        for y in range(step // 2, h, step):
            for x in range(step // 2, w, step): d.ellipse([x - step // 12, y - step // 12, x + step // 12, y + step // 12], fill=45)
    elif kind == 'grid':
        step = w // 12
        for x in range(0, w, step): d.line([x, 0, x, h], fill=30, width=max(1, w // 600))
        for y in range(0, h, step): d.line([0, y, w, y], fill=30, width=max(1, w // 600))
    elif kind == 'rays':
        cx, cy = w / 2, h * 0.55
        for i in range(0, 360, 12):
            a, b = math.radians(i), math.radians(i + 5)
            d.polygon([(cx, cy), (cx + s * 2 * math.cos(a), cy + s * 2 * math.sin(a)), (cx + s * 2 * math.cos(b), cy + s * 2 * math.sin(b))], fill=22)
    else: raise ValueError(f'unknown pattern {kind!r}: use rings, dots, grid, rays or none')
    img.paste(Image.new('RGB', img.size, rgb(color)), (0, 0), layer)

def draw_headline(img, box, lines, color, accent, max_lines, sub=None):
    """Bold headline, *accent* runs in the accent colour, sized to the widest line; returns the bottom y."""
    x0, y0, x1, _ = box
    d = ImageDraw.Draw(img); W = x1 - x0
    size = int(img.width * (0.085 if img.width < img.height else 0.06))
    while size > 12:
        f = font(BOLD_FONTS, size)
        if max(sum(f.getlength(t) for t, _ in line) for line in lines) <= W: break
        size = int(size * 0.94)
    lh = int(size * 1.18); y = y0
    for line in lines[:max(max_lines, 1)]:
        lw = sum(f.getlength(t) for t, _ in line); x = x0 + (W - lw) / 2
        for t, em in line:
            d.text((x, y), t, font=f, fill=accent if em else color); x += f.getlength(t)
        y += lh
    if sub:
        fs = font(REG_FONTS, int(size * 0.42)); y += int(size * 0.15)
        d.text((x0 + (W - fs.getlength(sub)) / 2, y), sub, font=fs, fill=color); y += int(size * 0.6)
    return y

def device_h(shot, width):
    """Height of device(shot, width) without rendering it."""
    bez = max(4, round(width * 0.035))
    return round((width - 2 * bez) * shot.height / shot.width) + 2 * bez

def device(shot, width, platform='ios', frame='black', cutout=True):
    """The screenshot inside a phone frame (RGBA). The screenshot pixels are only resized, never redrawn."""
    sw = width - 2 * (bez := max(4, round(width * 0.035)))
    sh = round(sw * shot.height / shot.width)
    h = sh + 2 * bez
    r_out = round(width * (0.13 if platform == 'ios' else 0.08)); r_in = max(2, r_out - bez)
    body = Image.new('RGBA', (width, h), (0, 0, 0, 0)); d = ImageDraw.Draw(body)
    d.rounded_rectangle([0, 0, width - 1, h - 1], r_out, fill=FRAMES.get(frame, frame))
    screen = shot.convert('RGB').resize((sw, sh), Image.LANCZOS)
    mask = Image.new('L', (sw, sh), 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw - 1, sh - 1], r_in, fill=255)
    body.paste(screen, (bez, bez), mask)
    if cutout:
        if platform == 'ios':  # dynamic island
            iw, ih = round(sw * 0.3), round(sw * 0.085); ix, iy = (width - iw) // 2, bez + round(sw * 0.03)
            d.rounded_rectangle([ix, iy, ix + iw, iy + ih], ih // 2, fill='#000')
        else:  # punch-hole camera
            r = round(sw * 0.025); cx, cy = width // 2, bez + round(sw * 0.045)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill='#000')
    return body, (bez, bez, bez + sw, bez + sh)

def compose(size, shot, theme, headline='', sub=None):
    """One store image: background, headline, framed device. Returns (RGB image, screen box on the canvas)."""
    W, H = size
    img = gradient(size, theme['bg'], theme['bg2'])
    text = theme['text'] or ('#ffffff' if luminance(theme['bg']) < 0.55 else '#15151c')
    pattern(img, theme.get('pattern'), text)
    accent = theme['accent2'] or theme['accent']
    m = round(W * 0.07)
    landscape = W > H
    if landscape:  # feature graphic: words left, device right
        bottom = draw_headline(img, (m, round(H * 0.28), round(W * 0.58), H), parse_headline(headline), text, accent, theme['headline_lines'], sub)
        dev_h = round(H * 0.86); dev_w = round(dev_h * shot.width / shot.height * 1.0)
        if (bh := device_h(shot, dev_w)) > dev_h: dev_w = round(dev_w * dev_h / bh)
        body, sbox = device(shot, dev_w, theme['platform'], theme['frame'], theme['cutout'])
        x, y = round(W * 0.78 - body.width / 2), (H - body.height) // 2
    else:
        top = draw_headline(img, (m, round(H * 0.06), W - m, H), parse_headline(headline), text, accent, theme['headline_lines'], sub) + round(H * 0.03)
        room_h = H - top - round(H * 0.04)
        dev_w = round(W * theme['device_max_w'])
        if (bh := device_h(shot, dev_w)) > room_h:  # fit the whole phone: never crop the UI
            dev_w = int(dev_w * room_h / bh)
        body, sbox = device(shot, dev_w, theme['platform'], theme['frame'], theme['cutout'])
        x, y = (W - body.width) // 2, top + (room_h - body.height) // 2
    shadow = Image.new('L', size, 0)
    ImageDraw.Draw(shadow).rounded_rectangle([x, y + body.width // 40, x + body.width, y + body.height + body.width // 40], body.width // 8, fill=110)
    img.paste(Image.new('RGB', size, (0, 0, 0)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(body.width // 25)))
    img.paste(body, (x, y), body)
    return img.convert('RGB'), (x + sbox[0], y + sbox[1], x + sbox[2], y + sbox[3])

def resolve(base, p): return Path(p).expanduser() if Path(p).expanduser().is_absolute() else base / p

def size_of(text):
    w, h = (int(v) for v in re.fullmatch(r'\s*(\d+)\s*[x×]\s*(\d+)\s*', text).groups())
    return w, h

def play_ok(w, h): return 320 <= min(w, h) and max(w, h) <= 3840 and max(w, h) <= 2 * min(w, h)

def render(config_path, sizes=None, feature=False, out_dir=None):
    cfg_path = Path(config_path); cfg = json.loads(cfg_path.read_text(encoding='utf-8')); base = cfg_path.parent
    images = cfg.get('images') or []
    if not images: raise SystemExit('set.json has no "images"')
    targets = [(n, SIZES[n]) for n in sizes] if sizes else [('', size_of(cfg.get('size', '1290x2796')))]
    out_root = Path(out_dir) if out_dir else resolve(base, cfg.get('out_dir', 'stores'))
    done = []
    for slot, (w, h) in targets:
        folder = out_root / (f'{slot}_{w}x{h}' if slot else '')
        folder.mkdir(parents=True, exist_ok=True)
        for i, im in enumerate(images, 1):
            theme = {**THEME, **cfg.get('theme', {}), **{k: v for k, v in im.items() if k in THEME}}
            shot = Image.open(resolve(base, im['screenshot']))
            img, _ = compose((w, h), shot, theme, im.get('headline', ''), im.get('sub'))
            out = folder / im.get('out', f'{i:02d}.png'); img.save(out); done.append(out)
    if feature:
        im = images[0]; theme = {**THEME, **cfg.get('theme', {}), **{k: v for k, v in im.items() if k in THEME}}
        f = cfg.get('feature', {})
        img, _ = compose(FEATURE, Image.open(resolve(base, f.get('screenshot', im['screenshot']))), theme, f.get('headline', im.get('headline', '')), f.get('sub'))
        out = out_root / 'feature-graphic_1024x500.png'; out_root.mkdir(parents=True, exist_ok=True); img.save(out); done.append(out)
    return done

def main(argv=None):
    ap = argparse.ArgumentParser(description='Turn raw app screenshots into store-ready App Store and Google Play images.')
    ap.add_argument('config', nargs='?', help='set.json (zaferayan/app-store-screenshot-skill format)')
    ap.add_argument('--stores', help='all, ios, play, or a comma list of: ' + ', '.join(SIZES))
    ap.add_argument('--feature', action='store_true', help='also make the 1024x500 Google Play feature graphic')
    ap.add_argument('--out', help='output folder (default: out_dir in set.json)')
    ap.add_argument('--strict', action='store_true', help='exit 1 when the copy has claims stores reject')
    ap.add_argument('--demo', action='store_true', help='render examples/set.json for every store')
    a = ap.parse_args(argv)
    if a.demo: a.config, a.stores, a.feature = a.config or str(Path(__file__).with_name('examples') / 'set.json'), a.stores or 'all', True
    if not a.config: ap.error('give a set.json or --demo')
    sizes = None
    if a.stores:
        sizes = [s for part in a.stores.split(',') for s in GROUPS.get(part.strip(), [part.strip()])]
        bad = [s for s in sizes if s not in SIZES]
        if bad: ap.error(f'unknown store size {bad}; use all, ios, play or {", ".join(SIZES)}')
    cfg = json.loads(Path(a.config).read_text(encoding='utf-8'))
    warn = check_text(cfg.get('images', []))
    for out, phrase in warn: print(f'warning: {out}: "{phrase}" is a claim both stores reject unless you can prove it', file=sys.stderr)
    if warn and a.strict: return 1
    for p in render(a.config, sizes, a.feature, a.out):
        with Image.open(p) as im:
            note = '' if not p.parent.name.startswith('android') or play_ok(*im.size) else '  (outside Play limits!)'
            print(f'{p}  {im.size[0]}x{im.size[1]} {im.mode}{note}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
