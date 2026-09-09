# Decked Out Living — website

Static website for Decked Out Living, deck and outdoor living construction,
Griffin GA. Plain HTML, CSS and vanilla JavaScript. No framework, no build step,
nothing to compile.

---

## Start here

| I want to… | Do this |
|---|---|
| **Get the site online for the first time** | Read **[GO-LIVE-GUIDE.md](GO-LIVE-GUIDE.md)** |
| **Know what still needs my input** | Read **[PLACEHOLDERS.md](PLACEHOLDERS.md)** |
| **Add job photos** | Drop them in `photo-inbox/`, run `publish-photos.cmd` |
| **Push changes live** | Run `publish-website.cmd` |

---

## The three buttons

| File | What it does | How often |
|---|---|---|
| `setup-github.cmd` | Connects this folder to GitHub | Once, ever |
| `publish-photos.cmd` | Turns dropped photos into website photos | Whenever you have new job photos |
| `publish-website.cmd` | Puts everything online | After any change |

---

## Adding photos

Drop files into the right folder and run one command. You never edit HTML.

```
photo-inbox/
├─ new-decks/
├─ deck-repair/
├─ staining-sealing/
├─ railings/
├─ pergolas/
├─ screened-porches/
├─ custom-woodwork/
└─ car-ports/
```

The folder names must match exactly. If you make a folder of your own, the tool
will tell you it is being ignored and list the valid ones — it will not fail
silently. Want a category that is not there? Ask and it can be added.

**Photos have to be real image files.** Dragging a picture out of a browser,
Discord, Google Photos or OneDrive gives you a `.url` shortcut, not the picture.
Right-click the image and choose *Save image as...* instead. The tool spots
shortcuts and says so in red.

Then double-click `publish-photos.cmd`. It will:

1. **Move your originals** to `photo-originals/` at full resolution, untouched.
2. **Rotate** photos according to the phone's orientation tag, then discard that
   tag — so portrait photos do not publish sideways.
3. **Convert colour** to sRGB first if the phone used a wider profile (iPhones
   do), so nothing looks washed out.
4. **Strip every piece of metadata**, GPS above all — see below.
5. **Build** a web-sized copy (1600px) and a thumbnail (800px).
6. **Rewrite** `docs/photos/gallery.json`, which the gallery reads.
7. **Verify** each finished file and refuse to continue if anything leaked.

### The filename becomes the caption

`cedar deck with pergola.jpg` publishes as *"Cedar Deck With Pergola"*.

**So never put a customer's name or street address in a filename.** The tool
warns you if a filename looks like an address, but it cannot catch everything.

### Before/after pairs

End two files with `-before` and `-after`:

```
barrett-rebuild-before.jpg
barrett-rebuild-after.jpg
```

They become a drag-slider automatically. Both halves must be present — a lone
`-before` is ignored, and the tool tells you it is waiting for the match.

Until you publish a pair, the slider shows a line-drawing illustration labelled
as an illustration. It is never presented as your work.

### About GPS

Phones record the exact location a photo was taken. On a job photo that is your
customer's home address, sitting inside the file.

Every published file is re-opened and checked three separate ways: a walk
through the file's internal structure, a raw byte search for GPS and EXIF
signatures, and a parse with the image library. If anything survives, the tool
stops and refuses to publish.

You can re-check everything already published at any time:

```
python tools\publish_photos.py --verify
```

### iPhone .heic photos

Supported. If support is ever missing, the tool leaves those files in the inbox
and tells you exactly what to do — either install it with
`pip install pillow-heif`, or set **Settings → Camera → Formats → Most
Compatible** on the iPhone so it takes ordinary `.jpg` photos.

---

## What is on the site

- Home
- Eight service pages — new decks, repair, staining & sealing, railings,
  pergolas & covered structures, screened porches, custom woodwork, car ports
  *(separate pages rank better than one combined page)*
- Gallery, About, Contact, and a 404 page

Features: a before/after drag slider, a filterable gallery with a lightbox, a
four-step estimate form, a sticky call/text/estimate bar on phones, and
`LocalBusiness` structured data covering the full service area.

**On a phone** the service cards, process steps and reviews become swipeable
side-scrolling rails rather than one long stack, and each service card carries a
photo band that fills itself in from the gallery as soon as you publish a photo
in that category. Until then it shows a branded tile. That keeps the home page
to roughly nine screens instead of fifteen.

---

## Brand colours

Sampled directly from `logo.jpg`:

| Colour | Hex | Where |
|---|---|---|
| Charcoal | `#343434` | Logo background — 67.8% of its pixels |
| Bright green | `#7EDA53` | The circle mark |
| Soft green | `#8FD074` | The wordmark |
| White | `#FFFFFF` | House and tree line art |

`#7EDA53` on white measures **1.74:1** contrast, far below the 4.5:1 needed to
be readable. So the site uses charcoal as a main surface — where that same green
reaches 7.14:1 — and a derived `#3F7A22` (5.23:1) for the few places green text
sits on white. The logo colours themselves are unchanged.

---

## Editing pages

Open any `.html` file in `docs` with Notepad. Change the words between the tags,
leave anything inside `< >` alone, save, run `publish-website.cmd`.

Adding a review: edit `docs/reviews.json`. The reviews section stays completely
hidden while that file is empty.

Changing the web address later: `python tools\set_domain.py <address>` updates
the structured data, sitemap and domain file in one go. Every asset path on the
site is relative, so nothing else changes.

---

## Requirements

- **Python 3** with `Pillow` and `pillow-heif` — only for the photo tool.
  `publish-photos.cmd` installs them the first time it runs.
- **Git** — only for publishing. See GO-LIVE-GUIDE.md.

The website itself needs neither. It is plain files.

---

## Hosting

GitHub Pages, served from the `docs/` folder on the `main` branch. No CI, no
Actions, no build. What is in `docs/` is what visitors get.
