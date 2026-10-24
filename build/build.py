#!/usr/bin/env python3
"""
Build the static ENJZ site from the Shopify export.

Inputs :  data/products_all.json   (Shopify Admin API export)
          data/content.json        (page copy)
          data/palette.json        (colour pulled from each artwork)
Output :  the site itself
"""

import json, os, re, html, unicodedata
from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent
DATA = ROOT / "data"
# In the published repository this script lives in build/ and writes the repo
# root. In the original workspace it writes to site/.
OUT = ROOT.parent if ROOT.name == "build" else ROOT / "site"

AR = re.compile(r"[؀-ۿ]")
TAG = re.compile(r"<[^>]+>")

# ---------------------------------------------------------------- helpers

def strip_tags(s): return html.unescape(TAG.sub("", s or "")).strip()
def has_ar(s): return bool(AR.search(s or ""))
def esc(s): return html.escape(s or "", quote=True)

def slugify(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return re.sub(r"-+", "-", s) or "work"

def english_name(title):
    t = title.split("|")[0]
    t = re.split(r"[—–-]\s*(?=[؀-ۿ])", t)[0]
    t = re.sub(r"\(.*?\)", "", t)
    return t.strip(" —–-|") or title.split("|")[0].strip()

def arabic_name(title):
    head = title.split("|")[0]
    for p in [p.strip() for p in re.split(r"[—–]", head)]:
        if has_ar(p):
            return p
    return head.strip() if AR.search(head) else ""

def paragraphs(src):
    out = []
    for m in re.finditer(r"<p\b[^>]*>(.*?)</p>", src or "", re.S | re.I):
        txt = strip_tags(re.sub(r"<br\s*/?>", "\n", m.group(1), flags=re.I))
        txt = txt.replace(" ", " ").strip()
        if txt:
            out.append(txt)
    return out

QUOTE = re.compile(r"[\"“”«»](.+?)[\"“”«»]", re.S)

def extract_verses(desc_html, seo_desc):
    text = "\n".join(paragraphs(desc_html))
    quoted = [q.strip() for q in QUOTE.findall(text)]
    verse_ar = next((q for q in quoted if has_ar(q)), "")
    verse_en = ""
    m = re.search(r"English\s*:\s*(.+)", text)
    if m:
        verse_en = m.group(1).strip().strip('"“”')
    if not verse_en:
        verse_en = next((q for q in quoted if not has_ar(q) and len(q) > 12), "")
    if not verse_en and seo_desc:
        qm = QUOTE.search(seo_desc)
        if qm: verse_en = qm.group(1).strip()
    if not verse_ar:
        for p in paragraphs(desc_html):
            if has_ar(p) and len(p) < 220 and "ENJZ" not in p:
                verse_ar = p.strip().strip('"“”'); break
    return verse_ar.replace("/", " "), verse_en

BOILER = ("original gicl", "enjz works with arabic language", "limited editions. printed",
          "each print is produced on archival", "printed as a limited-edition",
          "available in multiple sizes", "available in a4", "edition sizes",
          "ships within", "sold without frame", "returns accepted")

def norm(s): return re.sub(r"[^\w؀-ۿ]+", "", s or "")

def prose_paragraphs(desc_html, verse_ar, verse_en):
    nar, nen = norm(verse_ar)[:24], norm(verse_en)[:24]
    keep = []
    for p in paragraphs(desc_html):
        low, npar = p.lower(), norm(p)
        if any(b in low for b in BOILER): continue
        if low.startswith("english:"): continue
        if nar and nar in npar: continue
        if nen and nen in npar: continue
        if len(p) < 25: continue
        keep.append(p)
    return keep

def money(v):
    f = float(v)
    return f"€{f:,.0f}" if f == int(f) else f"€{f:,.2f}"

LETTERS = "أنجزضحمسعلبرقطفكهدتثخصشغويةىئء"
def glyphs(*sources, fallback=("أ", "ن")):
    seen = []
    for s in sources:
        for ch in (s or ""):
            if ch in LETTERS and ch not in seen:
                seen.append(ch)
            if len(seen) >= 2:
                return (seen[0], seen[1])
    while len(seen) < 2:
        seen.append(fallback[len(seen)])
    return (seen[0], seen[1])

# ---------------------------------------------------------------- load

products = json.loads((DATA / "products_all.json").read_text())["data"]["products"]["nodes"]
content = json.loads((DATA / "content.json").read_text())
try:
    PAL = json.loads((DATA / "palette.json").read_text())
except FileNotFoundError:
    PAL = {}
HOUSE = {"accent": "#9F5D41", "deep": "#3A2015", "glow": "#C98A6B",
         "tint": "#F2EBE7", "tintish": "#EADFD8"}
SHOP = content["shop"]

works, used, image_manifest = [], set(), []

for p in products:
    name_en = english_name(p["title"])
    slug = slugify(name_en)
    if slug in used:
        n = 2
        while f"{slug}-{n}" in used: n += 1
        slug = f"{slug}-{n}"
    used.add(slug)

    verse_ar, verse_en = extract_verses(p["descriptionHtml"], (p.get("seo") or {}).get("description"))

    imgs = []
    for i, m in enumerate(p["media"]["nodes"]):
        if not m.get("image"): continue
        url = m["image"]["url"]
        base = f"assets/img/{slug}/{i:02d}"
        rec = {"cdn": url, "full": f"{base}-full.jpg", "thumb": f"{base}-thumb.jpg",
               "alt": (m.get("alt") or "").split("\n")[0].strip() or
                      f"{name_en} — Arabic poetry art print by Zein Sourany",
               "w": m["image"].get("width"), "h": m["image"].get("height")}
        imgs.append(rec)
        image_manifest.append({"url": url, "full": rec["full"], "thumb": rec["thumb"]})

    variants = [{"size": ("Single edition" if v["title"].lower() == "default title" else v["title"]),
                 "price": money(v["price"])} for v in p["variants"]["nodes"]]

    col = (p["collections"]["nodes"] or [{}])[0]
    works.append({
        "slug": slug, "name_en": name_en, "name_ar": arabic_name(p["title"]),
        "handle": p["handle"], "listed": p["status"] == "ACTIVE",
        "verse_ar": verse_ar, "verse_en": verse_en,
        "prose": prose_paragraphs(p["descriptionHtml"], verse_ar, verse_en),
        "images": imgs, "variants": variants, "collection": col.get("handle", ""),
        "seo_desc": (p.get("seo") or {}).get("description") or "",
        "pal": {**HOUSE, **PAL.get(slug, {})},
    })

by_slug = {w["slug"]: w for w in works}
listed = [w for w in works if w["listed"] and w["images"]]

cols = []
for ch in content["collection_order"]:
    meta = content["collections"][ch]
    members = [w for w in listed if w["collection"] == ch]
    if members:
        cols.append({**meta, "handle": ch, "works": members, "pal": members[0]["pal"]})

# Only publicly listed works may appear here — hidden pieces stay link-only.
HERO_SLUGS = ["vision", "prayer", "faith", "resistance", "absence", "lebanon"]
HEROES = [by_slug[s] for s in HERO_SLUGS
          if s in by_slug and by_slug[s]["images"] and by_slug[s]["listed"]][:6]
if not HEROES: HEROES = listed[:5]

# ---------------------------------------------------------------- chrome

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400'
         '&family=Amiri:ital,wght@0,400;0,700;1,400&family=Noto+Naskh+Arabic:wght@400;500&display=swap" rel="stylesheet">')

def ghost(g):
    return f'<div class="ghost" aria-hidden="true"><span>{g[0]}</span><span>{g[1]}</span></div>'

def img_tag(rec, kind="thumb", sizes=None, cls="", loading="lazy", up=""):
    cdnw = 1600 if kind == "full" else 900
    sep = "&" if "?" in rec["cdn"] else "?"
    dims = f' width="{rec["w"]}" height="{rec["h"]}"' if rec.get("w") and rec.get("h") else ""
    sz = f' sizes="{sizes}"' if sizes else ""
    return (f'<img class="{cls}" src="{esc(up + rec[kind])}" data-cdn="{esc(rec["cdn"] + sep + "width=" + str(cdnw))}"'
            f' alt="{esc(rec["alt"])}"{dims}{sz} loading="{loading}" decoding="async"'
            f' onerror="if(!this.dataset.f){{this.dataset.f=1;this.src=this.dataset.cdn}}">')

def theme_style(pal):
    return ";".join(f"--{k}:{v}" for k, v in pal.items() if k in
                    ("accent", "deep", "glow", "tint", "tintish"))

def page(title, desc, body, depth=0, pal=None, noindex=False, canonical="", gl=("أ", "ن")):
    up = "../" * depth
    pal = pal or HOUSE
    nav = f"""<header class="site">
  <a class="mark" href="{up}index.html" aria-label="ENJZ home">
    <span class="mark-ar" lang="ar" dir="rtl">أنجِز</span><span class="mark-en">ENJZ</span></a>
  <nav aria-label="Main">
    <a href="{up}works/index.html">Works</a>
    <a href="{up}about/index.html">About</a>
    <a href="{up}enjz/index.html">Why ENJZ</a>
    <a class="nav-cta" href="{up}enquire/index.html">Enquire</a>
  </nav>
</header>"""
    foot = f"""<footer class="site">
{ghost(("ج", "ز"))}
<div class="foot-grid">
  <div class="foot-mark">
    <span lang="ar" dir="rtl">أنجِز</span>
    <p>Original Arabic poetry, written by hand and made into limited-edition works on Hahnemühle archival paper. Madrid.</p>
  </div>
  <div><h2>Collections</h2><ul>{"".join(f'<li><a href="{up}collections/{c["slug"]}/index.html">{esc(c["title_en"])}</a></li>' for c in cols)}</ul></div>
  <div><h2>Studio</h2><ul>
    <li><a href="{up}about/index.html">About the artist</a></li>
    <li><a href="{up}enjz/index.html">Why ENJZ</a></li>
    <li><a href="{up}editions/index.html">Editions &amp; production</a></li>
    <li><a href="{up}enquire/index.html">Enquire about a work</a></li></ul></div>
  <div><h2>Elsewhere</h2><ul>
    <li><a href="mailto:{SHOP['email']}">{SHOP['email']}</a></li>
    <li><a href="{SHOP['instagram']}" rel="me noopener">Instagram</a></li>
    <li><a href="{SHOP['substack']}" rel="noopener">Substack</a></li></ul></div>
</div>
<p class="rights">© {date.today().year} Zein Sourany. All works and texts are the artist's own.</p>
</footer>"""
    robots = '<meta name="robots" content="noindex,follow">' if noindex else ""
    canon = f'<link rel="canonical" href="https://{SHOP["domain"]}/{canonical}">' if canonical else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}{canon}
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="ENJZ">
<meta name="theme-color" content="{pal['accent']}">
{FONTS}
<link rel="stylesheet" href="{up}assets/site.css">
<script>document.documentElement.classList.add('js')</script>
</head>
<body style="{theme_style(pal)}">
<a class="skip" href="#main">Skip to content</a>
{nav}
<main id="main">
{body}
</main>
{foot}
<script src="{up}assets/site.js" defer></script>
</body>
</html>"""

def write(rel, text):
    f = OUT / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")

def card(w, up):
    return f"""<a class="card r" href="{up}works/{w['slug']}/index.html" style="--c-accent:{w['pal']['accent']};--c-tint:{w['pal']['tint']}">
  <figure>{img_tag(w['images'][0], 'thumb', sizes='(max-width:700px) 86vw, (max-width:1100px) 44vw, 30vw', up=up)}</figure>
  <div class="card-id"><span class="card-ar" lang="ar" dir="rtl">{esc(w['name_ar'])}</span>
  <span class="card-en">{esc(w['name_en'])}</span></div></a>"""

def closing(heading, text, href, label, gl):
    return f"""<section class="closing">{ghost(gl)}
<div class="closing-in r"><h2>{heading}</h2><p>{text}</p>
<a class="btn" href="{href}">{label}</a></div></section>"""

# ---------------------------------------------------------------- home

slides, texts, dots = [], [], []
for n, w in enumerate(HEROES):
    p = w["pal"]
    slides.append(f'<figure class="slide{" is-on" if n == 0 else ""}" data-accent="{p["accent"]}" '
                  f'data-deep="{p["deep"]}" data-glow="{p["glow"]}" data-tint="{p["tint"]}" '
                  f'data-tintish="{p["tintish"]}">'
                  + img_tag(w["images"][0], "full", sizes="(max-width:900px) 92vw, 48vw",
                            loading="eager" if n == 0 else "lazy") + "</figure>")
    texts.append(f"""<div class="htext{' is-on' if n == 0 else ''}">
<h2 class="hero-verse" lang="ar" dir="rtl">{esc(w['verse_ar'])}</h2>
<p class="hero-en">{esc(w['verse_en'])}</p>
<p class="hero-name"><a href="works/{w['slug']}/index.html"><span lang="ar" dir="rtl">{esc(w['name_ar'])}</span> · {esc(w['name_en'])}</a></p></div>""")
    dots.append(f'<button type="button" aria-label="Show {esc(w["name_en"])}" '
                f'aria-current="{"true" if n == 0 else "false"}"></button>')

marquee = "".join(f'<a href="works/{w["slug"]}/index.html">'
                  + img_tag(w["images"][0], "thumb") + "</a>"
                  for w in (listed + listed)[:34])

bands = ""
for n, c in enumerate(cols):
    bands += f"""<section class="band{' washed' if n % 2 == 0 else ''}" style="{theme_style(c['pal'])}">
{ghost(glyphs(c['title_ar']))}
<div class="band-in">
  <div class="band-head r">
    <h2><span lang="ar" dir="rtl">{esc(c['title_ar'])}</span><span class="band-en">{esc(c['title_en'])}</span></h2>
    <div class="band-copy">{c['body']}</div>
    <a class="band-link" href="collections/{c['slug']}/index.html">All {len(c['works'])} works in {esc(c['title_en'])}</a>
  </div>
  <div class="grid">{"".join(card(w, "") for w in c['works'][:6])}</div>
</div></section>"""

home = f"""<section class="hero" id="hero">{ghost(("أ", "ن"))}
<div class="hero-inner">
  <div class="hero-stage">{"".join(slides)}</div>
  <div class="hero-copy"><h1 class="visually-hidden" hidden>ENJZ — Arabic poetry as visual art</h1>{"".join(texts)}</div>
</div>
<div class="hero-fixed">
  <p class="hero-note">The letters are mine. Each work begins as a poem I wrote by hand, and ends as pigment on Hahnemühle paper, in editions small enough to stay rare.</p>
  <div class="hero-links">
    <a class="btn" href="works/index.html">See the works</a>
    <a class="btn quiet" href="enquire/index.html">Commission a piece</a>
    <div class="dots" role="group" aria-label="Choose a work">{"".join(dots)}</div>
  </div>
</div></section>

<section class="strip" aria-label="All works"><div class="strip-track">{marquee}</div></section>

<section class="statement r"><p>Arabic here is <em>material</em>, not ornament — letters with weight, silence and history, made into something you can live beside.</p></section>

{bands}

{closing("Nothing here is sold from a shelf",
         "Every piece is made after the conversation. Tell me the work, the format and the wall it is going to, and I will tell you what is still available in the edition and what it costs to make.",
         "enquire/index.html", "Start a conversation", ("ض", "ح"))}"""

write("index.html", page("ENJZ — Arabic Poetry as Visual Art | Zein Sourany",
     SHOP["description"], home, 0, HEROES[0]["pal"], canonical=""))

# ---------------------------------------------------------------- works index

wbands = ""
for n, c in enumerate(cols):
    wbands += f"""<section class="band{' washed' if n % 2 == 0 else ''}" style="{theme_style(c['pal'])}">
{ghost(glyphs(c['title_ar']))}
<div class="band-in">
  <div class="band-head row r">
    <h2><span lang="ar" dir="rtl">{esc(c['title_ar'])}</span><span class="band-en">{esc(c['title_en'])}</span></h2>
    <a class="band-link" href="../collections/{c['slug']}/index.html">About this collection</a>
  </div>
  <div class="grid">{"".join(card(w, "../") for w in c['works'])}</div>
</div></section>"""

write("works/index.html", page("Works — ENJZ | Arabic Poetry Art Prints by Zein Sourany",
     f"All {len(listed)} ENJZ works: original Arabic poetry by Zein Sourany, printed as limited editions on Hahnemühle archival paper.",
     f"""<section class="page-hero">{ghost(("ع", "م"))}
<div class="page-head r"><h1><span lang="ar" dir="rtl">الأعمال</span><span class="page-en">Works</span></h1>
<p>{len(listed)} works across {len(cols)} collections, each one a poem before it was a picture.</p></div></section>
{wbands}""", 1, by_slug.get("prayer", listed[0])["pal"], canonical="works/"))

# ---------------------------------------------------------------- collections

for c in cols:
    body = f"""<section class="page-hero">{ghost(glyphs(c['title_ar']))}
<div class="page-head r"><h1><span lang="ar" dir="rtl">{esc(c['title_ar'])}</span><span class="page-en">{esc(c['title_en'])}</span></h1>
<div class="page-copy">{c['body']}</div></div></section>
<div class="section"><div class="grid wide">{"".join(card(w, "../../") for w in c['works'])}</div></div>
{closing("Enquire about a work in " + esc(c['title_en']),
         "Editions are limited and made to order. Tell me which piece and which format, and I will come back with what remains and what it costs.",
         "../../enquire/index.html", "Enquire", glyphs(c['title_ar']))}"""
    write(f"collections/{c['slug']}/index.html", page(
        f"{c['title_en']} — {c['title_ar']} | Arabic Poetry Art Prints | ENJZ",
        strip_tags(c["body"])[:155], body, 2, c["pal"], canonical=f"collections/{c['slug']}/"))

# ---------------------------------------------------------------- work pages

for w in works:
    if not w["images"]: continue
    cmeta = content["collections"].get(w["collection"])
    first, rest = w["images"][0], w["images"][1:]
    gl = glyphs(w["name_ar"], w["verse_ar"])

    editions = ""
    if w["variants"]:
        rows = "".join(f'<tr><td>{esc(v["size"])}</td><td class="num">{esc(v["price"])}</td></tr>'
                       for v in w["variants"])
        editions = f"""<div class="editions"><h2>Formats and editions</h2>
<table><thead><tr><th scope="col">Format</th><th scope="col" class="num">From</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="editions-note">Prices are for the unframed print, made to order. Shipping is quoted per destination.</p></div>"""

    plates = ""
    if rest:
        cls = "plates two" if len(rest) > 2 else "plates"
        plates = f'<section class="{cls}">' + "".join(
            f'<figure class="plate r">{img_tag(r, "full", sizes="(max-width:900px) 92vw, 46vw", up="../../")}'
            + (f'<figcaption>{esc(r["alt"])}</figcaption>' if r["alt"] else "") + "</figure>"
            for r in rest) + "</section>"

    crumb = (f'<a href="../../collections/{cmeta["slug"]}/index.html">{esc(cmeta["title_en"])}</a>'
             if cmeta else '<a href="../index.html">Works</a>')
    enq = f"../../enquire/index.html?work={w['name_en'].replace(' ', '%20')}"
    h1 = (f'<h1 lang="ar" dir="rtl">{esc(w["verse_ar"])}</h1>' if w["verse_ar"]
          else f'<h1>{esc(w["name_en"])}</h1>')

    body = f"""<section class="work-hero">{ghost(gl)}
<p class="crumb">{crumb}</p>
<div class="work-head">
  <div class="work-verse r">{h1}
    {f'<p class="verse-en">{esc(w["verse_en"])}</p>' if w["verse_en"] else ""}
    <p class="work-title"><span lang="ar" dir="rtl">{esc(w['name_ar'])}</span> · {esc(w['name_en'])}</p>
  </div>
  <figure class="work-lead">{img_tag(first, 'full', sizes='(max-width:900px) 92vw, 50vw', loading='eager', up='../../')}</figure>
</div></section>

<div class="work-body">
  <div class="work-prose r">{"".join(f"<p>{esc(t)}</p>" for t in w["prose"])}</div>
  <aside class="work-aside r">{editions}
    <a class="btn" href="{enq}">Enquire about this work</a>
    <div class="aside-note">{content['production']}</div></aside>
</div>
{plates}
{closing(f'Ask about <span lang="ar" dir="rtl">{esc(w["name_ar"])}</span>',
         "Editions are small and made after the conversation. Tell me the format you have in mind and the wall it is going to.",
         enq, "Enquire about this work", gl)}"""

    desc = w["seo_desc"] or f"{w['verse_en']} Original Arabic poetry art print by Zein Sourany on Hahnemühle archival paper."
    write(f"works/{w['slug']}/index.html", page(
        f"{w['name_en']} — {w['name_ar']} | Arabic Poetry Art Print | ENJZ",
        desc[:300], body, 2, w["pal"], noindex=not w["listed"],
        canonical=f"works/{w['slug']}/" if w["listed"] else ""))

# ---------------------------------------------------------------- about

def pic(slug, idx, kind="full", sizes="(max-width:900px) 92vw, 46vw", up="../"):
    w = by_slug.get(slug)
    if not w or not w["images"]: return ""
    return img_tag(w["images"][min(idx, len(w["images"]) - 1)], kind, sizes=sizes, up=up)

def thumb(slug, idx, up="../"):
    w = by_slug.get(slug)
    if not w or not w["images"]: return ""
    return img_tag(w["images"][min(idx, len(w["images"]) - 1)], "thumb",
                   sizes="(max-width:700px) 45vw, 22vw", up=up)

about_pal = by_slug.get("the-sculptor", listed[0])["pal"]
about = f"""<section class="page-hero">{ghost(("ز", "ن"))}
<div class="page-head r"><h1><span lang="ar" dir="rtl">عن الفنان</span><span class="page-en">About the artist</span></h1>
<p>Zein Sourany — a Lebanese poet and artist in Madrid, writing in Arabic and building what he writes into objects.</p></div></section>

<div class="split r">
  <figure>{pic("vision", 4)}</figure>
  <div class="txt">
    <p lang="ar" dir="rtl">زين العابدين الصوراني</p>
    <p>I am a Lebanese artist based in Madrid. My work lives at the intersection of language, memory and form.</p>
    <p>I work primarily with Arabic text — not as calligraphy in the traditional sense, but as meaning. Letters treated as living material, carrying weight, silence and history.</p>
  </div>
</div>

<div class="split flip r">
  <figure>{pic("prayer", 1)}</figure>
  <div class="txt">
    <p>I come to art from a life outside the studio. Years of work in complex, high-pressure environments taught me restraint, observation and the value of what is left unsaid. Creation, for me, is not escape; it is return.</p>
    <p>I work by hand, then translate each piece into a physical object through carefully tested prints. Scale, texture and negative space matter as much as the words themselves.</p>
  </div>
</div>

<section class="band washed" style="{theme_style(by_slug.get('resistance', listed[0])['pal'])}">
{ghost(("ح", "ر"))}
<div class="band-in">
  <div class="band-head r"><h2><span lang="ar" dir="rtl">التفاصيل</span><span class="band-en">Up close</span></h2>
  <div class="band-copy"><p>Gold leaf, scratched grounds, ink pressed into the surface rather than laid on it. The detail is where the poem stops being a text.</p></div></div>
</div>
<div class="detail-strip r">
  {thumb("vision", 4)}{thumb("the-warrior", 0)}{thumb("lebanon", 2)}{thumb("absence", 1)}
</div>
</section>

<div class="section narrow r">
  <h2>ENJZ is not a persona</h2>
  <p>It is a continuation — a way to give form to ideas that insist on being made visible. Each work is produced in limited quantities, with attention to how it lives on a wall, in light, and over time.</p>
</div>

{closing("Working together",
         "Commissions, exhibitions, collaborations and press enquiries all reach me at the same place.",
         "../enquire/index.html", "Get in touch", ("ز", "ي"))}"""
write("about/index.html", page("About the artist — Zein Sourany | ENJZ",
     "Zein Sourany is a Lebanese poet and artist in Madrid, working with Arabic text as living material rather than traditional calligraphy.",
     about, 1, about_pal, canonical="about/"))

# ---------------------------------------------------------------- why enjz

enjz_pal = by_slug.get("the-dark-anthem", listed[0])["pal"]
enjz_body = f"""<section class="page-hero">{ghost(("أ", "ز"))}
<div class="page-head r"><h1><span lang="ar" dir="rtl">لماذا أنجِز؟</span><span class="page-en">Why ENJZ</span></h1>
<p>ENJZ is <span lang="ar" dir="rtl">أنجِز</span> — the imperative. Accomplish it. It also carries the initials of the people I love.</p></div></section>
<div class="split r">
  <figure>{pic("the-dark-anthem", 0)}</figure>
  <div class="txt"><p>What follows is the text the whole project came out of — written first, built into pictures afterwards.</p>
  <p lang="ar" dir="rtl">هو أن يحترق طائر الفينيق ليبعث في لغة الضاد في أرض الأندلس قبل أن يحين المغيب</p></div>
</div>
<div class="bilingual r">
  <div class="col-ar" lang="ar" dir="rtl">{content['why_enjz_ar']}</div>
  <div class="col-en">{content['why_enjz_en']}</div>
</div>
{closing("See where it went",
         "The text became a body of work: five collections, each one a different way of carrying the same thing.",
         "../works/index.html", "See the works", ("ف", "ن"))}"""
write("enjz/index.html", page("Why ENJZ — أنجِز | The origin of the project",
     "ENJZ is أنجِز, the imperative: accomplish it. The text behind the name, in Arabic and English.",
     enjz_body, 1, enjz_pal, canonical="enjz/"))

# ---------------------------------------------------------------- editions

ed_pal = by_slug.get("resistance", listed[0])["pal"]
ed = f"""<section class="page-hero">{ghost(("ط", "ب"))}
<div class="page-head r"><h1><span lang="ar" dir="rtl">الطبعات والإنتاج</span><span class="page-en">Editions &amp; production</span></h1>
<p>How the work is made, numbered and sent.</p></div></section>
<div class="split r">
  <figure>{pic("resistance", 1)}</figure>
  <div class="txt">{content['production']}</div>
</div>
<div class="prose-page r">
<h2>Edition sizes</h2>
<table class="plain"><thead><tr><th scope="col">Format</th><th scope="col" class="num">Edition</th></tr></thead>
<tbody><tr><td>A4</td><td class="num">15</td></tr><tr><td>A3</td><td class="num">12</td></tr>
<tr><td>A2</td><td class="num">10</td></tr><tr><td>A1</td><td class="num">5</td></tr>
<tr><td>A0</td><td class="num">3</td></tr></tbody></table>
<h2>Certificate</h2>
<p>Every piece ships with a signed certificate of authenticity carrying the title in Arabic and English, the collection, the format, the edition number and a reference unique to that print.</p>
<h2>Damage</h2>
<p>If a work arrives damaged, send photographs within seven days of delivery and it will be replaced.</p>
</div>
{closing("Ready when you are",
         "Choose the work and the format, and I will confirm what is left in the edition before anything is made.",
         "../enquire/index.html", "Enquire", ("ط", "ب"))}"""
write("editions/index.html", page("Editions & production — ENJZ",
     "How ENJZ works are made: limited editions on Hahnemühle archival paper, printed after order, signed, numbered and certified.",
     ed, 1, ed_pal, canonical="editions/"))

# ---------------------------------------------------------------- enquire

opts = "".join(f'<option value="{esc(w["name_en"])}">{esc(w["name_en"])} — {esc(w["name_ar"])}</option>'
               for w in sorted(listed, key=lambda x: x["name_en"]))
enq_pal = by_slug.get("faith", listed[0])["pal"]
enquire = f"""<section class="page-hero">{ghost(("ح", "د"))}
<div class="page-head r"><h1><span lang="ar" dir="rtl">اطلب عملاً</span><span class="page-en">Enquire</span></h1>
<p>Nothing is kept in stock. Each work is produced after the conversation, which is how the editions stay small and how I know where every piece goes. Tell me what you are looking at and I will reply with what remains in the edition, the cost to make it, and shipping to you.</p></div></section>

<div class="enq">
  <form id="enq" class="enq-form r">
    <p class="field"><label for="f-work">Work</label>
      <select id="f-work" name="work"><option value="">Not sure yet — or a commission</option>{opts}</select></p>
    <p class="field"><label for="f-format">Format</label>
      <select id="f-format" name="format"><option value="">To be decided together</option>
      <option>A4</option><option>A3</option><option>A2</option><option>A1</option><option>A0</option></select></p>
    <p class="field"><label for="f-name">Your name</label>
      <input id="f-name" name="name" type="text" autocomplete="name" required></p>
    <p class="field"><label for="f-email">Email</label>
      <input id="f-email" name="email" type="email" autocomplete="email" required></p>
    <p class="field"><label for="f-where">Where it is going</label>
      <input id="f-where" name="where" type="text" placeholder="City, country — and the wall, if you like"></p>
    <p class="field"><label for="f-msg">Anything else</label>
      <textarea id="f-msg" name="message" rows="5" placeholder="A commission, an exhibition, a question about the poem."></textarea></p>
    <button class="btn" type="submit">Send enquiry</button>
    <p class="enq-fallback">This opens your email app with the message ready. If nothing happens, write to
      <a href="mailto:{SHOP['email']}">{SHOP['email']}</a>.</p>
  </form>
  <aside class="enq-aside r">
    <h2>Direct</h2>
    <p><a href="mailto:{SHOP['email']}">{SHOP['email']}</a></p>
    <p><a href="{SHOP['instagram']}" rel="me noopener">Instagram — @zeinsourany</a></p>
    <p><a href="{SHOP['substack']}" rel="noopener">Substack — the writing</a></p>
    <h2>What happens next</h2>
    <p>I answer personally, usually within two days. Once the edition and format are agreed, the work is printed, signed, numbered and certified, then shipped within two to three weeks.</p>
    <h2>Galleries and institutions</h2>
    <p>For exhibitions, portfolio reviews or collaborations, write directly and say so in the first line.</p>
  </aside>
</div>
<script>
(function () {{
  var p = new URLSearchParams(location.search).get('work');
  var sel = document.getElementById('f-work');
  if (p) {{
    var hit = Array.prototype.find.call(sel.options, function (o) {{ return o.value === p; }});
    if (!hit) {{ hit = new Option(p, p); sel.add(hit); }}   // link-only works
    sel.value = hit.value;
  }}
  document.getElementById('enq').addEventListener('submit', function (e) {{
    e.preventDefault();
    var d = new FormData(e.target), g = function (k) {{ return (d.get(k) || '').toString().trim(); }};
    var work = g('work') || 'A commission';
    var body = ['Work: ' + work, 'Format: ' + (g('format') || 'to be decided'),
      'Name: ' + g('name'), 'Email: ' + g('email'),
      'Destination: ' + (g('where') || '—'), '', g('message') || ''].join('\\n');
    location.href = 'mailto:{SHOP["email"]}?subject=' + encodeURIComponent('ENJZ enquiry — ' + work) +
      '&body=' + encodeURIComponent(body);
  }});
}})();
</script>"""
write("enquire/index.html", page("Enquire — ENJZ | Commission a work by Zein Sourany",
     "Every ENJZ work is made after the conversation. Enquire about an edition, a format or a commission.",
     enquire, 1, enq_pal, canonical="enquire/"))

# ---------------------------------------------------------------- 404

write("404.html", page("Page not found — ENJZ", "That page has moved.",
     closing("That page is no longer here", "The shop moved. The work did not.",
             "/works/index.html", "See the works", ("ض", "م")),
     0, HOUSE, noindex=True))

# ------------------------------------------------- legacy Shopify redirects

def redirect(path, target, title):
    write(path, f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0;url={target}">
<link rel="canonical" href="https://{SHOP['domain']}/{target.lstrip('/')}">
<meta name="robots" content="noindex,follow"><title>{esc(title)}</title></head>
<body><p>This page has moved to <a href="{target}">{esc(title)}</a>.</p></body></html>""")

for w in works:
    if w["images"]:
        redirect(f"products/{w['handle']}/index.html", f"/works/{w['slug']}/index.html", w["name_en"])
for c in cols:
    redirect(f"collections/{c['handle']}/index.html", f"/collections/{c['slug']}/index.html", c["title_en"])
for old, new in [("pages/about-the-artist", "/about/index.html"),
                 ("pages/about-enjz", "/enjz/index.html"),
                 ("pages/shipping-returns-1", "/editions/index.html"),
                 ("pages/contact", "/enquire/index.html"),
                 ("cart", "/enquire/index.html"),
                 ("collections/all", "/works/index.html")]:
    redirect(f"{old}/index.html", new, "ENJZ")

# ---------------------------------------------------------------- seo

urls = ["", "works/", "about/", "enjz/", "editions/", "enquire/"] + \
       [f"collections/{c['slug']}/" for c in cols] + [f"works/{w['slug']}/" for w in listed]
today = date.today().isoformat()
write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
      "".join(f"  <url><loc>https://{SHOP['domain']}/{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) +
      "</urlset>\n")
write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: https://{SHOP['domain']}/sitemap.xml\n")
write(".nojekyll", "")
write("assets/images.json", json.dumps(image_manifest, indent=1, ensure_ascii=False))

print(f"works {len(works)} ({len(listed)} listed) · collections {len(cols)} · "
      f"images {len(image_manifest)} · html {sum(1 for _ in OUT.rglob('*.html'))} · "
      f"palettes {len(PAL)}")
