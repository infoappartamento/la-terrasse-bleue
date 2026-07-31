#!/usr/bin/env python3
"""
Generatore statico multilingua — laterrassebleue.com

Da un unico sorgente (src/index.html) produce una pagina per lingua con il
testo gia' tradotto nell'HTML, cosi' che Google possa indicizzare ogni lingua:

    /            italiano
    /en/         inglese
    /fr/         francese
    /de/         tedesco

Uso:  python3 build.py
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
SRC = ROOT / "src" / "index.html"
SITE = "https://laterrassebleue.com"

sys.path.insert(0, str(ROOT / "src"))
from guide_data import GUIDE, SLUG  # noqa: E402

LANGS = ["it", "en", "fr", "de"]
DEFAULT_LANG = "it"
# lingua -> (sottocartella di output, path URL)
OUT = {"it": ("", "/"), "en": ("en", "/en/"), "fr": ("fr", "/fr/"), "de": ("de", "/de/")}


def extract_translations(html: str) -> dict:
    """Estrae l'oggetto `const T = {...}` dal sorgente. E' gia' JSON valido."""
    m = re.search(r"const T = (\{.*?\n\});", html, re.DOTALL)
    if not m:
        raise SystemExit("ERRORE: oggetto T non trovato in src/index.html")
    return json.loads(m.group(1))


def set_meta(soup, *, name=None, prop=None, content):
    tag = soup.find("meta", attrs={"name": name} if name else {"property": prop})
    if tag:
        tag["content"] = content


def build_language(html: str, T: dict, lang: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    t = T[lang]
    url = SITE + OUT[lang][1]

    # ── testo tradotto direttamente nell'HTML ──────────────────────────
    for el in soup.select("[data-i18n]"):
        key = el["data-i18n"]
        if key in t:
            el.clear()
            # i valori contengono markup (<em>, <br>, <strong>): va reinterpretato
            el.append(BeautifulSoup(t[key], "html.parser"))

    # ── lingua dichiarata, title e meta ────────────────────────────────
    soup.html["lang"] = lang
    if soup.title:
        soup.title.string = t["meta_title"]
    set_meta(soup, name="description", content=t["meta_desc"])
    set_meta(soup, prop="og:title", content=t["og_title"])
    set_meta(soup, prop="og:description", content=t["og_desc"])
    set_meta(soup, prop="og:url", content=url)
    set_meta(soup, prop="og:locale", content=t["og_locale"])
    set_meta(soup, name="twitter:title", content=t["og_title"])
    set_meta(soup, name="twitter:description", content=t["og_desc"])

    # og:locale:alternate = le altre tre lingue
    for tag in soup.find_all("meta", attrs={"property": "og:locale:alternate"}):
        tag.decompose()
    og_locale = soup.find("meta", attrs={"property": "og:locale"})
    for other in LANGS:
        if other == lang:
            continue
        alt = soup.new_tag("meta", property="og:locale:alternate")
        alt["content"] = T[other]["og_locale"]
        og_locale.insert_after(alt)

    # ── canonical + hreflang reciproci ────────────────────────────────
    canonical = soup.find("link", rel="canonical")
    if canonical:
        canonical["href"] = url
    for tag in soup.find_all("link", attrs={"hreflang": True}):
        tag.decompose()
    anchor = canonical or soup.find("meta", attrs={"name": "description"})
    for code in LANGS + ["x-default"]:
        target = DEFAULT_LANG if code == "x-default" else code
        link = soup.new_tag("link", rel="alternate", href=SITE + OUT[target][1])
        link["hreflang"] = code
        anchor.insert_after(link)

    # ── switcher lingua: evidenzia quella corrente ────────────────────
    for a in soup.select("a.lang-btn"):
        a["class"] = ["lang-btn", "active"] if a.get("data-lang") == lang else ["lang-btn"]

    # ── dati strutturati: URL e lingua della pagina ───────────────────
    for script in soup.find_all("script", type="application/ld+json"):
        data = json.loads(script.string)
        if data.get("@type") in (["VacationRental", "LodgingBusiness"], "Organization"):
            data["url"] = url
            data["inLanguage"] = lang
            if "description" in data:
                data["description"] = t["meta_desc"]
        script.string = json.dumps(data, ensure_ascii=False, indent=2)

    out = str(soup).replace("{{GUIDEURL}}", f"/{SLUG[lang]}/")

    # ── path assoluti: le pagine vivono in sottocartelle ──────────────
    out = out.replace('src="images/', f'src="{"/images/"}').replace(
        "url('images/", "url('/images/"
    ).replace('href="images/', 'href="/images/')

    # ── il traduttore a runtime non serve piu': testo gia' nell'HTML ──
    out = re.sub(r"const T = \{.*?\n\};\n", "", out, flags=re.DOTALL)
    out = re.sub(r"function setLang\(lang\) \{.*?\n\}\n", "", out, flags=re.DOTALL)

    return out


GUIDE_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>{meta_title}</title>
<meta name="description" content="{meta_desc}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{url}">
{hreflang}
<meta property="og:type" content="article">
<meta property="og:title" content="{meta_title}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{site}/images/terrazza-privata-juan-les-pins.jpg">
<meta property="og:locale" content="{og_locale}">
<meta name="theme-color" content="#00111F">
<link rel="icon" type="image/svg+xml" href='data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="14" fill="%2300111F"/><text x="50" y="72" font-family="Georgia,serif" font-size="68" font-style="italic" fill="%23C9A961" text-anchor="middle">T</text></svg>'>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script type="application/ld+json">
{jsonld}
</script>
<style>
*,*::before,*::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --navy-deepest:#00111F; --navy:#003566; --blue-sea:#0077B6;
  --gold:#C9A961; --gold-light:#E8D5A3; --cream:#F8F4ED;
  --white:#fff; --text-dark:#0A1A2A; --text-soft:#4A5C70; --text-muted:#8A98A8;
  --line:rgba(201,169,97,.25);
  --serif:'Cormorant Garamond',Georgia,serif; --sans:'Inter',-apple-system,sans-serif;
}}
html {{ scroll-behavior:smooth; }}
body {{ font-family:var(--sans); color:var(--text-dark); background:var(--cream); font-weight:300; line-height:1.6; -webkit-font-smoothing:antialiased; }}
a {{ color:inherit; text-decoration:none; }}
.gnav {{ position:sticky; top:0; z-index:50; background:rgba(0,17,31,.95); backdrop-filter:blur(18px); -webkit-backdrop-filter:blur(18px);
  padding:16px 40px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(201,169,97,.2); }}
.gnav-logo {{ font-family:var(--serif); font-size:20px; color:var(--white); }}
.gnav-logo span {{ color:var(--gold); font-style:italic; }}
.gnav-right {{ display:flex; align-items:center; gap:18px; }}
.gnav-lang {{ display:flex; gap:4px; }}
.gnav-lang a {{ font-size:15px; opacity:.5; transition:opacity .2s; line-height:1; }}
.gnav-lang a:hover, .gnav-lang a.active {{ opacity:1; }}
.gnav-back {{ font-size:10px; letter-spacing:.22em; text-transform:uppercase; color:var(--gold-light); border:1px solid var(--gold); padding:9px 18px; transition:all .3s; }}
.gnav-back:hover {{ background:var(--gold); color:var(--navy-deepest); }}
.ghero {{ background:var(--navy-deepest); color:var(--white); padding:80px 40px 70px; }}
.gwrap {{ max-width:900px; margin:0 auto; }}
.gkicker {{ font-size:11px; font-weight:500; letter-spacing:.35em; text-transform:uppercase; color:var(--gold); display:inline-flex; align-items:center; gap:12px; margin-bottom:22px; }}
.gkicker::before {{ content:''; width:32px; height:1px; background:var(--gold); opacity:.6; }}
h1 {{ font-family:var(--serif); font-size:clamp(38px,5.4vw,68px); font-weight:300; line-height:1.06; letter-spacing:-.015em; color:var(--white); margin-bottom:26px; }}
h1 em {{ font-style:italic; color:var(--gold-light); }}
.gintro {{ font-family:var(--serif); font-size:clamp(17px,1.5vw,21px); font-style:italic; line-height:1.6; color:rgba(255,255,255,.82); }}
main {{ background:var(--white); }}
section {{ padding:70px 40px; border-bottom:1px solid var(--line); }}
h2 {{ font-family:var(--serif); font-size:clamp(28px,3.4vw,44px); font-weight:300; color:var(--text-dark); margin-bottom:18px; letter-spacing:-.01em; }}
.glead {{ font-size:16px; color:var(--text-soft); margin-bottom:36px; max-width:70ch; }}
.gitem {{ padding:24px 0; border-top:1px solid var(--line); display:grid; grid-template-columns:220px 1fr; gap:28px; }}
.gitem:last-child {{ border-bottom:1px solid var(--line); }}
h3 {{ font-family:var(--serif); font-size:22px; font-weight:400; color:var(--navy); }}
.gdist {{ font-size:11px; letter-spacing:.2em; text-transform:uppercase; color:var(--gold); margin-top:6px; }}
.gtext {{ font-size:15px; line-height:1.75; color:var(--text-soft); }}
.gfood {{ display:grid; grid-template-columns:repeat(2,1fr); gap:1px; background:var(--line); border:1px solid var(--line); }}
.gfood > div {{ background:var(--white); padding:22px 24px; }}
.gfood h3 {{ font-size:19px; margin-bottom:4px; }}
.gcta {{ background:var(--navy-deepest); color:var(--white); text-align:center; padding:80px 40px; border:0; }}
.gcta h2 {{ color:var(--white); }}
.gcta p {{ font-family:var(--serif); font-size:19px; font-style:italic; color:rgba(255,255,255,.8); max-width:56ch; margin:0 auto 34px; }}
.gbtn {{ display:inline-flex; align-items:center; gap:14px; padding:17px 36px; background:var(--gold); color:var(--navy-deepest);
  font-size:11px; font-weight:600; letter-spacing:.25em; text-transform:uppercase; border:1px solid var(--gold); transition:all .3s; }}
.gbtn:hover {{ background:transparent; color:var(--gold); }}
footer {{ background:var(--navy-deepest); color:rgba(255,255,255,.5); text-align:center; padding:40px 24px; font-size:11px; letter-spacing:.15em; border-top:1px solid rgba(201,169,97,.2); }}
@media (max-width:768px) {{
  .gnav {{ padding:14px 20px; }} .gnav-right {{ gap:12px; }}
  .ghero {{ padding:56px 24px 48px; }} section {{ padding:52px 24px; }}
  .gitem {{ grid-template-columns:1fr; gap:10px; }}
  .gfood {{ grid-template-columns:1fr; }}
  .gcta {{ padding:60px 24px; }}
}}
</style>
</head>
<body>
<nav class="gnav">
  <a href="{home}" class="gnav-logo">La <span>Terrasse</span> Bleue</a>
  <div class="gnav-right">
    <div class="gnav-lang">{langlinks}</div>
    <a href="{home}" class="gnav-back">{back}</a>
  </div>
</nav>

<header class="ghero">
  <div class="gwrap">
    <div class="gkicker">{kicker}</div>
    <h1>{h1}</h1>
    <p class="gintro">{intro}</p>
  </div>
</header>

<main>
  <section>
    <div class="gwrap">
      <h2>{s1_t}</h2>
      <p class="glead">{s1_p}</p>
      {beaches}
    </div>
  </section>

  <section>
    <div class="gwrap">
      <h2>{s2_t}</h2>
      {places}
    </div>
  </section>

  <section>
    <div class="gwrap">
      <h2>{s3_t}</h2>
      <p class="gtext" style="max-width:70ch;">{s3_p}</p>
    </div>
  </section>

  <section>
    <div class="gwrap">
      <h2>{s4_t}</h2>
      {trips}
    </div>
  </section>

  <section>
    <div class="gwrap">
      <h2>{s5_t}</h2>
      <p class="glead">{s5_p}</p>
      <div class="gfood">{food}</div>
    </div>
  </section>

  <section>
    <div class="gwrap">
      <h2>{s6_t}</h2>
      {transport}
    </div>
  </section>

  <section class="gcta">
    <h2>{cta_t}</h2>
    <p>{cta_p}</p>
    <a href="{home}" class="gbtn">{cta_btn}</a>
  </section>
</main>

<footer>© 2026 · La Terrasse Bleue · Boulevard Poincaré 93, 06160 Juan-les-Pins</footer>
</body>
</html>
"""


def build_guide(lang: str) -> str:
    """Pagina pubblica 'cosa fare in zona' per una lingua."""
    g = GUIDE[lang]
    url = f"{SITE}/{SLUG[lang]}/"
    home = OUT[lang][1]
    locales = {"it": "it_IT", "en": "en_GB", "fr": "fr_FR", "de": "de_DE"}
    flags = {"it": "🇮🇹", "en": "🇬🇧", "fr": "🇫🇷", "de": "🇩🇪"}

    hreflang = "\n".join(
        f'<link rel="alternate" hreflang="{code}" href="{SITE}/{SLUG[DEFAULT_LANG if code == "x-default" else code]}/">'
        for code in LANGS + ["x-default"]
    )
    langlinks = "".join(
        f'<a href="{SITE if False else ""}/{SLUG[l]}/" class="{"active" if l == lang else ""}" '
        f'hreflang="{l}" title="{l.upper()}">{flags[l]}</a>'
        for l in LANGS
    )

    def item(title, meta, text):
        return (f'<div class="gitem"><div><h3>{title}</h3>'
                f'{f"<div class=gdist>{meta}</div>" if meta else ""}</div>'
                f'<div class="gtext">{text}</div></div>')

    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": g["meta_title"],
        "description": g["meta_desc"],
        "inLanguage": lang,
        "url": url,
        "image": f"{SITE}/images/terrazza-privata-juan-les-pins.jpg",
        "author": {"@type": "Organization", "name": "La Terrasse Bleue",
                   "@id": f"{SITE}/#organization"},
        "about": [{"@type": "Place", "name": "Juan-les-Pins"},
                  {"@type": "Place", "name": "Antibes"}],
    }, ensure_ascii=False, indent=2)

    return GUIDE_TEMPLATE.format(
        lang=lang, url=url, site=SITE, home=home, hreflang=hreflang,
        langlinks=langlinks, og_locale=locales[lang], jsonld=jsonld,
        beaches="".join(item(n, d, t) for n, d, t in g["beaches"]),
        places="".join(item(n, "", t) for n, t in g["s2_items"]),
        trips="".join(item(n, d, t) for n, d, t in g["trips"]),
        transport="".join(item(n, "", t) for n, t in g["s6_items"]),
        food="".join(f'<div><h3>{n}</h3><div class="gtext">{d}</div></div>'
                     for n, d in g["food"]),
        **{k: g[k] for k in ("meta_title", "meta_desc", "back", "kicker", "h1", "intro",
                             "s1_t", "s1_p", "s2_t", "s3_t", "s3_p", "s4_t",
                             "s5_t", "s5_p", "s6_t", "cta_t", "cta_p", "cta_btn")},
    )


def main():
    html = SRC.read_text(encoding="utf-8")
    T = extract_translations(html)

    missing = [
        f"{lang}.{k}"
        for lang in LANGS
        for k in ("meta_title", "meta_desc", "og_title", "og_desc", "og_locale")
        if k not in T.get(lang, {})
    ]
    if missing:
        raise SystemExit("ERRORE: chiavi meta mancanti: " + ", ".join(missing))

    for lang in LANGS:
        subdir, url_path = OUT[lang]
        target_dir = ROOT / subdir if subdir else ROOT
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "index.html"
        target.write_text(build_language(html, T, lang), encoding="utf-8")
        print(f"  ✅ {url_path:<6} → {target.relative_to(ROOT)}  ({count_words(target)} parole)")

    print()
    for lang in LANGS:
        target = ROOT / SLUG[lang] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(build_guide(lang), encoding="utf-8")
        print(f"  ✅ /{SLUG[lang]}/ → {target.relative_to(ROOT)}  ({count_words(target)} parole)")

    (ROOT / "sitemap.xml").write_text(build_sitemap(), encoding="utf-8")
    print("\n  ✅ sitemap.xml (8 URL con hreflang)")


def build_sitemap() -> str:
    """Sitemap con le 8 pagine e i blocchi hreflang reciproci."""
    today = date.today().isoformat()
    home_alts = {l: SITE + OUT[l][1] for l in LANGS}
    guide_alts = {l: f"{SITE}/{SLUG[l]}/" for l in LANGS}

    def block(loc, alts, priority, freq, images=()):
        links = "".join(
            f'\n    <xhtml:link rel="alternate" hreflang="{code}" href="{alts[DEFAULT_LANG if code == "x-default" else code]}"/>'
            for code in LANGS + ["x-default"]
        )
        imgs = "".join(
            f'\n    <image:image><image:loc>{SITE}/images/{f}</image:loc>'
            f'<image:title>{t}</image:title></image:image>' for f, t in images
        )
        return (f'  <url>\n    <loc>{loc}</loc>\n    <lastmod>{today}</lastmod>\n'
                f'    <changefreq>{freq}</changefreq>\n    <priority>{priority}</priority>'
                f'{links}{imgs}\n  </url>')

    home_images = [
        ("terrazza-privata-juan-les-pins.jpg", "Terrazza privata a Juan-les-Pins"),
        ("soggiorno-appartamento-juan-les-pins.jpg", "Soggiorno dell'appartamento"),
        ("camera-da-letto-juan-les-pins.jpg", "Camera da letto"),
    ]
    urls = [block(home_alts[l], home_alts, "1.0", "monthly",
                  home_images if l == DEFAULT_LANG else ()) for l in LANGS]
    urls += [block(guide_alts[l], guide_alts, "0.8", "yearly") for l in LANGS]

    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:xhtml="http://www.w3.org/1999/xhtml"\n'
            '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
            + "\n".join(urls) + "\n</urlset>\n")


def count_words(path: Path) -> int:
    """Parole di testo realmente visibile (esclusi script e stili)."""
    html = path.read_text(encoding="utf-8")
    body = re.search(r"<body.*?</body>", html, re.DOTALL)
    body = body.group(0) if body else html
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", body, flags=re.DOTALL)
    return len(re.sub(r"<[^>]+>", " ", body).split())


if __name__ == "__main__":
    main()
