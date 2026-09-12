# Things to confirm or delete before going live

Nothing on this site claims anything about your business that you have not
confirmed. This is the full list of what is claimed, what is deliberately
absent, and the one thing that is now blocking.

---

## 1. BLOCKER — your Georgia licence number

**The site now says "Licensed and insured" because you confirmed it. Georgia
requires the licence number to appear alongside that claim in advertising, and a
website counts as advertising.**

Under the residential and general contractor rules (O.C.G.A. Ch. 43-41),
contractors must display their licence number on contracts, proposals and
advertising. Right now the site makes the claim without the number.

**Send me the number and I will place it everywhere it needs to go.** It is a
two-minute change.

If you would rather do it yourself, there are two spots, each marked with an HTML
comment saying `LICENCE NUMBER`:

- `docs/index.html` — the "Licensed & insured" card
- `docs/about.html` — the "Experience, and the paperwork behind it" section

The wording to use is `licensed (GA #XXXXXXX) and insured`.

**Also worth telling me:** which licence it is. A *Georgia State Licensing Board
residential contractor* licence and a *county business licence* are different
things, and only the first one means what a customer reads it to mean. If it is
the county business licence, the honest wording is different and I will change it.

---

## 2. Claims now on the site — confirmed by you

| Claim | Where it appears |
|---|---|
| Licensed | Home hero, home trust card, About, every sidebar, every footer |
| Insured | Same |
| Over 30 years of experience *(the owner's, not the company's age)* | Same |

Note the wording on the About page is deliberate: **"The owner has been building
outdoor structures for over 30 years."** That is what you told me. It does not
say the company has traded for 30 years, because you did not say that. If the
business itself is also that old, tell me and I will say so directly — it is a
stronger claim.

---

## 3. Services removed on 2026-09-09

New Deck Construction, Deck Staining & Sealing and Railing Installation were
deleted at your request, because no photos were ever filed under them. Their
categories are gone from `photo-categories.json` too.

Two consequences worth knowing:

- **The site is live**, so those three URLs now return the 404 page. Nothing on
  the site links to them any more, and almost nothing external will either on a
  site this new — but that is the trade.
- **New Deck Construction was the page targeting "deck builder Griffin GA."**
  Say the word and it comes back in minutes; the writing still exists in git
  history.

---

## 4. Claims still deliberately absent

The site says **nothing** about any of these. The words do not appear:

- **Bonded** — you confirmed licensed and insured, but not bonded
- Number of decks, projects or homes completed
- Awards, certifications, accreditations, manufacturer partnerships
- Star ratings or review counts, including in the code Google reads
- Warranties or guarantees
- **Family-run, locally-owned, family-owned** — your old site says this, you have not confirmed it

Any of these can be added in minutes. Just confirm them.

---

## 5. Details taken from your existing site — confirm these are current

| Detail | Value used | Where it came from |
|---|---|---|
| Phone | (678) 308-9153 | deckedoutliving.net |
| Email | bilesenterprise@gmail.com | your brief |
| Facebook | facebook.com/profile.php?id=61562897721519 | deckedoutliving.net |
| Owner name | Josh — appears only inside the customer reviews | deckedoutliving.net |

---

## 6. Opening hours — one assumption I had to make

You said **7:30am–5:30pm** but not which days. Your existing site says
Monday–Friday, so the site uses **Monday–Friday, 7:30am–5:30pm**.

Most deck builders take Saturday calls. If you do, it is worth adding — Google
shows these hours directly in search results.

**To change:** search all files in `docs` for `7:30am` and for `07:30`. The
`07:30` version is in the code Google reads, so change both.

---

## 7. Your address — a decision to make

The site publishes **Griffin, GA** with no street address, and lists the full
service area. That is the right setup for a business that travels to customers.

The trade-off: Google Business Profile listings with a verified street address
tend to rank better locally.

- **Leave it** — normal for contractors, perfectly fine.
- **Add your address** — send it and I will put it in the code Google reads.
- Either way, **set up a free Google Business Profile** at google.com/business.
  For a local trade this does more than anything on the website itself.

The map coordinates in the code are Griffin town centre, not your actual
location. Harmless, but that is what they are.

---

## 8. Customer reviews — imported, please verify

Four reviews from your existing site are in `docs/reviews.json` and show on the
home and about pages:

Rylan Hall · Marie Rea Shaw Sims · Steven Fletcher · Keith Graham

Copied word for word — nothing rewritten or invented.

**Please confirm** they are genuine and that you are happy to keep publishing
them. Delete any you are unsure about; the section shrinks to fit, and emptying
the file removes the section entirely with no gap.

**No star ratings are shown**, and no rating data is in the code Google reads.
Star ratings must come from a real review platform. Inventing them breaks
Google's rules and can get a site penalised.

---

## 9. Permits and code compliance — your decision, noted

You chose to leave permits off the site, and it is off. This is a note, not an
argument.

- Georgia requires a state licence for residential work over **$2,500** in
  combined labour and materials — which you have confirmed you hold.
- Spalding County requires permits for accessory structures over **120 sq ft**.

Most decks cross both thresholds. Now that you are stating you are licensed,
"we handle the permits" is a natural and strong thing to add beside it, because
it answers the next question a customer asks. **Say the word and I will add it.**

---

## 10. Before it can go live

Ordered by what actually blocks you.

- [ ] **Send me your Georgia licence number** — see section 1. This is the only
      hard blocker, and it exists because the site now claims you are licensed
- [ ] **Confirm the phone number** — it is on every page and in the sticky bar
- [x] ~~Connect Formspree~~ — done 2026-09-12, form `xljeyenw`, emails
      bilesenterprise@gmail.com
- [ ] **Confirm the four reviews** are genuine, or delete them
- [ ] **Confirm the opening days** (Mon–Fri assumed)
- [x] ~~Add job photos~~ — 4 published, all in Deck Repair
- [x] ~~Add a before/after pair~~ — done, it is live on the slider
- [ ] **Rename two photos.** `img-20260714-121904.jpg` and
      `img-20260714-121914.jpg` are still camera filenames. The filename becomes
      the visible caption and the alt text Google reads, so these currently fall
      back to the generic "Deck Repair". Rename them in
      `photo-originals/deck-repair/` to something descriptive
      (`pergola-over-new-deck.jpg`), then run `publish-photos.cmd` again. The
      same applies to `deck-before.jpg` / `deck-after.jpg`, which caption as
      just "Deck"
- [x] ~~Re-save the five Discord photos properly~~ — the `.url` shortcut files
      have been deleted. Dragging a picture out of Discord makes a link, not a
      copy, and those particular links had already expired
- [ ] **Set up the Discord bot** — GO-LIVE-GUIDE Step 8, about five minutes,
      once. Then `import-photos.cmd` brings back the four job photos those dead
      shortcuts were pointing at, along with everything else you have posted
- [ ] **Check what is in your `pics` group in Discord.** The channels inside it
      become the folders in `photo-inbox` and the categories on the gallery,
      one per channel. Anything outside `pics` is ignored. Add a channel, run
      `import-photos.cmd --setup`, and it becomes a new gallery category on its
      own — though a *service page* for it still needs writing
- [ ] **Type a few words when you post to Discord.** Not required, but what you
      type becomes the caption on your website. Photos posted with no text land
      as `untitled-...` and caption as the bare category name until renamed —
      the naming page that opens after each import is the easy place to fix that
- [ ] **Read the Complete Remodel page and confirm the scope.** You said the
      page should cover exterior *and* interior work, so it does. It claims:
      siding, roofing, porches, windows, gutters, exterior painting, and inside
      flooring, painting, trim and doors. That is what your photos actually
      show. It deliberately does **not** claim kitchens, bathrooms, plumbing or
      electrical — the FAQ says to ask about those. Tell me if you want any of
      that added or removed
- [ ] **Read the Custom Woodwork and Car Ports pages.** Still written from
      general trade knowledge rather than from what you confirmed
- [ ] Decide on **bonded** and **family-run / locally-owned** (section 3)
- [ ] Set up a **Google Business Profile** — biggest single win for local search
- [ ] Once live, submit to **Google Search Console** so you get found faster

**Nice to have, not blocking:**

- [ ] A photo of the owner or crew for the About page — trust beats polish
- [ ] Move deckedoutliving.net across (GO-LIVE-GUIDE Step 7)
- [ ] Back up `photo-originals/` somewhere — GitHub does **not** hold those
