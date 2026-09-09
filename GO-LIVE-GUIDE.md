# Getting the website online

Written for someone who has never used GitHub. Nothing here assumes you know
what any of it means. Follow it in order and skip nothing.

Set aside about 30 minutes for the first time. After that, publishing a change
takes about ten seconds.

---

## What you are actually doing

Three ideas, and then the rest is just clicking:

| Thing | What it really is |
|---|---|
| **Git** | A program on your computer that keeps track of changes to files. |
| **GitHub** | A website that stores a copy of those files for you, free. |
| **GitHub Pages** | A free service from GitHub that turns those files into a live website. |

So: your files live on your computer, get copied up to GitHub, and GitHub
publishes them as a website. That is the whole system.

**Free.** All of it, permanently, for a site like this.

---

## Step 1 — Install Git

1. Go to **https://git-scm.com/download/win**
2. The download starts on its own. Run the file when it finishes.
3. Click **Next** on every screen. Every default is fine. Do not change anything.
4. **Restart your computer** when it finishes. This matters — Windows will not
   find Git until you do.

---

## Step 2 — Make a GitHub account

1. Go to **https://github.com/signup**
2. Use your business email so you do not lose it.
3. Pick a username. **This becomes part of your web address**, so choose
   something you would not mind a customer seeing — `deckedoutliving` or
   `joshbiles` rather than something jokey.
4. Confirm the email GitHub sends you.

Write your username and password down somewhere safe. You will need them.

---

## Step 3 — Create the storage space ("repository")

1. Sign in to GitHub and go to **https://github.com/new**
2. **Repository name:** `deckedoutliving-website`
3. **Public** — leave this selected. It has to be public for the free website
   to work. This only means the files are visible; that is normal and fine.
4. **IMPORTANT:** leave all three tick boxes **unticked** — no README, no
   .gitignore, no licence. The repository must be completely empty or Step 4
   will fail.
5. Click **Create repository**.
6. The next page shows an address like
   `https://github.com/yourname/deckedoutliving-website.git`.
   **Copy it.** You need it in about ten seconds.

---

## Step 4 — Connect this folder

1. Open the project folder (the one containing this guide).
2. Double-click **`setup-github.cmd`**
3. Paste the address you copied when it asks.
4. A GitHub sign-in window may pop up. Sign in and let it finish.

When it says *Uploaded*, your files are on GitHub. They are not a website yet —
that is the next step.

---

## Step 5 — Turn the website on

1. On GitHub, open your repository.
2. Click **Settings** (the tab along the top, on the right).
3. In the left-hand menu, click **Pages**.
4. Set these three things:
   - **Source:** `Deploy from a branch`
   - **Branch:** `main`
   - **Folder:** `/docs` ← this one is easy to miss, and nothing works without it
5. Click **Save**.

Wait about a minute, then reload that page. GitHub shows a green box with your
address:

```
https://yourname.github.io/deckedoutliving-website/
```

**That is your live website.** Open it on your phone. Send it to someone.

> If you get a 404 page, wait two more minutes and reload. The very first build
> is the slowest. If it is still 404 after five minutes, go back and check that
> **Folder** says `/docs` and not `/ (root)`.

---

## Step 6 — Make the form actually email you

Until you do this, the estimate form tells visitors plainly that it is not
connected yet and points them to call or text instead. It does not pretend to
send. But you want it working.

1. Go to **https://formspree.io** and create a free account using
   **bilesenterprise@gmail.com**.
2. Create a new form. Call it *Website quote requests*.
3. Formspree gives you an address like `https://formspree.io/f/abcdwxyz`.
   Copy the code on the end — the `abcdwxyz` part.
4. Open **`docs/contact.html`** in Notepad.
   (Right-click the file → *Open with* → *Notepad*.)
5. Press **Ctrl+F** and search for `YOUR_FORM_ID`.
6. Replace `YOUR_FORM_ID` with your code, so the line reads:

   ```html
   action="https://formspree.io/f/abcdwxyz"
   ```

7. Save and close.
8. Double-click **`publish-website.cmd`**.
9. Go to your live site and send yourself a test request. Formspree will email
   you once to confirm the address the first time.

The free plan covers 50 messages a month, which is plenty.

---

## Step 7 — Use your real domain (deckedoutliving.net)

Only when you are ready to move off the old site.

1. In this folder, hold **Shift**, right-click empty space, choose
   **Open PowerShell window here**, and run:

   ```
   python tools\set_domain.py https://www.deckedoutliving.net
   ```

   That updates the address Google reads, rewrites the sitemap, and creates the
   file GitHub needs.

2. Go to wherever you bought deckedoutliving.net (GoDaddy, Namecheap, Squarespace
   — wherever you pay for it) and find the **DNS** settings. Add these:

   | Type | Name | Value |
   |---|---|---|
   | A | @ | 185.199.108.153 |
   | A | @ | 185.199.109.153 |
   | A | @ | 185.199.110.153 |
   | A | @ | 185.199.111.153 |
   | CNAME | www | `yourname.github.io` |

3. Back on GitHub: **Settings → Pages → Custom domain**, type
   `www.deckedoutliving.net`, click **Save**.
4. Wait. DNS changes can take anywhere from ten minutes to a day.
5. When the **Enforce HTTPS** tick box becomes available, tick it. This gives
   you the padlock in the address bar. Do not skip it.
6. Run **`publish-website.cmd`**.

Every link and image on the site is relative, so nothing else needs changing.
The site works identically at both addresses.

---

## Step 8 — Connect Discord (optional)

You already send job photos to Discord from your phone. This lets the computer
fetch them for you instead of downloading each one by hand. Skip this step if
you would rather keep copying photos across yourself — everything else works
the same either way.

You are creating a **bot**: a second account that can read your server and
nothing else. It cannot post, delete, or change anything.

### In your web browser

1. Go to **discord.com/developers/applications**
   Click **New Application**, name it `Decked Out Living Photos`, click
   **Create**.

2. On the left, click **Bot**.

3. Scroll down to **Privileged Gateway Intents** and turn on
   **MESSAGE CONTENT INTENT**. Click **Save Changes**.

   > This one is not optional. Without it Discord hides your photos from the
   > bot completely and the tool will report that it found nothing.

4. Click **Reset Token**, confirm, then **Copy**.
   Discord shows this once and never again. It is a password — do not put it
   in an email or a chat window.

### On this computer

5. Double-click **`import-photos.cmd`**. The first time, it walks you through
   the rest: it asks for the token (typing is hidden), gives you a link to add
   the bot to your server, then lists your channels and asks which ones hold
   job photos.

   **One channel per kind of work.** The channel a photo is posted in decides
   which category it lands in. If you make a new channel later, run
   `import-photos.cmd --setup` again and it becomes a new category.

6. **If your photo channels are private, the bot still cannot see them.**
   In Discord, right-click the channel *category* that holds them:
   **Edit Channel → Permissions → Add members or roles**, add
   `Decked Out Living Photos`, and allow **View Channel** and
   **Read Message History**. Doing that once on the category covers every
   channel inside it.

Your token is saved in `discord-bot.secret.json`. That file is **never**
uploaded to GitHub, and `publish-website.cmd` refuses to run if it ever ends up
in an upload. If you think it has leaked, go back to
discord.com/developers → your app → **Bot** → **Reset Token**; the old one
stops working immediately.

---

## Day-to-day: publishing changes

**Adding job photos — from Discord**

1. Post the photos to Discord as you already do, one job per message, in the
   channel for that kind of work.
2. Double-click **`import-photos.cmd`**. It downloads them into `photo-inbox`
   and opens a page in your browser.
3. On that page, type a name for each job and click **Save names**. What you
   type becomes the caption on your website, so no customer names or addresses.
4. Double-click **`publish-photos.cmd`**.
5. Double-click **`publish-website.cmd`**.

**Adding job photos — by hand**

1. Drop photos into the matching folder inside `photo-inbox`.
2. Double-click **`publish-photos.cmd`**.
3. Double-click **`publish-website.cmd`**.

**Changing words on a page**

1. Open the `.html` file in `docs` with Notepad.
2. Change the text between the tags. Leave anything inside `< >` alone.
3. Save.
4. Double-click **`publish-website.cmd`**.

**Adding a customer review**

1. Open `docs/reviews.json` in Notepad.
2. Copy an existing block and change the quote and name. Watch the commas —
   every block except the last needs one after its closing `}`.
3. Save, then **`publish-website.cmd`**.

The reviews section stays completely hidden if that file is empty.

---

## When something goes wrong

**"The site still shows the old version"**
GitHub takes up to a minute, and your phone may be showing a cached copy. Wait,
then pull down to refresh. On a computer, press **Ctrl+Shift+R**.

**"publish-website.cmd says nothing has changed"**
It means exactly that — you have already published everything. Not an error.

**"A sign-in window keeps appearing"**
Sign in and tick *remember me*. If it will not stick, search Windows for
**Credential Manager**, open **Windows Credentials**, delete anything mentioning
`github`, then try again.

**"I edited a page and now it looks broken"**
You probably deleted a `<` or a `>`. Undo with **Ctrl+Z** in Notepad until it
looks right. If it is beyond saving, the file is still on GitHub — open your
repository, click the file, and click **History** to see the earlier version.

**"I need to undo everything since the last publish"**
Open PowerShell in this folder and run `git restore .` — that throws away
unpublished edits and returns the files to the last published state.

**"Discord says the token is wrong"**
Tokens get reset, and sometimes only half of one gets pasted. Go to
discord.com/developers → your app → **Bot** → **Reset Token** → **Copy**, then
run `import-photos.cmd --setup` and paste the new one.

**"The bot cannot see one of my channels"**
Private channels have to let it in. Right-click the channel in Discord:
**Edit Channel → Permissions → Add members or roles**, add the bot, allow
**View Channel** and **Read Message History**. The other channels still import
normally in the meantime.

**"It says it found nothing, but I just posted photos"**
Almost always the message content setting. Go to discord.com/developers → your
app → **Bot** → **Privileged Gateway Intents** → turn on **MESSAGE CONTENT
INTENT** → **Save Changes**, then run it again.

**"It downloaded the same photos twice"**
The tool keeps a list of what it has already fetched in
`tools\.import-state.json`. If that file is deleted, it starts over. Delete the
duplicates out of `photo-inbox` before running `publish-photos.cmd`.

**"A photo published with the caption 'Car Ports' instead of a real name"**
That photo still had its camera filename. Post-and-forget photos come in named
`untitled-...`, and the tool tells you which ones. Rename them in `photo-inbox`
before publishing, or use the naming page that opens after an import.

**Something else**
Your files are safe. Every published version is kept on GitHub forever, and you
can always go back to an earlier one. Nothing you do by editing a page can
permanently break anything.

---

## Where things live

```
deckedoutliving-website/
│
├─ setup-github.cmd       run once, connects to GitHub
├─ import-photos.cmd      Discord ->  photo-inbox
├─ publish-photos.cmd     photos  ->  website
├─ publish-website.cmd    website ->  online
│
├─ photo-categories.json  your categories, and which channel feeds each one
├─ discord-bot.secret.json  your bot password - NEVER UPLOADED
│
├─ photo-inbox/           DROP JOB PHOTOS HERE, by category
├─ photo-originals/       your full-size originals (kept, not uploaded)
│
├─ docs/                  the website itself - this is what visitors see
│   ├─ index.html         home page
│   ├─ services/          one page per service
│   ├─ gallery.html       photo gallery
│   ├─ contact.html       the estimate form
│   ├─ reviews.json       customer reviews
│   └─ photos/            generated web photos - do not edit by hand
│
└─ tools/                 the scripts behind the .cmd files
```

The only folders you ever touch are **`photo-inbox`** and **`docs`**.
