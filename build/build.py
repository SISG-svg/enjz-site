#!/usr/bin/env python3
"""
Build the static ENJZ site from the Shopify export.

Inputs :  data/products_all.json   (Shopify Admin API export)
          data/content.json        (hand-curated page copy)
Output :  site/                     (a complete, deployable static site)
"""

import json, os, re, html, shutil, unicodedata
from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent
DATA = ROOT / "data"
# Inside the published repository this script lives in build/, and the site it
# generates is the repository root. In the original workspace it writes to site/.
OUT = ROOT.parent if ROOT.name == "build" else ROOT / "site"

AR = re.compile(r"[؀-ۿ]")
TAG = re.compile(r"<[^>]+>")

# ---------------------------------------------------------------- helpers

def strip_tags(s):
    return html.unescape(TAG.sub("", s or "")).strip()

def has_ar(s):
    return bool(AR.search(s or ""))

def slugify(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return re.sub(r"-+", "-", s) or "work"

def english_name(title):
    """'Absence — الغياب | Arabic Poetry Art Print | ENJZ' -> 'Absence'"""
    t = title.split("|")[0]
    t = re.split(r"[—–-]\s*(?=[؀-ۿ])", t)[0]
    t = re.sub(r"\(.*?\)", "", t)
    return t.strip(" —–-|") or title.split("|")[0].strip()

def arabic_name(title):
    head = title.split("|")[0]
    parts = [p.strip() for p in re.split(r"[—–]", head)]
    for p in parts:
        if has_ar(p):
            return p
    m = AR.search(head)
    return head.strip() if m else ""

def paragraphs(html_src):
    out = []
    for m in re.finditer(r"<p\b[^>]*>(.*?)</p>", html_src or "", re.S | re.I):
        inner = m.group(1)
        inner = re.sub(r"<br\s*/?>", "\n", inner, flags=re.I)
        txt = strip_tags(inner)
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
        if qm:
            verse_en = qm.group(1).strip()

    if not verse_ar:
        for p in paragraphs(desc_html):
            if has_ar(p) and len(p) < 220 and "ENJZ" not in p:
                verse_ar = p.strip().strip('"“”')
                break
    return verse_ar.replace("/", " "), verse_en

BOILER = (
    "original gicl", "enjz works with arabic language", "limited editions. printed",
    "each print is produced on archival", "printed as a limited-edition",
    "available in multiple sizes", "available in a4", "edition sizes",
    "ships within", "sold without frame", "returns accepted",
)

def norm(s):
    return re.sub(r"[^\w؀-ۿ]+", "", s or "")

def prose_paragraphs(desc_html, verse_ar, verse_en):
    nar, nen = norm(verse_ar)[:24], norm(verse_en)[:24]
    keep = []
    for p in paragraphs(desc_html):
        low, npar = p.lower(), norm(p)
        if any(b in low for b in BOILER):
            continue
        if low.startswith("english:"):
            continue
        if nar and nar in npar:
            continue
        if nen and nen in npar:
            continue
        if len(p) < 25:
            continue
        keep.append(p)
    return keep

def money(v):
    f = float(v)
    return f"€{f:,.0f}" if f == int(f) else f"€{f:,.2f}"

def esc(s):
    return html.escape(s or "", quote=True)

# ---------------------------------------------------------------- load

products = json.loads((DATA / "products_all.json").read_text())["data"]["products"]["nodes"]
content = json.loads((DATA / "content.json").read_text())
SHOP = content["shop"]

works = []
used_slugs = set()
image_manifest = []

for p in products:
    name_en = english_name(p["title"])
    slug = slugify(name_en)
    if slug in used_slugs:
        n = 2
        while f"{slug}-{n}" in used_slugs:
            n += 1
        slug = f"{slug}-{n}"
    used_slugs.add(slug)

    verse_ar, verse_en = extract_verses(p["descriptionHtml"], (p.get("seo") or {}).get("description"))
    prose = prose_paragraphs(p["descriptionHtml"], verse_ar, verse_en)

    imgs = []
    for i, m in enumerate(p["media"]["nodes"]):
        if not m.get("image"):
            continue
        url = m["image"]["url"]
        base = f"assets/img/{slug}/{i:02d}"
        rec = {
            "cdn": url,
            "full": f"{base}-full.jpg",
            "thumb": f"{base}-thumb.jpg",
            "alt": (m.get("alt") or "").split("\n")[0].strip() or f"{name_en} — Arabic poetry art print by Zein Sourany",
            "w": m["image"].get("width"),
            "h": m["image"].get("height"),
        }
        imgs.append(rec)
        image_manifest.append({"url": url, "full": rec["full"], "thumb": rec["thumb"]})

    variants = []
    for v in p["variants"]["nodes"]:
        t = v["title"]
        if t.lower() == "default title":
            t = "Single edition"
        variants.append({"size": t, "price": money(v["price"])})

    col = (p["collections"]["nodes"] or [{}])[0]
    works.append({
        "slug": slug,
        "name_en": name_en,
        "name_ar": arabic_name(p["title"]),
        "handle": p["handle"],
        "status": p["status"],
        "listed": p["status"] == "ACTIVE",
        "verse_ar": verse_ar,
        "verse_en": verse_en,
        "prose": prose,
        "images": imgs,
        "variants": variants,
        "collection": col.get("handle", ""),
        "seo_desc": (p.get("seo") or {}).get("description") or "",
        "tags": p.get("tags") or [],
    })

by_slug = {w["slug"]: w for w in works}
listed = [w for w in works if w["listed"] and w["images"]]

cols = []
for ch in content["collection_order"]:
    meta = content["collections"][ch]
    members = [w for w in listed if w["collection"] == ch]
    if members:
        cols.append({**meta, "handle": ch, "works": members})

HERO = by_slug.get("vision") or listed[0]

# ---------------------------------------------------------------- chrome

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400'
         '&family=Amiri:ital,wght@0,400;0,700;1,400&family=Noto+Naskh+Arabic:wght@400;500&display=swap" rel="stylesheet">')

def img_tag(rec, kind="thumb", sizes=None, cls="", loading="lazy"):
    src = rec[kind]
    cdnw = 1600 if kind == "full" else 900
    sep = "&" if "?" in rec["cdn"] else "?"
    fallback = f'{rec["cdn"]}{sep}width={cdnw}'
    ratio = ""
    if rec.get("w") and rec.get("h"):
        ratio = f' width="{rec["w"]}" height="{rec["h"]}"'
    sz = f' sizes="{sizes}"' if sizes else ""
    return (f'<img class="{cls}" src="{esc(src)}" data-cdn="{esc(fallback)}" alt="{esc(rec["alt"])}"'
            f'{ratio}{sz} loading="{loading}" decoding="async" '
            f'onerror="if(!this.dataset.f){{this.dataset.f=1;this.src=this.dataset.cdn}}">')

def page(title, desc, body, depth=0, extra_head="", noindex=False, canonical=""):
    up = "../" * depth
    nav = f"""
<header class="site">
  <a class="mark" href="{up}index.html" aria-label="ENJZ home">
    <span class="mark-ar" lang="ar" dir="rtl">أنجِز</span><span class="mark-en">ENJZ</span>
  </a>
  <nav aria-label="Main">
    <a href="{up}works/index.html">Works</a>
    <a href="{up}about/index.html">About</a>
    <a href="{up}enjz/index.html">Why ENJZ</a>
    <a class="nav-cta" href="{up}enquire/index.html">Enquire</a>
  </nav>
</header>"""
    foot = f"""
<footer class="site">
  <div class="foot-grid">
    <div class="foot-mark">
      <span lang="ar" dir="rtl">أنجِز</span>
      <p>Original Arabic poetry, written by hand and made into limited-edition works on Hahnemühle archival paper. Madrid.</p>
    </div>
    <div>
      <h2>Collections</h2>
      <ul>{"".join(f'<li><a href="{up}collections/{c["slug"]}/index.html">{esc(c["title_en"])}</a></li>' for c in cols)}</ul>
    </div>
    <div>
      <h2>Studio</h2>
      <ul>
        <li><a href="{up}about/index.html">About the artist</a></li>
        <li><a href="{up}enjz/index.html">Why ENJZ</a></li>
        <li><a href="{up}editions/index.html">Editions &amp; production</a></li>
        <li><a href="{up}enquire/index.html">Enquire about a work</a></li>
      </ul>
    </div>
    <div>
      <h2>Elsewhere</h2>
      <ul>
        <li><a href="mailto:{SHOP['email']}">{SHOP['email']}</a></li>
        <li><a href="{SHOP['instagram']}" rel="me noopener">Instagram</a></li>
        <li><a href="{SHOP['substack']}" rel="noopener">Substack</a></li>
      </ul>
    </div>
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
{FONTS}
<link rel="stylesheet" href="{up}assets/site.css">
{extra_head}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{nav}
<main id="main">
{body}
</main>
{foot}
</body>
</html>"""

def write(relpath, text):
    f = OUT / relpath
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------- pieces

def verse_block(w, tag="h1"):
    ar = f'<p class="verse-ar" lang="ar" dir="rtl">{esc(w["verse_ar"])}</p>' if w["verse_ar"] else ""
    en = f'<p class="verse-en">{esc(w["verse_en"])}</p>' if w["verse_en"] else ""
    return ar + en

def work_card(w, up):
    rec = w["images"][0]
    return f"""<a class="card" href="{up}works/{w['slug']}/index.html">
  <figure>{img_tag(rec, 'thumb', sizes='(max-width:700px) 86vw, (max-width:1100px) 44vw, 30vw')}</figure>
  <div class="card-id">
    <span class="card-ar" lang="ar" dir="rtl">{esc(w['name_ar'])}</span>
    <span class="card-en">{esc(w['name_en'])}</span>
  </div>
</a>"""

# ---------------------------------------------------------------- home

hero_img = HERO["images"][0]
hero_more = [w for w in listed if w["slug"] != HERO["slug"]][:6]

home_body = f"""
<section class="hero">
  <figure class="hero-fig">{img_tag(hero_img, 'full', sizes='(max-width:900px) 92vw, 48vw', loading='eager')}</figure>
  <div class="hero-text">
    <h1 class="hero-verse" lang="ar" dir="rtl">{esc(HERO['verse_ar'])}</h1>
    <p class="hero-en">{esc(HERO['verse_en'])}</p>
    <p class="hero-note">The letters are not copied from anyone. The poems are mine, written by hand, then built into a surface you can live with — pigment on Hahnemühle paper, in editions small enough to stay rare.</p>
    <p class="hero-links">
      <a class="btn" href="works/index.html">See the works</a>
      <a class="btn quiet" href="enquire/index.html">Commission a piece</a>
    </p>
    <p class="hero-cap"><span lang="ar" dir="rtl">{esc(HERO['name_ar'])}</span> · {esc(HERO['name_en'])}</p>
  </div>
</section>

<section class="statement">
  <p>Arabic is treated here as material, not ornament. Each work begins as a poem I wrote, in my own hand, and ends as a printed object made to be looked at slowly.</p>
</section>

{"".join(f'''
<section class="band">
  <div class="band-head">
    <h2><span lang="ar" dir="rtl">{esc(c["title_ar"])}</span><span class="band-en">{esc(c["title_en"])}</span></h2>
    <div class="band-copy">{c["body"]}</div>
    <a class="band-link" href="collections/{c["slug"]}/index.html">All {len(c["works"])} works in {esc(c["title_en"])}</a>
  </div>
  <div class="grid">{"".join(work_card(w, "") for w in c["works"][:6])}</div>
</section>''' for c in cols)}

<section class="closing">
  <h2>Nothing here is sold from a shelf</h2>
  <p>Every piece is made after the conversation. Tell me the work, the format and the wall it is going to, and I will tell you what is still available in the edition and what it costs to make.</p>
  <a class="btn" href="enquire/index.html">Start a conversation</a>
</section>
"""
write("index.html", page(
    "ENJZ — Arabic Poetry as Visual Art | Zein Sourany",
    SHOP["description"], home_body, 0, canonical=""))

# ---------------------------------------------------------------- works index

works_body = f"""
<header class="page-head">
  <h1><span lang="ar" dir="rtl">الأعمال</span><span class="page-en">Works</span></h1>
  <p>{len(listed)} works across {len(cols)} collections. Each is an original poem by Zein Sourany, written by hand and printed in a limited edition on Hahnemühle archival paper.</p>
</header>
{"".join(f'''
<section class="band">
  <div class="band-head compact">
    <h2><span lang="ar" dir="rtl">{esc(c["title_ar"])}</span><span class="band-en">{esc(c["title_en"])}</span></h2>
    <a class="band-link" href="../collections/{c["slug"]}/index.html">About this collection</a>
  </div>
  <div class="grid">{"".join(work_card(w, "../") for w in c["works"])}</div>
</section>''' for c in cols)}
"""
write("works/index.html", page("Works — ENJZ | Arabic Poetry Art Prints by Zein Sourany",
     f"All {len(listed)} ENJZ works: original Arabic poetry by Zein Sourany, printed as limited editions on Hahnemühle archival paper.",
     works_body, 1, canonical="works/"))

# ---------------------------------------------------------------- collections

for c in cols:
    body = f"""
<header class="page-head">
  <h1><span lang="ar" dir="rtl">{esc(c['title_ar'])}</span><span class="page-en">{esc(c['title_en'])}</span></h1>
  <div class="page-copy">{c['body']}</div>
</header>
<div class="grid wide">{"".join(work_card(w, "../../") for w in c["works"])}</div>
<section class="closing">
  <h2>Enquire about a work in {esc(c['title_en'])}</h2>
  <p>Editions are limited and made to order. Tell me which piece and which format, and I will come back with what remains and what it costs.</p>
  <a class="btn" href="../../enquire/index.html">Enquire</a>
</section>"""
    write(f"collections/{c['slug']}/index.html", page(
        f"{c['title_en']} — {c['title_ar']} | Arabic Poetry Art Prints | ENJZ",
        strip_tags(c["body"])[:155], body, 2, canonical=f"collections/{c['slug']}/"))

# ---------------------------------------------------------------- work pages

for w in works:
    if not w["images"]:
        continue
    cmeta = content["collections"].get(w["collection"])
    first, rest = w["images"][0], w["images"][1:]

    editions = ""
    if w["variants"]:
        rows = "".join(
            f'<tr><td>{esc(v["size"])}</td><td class="num">{esc(v["price"])}</td></tr>'
            for v in w["variants"])
        editions = f"""
<section class="editions">
  <h2>Formats and editions</h2>
  <table>
    <thead><tr><th scope="col">Format</th><th scope="col" class="num">From</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p class="editions-note">Prices are for the unframed print, made to order. Shipping is quoted per destination when you enquire.</p>
</section>"""

    gallery = ""
    if rest:
        gallery = '<section class="plates">' + "".join(
            f'<figure class="plate">{img_tag(r, "full", sizes="(max-width:900px) 92vw, 70vw")}'
            f'{f"<figcaption>{esc(r['alt'])}</figcaption>" if r["alt"] else ""}</figure>'
            for r in rest) + "</section>"

    prose = "".join(f"<p>{esc(t)}</p>" for t in w["prose"])
    crumb = (f'<a href="../../collections/{cmeta["slug"]}/index.html">{esc(cmeta["title_en"])}</a>'
             if cmeta else '<a href="../index.html">Works</a>')

    enq = f"../../enquire/index.html?work={esc(w['name_en'].replace(' ', '%20'))}"

    body = f"""
<article class="work">
  <p class="crumb">{crumb}</p>
  <header class="work-head">
    <div class="work-verse">
      {f'<h1 class="verse-ar" lang="ar" dir="rtl">{esc(w["verse_ar"])}</h1>' if w["verse_ar"] else f'<h1>{esc(w["name_en"])}</h1>'}
      {f'<p class="verse-en">{esc(w["verse_en"])}</p>' if w["verse_en"] else ""}
      <p class="work-title"><span lang="ar" dir="rtl">{esc(w['name_ar'])}</span> · {esc(w['name_en'])}</p>
    </div>
    <figure class="work-lead">{img_tag(first, 'full', sizes='(max-width:900px) 92vw, 52vw', loading='eager')}</figure>
  </header>
  <div class="work-body">
    <div class="work-prose">{prose}</div>
    <aside class="work-aside">
      {editions}
      <a class="btn" href="{enq}">Enquire about this work</a>
      <div class="aside-note">{content['production']}</div>
    </aside>
  </div>
  {gallery}
</article>
<section class="closing">
  <h2>Ask about <span lang="ar" dir="rtl">{esc(w['name_ar'])}</span></h2>
  <p>Editions are small and made after the conversation. Tell me the format you have in mind and the wall it is going to.</p>
  <a class="btn" href="{enq}">Enquire about this work</a>
</section>"""

    desc = w["seo_desc"] or f"{w['verse_en']} Original Arabic poetry art print by Zein Sourany on Hahnemühle archival paper."
    write(f"works/{w['slug']}/index.html", page(
        f"{w['name_en']} — {w['name_ar']} | Arabic Poetry Art Print | ENJZ",
        desc[:300], body, 2, noindex=not w["listed"],
        canonical=f"works/{w['slug']}/" if w["listed"] else ""))

# ---------------------------------------------------------------- static pages

about_body = f"""
<header class="page-head">
  <h1><span lang="ar" dir="rtl">عن الفنان</span><span class="page-en">About the artist</span></h1>
</header>
<div class="prose-page">{content['about_artist']}</div>
<section class="closing">
  <h2>Working together</h2>
  <p>Commissions, exhibitions, collaborations and press enquiries all reach me at the same place.</p>
  <a class="btn" href="../enquire/index.html">Get in touch</a>
</section>"""
write("about/index.html", page("About the artist — Zein Sourany | ENJZ",
     "Zein Sourany is a Lebanese poet and artist in Madrid, working with Arabic text as living material rather than traditional calligraphy.",
     about_body, 1, canonical="about/"))

enjz_body = f"""
<header class="page-head">
  <h1><span lang="ar" dir="rtl">لماذا أنجِز؟</span><span class="page-en">Why ENJZ</span></h1>
  <p>ENJZ is <span lang="ar" dir="rtl">أنجِز</span> — the imperative. Accomplish it. It also holds the initials of the people I love.</p>
</header>
<div class="bilingual">
  <div class="col-ar" lang="ar" dir="rtl">{content['why_enjz_ar']}</div>
  <div class="col-en">{content['why_enjz_en']}</div>
</div>"""
write("enjz/index.html", page("Why ENJZ — أنجِز | The origin of the project",
     "ENJZ is أنجِز, the imperative: accomplish it. The text behind the name, in Arabic and English.",
     enjz_body, 1, canonical="enjz/"))

ed_body = f"""
<header class="page-head">
  <h1><span lang="ar" dir="rtl">الطبعات والإنتاج</span><span class="page-en">Editions &amp; production</span></h1>
</header>
<div class="prose-page">
{content['production']}
<h2>Edition sizes</h2>
<table class="plain">
<thead><tr><th scope="col">Format</th><th scope="col" class="num">Edition</th></tr></thead>
<tbody>
<tr><td>A4</td><td class="num">15</td></tr>
<tr><td>A3</td><td class="num">12</td></tr>
<tr><td>A2</td><td class="num">10</td></tr>
<tr><td>A1</td><td class="num">5</td></tr>
<tr><td>A0</td><td class="num">3</td></tr>
</tbody></table>
<h2>Certificate</h2>
<p>Every piece ships with a signed certificate of authenticity carrying the title in Arabic and English, the collection, the format, the edition number and a reference identifier unique to that print.</p>
<h2>Damage</h2>
<p>If a work arrives damaged, send photographs within seven days of delivery and it will be replaced.</p>
</div>
<section class="closing">
  <h2>Ready when you are</h2>
  <p>Choose the work and the format, and I will confirm what is left in the edition before anything is made.</p>
  <a class="btn" href="../enquire/index.html">Enquire</a>
</section>"""
write("editions/index.html", page("Editions & production — ENJZ",
     "How ENJZ works are made: limited editions on Hahnemühle archival paper, printed after order, signed, numbered and certified.",
     ed_body, 1, canonical="editions/"))

# ---------------------------------------------------------------- enquire

opts = "".join(f'<option value="{esc(w["name_en"])}">{esc(w["name_en"])} — {esc(w["name_ar"])}</option>'
                for w in sorted(listed, key=lambda x: x["name_en"]))

enquire_body = f"""
<header class="page-head">
  <h1><span lang="ar" dir="rtl">اطلب عملاً</span><span class="page-en">Enquire</span></h1>
  <p>Nothing is kept in stock. Each work is produced after the conversation, which is how the editions stay small and how I know where every piece goes. Tell me what you are looking at and I will reply with what remains in the edition, the cost to make it, and shipping to you.</p>
</header>

<div class="enq">
  <form id="enq" class="enq-form">
    <p class="field">
      <label for="f-work">Work</label>
      <select id="f-work" name="work">
        <option value="">Not sure yet — or a commission</option>
        {opts}
      </select>
    </p>
    <p class="field">
      <label for="f-format">Format</label>
      <select id="f-format" name="format">
        <option value="">To be decided together</option>
        <option>A4</option><option>A3</option><option>A2</option><option>A1</option><option>A0</option>
      </select>
    </p>
    <p class="field">
      <label for="f-name">Your name</label>
      <input id="f-name" name="name" type="text" autocomplete="name" required>
    </p>
    <p class="field">
      <label for="f-email">Email</label>
      <input id="f-email" name="email" type="email" autocomplete="email" required>
    </p>
    <p class="field">
      <label for="f-where">Where it is going</label>
      <input id="f-where" name="where" type="text" placeholder="City, country — and the wall, if you like">
    </p>
    <p class="field">
      <label for="f-msg">Anything else</label>
      <textarea id="f-msg" name="message" rows="5" placeholder="A commission, an exhibition, a question about the poem."></textarea>
    </p>
    <button class="btn" type="submit">Send enquiry</button>
    <p class="enq-fallback">This opens your email app with the message ready. If nothing happens, write to
      <a href="mailto:{SHOP['email']}">{SHOP['email']}</a>.</p>
  </form>

  <aside class="enq-aside">
    <h2>Direct</h2>
    <p><a href="mailto:{SHOP['email']}">{SHOP['email']}</a></p>
    <p><a href="{SHOP['instagram']}" rel="me noopener">Instagram — @zeinsourany</a></p>
    <p><a href="{SHOP['substack']}" rel="noopener">Substack — the writing</a></p>
    <h2>What happens next</h2>
    <p>I answer personally, usually within two days. If the edition and format are agreed, the work is printed, signed, numbered and certified, then shipped within two to three weeks.</p>
    <h2>Galleries and institutions</h2>
    <p>For exhibitions, portfolio reviews or collaborations, write directly and say so in the first line — those go to the top.</p>
  </aside>
</div>

<script>
(function () {{
  var p = new URLSearchParams(location.search).get('work');
  var sel = document.getElementById('f-work');
  if (p) {{
    var hit = Array.prototype.find.call(sel.options, function (o) {{ return o.value === p; }});
    if (hit) sel.value = hit.value;
  }}
  document.getElementById('enq').addEventListener('submit', function (e) {{
    e.preventDefault();
    var d = new FormData(e.target), g = function (k) {{ return (d.get(k) || '').toString().trim(); }};
    var work = g('work') || 'A commission';
    var body = [
      'Work: ' + work,
      'Format: ' + (g('format') || 'to be decided'),
      'Name: ' + g('name'),
      'Email: ' + g('email'),
      'Destination: ' + (g('where') || '—'),
      '',
      g('message') || ''
    ].join('\\n');
    location.href = 'mailto:{SHOP["email"]}?subject=' + encodeURIComponent('ENJZ enquiry — ' + work) +
      '&body=' + encodeURIComponent(body);
  }});
}})();
</script>"""
write("enquire/index.html", page("Enquire — ENJZ | Commission a work by Zein Sourany",
     "Every ENJZ work is made after the conversation. Enquire about an edition, a format or a commission.",
     enquire_body, 1, canonical="enquire/"))

# ---------------------------------------------------------------- 404

write("404.html", page("Page not found — ENJZ", "That page has moved.", """
<section class="closing tall">
  <h2>That page is no longer here</h2>
  <p>The shop moved. The work did not.</p>
  <a class="btn" href="/works/index.html">See the works</a>
</section>""", 0, noindex=True))

# ------------------------------------------------- legacy Shopify redirects

def redirect(path, target, title):
    write(path, f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0;url={target}">
<link rel="canonical" href="https://{SHOP['domain']}/{target.lstrip('/')}">
<meta name="robots" content="noindex,follow">
<title>{esc(title)}</title></head>
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

# ---------------------------------------------------------------- seo files

urls = ["", "works/", "about/", "enjz/", "editions/", "enquire/"] + \
       [f"collections/{c['slug']}/" for c in cols] + \
       [f"works/{w['slug']}/" for w in listed]
today = date.today().isoformat()
write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
      "".join(f"  <url><loc>https://{SHOP['domain']}/{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) +
      "</urlset>\n")
write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: https://{SHOP['domain']}/sitemap.xml\n")
write("CNAME", SHOP["domain"] + "\n")
write(".nojekyll", "")

# ---------------------------------------------------------------- manifest

seen, manifest = set(), []
for m in image_manifest:
    if m["url"] not in seen or True:
        manifest.append(m)
write("assets/images.json", json.dumps(manifest, indent=1, ensure_ascii=False))

print(f"works total      : {len(works)}")
print(f"works listed     : {len(listed)}")
print(f"collections      : {len(cols)}")
print(f"images to fetch  : {len(manifest)}")
print(f"html files       : {sum(1 for _ in OUT.rglob('*.html'))}")
