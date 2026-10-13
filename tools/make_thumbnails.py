"""Makes the pictures shown in the Research list, one per project, from stored runs.

Each picture is saved as a black PNG whose transparency carries the field value. The site paints
the accent colour through it (see .project-thumb in custom.scss), so the pictures follow whatever
colour scheme is active, light or dark, without being regenerated.

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
SIZE = 240  # pixels, square

# Where each picture comes from.
GS_RUN = r"C:\Clean Projects\gs-model-browser\viewer\data\runs\ic__edm_baseline__n64_obs819_z120000.js"
GS_SCENE = 0
LMD_RUN = r"C:\Users\Yumpu\Desktop\Jack\Bachelor thesis\LMD\proto_2d\lines_n12_d38"
CA_RUN = r"C:\Vscode\Gray-Scott solvers comparison\structures_lab\runs\A_bin_d4_template_none"
CA_DENSITY = "0.30"
CA_ALPHA = np.array([0.0, 0.55, 1.0, 0.25])  # empty, free material, assembled wall, compartment interior


def save(alpha01, slug):
    """alpha01: 2D array in [0, 1]. Writes research/<slug>/thumb.png."""
    a = np.clip(np.asarray(alpha01, float), 0, 1)
    img = Image.fromarray((a * 255).round().astype(np.uint8), "L")
    # Small grids are enlarged without smoothing so single cells stay sharp.
    img = img.resize((SIZE, SIZE), Image.NEAREST if max(a.shape) <= SIZE // 2 else Image.LANCZOS)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.putalpha(img)
    path = os.path.join(SITE, "research", slug, "thumb.png")
    out.save(path)
    print(f"{slug}: {a.shape[0]}x{a.shape[1]} field -> {os.path.relpath(path, SITE)}")


def gray_scott():
    text = open(GS_RUN, encoding="utf-8").read()
    run = json.loads(text[text.index(",{") + 1:text.rindex(")")])
    panel = next(p for p in run["scenes"][GS_SCENE]["panels"] if p.get("role") == "given" and p["kind"] == "u")
    u = np.frombuffer(base64.b64decode(panel["data"]), np.uint8).reshape(panel["h"], panel["w"]) / 255.0
    save(u, "gray-scott-inversion")
    return panel["title"]


def lmd():
    last = sorted(glob.glob(os.path.join(LMD_RUN, "depth_*.npz")))[-1]
    z = np.load(last)
    ta = z["cTa"]
    save((ta - ta.min()) / (ta.max() - ta.min()), "lmd-inversion")
    return f"{os.path.basename(last)}, front depth {float(z['depth_nm']):.2f} nm"


def cellular_automata():
    z = np.load(os.path.join(CA_RUN, "examples.npz"))
    types = np.clip(np.rint(z[f"ex_{CA_DENSITY}_final"][0]).astype(int), 0, 3)
    save(CA_ALPHA[types], "cellular-automata")


if __name__ == "__main__":
    print("Gray-Scott panel:", gray_scott())
    print("LMD snapshot:", lmd())
    cellular_automata()
