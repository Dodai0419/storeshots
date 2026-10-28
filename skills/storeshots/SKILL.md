---
name: storeshots
description: Turn raw app screenshots into App Store and Google Play marketing images (headline, phone frame, background) at every store size, plus the Play feature graphic, and flag copy the stores reject. Use when the user asks for store screenshots, App Store / Play Store images, or a feature graphic for their app.
---

# storeshots

One Python file (needs Pillow). No Chrome, no Node, no network.

## Steps
1. Ask for (or find) the raw screenshots, in the order the story should go: value, main feature, differentiator.
2. Write `set.json` next to them. Short headlines, 2 lines max, `*word*` gets the accent colour:

```json
{
  "out_dir": "stores",
  "theme": {"accent2": "#ffe08a", "device_max_w": 0.66, "platform": "ios", "frame": "black"},
  "feature": {"headline": "Small habits,\n*every day*"},
  "images": [
    {"screenshot": "raw/home.png", "out": "01-today.png", "headline": "Every habit,\n*one glance*",
     "bg": "#22a88b", "bg2": "#11705f", "pattern": "rings"}
  ]
}
```

3. Run from the repo folder:

```bash
python storeshots.py path/to/set.json --stores all --feature   # iPhone 6.9", iPad 13", Android phone + 7" tablet, feature graphic
python storeshots.py path/to/set.json                          # just the "size" in set.json (default 1290x2796)
python storeshots.py path/to/set.json --stores play --strict   # fail if the copy has "#1", "best", prices...
```

4. Show the user the files it printed. Every output is RGB (no alpha) at the exact store size.

Theme keys (any can be set per image): `bg`, `bg2`, `accent`, `accent2`, `text`, `platform` (ios/android),
`frame` (black/white/silver/gold or a colour), `cutout`, `device_max_w`, `headline_lines`, `pattern`
(rings/dots/grid/rays/none). `sub` on an image adds a one-line subheadline.
