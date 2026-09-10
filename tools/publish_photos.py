#!/usr/bin/env python3
"""
Decked Out Living - photo publisher.

What this does, in order:

  1. Takes everything you dropped in  photo-inbox/<category>/
     and files it away in            photo-originals/<category>/
     at full resolution, untouched.

  2. Rebuilds  docs/photos/<category>/  from the originals:
       <name>.jpg        web size   (long edge 1600px)
       <name>-thumb.jpg  thumbnail  (long edge 800px)

  3. Applies the EXIF orientation tag so portrait phone photos are
     the right way up, then throws the tag away.

  4. Strips every scrap of metadata - GPS coordinates above all.
     Job photos record the customer's home address. That must never
     reach the web. Every file written is then RE-OPENED and checked
     at the byte level to prove the metadata is actually gone.

  5. Writes docs/photos/gallery.json, which is what the website reads.
     You never edit HTML to add a photo.

Usage:
    python publish_photos.py              normal run
    python publish_photos.py --force      re-process everything
    python publish_photos.py --verify     only audit what is published
"""

import hashlib
import io
import json
import os
import shutil
import sys
from datetime import datetime, timezone

# Shared with import_photos.py. Standard library only, so this import is safe
# to do before the Pillow check below.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from photo_common import (  # noqa: E402
    ADDRESS_RE, CAMERA_RE, PAIR_RE, READABLE,
    add_tags, humanise, load_categories, slugify, split_tags, strip_index,
)

# --------------------------------------------------------------------------
# Dependencies
# --------------------------------------------------------------------------
try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit(
        "\nPillow is not installed.\n"
        "Open PowerShell and run:\n\n    pip install Pillow pillow-heif\n"
    )

try:
    from PIL import ImageCms
    HAVE_CMS = True
except ImportError:
    HAVE_CMS = False

# iPhone .heic support is optional but strongly recommended.
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HAVE_HEIC = True
except ImportError:
    HAVE_HEIC = False

# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(ROOT, "photo-inbox")
ARCHIVE = os.path.join(ROOT, "photo-originals")
PUBLISH = os.path.join(ROOT, "docs", "photos")

WEB_EDGE = 1600
THUMB_EDGE = 800
WEB_QUALITY = 82
THUMB_QUALITY = 78

# The category list, the slug rules and the before/after convention are shared
# with import_photos.py. They live in tools/photo_common.py because if the two
# tools ever disagree about them, before/after pairs stop matching and there is
# nothing on screen to say why.
CATEGORIES, CATEGORY_NOTES = load_categories(ROOT)
CATEGORY_LABEL = dict(CATEGORIES)

GREEN, YELLOW, RED, DIM, OFF = "\033[92m", "\033[93m", "\033[91m", "\033[2m", "\033[0m"
if os.name == "nt" and not os.environ.get("WT_SESSION"):
    try:
        import colorama  # noqa: F401
        colorama.just_fix_windows_console()
    except Exception:
        GREEN = YELLOW = RED = DIM = OFF = ""


def say(msg="", colour=""):
    print(f"{colour}{msg}{OFF}" if colour else msg)


# --------------------------------------------------------------------------
# Metadata verification - the part that must never be taken on trust
# --------------------------------------------------------------------------
# JPEG application segments that can carry identifying information.
RISKY_MARKERS = {
    0xE1: "APP1 (EXIF or XMP - can hold GPS)",
    0xE2: "APP2 (ICC profile)",
    0xE3: "APP3 (Meta)",
    0xEC: "APP12 (Ducky/picture info)",
    0xED: "APP13 (Photoshop IRB / IPTC)",
    0xEE: "APP14 (Adobe)",
    0xFE: "COM (comment)",
}

RISKY_STRINGS = [
    b"Exif\x00\x00",
    b"GPS",
    b"http://ns.adobe.com/xap",   # XMP
    b"Photoshop 3.0",
    b"ICC_PROFILE",
    b"GPSLatitude",
    b"GPSLongitude",
    b"AppleiOS",
]


def scan_jpeg_segments(path):
    """Walk the JPEG marker chain and report any segment that could carry PII."""
    found = []
    with open(path, "rb") as fh:
        data = fh.read()

    if not data.startswith(b"\xff\xd8"):
        return ["not a JPEG file"]

    i = 2
    n = len(data)
    while i < n - 1:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        # padding / standalone markers
        if marker in (0xFF, 0x01) or 0xD0 <= marker <= 0xD9:
            i += 2
            continue
        if i + 4 > n:
            break
        seg_len = int.from_bytes(data[i + 2:i + 4], "big")
        if marker in RISKY_MARKERS:
            found.append(RISKY_MARKERS[marker])
        if marker == 0xDA:          # start of scan - image data follows
            break
        i += 2 + seg_len

    return found


def header_region(data):
    """
    Everything before the start-of-scan marker - i.e. the part of a JPEG that
    can hold metadata. After SOS it is entropy-coded pixel data, where any byte
    sequence can occur by chance.
    """
    i = 2
    n = len(data)
    while i < n - 1:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xFF, 0x01) or 0xD0 <= marker <= 0xD9:
            i += 2
            continue
        if i + 4 > n:
            break
        if marker == 0xDA:          # start of scan
            return data[:i]
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    return data


def verify_clean(path):
    """
    Prove a published file carries no metadata. Three independent checks,
    because one library saying 'no exif' is not evidence.
    Returns (ok, [problems]).
    """
    problems = []

    # 1. byte-level JPEG segment walk
    problems += [f"segment present: {s}" for s in scan_jpeg_segments(path)]

    # 2. byte-signature scan of the METADATA REGION only.
    #    Scanning the whole file gives false alarms: "GPS" is three bytes, and
    #    across a few hundred photos it turns up by chance inside the compressed
    #    pixel data. Metadata can only live before the start-of-scan marker, so
    #    that is the only part worth searching.
    with open(path, "rb") as fh:
        blob = fh.read()
    head = header_region(blob)
    for needle in RISKY_STRINGS:
        if needle in head:
            problems.append(f"byte signature found: {needle.decode('latin-1')}")

    # 3. ask Pillow what it can parse back out
    try:
        with Image.open(path) as im:
            exif = im.getexif()
            if exif and len(exif):
                problems.append(f"Pillow parsed {len(exif)} EXIF tag(s)")
            # GPS lives in its own IFD
            try:
                gps = exif.get_ifd(0x8825) if exif else None
                if gps:
                    problems.append(f"GPS IFD present with {len(gps)} tag(s)")
            except Exception:
                pass
            for key in ("exif", "icc_profile", "photoshop", "comment", "XML:com.adobe.xmp", "xmp"):
                if key in im.info and im.info[key]:
                    problems.append(f"info['{key}'] present")
    except Exception as exc:
        problems.append(f"could not reopen: {exc}")

    return (not problems), problems


# --------------------------------------------------------------------------
# Image processing
# --------------------------------------------------------------------------
_SRGB = None


def srgb_profile():
    global _SRGB
    if _SRGB is None and HAVE_CMS:
        _SRGB = ImageCms.createProfile("sRGB")
    return _SRGB


def load_clean(path):
    """
    Open an image, honour its EXIF orientation, normalise colour to sRGB,
    and return a brand-new image object that carries no metadata at all.
    """
    im = Image.open(path)

    # 1. rotate per the EXIF orientation tag. exif_transpose bakes the
    #    rotation into the pixels and drops the tag.
    im = ImageOps.exif_transpose(im)

    # 2. convert an embedded colour profile (iPhones shoot Display P3)
    #    into sRGB *before* we discard the profile, so colours survive.
    icc = im.info.get("icc_profile")
    if icc and HAVE_CMS:
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGB")
            im = ImageCms.profileToProfile(im, src, srgb_profile(), outputMode="RGB")
        except Exception:
            pass  # unreadable profile - fall through and just drop it

    if im.mode != "RGB":
        # flatten transparency onto white rather than producing a black box
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            flat = Image.new("RGB", im.size, (255, 255, 255))
            flat.paste(im, mask=im.split()[-1])
            im = flat
        else:
            im = im.convert("RGB")

    return im


def strip(im):
    """Rebuild pixels into a fresh object so nothing from .info can ride along."""
    clean = Image.frombytes(im.mode, im.size, im.tobytes())
    return clean


def resize_to(im, edge):
    w, h = im.size
    if max(w, h) <= edge:
        return im.copy()
    if w >= h:
        return im.resize((edge, max(1, round(h * edge / w))), Image.LANCZOS)
    return im.resize((max(1, round(w * edge / h)), edge), Image.LANCZOS)


def write_jpeg(im, path, quality):
    im = strip(im)
    buf = io.BytesIO()
    im.save(
        buf,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
        subsampling=1,
        exif=b"",           # explicitly empty
        icc_profile=None,   # explicitly none
    )
    with open(path, "wb") as fh:
        fh.write(buf.getvalue())
    return im.size


# --------------------------------------------------------------------------
# Steps
# --------------------------------------------------------------------------
def ensure_dirs():
    for cat, _ in CATEGORIES:
        os.makedirs(os.path.join(INBOX, cat), exist_ok=True)
        os.makedirs(os.path.join(ARCHIVE, cat), exist_ok=True)
        os.makedirs(os.path.join(PUBLISH, cat), exist_ok=True)


# Dragging a picture out of a browser, Discord, Google Photos or OneDrive
# drops a tiny shortcut file rather than the picture itself. It looks right
# in Explorer and is not an image at all, so say so plainly.
SHORTCUT_EXT = {".url", ".lnk", ".webloc", ".website"}


def file_hash(path):
    """SHA-256 of a file's bytes, read in chunks so a big photo is not slurped."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def archive_hashes():
    """content hash -> "category/filename" for everything already archived.

    Keyed on content, not filename, and spanning every category. That is what
    stops the same photo being filed twice - which used to happen two ways:
    dropping a photo in again after it was published, and the same job being
    added by hand under one category and imported from Discord under another.
    A job that genuinely belongs in two places is a "+tag", not a second copy.
    """
    out = {}
    for cat, _label, path, name in collect_originals():
        try:
            out.setdefault(file_hash(path), f"{cat}/{name}")
        except OSError:
            pass
    return out


def intake():
    """Move inbox files into the originals archive. Returns count moved."""
    moved = 0
    skipped_heic = []
    shortcuts = []
    other_files = []
    already = []
    seen_hashes = archive_hashes()

    known = {c for c, _ in CATEGORIES}

    # Folders somebody made by hand that the tool does not publish from.
    stray_dirs = []
    if os.path.isdir(INBOX):
        for entry in sorted(os.listdir(INBOX)):
            p = os.path.join(INBOX, entry)
            if os.path.isdir(p) and entry not in known and not entry.startswith("."):
                n = sum(1 for f in os.listdir(p)
                        if os.path.isfile(os.path.join(p, f)) and not f.endswith(".txt"))
                stray_dirs.append((entry, n))

    for cat, _ in CATEGORIES:
        src_dir = os.path.join(INBOX, cat)
        if not os.path.isdir(src_dir):
            continue
        for name in sorted(os.listdir(src_dir)):
            src = os.path.join(src_dir, name)
            if not os.path.isfile(src) or name.startswith("."):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in SHORTCUT_EXT:
                shortcuts.append(f"{cat}/{name}")
                continue
            if ext not in READABLE:
                if ext != ".txt":
                    other_files.append(f"{cat}/{name}")
                continue
            if ext in (".heic", ".heif") and not HAVE_HEIC:
                skipped_heic.append(f"{cat}/{name}")
                continue

            stem, _ = os.path.splitext(name)
            # Split the "+category" tags off BEFORE slugify, which strips "+"
            # and would weld the tag onto the job name.
            base, tags = split_tags(stem)

            digest = file_hash(src)
            if digest in seen_hashes:
                already.append((f"{cat}/{name}", seen_hashes[digest]))
                os.remove(src)
                continue

            dest = os.path.join(ARCHIVE, cat, add_tags(slugify(base), tags) + ext)
            n = 2
            # Only reached when the CONTENT differs but the name collides -
            # two genuinely different photos both called "deck.jpg".
            while os.path.exists(dest):
                dest = os.path.join(
                    ARCHIVE, cat, add_tags(f"{slugify(base)}-{n}", tags) + ext)
                n += 1
            shutil.move(src, dest)
            seen_hashes[digest] = f"{cat}/{os.path.basename(dest)}"
            say(f"    filed  {cat}/{os.path.basename(dest)}", GREEN)
            moved += 1

    if already:
        say()
        say("  Already had these - the same picture, byte for byte. Skipped:", YELLOW)
        for dropped, existing in already:
            say(f"       {dropped}", YELLOW)
            say(f"         already filed as {existing}", DIM)
        say()
        say("  Nothing was lost: the copy you already had is untouched, and the", DIM)
        say("  one in the inbox has been cleared away.", DIM)
        say("  If you meant it to show under a second category, do not copy it -", DIM)
        say("  add a tag to the existing file instead, e.g. rename it to", DIM)
        say("      <name>+pergolas.jpg", DIM)

    if shortcuts:
        say()
        say("  !! THESE ARE NOT PHOTOS - they are shortcuts, and were skipped:", RED)
        for f in shortcuts:
            say(f"       {f}", RED)
        say()
        say("  A file ending .url or .lnk is a link to a picture somewhere else,", YELLOW)
        say("  not the picture itself. Windows makes one of these when you DRAG", YELLOW)
        say("  an image out of a browser, Discord, Google Photos or OneDrive.", YELLOW)
        say()
        say("  To fix it: open the image so it fills the screen, RIGHT-CLICK it", YELLOW)
        say("  and choose 'Save image as...', save it into the inbox folder, then", YELLOW)
        say("  delete the .url file and run me again.", YELLOW)

    if stray_dirs:
        say()
        say("  These folders are not ones I publish from, so anything in them", YELLOW)
        say("  was ignored:", YELLOW)
        for d, n in stray_dirs:
            say(f"       photo-inbox/{d}/   ({n} file{'' if n == 1 else 's'} inside)", YELLOW)
        say()
        say("  Photos must go in one of these folders, spelled exactly:", YELLOW)
        for c, l in CATEGORIES:
            say(f"       photo-inbox/{c}/".ljust(38) + f"({l})", YELLOW)
        say()
        say("  Want a category that is not listed? Make a channel for it in", YELLOW)
        say("  Discord and run  import-photos.cmd --setup  - or add a line to", YELLOW)
        say("  photo-categories.json yourself.", YELLOW)

    if other_files:
        say()
        say("  Skipped - not a picture format I can read:", YELLOW)
        for f in other_files:
            say(f"       {f}", YELLOW)

    if skipped_heic:
        say()
        say("  iPhone .heic photos were left in the inbox:", YELLOW)
        for f in skipped_heic:
            say(f"      {f}", YELLOW)
        say()
        say("  To publish these, do ONE of the following:", YELLOW)
        say("    a) Install HEIC support - run this once, then re-run me:", YELLOW)
        say("           pip install pillow-heif", YELLOW)
        say("    b) Stop your iPhone making .heic files at all:", YELLOW)
        say("           Settings > Camera > Formats > Most Compatible", YELLOW)
        say("       (photos you take from then on will be ordinary .jpg)", YELLOW)

    return moved


def collect_originals():
    items = []
    for cat, label in CATEGORIES:
        d = os.path.join(ARCHIVE, cat)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if not os.path.isfile(p) or name.startswith("."):
                continue
            if os.path.splitext(name)[1].lower() not in READABLE:
                continue
            items.append((cat, label, p, name))
    return items


def build(force=False):
    photos = []
    pairs_raw = {}
    warnings = []
    made = 0
    reused = 0

    for cat, label, src, name in collect_originals():
        raw_stem = os.path.splitext(name)[0]
        # Extra categories ride on the end of the filename after a "+". Split
        # them off FIRST: slugify() strips "+" and would weld the tag onto the
        # job name, turning "deck+pergolas" into "deckpergolas".
        stem, tags = split_tags(raw_stem)
        slug = slugify(stem)

        out_dir = os.path.join(PUBLISH, cat)
        web_path = os.path.join(out_dir, slug + ".jpg")
        thumb_path = os.path.join(out_dir, slug + "-thumb.jpg")

        fresh = (
            force
            or not os.path.exists(web_path)
            or not os.path.exists(thumb_path)
            or os.path.getmtime(src) > os.path.getmtime(web_path)
        )

        if fresh:
            try:
                im = load_clean(src)
            except Exception as exc:
                warnings.append(f"could not read {cat}/{name}: {exc}")
                continue
            w, h = write_jpeg(resize_to(im, WEB_EDGE), web_path, WEB_QUALITY)
            tw, th = write_jpeg(resize_to(im, THUMB_EDGE), thumb_path, THUMB_QUALITY)
            im.close()
            made += 1
            say(f"    built  {cat}/{slug}.jpg  ({w}x{h})", GREEN)
        else:
            with Image.open(web_path) as im:
                w, h = im.size
            with Image.open(thumb_path) as im:
                tw, th = im.size
            reused += 1

        # caption comes from the filename, so flag anything address-shaped
        m = PAIR_RE.match(stem)
        caption_stem = m.group("stem") if m else stem

        # Photo 3 of one job is <job>-3. All the photos of a job describe the
        # same job, so drop the counter rather than captioning them
        # "Cedar Deck Rebuild 2", "Cedar Deck Rebuild 3". Must happen AFTER
        # PAIR_RE so that <job>-3-before still pairs with <job>-3-after.
        caption_stem = strip_index(caption_stem)

        if CAMERA_RE.match(caption_stem.replace("_", "-")):
            # straight off the camera - use the category rather than publish
            # "Img 20260714 121904" as the caption a customer reads
            caption = label
            warnings.append(
                f"{cat}/{name} still has its camera filename, so the caption falls "
                f"back to \"{label}\". Rename it to something descriptive "
                f"(e.g. \"cedar-deck-with-pergola.jpg\") and re-run me - the filename "
                f"becomes the caption and the alt text Google reads."
            )
        else:
            caption = humanise(caption_stem)

        if ADDRESS_RE.search(stem):
            warnings.append(
                f"filename looks like a street address and becomes the public "
                f"caption: {cat}/{name}  ->  \"{caption}\""
            )

        # A job can sit in more than one category - a deck with a pergola over
        # it belongs in both. The folder gives the main one; the "+" tags add
        # the rest. Unknown tags are reported rather than silently dropped,
        # because a typo would otherwise just quietly do nothing.
        categories = [cat]
        for tag in tags:
            if tag == cat:
                continue
            if tag in CATEGORY_LABEL:
                if tag not in categories:
                    categories.append(tag)
            else:
                known = ", ".join(c for c, _ in CATEGORIES)
                warnings.append(
                    f"{cat}/{name} is tagged \"+{tag}\", which is not a category. "
                    f"It has been ignored. Valid ones are: {known}"
                )

        rec = {
            "id": f"{cat}/{slug}",
            "category": cat,                 # the main one, from the folder
            "categories": categories,        # main + any "+" tags
            "categoryLabel": label,
            "categoryLabels": [CATEGORY_LABEL.get(c, c) for c in categories],
            "web": f"photos/{cat}/{slug}.jpg",
            "thumb": f"photos/{cat}/{slug}-thumb.jpg",
            "w": w, "h": h, "tw": tw, "th": th,
            "caption": caption,
        }

        if m:
            side = m.group("side").lower()
            key = (cat, slugify(m.group("stem")))
            pairs_raw.setdefault(key, {"label": caption, "category": cat})[side] = rec
            rec["badge"] = side.capitalize()

        photos.append(rec)

    # only keep pairs where BOTH halves exist
    pairs = []
    for (cat, key), v in sorted(pairs_raw.items()):
        if "before" in v and "after" in v:
            pairs.append({
                "id": f"{cat}/{key}",
                "label": v["label"],
                "category": cat,
                "before": v["before"],
                "after": v["after"],
            })
        else:
            have = "before" if "before" in v else "after"
            warnings.append(
                f"unmatched {have}-photo in {cat}: \"{key}\" - needs a matching "
                f"{'after' if have == 'before' else 'before'} file to show as a slider"
            )

    # A photo tagged into two categories counts towards both, so the filter
    # button totals match what the gallery actually shows when clicked.
    counts = {}
    for p in photos:
        for c in p["categories"]:
            counts[c] = counts.get(c, 0) + 1

    manifest = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "categories": [
            {"id": c, "label": l, "count": counts.get(c, 0)}
            for c, l in CATEGORIES if counts.get(c, 0)
        ],
        "photos": photos,
        "pairs": pairs,
    }

    os.makedirs(PUBLISH, exist_ok=True)
    with open(os.path.join(PUBLISH, "gallery.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    return manifest, made, reused, warnings


def prune():
    """Delete published files whose original is gone, so the site self-heals."""
    removed = 0
    keep = set()
    for cat, _, _, name in collect_originals():
        # Same split as build(), or a tagged original would map to a different
        # slug here and its published files would be deleted as orphans.
        base, _tags = split_tags(os.path.splitext(name)[0])
        slug = slugify(base)
        keep.add(os.path.join(PUBLISH, cat, slug + ".jpg"))
        keep.add(os.path.join(PUBLISH, cat, slug + "-thumb.jpg"))

    for cat, _ in CATEGORIES:
        d = os.path.join(PUBLISH, cat)
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            p = os.path.join(d, name)
            if os.path.isfile(p) and p not in keep:
                os.remove(p)
                say(f"    removed {cat}/{name} (original deleted)", DIM)
                removed += 1
    return removed


def audit():
    """Re-open every published JPEG and prove it carries no metadata."""
    checked, bad = 0, []
    for cat, _ in CATEGORIES:
        d = os.path.join(PUBLISH, cat)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(".jpg"):
                continue
            p = os.path.join(d, name)
            ok, problems = verify_clean(p)
            checked += 1
            if not ok:
                bad.append((f"{cat}/{name}", problems))
    return checked, bad


# --------------------------------------------------------------------------
def main():
    args = set(sys.argv[1:])
    force = "--force" in args or "-f" in args
    verify_only = "--verify" in args

    say()
    say("  DECKED OUT LIVING - publishing photos", GREEN)
    say("  " + "-" * 46, DIM)

    if CATEGORY_NOTES:
        say()
        say("  About your categories:", YELLOW)
        for note in CATEGORY_NOTES:
            say("    - " + note, YELLOW)

    ensure_dirs()

    if verify_only:
        checked, bad = audit()
        say()
        report_audit(checked, bad)
        return 1 if bad else 0

    say()
    say("  1. Taking photos out of the inbox")
    moved = intake()
    if not moved:
        say("    (inbox was empty - rebuilding from the archive)", DIM)

    say()
    say("  2. Building web and thumbnail versions")
    manifest, made, reused, warnings = build(force=force)
    if not made:
        say("    (everything already up to date)", DIM)
    prune()

    say()
    say("  3. Checking every published file for leftover metadata")
    checked, bad = audit()
    report_audit(checked, bad)

    say()
    say("  " + "-" * 46, DIM)
    n = len(manifest["photos"])
    say(f"  {n} photo{'' if n == 1 else 's'} published"
        f"  ({made} new, {reused} unchanged)", GREEN)
    if manifest["pairs"]:
        say(f"  {len(manifest['pairs'])} before/after pair"
            f"{'' if len(manifest['pairs']) == 1 else 's'} ready for the slider", GREEN)
    if not HAVE_HEIC:
        say("  iPhone .heic support: NOT installed  (pip install pillow-heif)", YELLOW)
    if not HAVE_CMS:
        say("  colour management unavailable - profiles dropped without conversion", YELLOW)

    if warnings:
        say()
        say("  Worth a look:", YELLOW)
        for w in warnings:
            say(f"    - {w}", YELLOW)

    say()
    if bad:
        say("  STOP - do not publish. See the metadata failures above.", RED)
        return 1

    say("  Done. To put these online, double-click  publish-website.cmd", GREEN)
    say("  in this folder:  %s" % ROOT, GREEN)
    say()
    return 0


def report_audit(checked, bad):
    if not checked:
        say("    nothing published yet - nothing to check", DIM)
        return
    if not bad:
        say(f"    {checked} file{'' if checked == 1 else 's'} checked - "
            f"no EXIF, no GPS, no XMP, no IPTC, no colour profile", GREEN)
        return
    say(f"    {len(bad)} of {checked} file(s) STILL CARRY METADATA:", RED)
    for name, problems in bad:
        say(f"      {name}", RED)
        for p in problems:
            say(f"          {p}", RED)


if __name__ == "__main__":
    sys.exit(main())
