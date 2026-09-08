# Things to confirm or delete before going live

Nothing on this site claims anything about your business that has not been
verified. Where a normal contractor site would make a claim, there is either
nothing at all or a clearly marked yellow box.

This is the full list. Work down it and the site is honest and finished.

---

## 1. Claims that are deliberately absent

The site says **nothing** about any of the following. Not vaguely, not by
implication — the words do not appear:

- Licensed, insured, or bonded
- Years in business or years of experience
- Number of decks, projects or homes completed
- Awards, certifications, accreditations, brand partnerships
- Star ratings or review counts anywhere, including in the code Google reads
- Warranties or guarantees
- Family-run, locally-owned, or family-owned

Your existing site at deckedoutliving.net says **"Over 30 years of experience"**
and describes the business as **locally-owned and family-run**. Those may well
be true, but they were not written here because you have not confirmed them.

**What to do:** tell me which are accurate and I will add them. Say nothing and
they stay off — which is a perfectly reasonable choice.

There are two yellow placeholder boxes on the live site saying this in plain
language, so a visitor is not left wondering:

- `docs/index.html` — in the "Why homeowners call us" section
- `docs/about.html` — in the main text

**Delete those two boxes before you go live**, whether or not you add the
claims. Search each file for `class="placeholder"` and delete from `<div` to the
matching `</div>`.

---

## 2. Details taken from your existing site — confirm these are current

| Detail | Value used | Where it came from |
|---|---|---|
| Phone | (678) 308-9153 | deckedoutliving.net |
| Email | bilesenterprise@gmail.com | your brief |
| Facebook | facebook.com/profile.php?id=61562897721519 | deckedoutliving.net |
| Owner name | Josh (appears only inside customer reviews) | deckedoutliving.net |

---

## 3. Opening hours — I had to make one assumption

You said **7:30am–5:30pm** but not which days. Your existing site says
Monday–Friday, so the site uses **Monday–Friday, 7:30am–5:30pm**.

Most deck builders take Saturday calls. If you do, it is worth adding — Google
displays these hours directly in search results.

**To change:** search all files in `docs` for `7:30am` and for `07:30`.
The `07:30` version is in the code Google reads, so change both.

---

## 4. Your address — a decision to make

The site currently publishes **Griffin, GA** with no street address, and lists
your full service area. That is the correct setup for a business that travels to
customers rather than having a shop people visit.

The trade-off: Google Business Profile listings with a verified street address
tend to rank better locally.

**Options:**
- **Leave it.** Fine. This is normal for contractors.
- **Add your address.** Send it to me and I will add it properly to the code
  Google reads.
- Either way, **set up a free Google Business Profile** at
  google.com/business. For a local trade this does more for you than anything
  on the website itself.

Also note the map coordinates in the code are Griffin town centre, not your
actual location. Harmless, but that is what they are.

---

## 5. Customer reviews — imported, please verify

Four reviews from your existing site are in `docs/reviews.json` and show on the
home and about pages:

Rylan Hall · Marie Rea Shaw Sims · Steven Fletcher · Keith Graham

They are copied word for word — nothing was rewritten or invented.

**Please confirm** these are genuine and that you are happy to keep publishing
them. Delete any you are unsure about; the section shrinks to fit, and if you
empty the file completely the whole section disappears with no gap.

**No star ratings are shown**, and no rating data is in the code Google reads.
Star ratings need to come from a real review platform. Inventing them is
against Google's rules and can get a site penalised.

---

## 6. Permits and code compliance — your decision, noted

You chose to leave permits off the site entirely, and it is off. This is a note,
not an argument.

Two facts for your own awareness:

- Georgia requires a state licence from the State Licensing Board for
  Residential and General Contractors for residential work over **$2,500** in
  combined labour and materials.
- Spalding County requires permits for accessory structures over **120 sq ft**.

Most decks cross both thresholds. Competitors who say "we handle the permits"
are answering a question your customers are already asking.

**If you change your mind**, tell me and I will add a short, accurate section to
the new-deck page and the FAQ. It is a ten-minute change.

---

## 7. Before it can go live

Ordered by what actually blocks you.

- [ ] **Delete the two yellow placeholder boxes** (`index.html`, `about.html`)
- [ ] **Confirm the phone number** is right — it is on every page and in the
      sticky bar at the bottom of every phone screen
- [ ] **Connect Formspree** so the form emails you (GO-LIVE-GUIDE Step 6).
      Until then the form says so honestly and offers call/text instead
- [ ] **Confirm the four reviews** are genuine, or delete them
- [ ] **Confirm the opening days** (Mon–Fri assumed)
- [ ] **Add 6–10 job photos** — the empty states are designed and look
      deliberate, but photos are what actually sell deck work
- [ ] **Add at least one before/after pair** — name them `something-before.jpg`
      and `something-after.jpg`. This is the single most persuasive thing you
      can put on a deck site
- [ ] Decide on the experience/licensing claims in section 1
- [ ] Set up a **Google Business Profile** — biggest single win for local search
- [ ] Once live, submit the site to **Google Search Console**
      (search.google.com/search-console) so you get found faster

**Nice to have, not blocking:**

- [ ] A photo of you or the crew for the About page — trust beats polish
- [ ] Move deckedoutliving.net across (GO-LIVE-GUIDE Step 7)
- [ ] Back up `photo-originals/` somewhere — GitHub does **not** hold those
