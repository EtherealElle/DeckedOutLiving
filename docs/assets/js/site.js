/* ============================================================
   Decked Out Living - shared site behaviour
   Loaded on every page. Everything here is progressive: if this
   file fails to load, the site still reads and every link works.
   ============================================================ */
(function () {
  'use strict';

  /* Base path so pages in /services can reach /photos and /reviews.json.
     Each page carries <body data-base="./"> or data-base="../">. */
  var BASE = (document.body && document.body.getAttribute('data-base')) || './';

  /* ---------- mobile navigation ---------- */
  (function nav() {
    var burger = document.querySelector('.burger');
    var menu = document.getElementById('nav');
    if (!burger || !menu) return;

    burger.addEventListener('click', function () {
      var open = menu.classList.toggle('open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    // Close when a link is tapped, so in-page anchors do not leave the menu open.
    menu.addEventListener('click', function (e) {
      if (e.target.closest('a')) {
        menu.classList.remove('open');
        burger.setAttribute('aria-expanded', 'false');
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu.classList.contains('open')) {
        menu.classList.remove('open');
        burger.setAttribute('aria-expanded', 'false');
        burger.focus();
      }
    });
  })();

  /* ---------- current year in the footer ---------- */
  Array.prototype.forEach.call(document.querySelectorAll('[data-year]'), function (el) {
    el.textContent = new Date().getFullYear();
  });

  /* ============================================================
     BEFORE / AFTER SLIDER
     Works with mouse, touch, pen and keyboard. If real before/after
     pairs exist in photos/gallery.json the illustrated placeholder
     is swapped out for the newest real pair automatically.
     ============================================================ */
  function initSlider(root) {
    var line = root.querySelector('.ba-line');
    var knob = root.querySelector('.ba-knob');
    var after = root.querySelector('.ba-after');
    if (!knob || !after) return;

    var pos = 50;
    var dragging = false;

    function paint(p) {
      pos = Math.max(0, Math.min(100, p));
      root.style.setProperty('--pos', pos + '%');
      knob.setAttribute('aria-valuenow', Math.round(pos));
    }

    function fromEvent(e) {
      var r = root.getBoundingClientRect();
      if (!r.width) return;
      paint(((e.clientX - r.left) / r.width) * 100);
    }

    knob.addEventListener('pointerdown', function (e) {
      dragging = true;
      knob.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    knob.addEventListener('pointermove', function (e) {
      if (dragging) fromEvent(e);
    });
    function stop(e) {
      if (!dragging) return;
      dragging = false;
      try { knob.releasePointerCapture(e.pointerId); } catch (err) { /* already released */ }
    }
    knob.addEventListener('pointerup', stop);
    knob.addEventListener('pointercancel', stop);

    // Tapping anywhere on the image jumps the divider there.
    root.addEventListener('pointerdown', function (e) {
      if (e.target === knob || knob.contains(e.target)) return;
      fromEvent(e);
    });

    knob.addEventListener('keydown', function (e) {
      var step = e.shiftKey ? 10 : 2;
      if (e.key === 'ArrowLeft') { paint(pos - step); e.preventDefault(); }
      else if (e.key === 'ArrowRight') { paint(pos + step); e.preventDefault(); }
      else if (e.key === 'Home') { paint(0); e.preventDefault(); }
      else if (e.key === 'End') { paint(100); e.preventDefault(); }
    });

    paint(50);
    if (line) line.style.left = 'var(--pos)';
  }

  var sliders = document.querySelectorAll('.ba');
  Array.prototype.forEach.call(sliders, initSlider);

  /* Swap the illustrated placeholder for a real pair when one exists. */
  function hydrateSlider(data) {
    var root = document.querySelector('.ba[data-auto]');
    if (!root || !data || !data.pairs || !data.pairs.length) return;

    var pair = data.pairs[0];
    var beforePane = root.querySelector('.ba-before');
    var afterPane = root.querySelector('.ba-after');
    if (!beforePane || !afterPane) return;

    function img(src, alt) {
      var i = document.createElement('img');
      i.src = BASE + src;
      i.alt = alt;
      i.loading = 'lazy';
      i.decoding = 'async';
      return i;
    }

    beforePane.innerHTML = '';
    afterPane.innerHTML = '';
    beforePane.appendChild(img(pair.before.web, 'Before: ' + pair.label));
    afterPane.appendChild(img(pair.after.web, 'After: ' + pair.label));

    var note = root.parentNode.querySelector('.ba-note');
    if (note) note.textContent = pair.label;

    var cap = document.querySelector('[data-ba-caption]');
    if (cap) cap.textContent = pair.label;
  }

  /* ============================================================
     REVIEWS
     The section stays completely hidden unless reviews.json holds
     at least one entry. Nothing is ever invented here.
     ============================================================ */
  function renderReviews(list) {
    var sec = document.getElementById('reviews');
    if (!sec) return;
    if (!list || !list.length) return; // stays hidden

    var grid = sec.querySelector('[data-reviews]');
    if (!grid) return;

    var frag = document.createDocumentFragment();
    list.forEach(function (r) {
      if (!r || !r.quote || !r.name) return;
      var art = document.createElement('article');
      art.className = 'rev';

      var bq = document.createElement('blockquote');
      bq.textContent = r.quote;

      var cite = document.createElement('cite');
      cite.textContent = r.name;

      if (r.source) {
        var s = document.createElement('span');
        s.className = 'src';
        s.textContent = r.source;
        cite.appendChild(s);
      }

      art.appendChild(bq);
      art.appendChild(cite);
      frag.appendChild(art);
    });

    if (!frag.childNodes.length) return;
    grid.appendChild(frag);
    sec.hidden = false;
  }

  /* One fetch per file, shared by everything that needs it, so the
     slider, the service cards and the gallery do not each hit the network. */
  var cache = {};
  function loadJSON(path, cb) {
    if (!window.fetch) return;
    if (!cache[path]) {
      cache[path] = fetch(BASE + path, { cache: 'no-cache' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; });
    }
    cache[path].then(function (d) { if (d) cb(d); });
  }

  /* ============================================================
     SERVICE CARD PHOTOS
     Each service card carries a photo band. Until a job photo exists
     for that category the band shows a branded tile; once one does,
     the newest photo drops straight in. Nobody edits HTML.
     ============================================================ */
  function fillServicePhotos(data) {
    var bands = document.querySelectorAll('.card-photo[data-cat]');
    if (!bands.length || !data || !data.photos || !data.photos.length) return;

    // Two cards showing the same picture looks like a mistake, and a job that
    // is tagged into several categories would otherwise front all of them. So
    // prefer a photo nothing else has taken, and prefer one whose MAIN
    // category is this card's before falling back to a tagged-in one.
    var used = {};

    function candidates(cat) {
      var primary = [], tagged = [];
      for (var i = 0; i < data.photos.length; i++) {
        var p = data.photos[i];
        var cats = (p.categories && p.categories.length) ? p.categories : [p.category];
        if (cats.indexOf(cat) === -1) continue;
        (p.category === cat ? primary : tagged).push(p);
      }
      return primary.concat(tagged);
    }

    Array.prototype.forEach.call(bands, function (band) {
      var cat = band.getAttribute('data-cat');
      var list = candidates(cat);
      var pick = null;
      for (var i = 0; i < list.length; i++) {
        if (!used[list[i].web]) { pick = list[i]; break; }
      }
      if (!pick && list.length) pick = list[0];   // all taken - repeat rather than blank
      if (!pick) return;                          // nothing in this category yet
      used[pick.web] = true;

      var img = band.querySelector('img');
      if (!img) return;
      // The card shows this at roughly 300px wide, so the 800px thumbnail is
      // still sharp on a 3x phone screen and about a quarter of the bytes.
      // Falls back to the full version if an old gallery.json has no thumb.
      img.src = BASE + (pick.thumb || pick.web);
      img.alt = pick.caption || pick.categoryLabel;
      band.classList.add('has-photo');
    });
  }

  /* A rail only needs a "swipe" hint when it actually overflows. */
  function railHints() {
    Array.prototype.forEach.call(document.querySelectorAll('.rail'), function (rail) {
      if (rail.dataset.hinted) return;
      if (rail.scrollWidth - rail.clientWidth < 24) return;
      var p = document.createElement('p');
      p.className = 'rail-hint';
      p.innerHTML = 'Swipe for more <svg width="15" height="15" viewBox="0 0 24 24" fill="none" ' +
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ' +
        'aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';
      rail.parentNode.insertBefore(p, rail.nextSibling);
      rail.dataset.hinted = '1';
    });
  }

  if (document.getElementById('reviews')) {
    loadJSON('reviews.json', function (d) {
      renderReviews(Array.isArray(d) ? d : d.reviews);
      railHints();
    });
  }

  if (document.querySelector('.ba[data-auto]') || document.querySelector('.card-photo[data-cat]')) {
    loadJSON('photos/gallery.json', function (d) {
      hydrateSlider(d);
      fillServicePhotos(d);
    });
  }

  railHints();
  window.addEventListener('resize', railHints);

  /* Expose for gallery.js so it can reuse the same base + loader. */
  window.DOL = { base: BASE, loadJSON: loadJSON };
})();
