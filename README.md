# ENJZ — enjzworks.art

The ENJZ website as plain files. No Shopify, no theme, no monthly fee, no cart.
Every work now ends in a conversation instead of a checkout.

Built from the live Shopify store on 24 October 2026: **29 works** (22 shown
publicly, 7 kept link-only exactly as they were), **4 collections**, all
descriptions, verses, formats, prices and SEO text.

---

## Where this stands

Steps 1 to 4 are **done**. The repository is live at
**github.com/SISG-svg/enjz-site**, GitHub Pages is serving it, all 142 artwork
images are committed here (so the site no longer needs Shopify for anything),
and the enquiry form is switched on and delivering to
zeinsourany@enjzworks.art.

You can see the site right now at **https://sisg-svg.github.io/enjz-site/**

**One step is left: move the domain.** After that, and only after that, the
Shopify store can be closed.

<details>
<summary>What was already done (for the record)</summary>

1. **Repository pushed** — SISG-svg/enjz-site, public.
2. **Pages turned on** — Settings → Pages → Source: GitHub Actions.
3. **Artwork collected** — the "Fetch artwork images" job pulled all 142 images
   off Shopify's CDN, resized them and committed them. The site serves its own
   images; closing Shopify will not empty any page.
4. **Enquiry form switched on** — Web3Forms, key in `build/data/content.json`,
   delivering to zeinsourany@enjzworks.art. Free tier 250 enquiries a month.
   A hidden field rejects bot submissions.

</details>

### 5. Point the domain here

At Namecheap, replace the Shopify DNS records for `enjzworks.art` with:

| Type | Host | Value |
|------|------|-------|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | sisg-svg.github.io |

**Leave the MX records alone.** They are what deliver mail to
zeinsourany@enjzworks.art — the address the enquiry form sends to. Change only
the A and CNAME records above. If you delete the MX records, enquiries are sent
and then vanish, with nothing to show anyone went wrong.

Then in **Settings → Pages**, type `enjzworks.art` into **Custom domain** and
save. GitHub writes the CNAME file itself. Once the tick appears, switch on
**Enforce HTTPS**. DNS can take a few hours.

Until you do that, the site lives at https://sisg-svg.github.io/enjz-site/ —
which is where to check it before moving the domain.

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
| Change where enquiries are sent | Get a new key from web3forms.com for the new address and replace `form_access_key` in `build/data/content.json`. |

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
sitemap.xml, robots.txt
```

Running the images locally instead, if you ever want to:

```bash
brew install imagemagick     # macOS
python3 scripts/fetch_images.py
```
