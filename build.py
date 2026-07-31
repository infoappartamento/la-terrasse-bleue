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
import shutil
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
SRC = ROOT / "src" / "index.html"
SITE = "https://laterrassebleue.com"

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

    out = str(soup)

    # ── path assoluti: le pagine vivono in sottocartelle ──────────────
    out = out.replace('src="images/', f'src="{"/images/"}').replace(
        "url('images/", "url('/images/"
    ).replace('href="images/', 'href="/images/')

    # ── il traduttore a runtime non serve piu': testo gia' nell'HTML ──
    out = re.sub(r"const T = \{.*?\n\};\n", "", out, flags=re.DOTALL)
    out = re.sub(r"function setLang\(lang\) \{.*?\n\}\n", "", out, flags=re.DOTALL)

    return out


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
        words = len(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", "", target.read_text(encoding='utf-8'), flags=re.DOTALL)).split())
        print(f"  ✅ {url_path:<6} → {target.relative_to(ROOT)}  ({words} parole indicizzabili)")


if __name__ == "__main__":
    main()
