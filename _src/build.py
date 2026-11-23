#!/usr/bin/env python3
"""Build the four language versions of the page.

Source of truth: _src/page.html, which carries English and Portuguese side by
side (elements with class "en" or "pt"), and _src/i18n.json, which carries the
Spanish and French text keyed by the English text.

Output: index.html (en), pt/index.html, es/index.html, fr/index.html.
The build stops if an English string has no Spanish or French translation,
so no language version can fall behind unnoticed.

Run from the repository root:  python3 _src/build.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://gabrielguedesmath.github.io"  # change here when a custom domain arrives
LANGS = ["en", "pt", "es", "fr"]
PATHS = {"en": "/", "pt": "/pt/", "es": "/es/", "fr": "/fr/"}
HTML_LANG = {"en": "en", "pt": "pt-BR", "es": "es", "fr": "fr"}

LANG_EL = re.compile(
    r'<(span|p)\s+class="((?:[^"]*\s)?(en|pt)(?:\s[^"]*)?)">(.*?)</\1>', re.S
)


def render(src, lang, i18n):
    strings = i18n["strings"]
    missing = []

    def repl(m):
        tag, classes, el_lang, inner = m.group(1), m.group(2).split(), m.group(3), m.group(4)
        keep_from = lang if lang in ("en", "pt") else "en"
        if el_lang != keep_from:
            return ""
        if lang in ("es", "fr"):
            entry = strings.get(inner)
            if entry is None or lang not in entry:
                missing.append(inner)
                return ""
            inner = entry[lang]
        rest = [c for c in classes if c not in ("en", "pt")]
        if tag == "span" and not rest:
            return inner
        attr = f' class="{" ".join(rest)}"' if rest else ""
        return f"<{tag}{attr}>{inner}</{tag}>"

    out = LANG_EL.sub(repl, src)
    if missing:
        sys.exit(f"[{lang}] missing translations for:\n  " + "\n  ".join(missing))

    meta = i18n["meta"][lang]
    nav = "\n".join(
        '      <a href="{href}" lang="{hl}" hreflang="{hl}"{cur}>{name}</a>'.format(
            href=PATHS[l],
            hl=HTML_LANG[l],
            cur=' aria-current="page"' if l == lang else "",
            name=i18n["meta"][l]["name"],
        )
        for l in LANGS
    )
    nav = f'<nav class="langs" aria-label="{meta["nav"]}">\n{nav}\n    </nav>'
    alternates = "\n".join(
        f'<link rel="alternate" hreflang="{HTML_LANG[l]}" href="{BASE}{PATHS[l]}">' for l in LANGS
    )
    head = (
        f'<link rel="canonical" href="{BASE}{PATHS[lang]}">\n'
        f"{alternates}\n"
        f'<link rel="alternate" hreflang="x-default" href="{BASE}/">'
    )

    for token, value in {
        "{{HTML_LANG}}": HTML_LANG[lang],
        "{{DESCRIPTION}}": meta["description"],
        "{{FIGURE_LABEL}}": meta["figure"],
        "<!--LANGNAV-->": nav,
        "<!--ALTERNATES-->": head,
    }.items():
        assert out.count(token) == 1, (lang, token, out.count(token))
        out = out.replace(token, value)

    # tidy the blank lines left where the other language was removed
    out = re.sub(r"\n[ \t]+\n", "\n", out)
    assert 'class="en"' not in out and 'class="pt"' not in out and "{{" not in out
    return out


def main():
    src = (ROOT / "_src" / "page.html").read_text(encoding="utf-8")
    i18n = json.loads((ROOT / "_src" / "i18n.json").read_text(encoding="utf-8"))
    used = {m.group(4) for m in LANG_EL.finditer(src) if m.group(3) == "en"}
    stale = [k for k in i18n["strings"] if k not in used]
    if stale:
        print("note: translations no longer used:\n  " + "\n  ".join(stale))
    for lang in LANGS:
        html = render(src, lang, i18n)
        target = ROOT / ("index.html" if lang == "en" else f"{lang}/index.html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        print(f"{lang}: {target.relative_to(ROOT)} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
