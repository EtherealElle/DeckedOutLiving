#!/usr/bin/env python3
"""
Point the site at a web address.

Only two things in the site care about the full web address: the structured
data Google reads, and sitemap.xml. Every image, stylesheet and link is
relative, so the site itself works at any address without being rebuilt.

Run this once when you know your final address:

    python set_domain.py https://joshbiles.github.io/deckedoutliving-website
    python set_domain.py https://www.deckedoutliving.net

Adding a real domain also writes the CNAME file GitHub Pages needs.
"""
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

PAGES = [
    ("index.html", "1.0", "weekly"),
    ("services/index.html", "0.9", "monthly"),
    ("services/new-deck-construction.html", "0.9", "monthly"),
    ("services/deck-repair.html", "0.9", "monthly"),
    ("services/deck-staining-and-sealing.html", "0.8", "monthly"),
    ("services/railing-installation.html", "0.8", "monthly"),
    ("services/pergolas-and-covered-structures.html", "0.8", "monthly"),
    ("services/screened-porches.html", "0.8", "monthly"),
    ("services/custom-woodwork.html", "0.8", "monthly"),
    ("services/car-ports.html", "0.8", "monthly"),
    ("gallery.html", "0.8", "weekly"),
    ("about.html", "0.6", "yearly"),
    ("contact.html", "0.9", "monthly"),
]

URL_RE = re.compile(r"https?://[^\"\s]*?(?=/(?:#business|assets|services|$)|\"|/\")")


def current_domain():
    """Read whatever domain the structured data currently uses."""
    with open(os.path.join(DOCS, "index.html"), encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r'"@id":\s*"(https?://[^/"]+(?:/[^"#]*?)?)/#business"', text)
    return m.group(1) if m else None


def write_sitemap(base):
    today = date.today().isoformat()
    rows = "\n".join(
        f"  <url>\n"
        f"    <loc>{base}/{p}</loc>\n"
        f"    <lastmod>{today}</lastmod>\n"
        f"    <changefreq>{freq}</changefreq>\n"
        f"    <priority>{pri}</priority>\n"
        f"  </url>"
        for p, pri, freq in PAGES
    )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{rows}\n</urlset>\n")
    with open(os.path.join(DOCS, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(xml)


def write_robots(base):
    txt = ("User-agent: *\n"
           "Allow: /\n\n"
           f"Sitemap: {base}/sitemap.xml\n")
    with open(os.path.join(DOCS, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(txt)


def main():
    if len(sys.argv) < 2:
        cur = current_domain()
        print(__doc__)
        print(f"  The site currently points at: {cur}")
        return 1

    new = sys.argv[1].rstrip("/")
    if not new.startswith("http"):
        new = "https://" + new

    old = current_domain()
    if not old:
        print("Could not work out the current address from index.html.")
        return 1

    if old == new:
        print(f"Already set to {new}. Refreshing sitemap and robots.txt anyway.")
    else:
        changed = 0
        for dirpath, _, files in os.walk(DOCS):
            for f in files:
                if not f.endswith(".html"):
                    continue
                p = os.path.join(dirpath, f)
                with open(p, encoding="utf-8") as fh:
                    text = fh.read()
                if old in text:
                    with open(p, "w", encoding="utf-8") as fh:
                        fh.write(text.replace(old, new))
                    changed += 1
        print(f"Updated {changed} page(s):\n    {old}\n -> {new}")

    write_sitemap(new)
    write_robots(new)
    print("Rewrote sitemap.xml and robots.txt.")

    # A custom domain needs a CNAME file; a github.io address must not have one.
    cname_path = os.path.join(DOCS, "CNAME")
    host = new.split("//", 1)[1].split("/", 1)[0]
    if host.endswith(".github.io"):
        if os.path.exists(cname_path):
            os.remove(cname_path)
            print("Removed CNAME (not needed for a github.io address).")
    else:
        with open(cname_path, "w", encoding="utf-8") as fh:
            fh.write(host + "\n")
        print(f"Wrote CNAME for {host}.")
        print("\nRemember to add these DNS records at your domain registrar:")
        print("    A     @   185.199.108.153")
        print("    A     @   185.199.109.153")
        print("    A     @   185.199.110.153")
        print("    A     @   185.199.111.153")
        if host.startswith("www."):
            print(f"    CNAME www <your-github-username>.github.io")

    print("\nNow run publish-website.cmd to put the change online.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
