"""Makes the project pictures: a square one (thumb.png) and a wide one (banner.png) per project.

Each picture is saved as a black PNG whose transparency carries the field value. The site paints
the accent colour through it (see .banner-pic and .hero-pic in custom.scss), so the pictures follow
whatever colour scheme is active, light or dark, without being regenerated.

Where the pictures come from:
  gray-scott-inversion   banner: a Gray-Scott simulation run here (labyrinth regime); thumb: stored run
  cellular-automata      banner: a lattice-gas diffusion automaton run here; thumb: stored run
  lmd-inversion          stored phase-field run
  fno                    stored training fields of the LMD surrogate that the FNO was trained on
  artificial-cell-differentiation   thesis figure modes_MDA_colony.png, recoloured
  artificial-cell-continuous-fields thesis ERK figure: network output (banner.png) under the
                                    nuclei imagery it was computed from (banner-over.png)

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
BANNER = (1920, 880)
RATIO = BANNER[0] / BANNER[1]

# Stored sources.
GS_RUN = r"C:\Clean Projects\gs-model-browser\viewer\data\runs\ic__edm_baseline__n64_obs819_z120000.js"
GS_SCENE = 0
LMD_RUN = r"C:\Users\Yumpu\Desktop\Jack\Bachelor thesis\LMD\proto_2d\lines_n12_d38"
CA_RUN = r"C:\Vscode\Gray-Scott solvers comparison\structures_lab\runs\A_bin_d4_template_none"
CA_DENSITY = "0.30"
CA_ALPHA = np.array([0.0, 0.55, 1.0, 0.25])  # empty, free material, assembled wall, compartment interior
FNO_DATA = r"C:\Users\Yumpu\Desktop\Jack\Bachelor thesis\LMD\surrogate\train_all.npz"
FNO_SAMPLES = (0, 1100, 2200)
ERK_DIR = r"C:\Users\Yumpu\Desktop\Jack\Bachelor thesis\Images\erk_field"
ERK_FIELD = os.path.join(ERK_DIR, "erk_recovered.png")  # field the U-net returned
ERK_NUCLEI = os.path.join(ERK_DIR, "nuclei_t.png")      # blurred-nuclei frame it was given
CELL_FIGURE =r"C:\Users\Yumpu\Desktop\Jack\Bachelor thesis\Images\modes_MDA_colony.png"

# Gray-Scott labyrinth simulation (5-point Laplacian, periodic, explicit Euler, dt = 1).
GS_SIM = dict(h=200, w=440, Du=0.16, Dv=0.08, F=0.029, k=0.057, steps=12000, seed=0)
# Lattice-gas diffusion: Toffoli-Margolus rule, every 2x2 block turned a quarter either way at random.
GAS_SIM = dict(h=220, w=480, steps=300, seed=0)


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


def unit(a):
    a = np.asarray(a, float)
    return (a - a.min()) / (a.max() - a.min())


def widest_band(a, ratio=RATIO):
    """The horizontal band of the banner's proportions in which the field varies most."""
    rows = max(1, min(a.shape[0], round(a.shape[1] / ratio)))
    score = [a[i:i + rows].var() for i in range(a.shape[0] - rows + 1)]
    i = int(np.argmax(score))
    return a[i:i + rows]


def gray_scott():
    # Thumbnail: a stored target pattern, stretched to its own range and inverted so the spots carry the colour.
    text = open(GS_RUN, encoding="utf-8").read()
    run = json.loads(text[text.index(",{") + 1:text.rindex(")")])
    panel = next(p for p in run["scenes"][GS_SCENE]["panels"] if p.get("role") == "given" and p["kind"] == "u")
    u = np.frombuffer(base64.b64decode(panel["data"]), np.uint8).reshape(panel["h"], panel["w"])
    save(1 - unit(u), "gray-scott-inversion", "thumb", THUMB, smooth=False)

    # Banner: labyrinth pattern simulated here.
    p = GS_SIM
    rng = np.random.default_rng(p["seed"])
    u = np.ones((p["h"], p["w"]))
    v = np.zeros((p["h"], p["w"]))
    for _ in range(40):  # scattered square seeds
        i, j = rng.integers(0, p["h"] - 6), rng.integers(0, p["w"] - 6)
        u[i:i + 6, j:j + 6], v[i:i + 6, j:j + 6] = 0.5, 0.25
    v += 0.01 * rng.random(v.shape)

    def lap(a):
        return np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1) - 4 * a

    for _ in range(p["steps"]):
        uvv = u * v * v
        u += p["Du"] * lap(u) - uvv + p["F"] * (1 - u)
        v += p["Dv"] * lap(v) + uvv - (p["F"] + p["k"]) * v
    save(unit(v), "gray-scott-inversion", "banner", BANNER, smooth=True)


def lmd():
    z = np.load(sorted(glob.glob(os.path.join(LMD_RUN, "depth_*.npz")))[-1])
    a = unit(z["cTa"])
    save(a, "lmd-inversion", "thumb", THUMB, smooth=True)
    save(widest_band(a), "lmd-inversion", "banner", BANNER, smooth=True)


def cellular_automata():
    # Thumbnail: final state of a stored wall-assembly run.
    z = np.load(os.path.join(CA_RUN, "examples.npz"))
    types = np.clip(np.rint(z[f"ex_{CA_DENSITY}_final"][0]).astype(int), 0, 3)
    save(CA_ALPHA[types], "cellular-automata", "thumb", THUMB, smooth=False)

    # Banner: gas particles, started as sharp discs and bars, after diffusing.
    p = GAS_SIM
    rng = np.random.default_rng(p["seed"])
    yy, xx = np.mgrid[:p["h"], :p["w"]]
    g = np.zeros((p["h"], p["w"]), bool)
    for cy, cx, r in ((110, 90, 60), (70, 250, 34), (160, 300, 26), (110, 410, 46)):
        g |= (yy - cy) ** 2 + (xx - cx) ** 2 < r ** 2
    g[:, 180:190] = True
    for t in range(p["steps"]):
        s = t % 2
        g = np.roll(g, (-s, -s), (0, 1))
        a, b, c, d = g[0::2, 0::2].copy(), g[0::2, 1::2].copy(), g[1::2, 0::2].copy(), g[1::2, 1::2].copy()
        cw = rng.random(a.shape) < 0.5
        g[0::2, 0::2] = np.where(cw, c, b)
        g[0::2, 1::2] = np.where(cw, a, d)
        g[1::2, 1::2] = np.where(cw, b, c)
        g[1::2, 0::2] = np.where(cw, d, a)
        g = np.roll(g, (s, s), (0, 1))
    save(g.astype(float), "cellular-automata", "banner", BANNER, smooth=False)


def fno():
    z = np.load(FNO_DATA)
    fields = [unit(z["uf"][i]) for i in FNO_SAMPLES]
    save(fields[0], "fno", "thumb", THUMB, smooth=True)
    gap = np.zeros((fields[0].shape[0], 4))
    wide = np.concatenate(sum([[f, gap] for f in fields], [])[:-1], axis=1)
    save(widest_band(wide), "fno", "banner", BANNER, smooth=True)


def cell_differentiation():
    rgb = np.asarray(Image.open(CELL_FIGURE).convert("RGB"), float) / 255
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dark = 1 - (0.2126 * r + 0.7152 * g + 0.0722 * b)
    red = (r - np.maximum(g, b)) > 0.3
    # The figure's red cells (the less common mode) get full colour, its grey cells about half.
    a = np.where(red, 1.0, 0.6 * dark)
    side = min(a.shape)
    square = Image.fromarray((a[:side, :side] * 255).astype(np.uint8)).resize((480, 480), Image.LANCZOS)
    save(np.asarray(square) / 255, "artificial-cell-differentiation", "thumb", THUMB, smooth=True)
    band = widest_band(a[::2, ::2])
    save(band, "artificial-cell-differentiation", "banner", BANNER, smooth=True)


def cell_continuous_fields():
    """Two layers from one validation sample: the field the network returned, and on top of it the
    blurred-nuclei frame it was given. The site paints them in two different colours."""
    def grid(path):  # the thesis panels are 64x64 fields enlarged 8 times
        return np.asarray(Image.open(path).convert("L"), float)[4::8, 4::8] / 255

    field, nuclei = grid(ERK_FIELD), grid(ERK_NUCLEI)
    slug = "artificial-cell-continuous-fields"
    save(unit(field), slug, "thumb", THUMB, smooth=True)
    # Both layers are cut to the same band so they stay aligned.
    rows = round(field.shape[1] / RATIO)
    i = int(np.argmax([field[k:k + rows].var() for k in range(field.shape[0] - rows + 1)]))
    save(0.85 * unit(field)[i:i + rows], slug, "banner", BANNER, smooth=True)
    save(unit(nuclei)[i:i + rows] ** 0.8, slug, "banner-over", BANNER, smooth=True)


if __name__ == "__main__":
    gray_scott()
    lmd()
    cellular_automata()
    fno()
    cell_differentiation()
    cell_continuous_fields()
