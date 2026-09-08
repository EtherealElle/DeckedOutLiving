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

  function loadJSON(path, cb) {
    if (!window.fetch) return;
    fetch(BASE + path, { cache: 'no-cache' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) cb(d); })
      .catch(function () { /* offline or not generated yet - empty states stand */ });
  }

  if (document.getElementById('reviews')) {
    loadJSON('reviews.json', function (d) {
      renderReviews(Array.isArray(d) ? d : d.reviews);
    });
  }

  if (document.querySelector('.ba[data-auto]')) {
    loadJSON('photos/gallery.json', hydrateSlider);
  }

  /* Expose for gallery.js so it can reuse the same base + loader. */
  window.DOL = { base: BASE, loadJSON: loadJSON };
})();
