"""TEMPORARY. Writes design-preview.scss and design-compare.html, the side-by-side view of the
candidate colour sets. Run from the site folder:  python tools/build_compare.py .
Delete together with those two files once a set is chosen."""
import colorsys
import pathlib
import sys

root = pathlib.Path(sys.argv[1])


def rgb(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def lum(h):
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb(h)]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def cr(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def sat(h):
    return colorsys.rgb_to_hls(*rgb(h))[2]


def auto(cols, mode):
    """Background = lightest (or darkest) colour, text = the opposite end,
    links = the most saturated remaining colour that still reaches contrast 3, lines = the next one."""
    by = sorted(cols, key=lum)
    bg, fg = (by[-1], by[0]) if mode == 'light' else (by[0], by[-1])
    rest = [c for c in cols if c not in (bg, fg)]
    ok = [c for c in rest if cr(c, bg) >= 3]
    ac = max(ok, key=sat) if ok else max(rest, key=lambda c: cr(c, bg))
    rest2 = [c for c in rest if c != ac] or [ac]
    ru = min(rest2, key=lambda c: abs(cr(c, bg) - 2.5))
    hl = max(rest2, key=sat)
    return (bg, bg, fg, ac, ru, hl)


# (id, name, colours, {mode: explicit roles or None for auto}); roles = bg, surface, fg, accent, rule, hl
A = {'light': None, 'dark': None}
SETS = [
    ('s1', 'Set 1', '#95867B #DDC5B1 #CABEA9 #605550 #C7B5A7', {
        'light': ('#DDC5B1', '#C7B5A7', '#605550', '#605550', '#95867B', '#95867B'),
        'dark': ('#605550', '#605550', '#DDC5B1', '#CABEA9', '#95867B', '#C7B5A7')}),
    ('s3', 'Set 3 / Cold metal', '#0E0F11 #ECEEF0 #89969B #625B9F #A564DF', {
        'light': ('#ECEEF0', '#ECEEF0', '#0E0F11', '#625B9F', '#89969B', '#A564DF'),
        'dark': ('#0E0F11', '#0E0F11', '#ECEEF0', '#A564DF', '#89969B', '#625B9F')}),
    # Light half from set 4, dark half from the green-and-navy palette; light text uses that palette's navy.
    ('s4', 'Set 4 (light) with Green and navy (dark)',
     '#DBDCF9 #FFFFFF #E7EAF9 #AEBCE7 #8E82DC #5EC14E #091037 #E4F6E9 #5CC3E9 #91A4F6', {
        'light': ('#FFFFFF', '#E7EAF9', '#091037', '#8E82DC', '#AEBCE7', '#8E82DC'),
        'dark': auto('#5EC14E #091037 #E4F6E9 #5CC3E9 #91A4F6'.split(), 'dark')}),
    ('p1', 'Concrete wall', '#303337 #D9D8D3 #8E9090 #A9ADAB #9E9FAD', A),
]


def grade(v, need):
    return f'<b class="{"ok" if v >= need else "bad"}">{v:.1f}</b>'


css = ('/*-- scss:rules --*/\n'
       '// TEMPORARY: candidate colour themes for design-compare.html.\n'
       '// Selected per page with ?theme=<name>; remove once one set is chosen.\n')
rows = ''
print(f'{"theme":10s} text  link  line')
for sid, name, cols, modes in SETS:
    cols = cols.split()
    sw = ''.join(f'<span class="sw"><i style="background:{c}"></i>{c}</span>' for c in cols)
    cells = ''
    for m in ('light', 'dark'):
        if m not in modes:
            cells += '<div class="cell"><div class="cap">Dark: not requested for this set.</div></div>'
            continue
        key = f'{sid}-{m}'
        bg, sf, fg, ac, ru, hl = modes[m] or auto(cols, m)
        css += (f'html[data-theme="{key}"] {{\n  --bg: {bg};\n  --surface: {sf};\n  --fg: {fg};\n'
                f'  --accent: {ac};\n  --rule: {ru};\n  --hl: {hl};\n}}\n')
        print(f'{key:10s} {cr(fg, bg):4.1f}  {cr(ac, bg):4.1f}  {cr(ru, bg):4.1f}')
        cells += (f'<div class="cell"><div class="cap">{m.capitalize()} &middot; background {bg}, text {fg}, '
                  f'links {ac}, lines {ru}<br>Contrast: text {grade(cr(fg, bg), 4.5)}, links {grade(cr(ac, bg), 4.5)} '
                  f'&middot; <a target="_blank" data-theme="{key}" class="open">open full size</a></div>'
                  f'<div class="frame"><iframe loading="lazy" data-theme="{key}" title="{name} {m}"></iframe></div></div>')
    rows += f'<section><h2>{name}</h2><div class="sws">{sw}</div><div class="pair">{cells}</div></section>\n'

(root / 'design-preview.scss').write_text(css, encoding='utf-8', newline='\n')

(root / 'design-compare.html').write_text('''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Colour sets, light and dark</title>
<style>
  body { font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif; margin: 0; padding: 24px; background: #f4f4f4; color: #222; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  h2 { font-size: 16px; margin: 32px 0 6px; }
  .note { font-size: 13px; color: #555; margin: 0 0 8px; max-width: 900px; }
  .bar { position: sticky; top: 0; background: #f4f4f4; padding: 8px 0; z-index: 2; }
  button { font: inherit; padding: 4px 12px; margin-right: 6px; border: 1px solid #999; background: #fff; border-radius: 4px; cursor: pointer; }
  button.on { background: #222; color: #fff; border-color: #222; }
  .sws { display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 10px; font-family: ui-monospace, Consolas, monospace; font-size: 13px; }
  .sw i { display: inline-block; width: 18px; height: 18px; vertical-align: -4px; margin-right: 5px; border: 1px solid #888; }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .cap { font-size: 13px; color: #555; margin-bottom: 4px; }
  .ok { color: #17692f; }
  .bad { color: #b3261e; }
  .frame { height: 480px; overflow: hidden; border: 1px solid #bbb; background: #fff; }
  iframe { width: 166.667%; height: 800px; border: 0; transform: scale(.6); transform-origin: 0 0; }
  @media (max-width: 900px) { .pair { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<h1>Colour sets, light and dark</h1>
<p class="note">Contrast is measured against the background. Text and links need 4.5 to be comfortably readable;
green passes, red fails. For the screenshot palettes the roles were assigned by rule: lightest colour as light
background, darkest as dark background, the opposite end as text, the most saturated readable colour as links.</p>
<div class="bar">Page shown:
  <button data-page="index.html">Home</button>
  <button data-page="research/index.html">Research list</button>
  <button data-page="research/gray-scott-inversion/index.html">Project page</button>
  <button data-page="about.html">About</button>
</div>
''' + rows + '''<script>
  var buttons = document.querySelectorAll("button[data-page]");
  function show(page) {
    document.querySelectorAll("iframe").forEach(function (f) { f.src = page + "?theme=" + f.dataset.theme; });
    document.querySelectorAll("a.open").forEach(function (a) { a.href = page + "?theme=" + a.dataset.theme; });
    buttons.forEach(function (b) { b.classList.toggle("on", b.dataset.page === page); });
  }
  buttons.forEach(function (b) { b.addEventListener("click", function () { show(b.dataset.page); }); });
  show("research/index.html");
</script>
</body>
</html>
''', encoding='utf-8', newline='\n')
