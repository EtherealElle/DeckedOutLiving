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
| **Get job photos off Discord** | Run `import-photos.cmd` |
| **Add job photos by hand** | Drop them in `photo-inbox/`, run `publish-photos.cmd` |
| **Push changes live** | Run `publish-website.cmd` |

---

## The four buttons

| File | What it does | How often |
|---|---|---|
| `setup-github.cmd` | Connects this folder to GitHub | Once, ever |
| `import-photos.cmd` | Fetches job photos out of Discord | Whenever you have posted photos |
| `publish-photos.cmd` | Turns dropped photos into website photos | After importing, or after dropping photos in by hand |
| `publish-website.cmd` | Puts everything online | After any change |

---

## Adding photos — from Discord

You already post job photos to Discord from your phone, one job per message.
`import-photos.cmd` fetches them, files them by category, and opens a page in
your browser where you name each job once.

1. Post to Discord as usual, in the channel for that kind of work.
2. Run `import-photos.cmd`.
3. Name each job on the page that opens, click **Save names**.
4. Run `publish-photos.cmd`.

**The channels inside your `pics` group decide the categories.** In Discord,
`pics` is the collapsible heading with your photo channels under it. Whatever
channels are in there become the folders in `photo-inbox`, one per channel:

```
Discord                     photo-inbox/
  PICS                        new-decks/
    #new-decks       ---->     deck-repair/
    #deck-repair               screen-rooms/
    #screen rooms
  ADMIN
    #general        (ignored - not in PICS)
```

Add a channel to `pics` and run `import-photos.cmd --setup`, and it becomes a
new category with its own filter button on the gallery — no HTML to edit. (It
does *not* get a service page or a menu entry; that needs real writing.)

Move a channel **out** of `pics` and it simply stops importing. Its photos stay
on the website — nothing is deleted.

Setting it up the first time is Step 8 of [GO-LIVE-GUIDE.md](GO-LIVE-GUIDE.md).
It needs no extra software. The import stops at `photo-inbox` on purpose —
nothing reaches the website without you looking at it.

Two things worth knowing:

- **Discord does not remove GPS from your photos.** It is a delivery van, not a
  cleaner. That is why `publish-photos.cmd` still strips everything and checks
  it three ways, exactly as it does for photos you copy across by hand.
- **Your phone may shrink a photo when it uploads.** For a shot you really care
  about, copy it off the phone straight into `photo-inbox` instead.

---

## Adding photos — by hand

Drop files into the right folder and run one command. You never edit HTML.

```
photo-inbox/
├─ deck-repair/
├─ pergolas/
├─ screened-porches/
├─ custom-woodwork/
├─ car-ports/
└─ complete-remodel/
```

That list lives in `photo-categories.json`, which is also where each category is
matched to its Discord channel. The folder names must match it exactly. If you
make a folder of your own, the tool tells you it is being ignored and lists the
valid ones — it will not fail silently.

Deleting a category from `photo-categories.json` does **not** delete its photos.
If the folder still holds any, the tool keeps the category and says so. To
retire one for real, delete its folders under `photo-originals/` and
`docs/photos/`.

**The same photo cannot be added twice.** Before filing anything, the tool
hashes it and compares against every photo already archived, in every category.
An identical picture is skipped, not filed under a new name — so dropping a
photo in again after it is published does nothing, and you are told which file
it already matches. Two genuinely different photos that happen to share a
filename are both kept, as `name.jpg` and `name-2.jpg`.

If you wanted a photo to appear under a second category, do not copy it — add a
`+tag` to the file you already have (see below).

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

Importing from Discord, the chain runs one step further: **what you type in
Discord, or on the naming page, becomes the filename, which becomes the words
on your website.**

**So never put a customer's name or street address in a filename or a Discord
message.** Both tools warn you if something looks like an address, and phone
numbers and dollar amounts are stripped out automatically — but nothing can
recognise a bare surname. Post photos with no text at all and they arrive named
`untitled-...`, which is safe: the caption falls back to the category name and
the tool tells you which ones to rename.

### One job, more than one category

A deck with a pergola over it genuinely belongs in both places. It does not need
to be two copies of the same photo.

When you name a job on the import page there is a row of tick boxes:
**Also show under**. Tick Pergolas on a deck job and those photos appear under
both filters in the gallery, and can front either service card — while still
being one photo, counted once under "All work".

Behind the scenes the extra categories are written onto the end of the filename
after a `+`:

```
deck-rebuild-with-pergola-before+deck-repair.jpg
```

So you can do the same by hand for photos you copy in yourself — just add
`+category-id` before the `.jpg`. The ids are the folder names listed above. A
tag that is not a real category is reported rather than silently ignored.

The `+` is safe as a separator because it can never appear in a job name: the
slug rules strip it.

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
- Six service pages — deck repair, pergolas & covered structures, screened
  porches, custom woodwork, car ports, complete remodel
  *(separate pages rank better than one combined page)*
- Gallery, About, Contact, and a 404 page

Every service page has photos behind it. New Deck Construction, Deck Staining &
Sealing and Railing Installation were removed on 2026-09-09 because no photos
were ever filed under them — if you start photographing that work, say so and
the pages come back.

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

`import-photos.cmd` needs Python but nothing else — no extra packages, nothing
to install. It uses only what Python already ships with.

The website itself needs none of it. It is plain files.

---

## The Discord bot token

Connecting Discord creates `discord-bot.secret.json` in this folder. It is a
password for reading your Discord server, and **this repository is public**, so
it must never be uploaded.

Three things stop that happening, independently of each other:

- `.gitignore` hides it, by pattern, so renaming it does not un-hide it.
- `import-photos.cmd` refuses to save a token unless it can prove git is
  ignoring it.
- `publish-website.cmd` checks every upload and stops dead if a file with
  `secret` or `token` in its name is about to go out.

If you ever think it has leaked: discord.com/developers → your app → **Bot** →
**Reset Token**. The old one stops working the moment you do.

---

## Hosting

GitHub Pages, served from the `docs/` folder on the `main` branch. No CI, no
Actions, no build. What is in `docs/` is what visitors get.
