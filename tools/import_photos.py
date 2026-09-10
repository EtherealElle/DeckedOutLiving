#!/usr/bin/env python3
"""
Decked Out Living - pull job photos out of Discord.

You photograph a job on your phone and post it to Discord, one job per
message. This fetches those photos and files them into photo-inbox/, sorted
by which channel they were posted in. Then you run publish-photos.cmd as
usual. It stops at the inbox on purpose - nothing reaches the website
without you looking at it first.

Because the filename becomes the caption on your website, and because you
usually post photos without typing anything, this also opens a small page in
your browser showing each job's photos with one box to name it. One name per
job, not one per photo.

Usage:
    python import_photos.py                 fetch, then open the naming page
    python import_photos.py --setup         connect to Discord, map channels
    python import_photos.py --dry-run       show what it would do, change nothing
    python import_photos.py --channels      list channels the bot can see
    python import_photos.py --no-page       skip the naming page
    python import_photos.py --yes           do not ask before downloading
    python import_photos.py --limit N       at most N photos per channel
    python import_photos.py --all           ignore the cursor, re-check everything
    python import_photos.py --reset         forget what has been imported
    python import_photos.py --self-test     check the naming rules, no network

This file uses the standard library only. There is nothing to pip install.
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from photo_common import (  # noqa: E402
    ADDRESS_RE, CATEGORY_ID_RE, READABLE,
    add_tags, humanise, numbered, read_category_config, slugify,
    write_category_config,
)

# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(ROOT, "photo-inbox")
SECRET_PATH = os.path.join(ROOT, "discord-bot.secret.json")
STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          ".import-state.json")

API = "https://discord.com/api/v10"
# Discord asks bots to identify themselves in this exact shape.
UA = "DiscordBot (https://github.com/EtherealElle/DeckedOutLiving, 1.0)"
TIMEOUT = 30
PAGE = 100                       # messages per request, Discord's maximum
MAX_BYTES = 40 * 1024 * 1024     # a phone photo is 2-8MB; 40 is a generous roof
MIN_EDGE = 400                   # smaller than this is a sticker, not a job photo
MAX_CAPTION = 60                 # characters, before slugifying

# View Channels (1024) + Read Message History (65536). Nothing else. The bot
# cannot post, cannot delete, cannot manage anything.
INVITE_PERMISSIONS = 66560

TEXT_CHANNEL_TYPES = {0, 5}      # 0 text, 5 announcement
FORUM_CHANNEL_TYPES = {15, 16}
CATEGORY_CHANNEL_TYPE = 4        # the collapsible heading in the channel list

GREEN, YELLOW, RED, DIM, OFF = "\033[92m", "\033[93m", "\033[91m", "\033[2m", "\033[0m"
if os.name == "nt" and not os.environ.get("WT_SESSION"):
    try:
        import colorama  # noqa: F401
        colorama.just_fix_windows_console()
    except Exception:
        GREEN = YELLOW = RED = DIM = OFF = ""


def say(msg="", colour=""):
    text = f"{colour}{msg}{OFF}" if colour else str(msg)
    try:
        print(text)
    except UnicodeEncodeError:
        # The Windows console is usually cp1252, and Discord messages are full
        # of emoji. Never let a decorative character crash a photo import.
        enc = sys.stdout.encoding or "ascii"
        print(text.encode(enc, "replace").decode(enc, "replace"))


def how_to_run(args=""):
    """How to start this tool, spelled out.

    "Run:  import-photos.cmd --setup" reads as though "run" were part of the
    command - and PowerShell will not start a script in the current folder
    without a .\\ in front of it either. So never print a bare command: say
    which folder, and give something that can be pasted as-is.
    """
    tail = (" " + args) if args else ""
    return ("  Double-click  import-photos.cmd  in this folder:\n"
            "      %s\n\n"
            "  Or paste this into PowerShell:\n"
            "      cd \"%s\"; .\\import-photos.cmd%s" % (ROOT, ROOT, tail))


class Stop(Exception):
    """Something the user has to fix. The message is already plain English."""


# --------------------------------------------------------------------------
# Keeping the token out of a public repository
# --------------------------------------------------------------------------
def assert_secret_is_ignored():
    """Refuse to write a token that git would then upload.

    The repository is public and publish-website.cmd runs 'git add -A'. One
    line in .gitignore is the only thing between the token and the internet,
    so prove it is doing its job before creating the file rather than after.
    """
    import subprocess
    rel = os.path.relpath(SECRET_PATH, ROOT).replace("\\", "/")
    try:
        r = subprocess.run(["git", "check-ignore", "-q", rel],
                           cwd=ROOT, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        if r.returncode == 0:
            return
        ignored = None
    except (OSError, subprocess.SubprocessError):
        # No git on the machine. Fall back to reading .gitignore ourselves.
        ignored = None
        try:
            with open(os.path.join(ROOT, ".gitignore"), "r", encoding="utf-8") as fh:
                text = fh.read()
            if "*.secret.json" in text or "discord-bot.secret.json" in text:
                return
        except OSError:
            pass

    del ignored
    raise Stop(
        "Your bot token would be uploaded to GitHub.\n\n"
        "  This website's repository is public, so that would let anyone read\n"
        "  every message in your Discord server. I have not saved anything.\n\n"
        "  To fix it, add this line to the file called .gitignore in\n"
        "  " + ROOT + ":\n\n"
        "      *.secret.json\n\n"
        "  Then run this again."
    )


def load_secret():
    if not os.path.isfile(SECRET_PATH):
        raise Stop(
            "Discord is not connected yet.\n\n" + how_to_run("--setup")
        )
    try:
        with open(SECRET_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (ValueError, OSError) as exc:
        raise Stop(
            "discord-bot.secret.json could not be read (%s).\n\n" % exc
            + how_to_run("--setup")
        )
    if not data.get("token"):
        raise Stop("discord-bot.secret.json has no token in it.\n\n"
                   + how_to_run("--setup"))
    return data


def save_secret(data):
    assert_secret_is_ignored()
    data = dict(data)
    data["_warning"] = (
        "SECRET - this is the password for your Discord bot. Never upload it, "
        "email it, or paste it into a chat. If it ever leaves this computer, go "
        "to discord.com/developers, open your app, click Bot, click Reset Token."
    )
    tmp = SECRET_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, SECRET_PATH)
    try:
        os.chmod(SECRET_PATH, 0o600)
    except OSError:
        pass


# --------------------------------------------------------------------------
# State - what has already been imported
# --------------------------------------------------------------------------
def load_state():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as fh:
            s = json.load(fh)
    except (ValueError, OSError):
        s = {}
    s.setdefault("version", 1)
    s.setdefault("channels", {})
    s.setdefault("attachments", {})
    s.setdefault("messages", {})
    s.setdefault("skippedChannels", [])
    return s


def save_state(state):
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, STATE_PATH)


def snowflake_for(dt):
    """The message id Discord would have handed out at this moment in time."""
    return str((int(dt.timestamp() * 1000) - 1420070400000) << 22)


# --------------------------------------------------------------------------
# Talking to Discord
# --------------------------------------------------------------------------
class Api:
    def __init__(self, token):
        self.token = token
        self.calls = 0

    def get(self, path, params=None, _channel=None):
        url = API + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={
            "Authorization": "Bot " + self.token,
            "User-Agent": UA,
            "Accept": "application/json",
        })

        for attempt in range(6):
            try:
                self.calls += 1
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    body = json.loads(r.read().decode("utf-8"))
                    # If we just used the last request in this window, wait it
                    # out now rather than earning a 429 on the next call.
                    if r.headers.get("X-RateLimit-Remaining") == "0":
                        try:
                            time.sleep(min(float(r.headers.get(
                                "X-RateLimit-Reset-After", 0)), 5))
                        except (TypeError, ValueError):
                            pass
                    return body

            except urllib.error.HTTPError as e:
                raw = e.read().decode("utf-8", "replace")
                try:
                    payload = json.loads(raw)
                except ValueError:
                    payload = {}

                if e.code == 429:
                    wait = payload.get("retry_after")
                    if wait is None:
                        try:
                            wait = float(e.headers.get("Retry-After", 1))
                        except (TypeError, ValueError):
                            wait = 1
                    if payload.get("global"):
                        say("    Discord is rate limiting this token globally - "
                            "waiting %.1fs" % wait, YELLOW)
                    time.sleep(float(wait) + 0.5)
                    continue

                if e.code == 401:
                    raise Stop(
                        "Discord did not accept your bot token.\n\n"
                        "  Usually that means the token was reset, or only part\n"
                        "  of it was pasted. Get a fresh one:\n\n"
                        "      discord.com/developers  ->  your app  ->  Bot\n"
                        "      ->  Reset Token  ->  Copy\n\n"
                        "  Then run:  import-photos.cmd --setup")

                if e.code == 403:
                    raise Forbidden(_channel)
                if e.code == 404:
                    raise NotFound(_channel)

                if 500 <= e.code < 600 and attempt < 5:
                    time.sleep(2 ** attempt)
                    continue

                raise Stop("Discord returned an error (%s).\n\n  %s"
                           % (e.code, payload.get("message", raw[:200])))

            except ssl.SSLCertVerificationError:
                raise Stop(
                    "Python on this computer cannot verify secure connections,\n"
                    "  so it cannot talk to Discord.\n\n"
                    "  Open PowerShell and run:\n\n"
                    "      pip install --upgrade certifi\n")

            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt < 5:
                    time.sleep(2 ** attempt)
                    continue
                raise Stop(
                    "Could not reach Discord.\n\n"
                    "  That is almost always your internet connection or their\n"
                    "  end. Nothing has been downloaded. Try again shortly.")

        raise Stop("Discord kept asking us to slow down. Try again in a few minutes.")


class Forbidden(Exception):
    def __init__(self, channel):
        self.channel = channel


class NotFound(Exception):
    def __init__(self, channel):
        self.channel = channel


def download(url, dest):
    """Fetch one attachment.

    Deliberately sends no Authorization header: cdn.discordapp.com is a
    different host and has no business seeing the bot token.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    tmp = dest + ".part"
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r, \
                open(tmp, "wb") as fh:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                fh.write(chunk)
        os.replace(tmp, dest)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise
    return os.path.getsize(dest)


# --------------------------------------------------------------------------
# Naming
# --------------------------------------------------------------------------
URL_RE = re.compile(r"https?://\S+")
MENTION_RE = re.compile(r"<[@#!&:][^>]*>")
MONEY_RE = re.compile(r"[$£€]\s?\d[\d,.]*")
PHONE_RE = re.compile(r"\b\d{3}[-. ]?\d{3}[-. ]?\d{4}\b")
MD_RE = re.compile(r"[*_~`|]{1,3}")
# Deliberately strict. A false positive here silently turns an ordinary photo
# into half of a before/after slider, and "the deck after the storm damage" is
# a far more likely sentence than a caption meaning the After side. So the word
# only counts when it is punctuated as a label: at the start followed by a
# colon or dash, alone on the line, at the very end after a separator, or
# written as a hashtag.
SIDE_RE = re.compile(
    r"^(?P<a>before|after)\s*[:\-\u2013]\s*"
    r"|^(?P<b>before|after)\s*$"
    r"|[\s\u2013-]+(?P<c>before|after)\s*$"
    r"|#(?P<d>before|after)\b",
    re.IGNORECASE)


def _side_of(match):
    for key in ("a", "b", "c", "d"):
        if match.group(key):
            return match.group(key).lower()
    return None
EMOJI_RE = re.compile(
    "[" "\U0001F000-\U0001FAFF" "\u2600-\u27BF" "\uFE00-\uFE0F" "\u200d" "]+")


def clean_text(content):
    """The first line of a Discord message, stripped of anything unpublishable."""
    line = (content or "").strip().splitlines()
    line = line[0] if line else ""
    line = URL_RE.sub(" ", line)
    line = MENTION_RE.sub(" ", line)
    line = EMOJI_RE.sub(" ", line)
    line = MONEY_RE.sub(" ", line)
    line = PHONE_RE.sub(" ", line)     # never publish a customer's number
    line = MD_RE.sub(" ", line)
    return re.sub(r"\s+", " ", line).strip()


def ascii_slug(text):
    """slugify(), but the result is always safe in a URL.

    These names end up in gallery.json as paths the browser fetches from
    GitHub Pages, so accents get folded (cafe, not café) and anything with no
    Latin letters left in it - Japanese, emoji-only - is treated as no text at
    all, which sends it down the untitled-* path.
    """
    import unicodedata
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    folded = folded.encode("ascii", "ignore").decode("ascii")
    # Test before slugify(), which substitutes the literal word "photo" for an
    # empty result and would otherwise look like a real caption.
    if not re.search(r"[A-Za-z0-9]", folded):
        return ""
    return slugify(folded)


def parse_message_text(content):
    """-> (caption_stem_or_empty, side_or_None)"""
    text = clean_text(content)
    side = None
    m = SIDE_RE.search(text)
    if m:
        side = _side_of(m)
        text = (text[:m.start()] + " " + text[m.end():]).strip()
        text = re.sub(r"^[\s:\-\u2013]+|[\s:\-\u2013]+$", "", text)
    if len(text) > MAX_CAPTION:
        cut = text[:MAX_CAPTION].rsplit(" ", 1)[0]
        text = cut or text[:MAX_CAPTION]
    return (ascii_slug(text) if text.strip() else ""), side


def job_stem(message, fallback_date):
    """The stem every photo in this message shares, plus its before/after side.

    With no text - the normal case here - fall back to untitled-<date>-<n>.
    That is deliberate rather than arbitrary: publish_photos.CAMERA_RE already
    matches 'untitled-...', so the existing machinery takes over for free. The
    caption degrades to the category name instead of to an ugly filename, and
    the existing 'rename it to something descriptive' warning fires.
    """
    stem, side = parse_message_text(message.get("content", ""))
    if stem:
        return stem, side, True
    ts = message.get("timestamp") or ""
    day = ts[:10].replace("-", "") or fallback_date
    return "untitled-%s-%s" % (day, message["id"][-4:]), side, False


def usable_attachments(message):
    """Only real photographs, biggest-first filtering with a reason for each drop."""
    keep, dropped = [], []
    for att in message.get("attachments", []):
        name = att.get("filename", "")
        if name.startswith("SPOILER_"):
            name = name[len("SPOILER_"):]
        ext = os.path.splitext(name)[1].lower()
        if att.get("ephemeral"):
            dropped.append((name, "temporary"))
        elif ext not in READABLE:
            dropped.append((name, "not a picture"))
        elif (att.get("size") or 0) > MAX_BYTES:
            dropped.append((name, "bigger than 40MB"))
        elif att.get("width") and att.get("height") and \
                max(att["width"], att["height"]) < MIN_EDGE:
            dropped.append((name, "too small to be a job photo"))
        else:
            keep.append((att, ext))
    return keep, dropped


def plan_message(message, category, state, fallback_date):
    """-> list of {attachment, filename, ...} for the photos we would download."""
    keep, dropped = usable_attachments(message)
    if not keep:
        return [], dropped

    remembered = state["messages"].get(message["id"], {})
    stem = remembered.get("jobName")
    side = remembered.get("side")
    named = bool(stem)
    if not stem:
        stem, side, named = job_stem(message, fallback_date)

    out = []
    for i, (att, ext) in enumerate(keep, start=1):
        out.append({
            "attachmentId": att["id"],
            "messageId": message["id"],
            "url": att["url"],          # the original upload, never proxy_url
            "size": att.get("size") or 0,
            "category": category,
            "filename": numbered(stem, i, side) + ext,
            "stem": stem,
            "side": side,
            "index": i,
            "count": len(keep),
            "named": named,
            "timestamp": message.get("timestamp", ""),
        })
    return out, dropped


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------
def fetch_messages(api, channel_id, after, limit_pages=200):
    """Every message after the cursor, oldest first."""
    out = []
    cursor = after or "0"
    for _ in range(limit_pages):
        batch = api.get("/channels/%s/messages" % channel_id,
                        {"limit": PAGE, "after": cursor}, _channel=channel_id)
        if not batch:
            break
        batch.sort(key=lambda m: int(m["id"]))
        out.extend(batch)
        cursor = batch[-1]["id"]
        if len(batch) < PAGE:
            break
        time.sleep(0.25)
    return out


def looks_like_intent_missing(messages):
    """Message Content Intent off looks exactly like an empty channel."""
    if len(messages) < 5:
        return False
    return all(not m.get("content") and not m.get("attachments")
               for m in messages)


# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------
PORTAL_STEPS = """
  Connecting Discord. This is a one-time job and takes about five minutes.
  Everything below happens in your web browser, not here.

    1. Go to      discord.com/developers/applications
       Click      New Application
       Name it    Decked Out Living Photos
       Click      Create

    2. On the left, click  Bot

    3. Scroll to  Privileged Gateway Intents
       Turn ON    MESSAGE CONTENT INTENT
       Click      Save Changes

       This one is not optional. Without it Discord hides your photos
       from the bot completely and this tool will find nothing at all.

    4. Click      Reset Token   ->   Yes, do it   ->   Copy
       Discord shows the token once and never again.
       Do not paste it into an email or a chat window - only here.
"""

INVITE_STEPS = """
    5. Open this link to add the bot to your server:

       %s

       Pick your server, then click Authorize.

    6. If your photo channels are PRIVATE, the bot still cannot see them.
       In Discord, right-click the channel category that holds them:
           Edit Channel  ->  Permissions  ->  Add members or roles
           add "%s", and allow:
               View Channel
               Read Message History
       Doing that once on the category covers every channel inside it.
"""


def ask(prompt, default=""):
    try:
        got = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise Stop("Cancelled. Nothing was changed.")
    return got or default


def invite_url(bot_id):
    return ("https://discord.com/oauth2/authorize?client_id=%s"
            "&scope=bot&permissions=%d" % (bot_id, INVITE_PERMISSIONS))


def cmd_setup():
    import getpass

    say()
    say("  DECKED OUT LIVING - connecting Discord", GREEN)
    say("  " + "-" * 46, DIM)
    say(PORTAL_STEPS)

    existing = {}
    if os.path.isfile(SECRET_PATH):
        try:
            existing = load_secret()
        except Stop:
            existing = {}

    # Prove .gitignore is doing its job BEFORE asking for a token, not after.
    assert_secret_is_ignored()

    api = me = None
    for attempt in range(3):
        if existing.get("token") and attempt == 0:
            keep = ask("  A token is already saved. Use it? [Y/n] ", "y")
            if keep.lower().startswith("y"):
                token = existing["token"]
            else:
                token = getpass.getpass("  Paste the bot token (it stays hidden): ").strip()
        else:
            token = getpass.getpass("  Paste the bot token (it stays hidden): ").strip()

        if not token:
            say("  Nothing pasted.", YELLOW)
            continue
        api = Api(token)
        try:
            me = api.get("/users/@me")
            break
        except Stop as exc:
            say()
            say("  " + str(exc), RED)
            say()
            existing = {}
            api = me = None
    if not me:
        raise Stop("Could not sign in to Discord. Nothing was saved.")

    bot_name = me.get("username", "the bot")
    say()
    say("  Signed in as %s." % bot_name, GREEN)

    # Which server?
    guilds = api.get("/users/@me/guilds")
    while not guilds:
        say()
        say("  The bot is not in any server yet.", YELLOW)
        say(INVITE_STEPS % (invite_url(me["id"]), bot_name))
        ask("  Press Enter once you have authorized it. ")
        guilds = api.get("/users/@me/guilds")

    if len(guilds) == 1:
        guild = guilds[0]
    else:
        say()
        say("  Which server are your job photos in?")
        for i, g in enumerate(guilds, 1):
            say("    %2d  %s" % (i, g["name"]))
        while True:
            pick = ask("  Number: ")
            if pick.isdigit() and 1 <= int(pick) <= len(guilds):
                guild = guilds[int(pick) - 1]
                break
            say("  Type one of the numbers above.", YELLOW)

    say()
    say("  Server: %s" % guild["name"], GREEN)

    # Which channels?
    try:
        channels = api.get("/guilds/%s/channels" % guild["id"])
    except Forbidden:
        raise Stop("The bot cannot list channels in %s.\n\n"
                   "  Re-invite it with this link:\n\n      %s"
                   % (guild["name"], invite_url(me["id"])))

    by_id = {c["id"]: c for c in channels}
    all_text = sorted([c for c in channels if c.get("type") in TEXT_CHANNEL_TYPES],
                      key=lambda c: (c.get("position", 0), c.get("name", "")))

    if not all_text:
        raise Stop("The bot cannot see any text channels in %s.\n\n"
                   "  If your channels are private, it needs to be added to\n"
                   "  them - see step 6 above." % guild["name"])

    records, _notes, meta = read_category_config(ROOT)
    state = load_state()
    mapped = {r.get("discordChannelId"): r for r in records
              if r.get("discordChannelId")}

    # --- which Discord category holds the job photos? --------------------
    # A Discord "category" is the collapsible group in the channel sidebar.
    # Using one keeps #general and friends out of this entirely, and makes the
    # rule simple: the channels inside it ARE the photo-inbox folders.
    groups = sorted([c for c in channels if c.get("type") == CATEGORY_CHANNEL_TYPE],
                    key=lambda c: (c.get("position", 0), c.get("name", "")))
    chosen = None
    if meta.get("discordCategoryId"):
        chosen = by_id.get(meta["discordCategoryId"])
    if chosen is None:
        for g in groups:
            if slugify(g.get("name", "")) in ("pics", "photos", "job-photos"):
                chosen = g
                break
    if chosen is None and groups:
        say()
        say("  Which group of channels holds your job photos?")
        say("  (These are the headings in your Discord channel list.)", DIM)
        say()
        for i, g in enumerate(groups, 1):
            kids = [c["name"] for c in all_text if c.get("parent_id") == g["id"]]
            say("    %2d  %-20s %s" % (i, g["name"],
                                       ", ".join("#" + k for k in kids[:4]) +
                                       (" ..." if len(kids) > 4 else "")))
        say("     0  none - let me pick channels one at a time")
        say()
        while True:
            pick = ask("  Number: ")
            if pick == "0":
                break
            if pick.isdigit() and 1 <= int(pick) <= len(groups):
                chosen = groups[int(pick) - 1]
                break
            say("  Type one of the numbers above.", YELLOW)

    if chosen is not None:
        meta = {"discordCategoryId": chosen["id"],
                "discordCategoryName": chosen.get("name", "")}
        text = [c for c in all_text if c.get("parent_id") == chosen["id"]]
        if not text:
            raise Stop(
                "The \"%s\" group has no channels the bot can see.\n\n"
                "  If the channels inside it are private, the bot has to be let\n"
                "  in. In Discord, right-click \"%s\":\n"
                "      Edit Category  ->  Permissions  ->  Add members or roles\n"
                "      add \"%s\", allow View Channel and Read Message History.\n"
                % (chosen.get("name"), chosen.get("name"), bot_name))
    else:
        meta = {}
        text = all_text

    forums = [c for c in channels if c.get("type") in FORUM_CHANNEL_TYPES
              and (chosen is None or c.get("parent_id") == chosen["id"])]

    skipped = set(state.get("skippedChannels", []))
    if chosen is not None:
        # The group defines the list, so an old skip must not silently hide a
        # channel the owner has since put in it.
        skipped -= {c["id"] for c in text}

    say()
    if chosen is not None:
        say("  Channels in \"%s\" - these become your categories:"
            % chosen.get("name"), GREEN)
    else:
        say("  Channels the bot can see in %s:" % guild["name"])
    say()
    for c in text:
        if c["id"] in mapped:
            note = "-> %s" % mapped[c["id"]]["label"]
            colour = GREEN
        elif c["id"] in skipped:
            note = "(skipped)"
            colour = DIM
        else:
            note = "NEW"
            colour = YELLOW
        say("    #%-24s %s" % (c["name"], note), colour)

    if forums:
        say()
        say("  These are Forum channels, which this tool cannot read yet:", YELLOW)
        for c in forums:
            say("    #%s" % c["name"], YELLOW)
        say("  If your photos live in one of those, say so and it can be added.",
            YELLOW)

    # --- channels no longer in the group stop feeding their category ------
    if chosen is not None:
        live = {c["id"] for c in text}
        for r in records:
            cid = r.get("discordChannelId")
            if cid and cid not in live:
                say()
                say("  #%s is no longer in \"%s\", so it will stop importing."
                    % (r.get("discordChannelName") or cid, chosen.get("name")),
                    YELLOW)
                say("    Your published %s photos are untouched and stay on the "
                    "website." % r["label"], DIM)
                r["discordChannelId"] = None
                r["discordChannelName"] = None
        mapped = {r.get("discordChannelId"): r for r in records
                  if r.get("discordChannelId")}

    # --- map whatever is not mapped yet -----------------------------------
    unmapped = [c for c in text if c["id"] not in mapped and c["id"] not in skipped]

    def suggestion(c):
        s = slugify(c["name"])
        return s if CATEGORY_ID_RE.match(s) else "channel-" + c["id"][-6:]

    # Picking the group already answered "which channels". It did NOT answer
    # "is #decks the same thing as New Decks" - and getting that wrong quietly
    # creates a second category next to one that already has a service page.
    # So a channel whose name matches an existing category is taken silently,
    # and only the others are worth a question.
    existing_now = {r["id"] for r in records}
    exact = [c for c in unmapped if suggestion(c) in existing_now]
    ambiguous = [c for c in unmapped if suggestion(c) not in existing_now]
    accept_all = False

    # Exact matches go first. Otherwise an ambiguous channel answered earlier in
    # the list could claim the category that an exact match was about to fill,
    # and the exact match would silently end up unlinked.
    if chosen is not None:
        unmapped = exact + ambiguous

    if unmapped and (chosen is None or ambiguous):
        say()
        if chosen is not None and ambiguous:
            say("  These channels do not match a category you already have:")
        else:
            say("  Now, which of these hold job photos?")
        say("  For each one:  Enter = make it a category,  s = skip it,", DIM)
        say("                 a number = file it into a category you already have,", DIM)
        say("                 A = accept every suggestion below.", DIM)

    for c in unmapped:
        suggested_id = suggestion(c)
        existing_ids = [r["id"] for r in records]

        # a channel named exactly like an existing category needs no question
        auto = accept_all or (chosen is not None and suggested_id in existing_ids)

        while True:
            if auto:
                answer = ""
            else:
                say()
                say("    #%s" % c["name"], YELLOW)
                for i, r in enumerate(records, 1):
                    taken = r.get("discordChannelName")
                    say("       %2d  %-30s %s"
                        % (i, r["label"],
                           ("already fed by #" + taken) if taken else ""), DIM)
                answer = ask("    Enter=new category \"%s\"  /  s=skip  /  number  /  A: "
                             % humanise(suggested_id))

            # One category cannot be fed by two channels - the second would
            # quietly unlink the first and nothing would say so.
            if answer.isdigit() and 1 <= int(answer) <= len(records):
                target = records[int(answer) - 1]
                if target.get("discordChannelId") not in (None, c["id"]):
                    say("    \"%s\" already takes its photos from #%s. Pick "
                        "another, or press Enter for a new category."
                        % (target["label"], target["discordChannelName"]), YELLOW)
                    continue
            break

        if answer.lower() == "a":
            accept_all = True
            answer = ""
        if answer.lower() == "s":
            skipped.add(c["id"])
            continue
        if answer.isdigit() and 1 <= int(answer) <= len(records):
            target = records[int(answer) - 1]
            target["discordChannelId"] = c["id"]
            target["discordChannelName"] = c["name"]
            continue

        if suggested_id in existing_ids:
            target = records[existing_ids.index(suggested_id)]
            target["discordChannelId"] = c["id"]
            target["discordChannelName"] = c["name"]
        else:
            records.append({
                "id": suggested_id,
                "label": humanise(suggested_id),
                "discordChannelId": c["id"],
                "discordChannelName": c["name"],
                "isNew": True,
            })

    # How far back?
    since = None
    if not state.get("channels"):
        say()
        say("  How far back should the first import go?")
        say("     a  everything ever posted")
        say("     b  the last 90 days")
        say("     c  from today onward")
        pick = ask("  a / b / c  [b]: ", "b").lower()
        if pick.startswith("b"):
            since = snowflake_for(datetime.now(timezone.utc) - timedelta(days=90))
        elif pick.startswith("c"):
            since = snowflake_for(datetime.now(timezone.utc))

    # Confirm.
    linked = [r for r in records if r.get("discordChannelId")]
    say()
    say("  " + "-" * 46, DIM)
    say("  This is what will be saved:")
    say()
    for r in records:
        ch = r.get("discordChannelName")
        line = "    %-28s %s" % (r["label"],
                                 ("#" + ch) if ch else "(no Discord channel)")
        say(line, GREEN if ch else DIM)
    if not linked:
        say()
        say("  Nothing is linked to Discord, so there is nothing to import.", YELLOW)
    if meta.get("discordCategoryName"):
        say()
        say("  From now on the channels inside \"%s\" decide your categories."
            % meta["discordCategoryName"], DIM)
        say("  Add or remove a channel there, run this again, and it follows.", DIM)

    say()
    if not ask("  Save this? [y/N] ", "n").lower().startswith("y"):
        raise Stop("Nothing was saved.")

    new_cats = [r for r in records if r.pop("isNew", False)]
    write_category_config(ROOT, records, meta)

    # Make the folders now rather than at the first download, so the promise
    # that these channels are the photo-inbox folders is visible immediately.
    for r in records:
        try:
            os.makedirs(os.path.join(INBOX, r["id"]), exist_ok=True)
        except OSError:
            pass

    state["skippedChannels"] = sorted(skipped)
    for r in linked:
        entry = state["channels"].setdefault(r["discordChannelId"], {})
        entry["categoryId"] = r["id"]
        if since is not None and "lastMessageId" not in entry:
            entry["lastMessageId"] = since
    save_state(state)

    save_secret({"token": api.token, "guildId": guild["id"], "botName": bot_name})

    say()
    say("  Saved.", GREEN)
    for r in new_cats:
        say()
        say("  New category \"%s\" created from #%s." % (r["label"],
                                                        r["discordChannelName"]), GREEN)
        say("  Its photos will appear in the gallery and get their own filter", DIM)
        say("  button automatically - nothing for you to do.", DIM)
        say("  There is NO service page for it and the menu does not list it.", YELLOW)
        say("  If you want one, say so - it needs real writing, not a template.", YELLOW)
    say()
    say("  Your token is in discord-bot.secret.json and is NOT uploaded.", DIM)
    say("  If it ever leaks: discord.com/developers -> Bot -> Reset Token.", DIM)
    say()
    say("  Now import your photos:", GREEN)
    say(how_to_run(), GREEN)
    say()
    return 0


def cmd_channels():
    secret = load_secret()
    api = Api(secret["token"])
    me = api.get("/users/@me")
    guilds = api.get("/users/@me/guilds")
    records, _notes, meta = read_category_config(ROOT)
    mapped = {r.get("discordChannelId"): r for r in records if r.get("discordChannelId")}
    source = meta.get("discordCategoryId")
    say()
    say("  Signed in as %s." % me.get("username"), GREEN)
    if meta.get("discordCategoryName"):
        say("  Your categories come from the \"%s\" group."
            % meta["discordCategoryName"], DIM)
    for g in guilds:
        say()
        say("  %s" % g["name"], GREEN)
        try:
            channels = api.get("/guilds/%s/channels" % g["id"])
        except (Forbidden, NotFound):
            say("    (cannot list channels here)", YELLOW)
            continue
        by_id = {c["id"]: c for c in channels}
        # group the listing the way Discord shows it, so "which group is it in"
        # is answerable at a glance
        for c in sorted(channels, key=lambda c: (c.get("position", 0),)):
            if c.get("type") == CATEGORY_CHANNEL_TYPE:
                tag = "   <- your photo categories" if c["id"] == source else ""
                say("    %s%s" % (c.get("name", "").upper(), tag),
                    GREEN if c["id"] == source else DIM)
                continue
            parent = by_id.get(c.get("parent_id") or "", {})
            inside = (source is None) or (c.get("parent_id") == source)
            where = "      " if parent else "    "
            if c.get("type") in FORUM_CHANNEL_TYPES:
                say("%s#%-22s forum channel, not supported" % (where, c["name"]),
                    YELLOW)
            elif c.get("type") in TEXT_CHANNEL_TYPES:
                r = mapped.get(c["id"])
                if r:
                    note, colour = "-> " + r["label"], GREEN
                elif not inside:
                    note, colour = "(not in your photo group)", DIM
                else:
                    note, colour = "not linked - run --setup", YELLOW
                say("%s#%-22s %s" % (where, c["name"], note), colour)
    say()
    return 0


# --------------------------------------------------------------------------
# The naming page
# --------------------------------------------------------------------------
PAGE_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>Name your jobs</title>
<style>
 :root{--ink:#343434;--green:#3F7A22;--line:#e3e3e3}
 *{box-sizing:border-box}
 body{margin:0;font:16px/1.5 system-ui,Segoe UI,sans-serif;color:var(--ink);background:#faf9f7}
 header{background:#343434;color:#fff;padding:18px 24px;position:sticky;top:0;z-index:5;
        display:flex;align-items:center;gap:16px;flex-wrap:wrap}
 header h1{font-size:18px;margin:0;font-weight:600}
 header p{margin:0;font-size:14px;opacity:.8}
 .save{margin-left:auto;background:#7EDA53;color:#1d1d1d;border:0;border-radius:6px;
       padding:10px 22px;font-size:15px;font-weight:600;cursor:pointer}
 .save:disabled{opacity:.5;cursor:default}
 main{padding:24px;max-width:1100px;margin:0 auto}
 .job{background:#fff;border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:18px}
 .job h2{font-size:14px;margin:0 0 12px;font-weight:600;color:#666;text-transform:uppercase;
         letter-spacing:.04em}
 .shots{display:flex;gap:8px;overflow-x:auto;padding-bottom:8px}
 .shots img{height:150px;width:auto;border-radius:6px;border:1px solid var(--line);flex:0 0 auto}
 .shots .noimg{height:150px;width:150px;border:1px dashed #bbb;border-radius:6px;flex:0 0 auto;
   display:flex;align-items:center;justify-content:center;font-size:12px;color:#888;padding:8px;
   text-align:center}
 label{display:block;font-size:13px;color:#666;margin:14px 0 4px}
 input[type=text]{width:100%;padding:10px 12px;font-size:16px;border:1px solid #bbb;border-radius:6px}
 input[type=text]:focus{outline:2px solid var(--green);border-color:var(--green)}
 .row{display:flex;gap:20px;align-items:center;flex-wrap:wrap;margin-top:10px}
 .row label{margin:0;font-size:14px;color:var(--ink);display:flex;align-items:center;gap:6px}
 .preview{font:13px ui-monospace,Consolas,monospace;color:#555;margin-top:10px;word-break:break-all}
 .warn{color:#b3261e;font-size:13px;margin-top:8px;display:none}
 .warn.on{display:block}
 footer{padding:0 24px 60px;max-width:1100px;margin:0 auto;color:#666;font-size:14px}
 .cats{margin-top:14px;padding-top:12px;border-top:1px solid #eee}
 .cats>span{display:block;font-size:12px;color:#666;text-transform:uppercase;
   letter-spacing:.08em;margin-bottom:8px}
 .cats label{display:inline-flex;align-items:center;gap:6px;margin:0 14px 8px 0;font-size:14px}
 .done{padding:60px 24px;text-align:center}
 .done h2{color:var(--green)}
</style></head><body>
<header>
  <div><h1>Name your jobs</h1>
  <p>What you type becomes the caption on your website. No customer names or addresses.</p></div>
  <button class="save" id="save">Save names</button>
</header>
<main id="main"></main>
<footer id="foot"></footer>
<script>
const JOBS = __JOBS__;
const CATS = __CATS__;
const ADDRESS = /\b\d{1,6}\s*[-_ ]?(st|street|rd|road|dr|drive|ln|lane|ave|avenue|ct|court|way|blvd|hwy|circle|cir|trail|pkwy)\b/i;
function slug(s){return s.toLowerCase().replace(/[^\w\s-]/g,"").replace(/[\s_]+/g,"-")
  .replace(/^-+|-+$/g,"").replace(/-{2,}/g,"-");}
const main=document.getElementById("main");
JOBS.forEach((job,idx)=>{
  const el=document.createElement("section"); el.className="job";
  const shots=job.files.map(f=>f.viewable
    ? '<img src="/photo/'+encodeURIComponent(job.category)+'/'+encodeURIComponent(f.filename)+'" alt="">'
    : '<div class="noimg">'+f.filename+'<br>(no preview)</div>').join("");
  el.innerHTML=
    '<h2>Job '+(idx+1)+' of '+JOBS.length+' &middot; #'+job.channel+' &middot; '+job.when+
    ' &middot; '+job.files.length+' photo'+(job.files.length===1?"":"s")+'</h2>'+
    '<div class="shots">'+shots+'</div>'+
    '<label for="n'+idx+'">Name this job</label>'+
    '<input type="text" id="n'+idx+'" value="'+job.suggested+'" placeholder="cedar deck rebuild with pergola">'+
    '<div class="row">'+
      '<label><input type="radio" name="s'+idx+'" value="before"'+(job.side==="before"?" checked":"")+'> before photos</label>'+
      '<label><input type="radio" name="s'+idx+'" value="after"'+(job.side==="after"?" checked":"")+'> after photos</label>'+
      '<label><input type="radio" name="s'+idx+'" value=""'+(job.side?"":" checked")+'> neither</label>'+
    '</div>'+
    '<div class="cats"><span>Also show under</span>'+
      CATS.filter(c=>c.id!==job.category).map(c=>
        '<label><input type="checkbox" name="c'+idx+'" value="'+c.id+'"'+
        ((job.extra||[]).indexOf(c.id)>=0?" checked":"")+'> '+c.label+'</label>').join("")+
    '</div>'+
    '<div class="preview" id="p'+idx+'"></div>'+
    '<div class="warn" id="w'+idx+'">That looks like a street address. It would be published as the caption.</div>';
  main.appendChild(el);
  const inp=el.querySelector("input[type=text]");
  const upd=()=>{
    const base=slug(inp.value)||job.fallback;
    const side=el.querySelector('input[name="s'+idx+'"]:checked').value;
    const extra=[...el.querySelectorAll('input[name="c'+idx+'"]:checked')].map(c=>c.value);
    const tags=extra.map(t=>"+"+t).join("");
    const names=job.files.map((f,i)=>(i?base+"-"+(i+1):base)+(side?"-"+side:"")+tags+f.ext);
    document.getElementById("p"+idx).textContent=names.join("   ");
    document.getElementById("w"+idx).classList.toggle("on",ADDRESS.test(inp.value));
  };
  inp.addEventListener("input",upd);
  el.querySelectorAll("input[type=radio],input[type=checkbox]")
    .forEach(r=>r.addEventListener("change",upd));
  upd();
});
document.getElementById("foot").textContent=
  "Leave a name empty and those photos keep their untitled name. Tick “also show under” "+
  "for a job that belongs in more than one place - a deck with a pergola over it is both.";
document.getElementById("save").addEventListener("click",async e=>{
  e.target.disabled=true; e.target.textContent="Saving...";
  const payload=JOBS.map((job,idx)=>({
    messageId:job.messageId,
    name:document.getElementById("n"+idx).value,
    side:document.querySelector('input[name="s'+idx+'"]:checked').value,
    extra:[...document.querySelectorAll('input[name="c'+idx+'"]:checked')].map(c=>c.value)}));
  const r=await fetch("/save",{method:"POST",headers:{"Content-Type":"application/json"},
                              body:JSON.stringify(payload)});
  const res=await r.json();
  document.body.innerHTML='<div class="done"><h2>Saved.</h2><p>'+res.renamed+
    ' photo(s) renamed in photo-inbox.</p><p>You can close this tab, then run '+
    '<b>publish-photos.cmd</b>.</p></div>';
});
</script></body></html>
"""


def naming_page(jobs, categories, port=0):
    """Show every job with its photos and take one name for each."""
    import http.server
    import threading
    import webbrowser

    result = {"renamed": 0}
    payload = []
    for j in jobs:
        payload.append({
            "messageId": j["messageId"],
            "category": j["category"],
            "channel": j["channel"],
            "when": j["when"],
            "side": j["side"] or "",
            "suggested": "" if not j["named"] else j["stem"].replace("-", " "),
            "fallback": j["stem"],
            "extra": j.get("extra") or [],
            "files": [{"filename": f["filename"],
                       "ext": os.path.splitext(f["filename"])[1],
                       "viewable": os.path.splitext(f["filename"])[1].lower()
                       not in (".heic", ".heif", ".tif", ".tiff")}
                      for f in j["files"]],
        })
    html = (PAGE_HTML
            .replace("__JOBS__", json.dumps(payload))
            .replace("__CATS__", json.dumps(categories))
            .encode("utf-8"))
    by_message = {j["messageId"]: j for j in jobs}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urllib.parse.urlparse(self.path).path
            if path == "/":
                return self._send(200, html, "text/html; charset=utf-8")
            if path.startswith("/photo/"):
                parts = [urllib.parse.unquote(p) for p in path.split("/")[2:]]
                if len(parts) != 2:
                    return self._send(404, b"no", "text/plain")
                cat, name = parts
                # Never let a crafted path walk out of the inbox.
                if os.path.basename(name) != name or os.path.basename(cat) != cat:
                    return self._send(404, b"no", "text/plain")
                p = os.path.join(INBOX, cat, name)
                if not os.path.isfile(p):
                    return self._send(404, b"no", "text/plain")
                with open(p, "rb") as fh:
                    return self._send(200, fh.read(), "image/jpeg")
            return self._send(404, b"no", "text/plain")

        def do_POST(self):
            if urllib.parse.urlparse(self.path).path != "/save":
                return self._send(404, b"no", "text/plain")
            n = int(self.headers.get("Content-Length", 0))
            try:
                items = json.loads(self.rfile.read(n).decode("utf-8"))
            except ValueError:
                return self._send(400, b'{"renamed":0}', "application/json")
            result["renamed"] = apply_names(items, by_message)
            self._send(200, json.dumps(result).encode(), "application/json")
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    url = "http://127.0.0.1:%d/" % server.server_address[1]
    say()
    say("  Opening the naming page in your browser:", GREEN)
    say("      %s" % url)
    say("  Name each job there, then click Save names.", DIM)
    say("  (Close this window if you would rather rename the files yourself.)", DIM)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        say()
        say("  Stopped. The photos are in photo-inbox with their current names.",
            YELLOW)
    server.server_close()
    return result["renamed"]


def apply_names(items, by_message):
    """Rename the downloaded files to the names typed on the page."""
    state = load_state()
    renamed = 0
    for item in items:
        job = by_message.get(item.get("messageId"))
        if not job:
            continue
        typed = (item.get("name") or "").strip()
        if not typed:
            continue
        side = item.get("side") or None
        stem = slugify(typed)
        # Categories ticked on the page ride on the end of the filename as
        # "+tag". The job's own category comes from the folder, so it is never
        # written as a tag.
        extra = [t for t in (item.get("extra") or [])
                 if t and t != job["category"]]
        folder = os.path.join(INBOX, job["category"])
        for i, f in enumerate(job["files"], start=1):
            ext = os.path.splitext(f["filename"])[1]
            src = os.path.join(folder, f["filename"])
            if not os.path.isfile(src):
                continue
            target = add_tags(numbered(stem, i, side), extra) + ext
            dest = os.path.join(folder, target)
            bump = 2
            while os.path.exists(dest) and os.path.abspath(dest) != os.path.abspath(src):
                target = add_tags(numbered(stem + "-" + str(bump), i, side), extra) + ext
                dest = os.path.join(folder, target)
                bump += 1
            if os.path.abspath(dest) == os.path.abspath(src):
                continue
            os.replace(src, dest)
            state["attachments"][f["attachmentId"]] = "%s/%s" % (job["category"], target)
            f["filename"] = target
            renamed += 1
        state["messages"][job["messageId"]] = {
            "jobName": stem, "side": side, "categoryId": job["category"],
            "extra": extra}
    save_state(state)
    return renamed


# --------------------------------------------------------------------------
# Self test - the naming rules, with no network and no Pillow
# --------------------------------------------------------------------------
def cmd_self_test():
    from photo_common import PAIR_RE
    fails = []

    def check(label, got, want):
        if got != want:
            fails.append("%s\n      got:  %r\n      want: %r" % (label, got, want))

    def msg(content, n=1, mid="1408765432109876543", ts="2026-07-14T12:19:04+00:00"):
        return {"id": mid, "content": content, "timestamp": ts,
                "attachments": [{"id": "%s%03d" % (mid, i), "filename": "IMG_%d.jpg" % i,
                                 "size": 2000000, "width": 3000, "height": 4000,
                                 "url": "https://cdn.example/%d.jpg" % i}
                                for i in range(1, n + 1)]}

    def names(content, n=1):
        plan, _ = plan_message(msg(content, n), "new-decks",
                               load_state_blank(), "20260714")
        return [p["filename"] for p in plan]

    check("plain text", names("Cedar deck rebuild"), ["cedar-deck-rebuild.jpg"])
    check("three photos", names("Cedar deck rebuild", 3),
          ["cedar-deck-rebuild.jpg", "cedar-deck-rebuild-2.jpg",
           "cedar-deck-rebuild-3.jpg"])
    check("before prefix", names("Before: cedar deck rebuild", 2),
          ["cedar-deck-rebuild-before.jpg", "cedar-deck-rebuild-2-before.jpg"])
    check("after dash", names("After - cedar deck rebuild"),
          ["cedar-deck-rebuild-after.jpg"])
    check("no text", names(""), ["untitled-20260714-6543.jpg"])
    check("emoji only", names("\U0001F44D\U0001F44D"), ["untitled-20260714-6543.jpg"])
    check("phone number stripped", names("Deck rebuild 770-555-0134"),
          ["deck-rebuild.jpg"])
    check("money stripped", names("Deck rebuild $4,200"), ["deck-rebuild.jpg"])
    check("url stripped", names("Deck rebuild https://x.co/a"), ["deck-rebuild.jpg"])
    check("mention stripped", names("Deck rebuild <@1234567890>"), ["deck-rebuild.jpg"])
    check("first line only", names("Cedar deck rebuild\nsecond line here"),
          ["cedar-deck-rebuild.jpg"])
    check("after in a sentence is not a side",
          names("The deck after the storm damage"),
          ["the-deck-after-the-storm-damage.jpg"])
    check("long text truncated",
          names("A very long description of the job " * 6),
          ["a-very-long-description-of-the-job-a-very-long-description.jpg"])
    check("non latin", names("デッキ"), ["untitled-20260714-6543.jpg"])
    check("trailing side", names("Cedar deck rebuild - after"),
          ["cedar-deck-rebuild-after.jpg"])
    check("hashtag side", names("Cedar deck rebuild #before"),
          ["cedar-deck-rebuild-before.jpg"])
    check("side alone", names("before", 2),
          ["untitled-20260714-6543-before.jpg", "untitled-20260714-6543-2-before.jpg"])
    check("before in a sentence is not a side",
          names("Rebuilt the rail before the rain came"),
          ["rebuilt-the-rail-before-the-rain-came.jpg"])

    # Ten photos in a before message must pair one-for-one with ten afters.
    b = names("Before: big rebuild", 10)
    a = names("After: big rebuild", 10)
    for x, y in zip(b, a):
        mb = PAIR_RE.match(os.path.splitext(x)[0])
        ma = PAIR_RE.match(os.path.splitext(y)[0])
        if not mb or not ma:
            fails.append("pair regex did not match %s / %s" % (x, y))
        elif mb.group("stem") != ma.group("stem"):
            fails.append("pair stems differ: %s vs %s" % (mb.group("stem"),
                                                          ma.group("stem")))
        elif (mb.group("side"), ma.group("side")) != ("before", "after"):
            fails.append("sides wrong for %s / %s" % (x, y))

    if ADDRESS_RE.search("412-oak-ridge-dr-rebuild") is None:
        fails.append("address detector missed 412-oak-ridge-dr-rebuild")

    say()
    if fails:
        say("  %d naming test(s) FAILED:" % len(fails), RED)
        for f in fails:
            say("    - " + f, RED)
        say()
        return 1
    say("  All naming tests passed.", GREEN)
    say()
    return 0


def load_state_blank():
    return {"version": 1, "channels": {}, "attachments": {}, "messages": {},
            "skippedChannels": []}


# --------------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    flags = set(a for a in args if a.startswith("--"))

    if "--self-test" in flags:
        return cmd_self_test()
    if "--setup" in flags:
        return cmd_setup()
    if "--channels" in flags:
        return cmd_channels()

    dry = "--dry-run" in flags
    assume_yes = "--yes" in flags
    no_page = "--no-page" in flags
    redo_all = "--all" in flags
    limit = None
    for i, a in enumerate(args):
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])

    if "--reset" in flags:
        if not ask("  Forget everything already imported? Next run will "
                   "re-download it all. [y/N] ", "n").lower().startswith("y"):
            say("  Left alone.", DIM)
            return 0
        if os.path.exists(STATE_PATH):
            os.remove(STATE_PATH)
        say("  Done - the import history has been cleared.", GREEN)
        return 0

    say()
    say("  DECKED OUT LIVING - importing photos from Discord", GREEN)
    say("  " + "-" * 50, DIM)

    secret = load_secret()
    api = Api(secret["token"])
    state = load_state()
    records, notes, meta = read_category_config(ROOT)
    for n in notes:
        say("  " + n, YELLOW)

    linked = [r for r in records if r.get("discordChannelId")]
    if not linked:
        raise Stop("No Discord channels are linked to a category yet.\n\n"
                   + how_to_run("--setup"))

    # A channel added to the photo group since last time should not go
    # unnoticed, but creating a category is a decision, so ask rather than act.
    new_channels = []
    if meta.get("discordCategoryId") and secret.get("guildId"):
        try:
            known = {r.get("discordChannelId") for r in records}
            known |= set(state.get("skippedChannels", []))
            for c in api.get("/guilds/%s/channels" % secret["guildId"]):
                if (c.get("type") in TEXT_CHANNEL_TYPES
                        and c.get("parent_id") == meta["discordCategoryId"]
                        and c["id"] not in known):
                    new_channels.append(c["name"])
        except (Forbidden, NotFound, Stop):
            pass

    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    jobs, dropped_total, config_changed = [], [], False
    intent_suspect = False

    say()
    for rec in linked:
        cid = rec["discordChannelId"]
        chan_state = state["channels"].setdefault(cid, {})
        chan_state["categoryId"] = rec["id"]
        after = None if redo_all else chan_state.get("lastMessageId")

        try:
            messages = fetch_messages(api, cid, after)
        except Forbidden:
            say("  #%s - the bot cannot see this channel." % rec["discordChannelName"],
                YELLOW)
            say("    In Discord: right-click the channel  ->  Edit Channel  ->", DIM)
            say("    Permissions  ->  Add members or roles  ->  add \"%s\"  ->"
                % secret.get("botName", "the bot"), DIM)
            say("    allow View Channel and Read Message History.", DIM)
            continue
        except NotFound:
            say("  #%s no longer exists. Unlinking it." % rec["discordChannelName"],
                YELLOW)
            say("    Your published %s photos are untouched and still on the site."
                % rec["label"], DIM)
            rec["discordChannelId"] = None
            rec["discordChannelName"] = None
            config_changed = True
            continue

        if looks_like_intent_missing(messages):
            intent_suspect = True

        found = 0
        for m in messages:
            plan, dropped = plan_message(m, rec["id"], state, today)
            dropped_total.extend(dropped)
            plan = [p for p in plan if p["attachmentId"] not in state["attachments"]]
            if not plan:
                continue
            if limit is not None and found >= limit:
                break
            jobs.append({
                "messageId": m["id"],
                "category": rec["id"],
                "channel": rec["discordChannelName"] or rec["id"],
                "when": (m.get("timestamp") or "")[:10],
                "stem": plan[0]["stem"],
                "side": plan[0]["side"],
                "named": plan[0]["named"],
                "files": plan,
            })
            found += len(plan)

        n_new = sum(len(j["files"]) for j in jobs if j["category"] == rec["id"])
        say("  #%-22s %s" % (rec["discordChannelName"],
                             ("%d new photo%s" % (n_new, "" if n_new == 1 else "s"))
                             if n_new else "nothing new"),
            GREEN if n_new else DIM)
        if messages:
            chan_state["pendingCursor"] = messages[-1]["id"]

    if config_changed:
        write_category_config(ROOT, records, meta)

    if intent_suspect and not jobs:
        raise Stop(
            "Discord is hiding message text and photos from the bot.\n\n"
            "  Turn the setting on:\n"
            "      discord.com/developers  ->  your app  ->  Bot\n"
            "      ->  Privileged Gateway Intents\n"
            "      ->  MESSAGE CONTENT INTENT  ->  on  ->  Save Changes\n\n"
            "  Then run this again.")

    if not jobs:
        say()
        say("  Nothing new to import.", GREEN)
        for cid, cs in state["channels"].items():
            if cs.get("pendingCursor"):
                cs["lastMessageId"] = cs.pop("pendingCursor")
        if not dry:
            save_state(state)
        report_new_channels(new_channels, meta)
        say()
        return 0

    # Show the plan.
    total_files = sum(len(j["files"]) for j in jobs)
    total_bytes = sum(f["size"] for j in jobs for f in j["files"])
    say()
    say("  " + "-" * 50, DIM)
    say("  %d job%s, %d photo%s, %.1f MB"
        % (len(jobs), "" if len(jobs) == 1 else "s",
           total_files, "" if total_files == 1 else "s",
           total_bytes / 1048576.0))
    say()
    flagged = []
    for j in jobs:
        say("    #%-16s %-11s %s" % (j["channel"], j["when"],
                                     ", ".join(f["filename"] for f in j["files"][:3])
                                     + (" ..." if len(j["files"]) > 3 else "")), DIM)
        if ADDRESS_RE.search(j["stem"]):
            flagged.append(j)
    if flagged:
        say()
        say("  These look like street addresses, and the filename becomes the", RED)
        say("  caption on your website:", RED)
        for j in flagged:
            say("      %s" % j["stem"], RED)
        say("  Fix the wording in Discord, or rename them on the next screen.", YELLOW)

    if dropped_total:
        say()
        say("  Skipped %d attachment%s that are not job photos."
            % (len(dropped_total), "" if len(dropped_total) == 1 else "s"), DIM)

    if dry:
        say()
        say("  Dry run - nothing was downloaded and nothing was saved.", YELLOW)
        say()
        return 0

    if not assume_yes:
        say()
        if not ask("  Download these %d photo%s? [y/N] "
                   % (total_files, "" if total_files == 1 else "s"),
                   "n").lower().startswith("y"):
            say("  Left alone. Nothing was downloaded.", DIM)
            return 0

    # Download.
    say()
    say("  Downloading", GREEN)
    got = 0
    for j in jobs:
        folder = os.path.join(INBOX, j["category"])
        os.makedirs(folder, exist_ok=True)
        kept = []
        for f in j["files"]:
            dest = os.path.join(folder, f["filename"])
            bump = 2
            while os.path.exists(dest):
                stem, ext = os.path.splitext(f["filename"])
                dest = os.path.join(folder, "%s-%d%s" % (stem, bump, ext))
                bump += 1
            f["filename"] = os.path.basename(dest)
            try:
                download(f["url"], dest)
            except Exception as exc:
                say("    could not download %s (%s)" % (f["filename"], exc), YELLOW)
                continue
            state["attachments"][f["attachmentId"]] = "%s/%s" % (j["category"],
                                                                 f["filename"])
            kept.append(f)
            got += 1
        j["files"] = kept
        say("    %s/%s" % (j["category"], ", ".join(f["filename"] for f in kept)),
            DIM)

    for cid, cs in state["channels"].items():
        if cs.get("pendingCursor"):
            cs["lastMessageId"] = cs.pop("pendingCursor")
    save_state(state)

    jobs = [j for j in jobs if j["files"]]
    say()
    say("  %d photo%s downloaded into photo-inbox."
        % (got, "" if got == 1 else "s"), GREEN)

    if jobs and not no_page:
        naming_page(jobs, [{"id": c, "label": l} for c, l in categories])

    say()
    say("  " + "-" * 50, DIM)
    say("  Have a look at the names in photo-inbox, then", GREEN)
    say("  double-click  publish-photos.cmd  in this folder:", GREEN)
    say("      %s" % ROOT, GREEN)
    report_new_channels(new_channels, meta)
    say()
    return 0


def report_new_channels(names, meta):
    """A channel added to the photo group is a new category waiting to happen."""
    if not names:
        return
    say()
    say("  New channel%s in \"%s\": %s"
        % ("" if len(names) == 1 else "s",
           meta.get("discordCategoryName", "your photo group"),
           ", ".join("#" + n for n in names)), YELLOW)
    say("  To turn %s into %s, run setup again:"
        % ("it" if len(names) == 1 else "them",
           "a category" if len(names) == 1 else "categories"), YELLOW)
    say(how_to_run("--setup"), YELLOW)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as exc:
        say()
        say("  " + str(exc), RED)
        say()
        sys.exit(1)
    except KeyboardInterrupt:
        say()
        say("  Stopped.", YELLOW)
        sys.exit(1)
