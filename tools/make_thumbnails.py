"""Makes the project pictures from stored runs: a square one (thumb.png) and a wide one (banner.png).

Each picture is saved as a black PNG whose transparency carries the field value. The site paints
the accent colour through it (see .banner-pic and .hero-pic in custom.scss), so the pictures follow
whatever colour scheme is active, light or dark, without being regenerated.

Run with a Python that has numpy and Pillow:
    python tools/make_thumbnails.py
Nothing in the source folders is modified.
"""
import base64
import glob
import json
import os

import numpy as np
from PIL import Image

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THUMB = (240, 240)     # width, height in pixels
BANNER = (1680, 720)   # 21:9

# Where each picture comes from.
GS_RUN = r"C:\Clean Projects\gs-model-browser\viewer\data\runs\ic__edm_baseline__n64_obs819_z120000.js"
GS_SCENE = 0
LMD_RUN = r"C:\Users\Yumpu\Desktop\Jack\Bachelor thesis\LMD\proto_2d\lines_n12_d38"
CA_RUN = r"C:\Vscode\Gray-Scott solvers comparison\structures_lab\runs\A_bin_d4_template_none"
CA_DENSITY = "0.30"                 # thumbnail
CA_BANNER_DENSITIES = ("0.30", "0.50")  # banner: one row of examples per density
CA_ALPHA = np.array([0.0, 0.55, 1.0, 0.25])  # empty, free material, assembled wall, compartment interior


def save(alpha01, slug, name, size, smooth):
    """alpha01: 2D array in [0, 1]. Writes research/<slug>/<name>.png at the given size."""
    a = np.clip(np.asarray(alpha01, float), 0, 1)
    img = Image.fromarray((a * 255).round().astype(np.uint8), "L")
    img = img.resize(size, Image.BICUBIC if smooth else Image.NEAREST)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.putalpha(img)
    path = os.path.join(SITE, "research", slug, name + ".png")
    out.save(path, optimize=True)
    print(f"{slug}/{name}.png: from a {a.shape[0]}x{a.shape[1]} field, {os.path.getsize(path) // 1024} KB")


def widest_band(a, ratio):
    """The horizontal band of the banner's proportions in which the field varies most."""
    rows = max(1, round(a.shape[1] / ratio))
    score = [a[i:i + rows].var() for i in range(a.shape[0] - rows + 1)]
    i = int(np.argmax(score))
    return a[i:i + rows]


def gray_scott():
    text = open(GS_RUN, encoding="utf-8").read()
    run = json.loads(text[text.index(",{") + 1:text.rindex(")")])
    panel = next(p for p in run["scenes"][GS_SCENE]["panels"] if p.get("role") == "given" and p["kind"] == "u")
    u = np.frombuffer(base64.b64decode(panel["data"]), np.uint8).reshape(panel["h"], panel["w"]).astype(float)
    # Stretched to the field's own range and inverted, so the spots (low u) carry the colour.
    a = 1 - (u - u.min()) / (u.max() - u.min())
    save(a, "gray-scott-inversion", "thumb", THUMB, smooth=False)
    save(widest_band(a, BANNER[0] / BANNER[1]), "gray-scott-inversion", "banner", BANNER, smooth=True)


def lmd():
    z = np.load(sorted(glob.glob(os.path.join(LMD_RUN, "depth_*.npz")))[-1])
    ta = z["cTa"]
    a = (ta - ta.min()) / (ta.max() - ta.min())
    save(a, "lmd-inversion", "thumb", THUMB, smooth=True)
    save(widest_band(a, BANNER[0] / BANNER[1]), "lmd-inversion", "banner", BANNER, smooth=True)


def cellular_automata():
    z = np.load(os.path.join(CA_RUN, "examples.npz"))

    def alpha(types):
        return CA_ALPHA[np.clip(np.rint(types).astype(int), 0, 3)]

    save(alpha(z[f"ex_{CA_DENSITY}_final"][0]), "cellular-automata", "thumb", THUMB, smooth=False)
    # Banner: every stored example of two densities, separated by two empty cells.
    rows = []
    for d in CA_BANNER_DENSITIES:
        finals = z[f"ex_{d}_final"]
        gap = np.zeros((finals.shape[1], 2))
        rows.append(np.concatenate(sum([[alpha(f), gap] for f in finals], [])[:-1], axis=1))
    gap = np.zeros((2, rows[0].shape[1]))
    save(np.concatenate(sum([[r, gap] for r in rows], [])[:-1], axis=0), "cellular-automata", "banner", BANNER, smooth=False)


if __name__ == "__main__":
    gray_scott()
    lmd()
    cellular_automata()
