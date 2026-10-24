# ENJZ — enjzworks.art

The ENJZ website as plain files. No Shopify, no theme, no monthly fee, no cart.
Every work now ends in a conversation instead of a checkout.

Built from the live Shopify store on 24 October 2026: **29 works** (22 shown
publicly, 7 kept link-only exactly as they were), **4 collections**, all
descriptions, verses, formats, prices and SEO text.

---

## What you have to do (four steps, about fifteen minutes)

### 1. Put this folder on GitHub

Create a new **empty** repository on github.com — call it `enjz-site`, keep it
public — then from inside this folder:

```bash
git init -b main
git add .
git commit -m "ENJZ site, moved off Shopify"
git remote add origin https://github.com/YOUR-USERNAME/enjz-site.git
git push -u origin main
```

### 2. Turn on Pages

Repository → **Settings** → **Pages** → **Source: GitHub Actions**. That's the
only setting to change. The site builds and goes live at
`https://YOUR-USERNAME.github.io/enjz-site/` within a minute or two.

### 3. Let the robot collect the artwork

The moment you push, a job called **Fetch artwork images** starts on GitHub's
servers. It downloads all 142 artwork images from Shopify, resizes them for the
web and commits them back here. You don't download anything.

Watch it under the **Actions** tab. When it finishes it prints a line like
*"All images are in. The site no longer depends on Shopify."*

**Do not close Shopify until you have seen that line.** Until the images are in
the repository the site borrows them from Shopify's CDN, and closing the store
would empty every page. If the job reports failures, re-run it from the Actions
tab — it only fetches what is still missing.

### 4. Point the domain here

At Namecheap, replace the Shopify DNS records for `enjzworks.art` with:

| Type | Host | Value |
|------|------|-------|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | YOUR-USERNAME.github.io |

Then in **Settings → Pages**, enter `enjzworks.art` as the custom domain and,
once the tick appears, switch on **Enforce HTTPS**. DNS can take a few hours.

After the domain resolves and the images are committed, the Shopify store can be
closed. Not before.

---

## What changed from the shop

Nothing is bought from a shelf any more. Each work page lists its formats and
editions with prices, then invites an enquiry. The enquiry form opens the
visitor's email app with the work, format and their details already written into
the message, so it needs no server, no account and no monthly cost.

Your old Shopify links still work. Every `/products/…`, `/collections/…` and
`/pages/…` address forwards to its new home, so Google's index, your Instagram
bio link and anything already shared keep working.

The seven link-only works stay link-only: they have pages, they carry
`noindex`, and they appear in no grid.

---

## Changing things later

| You want to | Do this |
|-------------|---------|
| Fix a typo on a page | Edit the `.html` file, commit. Live in a minute. |
| Change wording across the site | Edit `build/data/content.json`, then `cd build && python3 build.py`, commit. |
| Add or edit a work | Edit `build/data/products_all.json`, rebuild as above. |
| Change the look | Edit `assets/site.css`. Nothing is generated from it. |
| Rename "New Works" | In `build/data/content.json` under `collections`, change `title_en` / `title_ar`, rebuild. |
| Collect enquiries in a form instead of email | Sign up at formspree.io, then in `enquire/index.html` change the form to `action="https://formspree.io/f/YOUR-ID" method="POST"` and delete the script at the bottom. |

The hero work on the front page is set by `HERO` near the middle of
`build/build.py` — currently *Vision*.

---

## What is in here

```
index.html            front page
works/                every work, one folder each
collections/          Lebanon · Indulgence · Hors Série · New Works
about/ enjz/ editions/ enquire/
assets/site.css       the entire design
assets/images.json    the list of artwork images to fetch
assets/img/           the artwork itself, filled in by the Actions job
products/ pages/ cart/ redirects from the old Shopify addresses
build/                the generator and the Shopify export it was built from
scripts/fetch_images.py   image fetcher, also runnable locally
.github/workflows/    the two jobs: fetch images, deploy site
CNAME, sitemap.xml, robots.txt
```

Running the images locally instead, if you ever want to:

```bash
brew install imagemagick     # macOS
python3 scripts/fetch_images.py
```
