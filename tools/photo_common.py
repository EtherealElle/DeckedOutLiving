#!/usr/bin/env python3
"""
Decked Out Living - the bits both photo tools have to agree on.

publish_photos.py turns a filename into a caption. import_photos.py turns a
Discord message into that filename. If the two ever disagree about what a slug
looks like, or about how a before/after pair is spelled, pairs quietly stop
matching and there is nothing on screen to explain why. So the rules live here,
once.

This module imports nothing outside the standard library, on purpose:
import_photos.py has to run on a computer where Pillow was never installed.
"""

import json
import os
import re

CONFIG_NAME = "photo-categories.json"

# The categories as they stood before the config file existed. Used only as a
# fallback when photo-categories.json is missing or unreadable, so a stray
# comma in a JSON file can never take the gallery down.
DEFAULT_CATEGORIES = [
    ("new-decks",        "New Decks"),
    ("deck-repair",      "Deck Repair"),
    ("staining-sealing", "Staining & Sealing"),
    ("railings",         "Railings"),
    ("pergolas",         "Pergolas & Covered Structures"),
    ("screened-porches", "Screened Porches"),
    ("custom-woodwork",  "Custom Woodwork"),
    ("car-ports",        "Car Ports"),
]

# A category id becomes a folder name and an HTML data-cat value, so it has to
# be exactly what slugify() would produce and nothing more.
CATEGORY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

READABLE = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff", ".bmp"}

# before/after filename conventions, most explicit first
PAIR_RE = re.compile(r"^(?P<stem>.+?)[-_]{1,2}(?P<side>before|after)$", re.IGNORECASE)

# A filename that looks like it carries a street address. The filename is
# published verbatim as the caption and the alt text, so a miss here puts a
# customer's home address on the website.
#
# Matches a house number followed by a street type, with up to three words of
# street name in between - "412 Oak Ridge Dr" as well as "412 Dr". False alarms
# are cheap here (it only prints a warning); a miss is not.
_STREET = ("st|street|rd|road|dr|drive|ln|lane|ave|avenue|ct|court|way|blvd|"
           "hwy|circle|cir|trail|trl|pkwy|place|pl|terrace|ter|loop|run|path")
ADDRESS_RE = re.compile(
    r"\b\d{1,6}[-_ ]*(?:[a-z]{2,}[-_ ]+){0,3}(?:" + _STREET + r")\b",
    re.IGNORECASE,
)

# A straight-off-the-camera filename: IMG_20260714_121904, DSC_0431, PXL_...,
# 20260714_121904, GOPR0012 and friends. Publishing one of those as the visible
# caption and alt text looks careless, so fall back to the category name.
CAMERA_RE = re.compile(
    r"^(?:img|dsc|dscn|dscf|pxl|gopr|dji|mvimg|photo|image|screenshot|untitled|p)"
    r"[-_]?\d+(?:[-_]\d+)*$"
    r"|^\d{8}[-_]\d{6}$"
    r"|^\d{4,}$",
    re.IGNORECASE,
)

# Seven photos of one job are cedar-deck-rebuild, -2, -3 and so on. They are all
# the same job, so they should all caption as "Cedar Deck Rebuild" rather than
# "Cedar Deck Rebuild 3".
#
# Capped at two digits deliberately. A counter here only ever counts photos
# within one Discord message, so it stays small - while a four-digit tail is far
# more likely to be a year the owner meant to keep ("deck-rebuild-2026").
INDEX_SUFFIX_RE = re.compile(r"^(?P<stem>.+?)-(?P<n>[2-9]|[1-9][0-9])$")


# --------------------------------------------------------------------------
# Naming
# --------------------------------------------------------------------------
def slugify(text):
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return re.sub(r"-{2,}", "-", text) or "photo"


def humanise(stem):
    words = re.sub(r"[-_]+", " ", stem).strip()
    words = re.sub(r"\s+", " ", words)
    small = {"a", "an", "and", "the", "in", "on", "at", "of", "for", "with", "to"}
    out = []
    for i, w in enumerate(words.split(" ")):
        out.append(w if (w.isupper() and len(w) <= 3) else
                   (w.lower() if (i and w.lower() in small) else w.capitalize()))
    return " ".join(out)


def strip_index(stem):
    """cedar-deck-rebuild-3 -> cedar-deck-rebuild. Leaves anything else alone."""
    m = INDEX_SUFFIX_RE.match(stem)
    return m.group("stem") if m else stem


def numbered(stem, index, side=None):
    """Build the filename stem for photo `index` (1-based) of one job.

    The counter goes in the MIDDLE, never at the end, because PAIR_RE only
    recognises a before/after when the stem finishes with it:

        cedar-deck-rebuild-2-before   pairs with   cedar-deck-rebuild-2-after
        cedar-deck-rebuild-before-2   pairs with   nothing at all
    """
    out = stem if index <= 1 else "%s-%d" % (stem, index)
    return "%s-%s" % (out, side) if side else out


# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------
def config_path(root):
    return os.path.join(root, CONFIG_NAME)


def _scan_category_dirs(root):
    """Every category folder that actually holds something, archived or published."""
    found = set()
    for base in (os.path.join(root, "photo-originals"),
                 os.path.join(root, "docs", "photos")):
        if not os.path.isdir(base):
            continue
        for entry in os.listdir(base):
            p = os.path.join(base, entry)
            if not os.path.isdir(p) or entry.startswith("."):
                continue
            try:
                if any(not f.startswith(".") for f in os.listdir(p)):
                    found.add(entry)
            except OSError:
                pass
    return found


def read_category_config(root):
    """Full category records, plus any notes worth showing the user.

    Returns (records, notes). A record is a dict with at least id and label,
    and usually discordChannelId / discordChannelName.

    This never raises and never returns an empty list. A config that is
    missing, malformed, or has had a category deleted out of it must not be
    able to make already-published photos disappear.
    """
    notes = []
    path = config_path(root)
    raw = None

    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (ValueError, OSError) as exc:
            notes.append(
                "%s could not be read (%s), so the original eight categories "
                "are being used instead. Nothing is lost - fix the file when "
                "you get a chance." % (CONFIG_NAME, exc)
            )
    else:
        notes.append(
            "%s does not exist yet, so the original eight categories are being "
            "used. Run import-photos.cmd --setup to create it." % CONFIG_NAME
        )

    records, seen = [], set()
    entries = (raw or {}).get("categories")
    if isinstance(entries, list):
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                notes.append("entry %d in %s is not a category, so it was skipped"
                             % (i + 1, CONFIG_NAME))
                continue
            cid = str(entry.get("id", "")).strip()
            label = str(entry.get("label", "")).strip()
            if not CATEGORY_ID_RE.match(cid):
                notes.append(
                    "\"%s\" in %s is not a usable folder name, so it was "
                    "skipped. Use lowercase letters, numbers and hyphens."
                    % (cid, CONFIG_NAME)
                )
                continue
            if cid in seen:
                notes.append("\"%s\" is listed twice in %s - keeping the first."
                             % (cid, CONFIG_NAME))
                continue
            seen.add(cid)
            rec = dict(entry)
            rec["id"] = cid
            rec["label"] = label or humanise(cid)
            rec.setdefault("discordChannelId", None)
            rec.setdefault("discordChannelName", None)
            records.append(rec)

    if not records:
        records = [{"id": c, "label": l,
                    "discordChannelId": None, "discordChannelName": None}
                   for c, l in DEFAULT_CATEGORIES]
        seen = set(c for c, _ in DEFAULT_CATEGORIES)

    # Adopt orphans. If a folder holds photos but is not in the config, keep it.
    # Otherwise deleting one line from the config would strand published JPEGs
    # in docs/ - gone from the gallery, still shipped to every visitor, never
    # cleaned up by prune(), and with nothing on screen to explain it.
    for entry in sorted(_scan_category_dirs(root) - seen):
        records.append({"id": entry, "label": humanise(entry),
                        "discordChannelId": None, "discordChannelName": None,
                        "adopted": True})
        notes.append(
            "\"%s\" holds photos but is not listed in %s, so it is being kept "
            "and will show in the gallery as \"%s\". To retire it for real, "
            "delete photo-originals/%s and docs/photos/%s."
            % (entry, CONFIG_NAME, humanise(entry), entry, entry)
        )

    return records, notes


def load_categories(root):
    """The [(id, label), ...] shape publish_photos.py has always used."""
    records, notes = read_category_config(root)
    return [(r["id"], r["label"]) for r in records], notes


def write_category_config(root, records):
    """Write the config back, dropping the bookkeeping keys we added in memory."""
    clean = []
    for r in records:
        clean.append({
            "id": r["id"],
            "label": r["label"],
            "discordChannelId": r.get("discordChannelId"),
            "discordChannelName": r.get("discordChannelName"),
        })
    payload = {
        "_readme": (
            "The categories your photos are filed under. The order here is the "
            "order of the filter buttons on the gallery page. Adding a channel "
            "in Discord adds a category - run import-photos.cmd --setup. "
            "Deleting a line here does NOT delete photos."
        ),
        "version": 1,
        "categories": clean,
    }
    path = config_path(root)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)
