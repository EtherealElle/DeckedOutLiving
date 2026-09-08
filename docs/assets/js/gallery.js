/* ============================================================
   Decked Out Living - filterable gallery + lightbox
   Reads photos/gallery.json, which is written by the photo tool.
   Nobody edits HTML to add a photo.
   ============================================================ */
(function () {
  'use strict';

  var DOL = window.DOL || { base: './', loadJSON: null };
  var BASE = DOL.base;

  var grid = document.getElementById('gallery');
  if (!grid) return;

  var filterBar = document.getElementById('filters');
  var emptyBox = document.getElementById('gallery-empty');
  var countEl = document.getElementById('gallery-count');
  var limit = parseInt(grid.getAttribute('data-limit') || '0', 10);

  var photos = [];
  var shown = [];
  var active = 'all';

  /* ---------- render ---------- */
  function render() {
    shown = active === 'all'
      ? photos.slice()
      : photos.filter(function (p) { return p.category === active; });

    if (limit > 0) shown = shown.slice(0, limit);

    grid.innerHTML = '';
    var frag = document.createDocumentFragment();

    shown.forEach(function (p, i) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'gal-item';
      btn.setAttribute('data-i', i);
      btn.setAttribute('aria-label', 'Open photo: ' + (p.caption || p.categoryLabel));

      var img = document.createElement('img');
      img.src = BASE + p.thumb;
      img.alt = p.caption || (p.categoryLabel + ' by Decked Out Living');
      img.loading = 'lazy';
      img.decoding = 'async';
      if (p.tw && p.th) { img.width = p.tw; img.height = p.th; }
      btn.appendChild(img);

      if (p.badge) {
        var b = document.createElement('span');
        b.className = 'gal-badge';
        b.textContent = p.badge;
        btn.appendChild(b);
      }

      var cap = document.createElement('span');
      cap.className = 'gal-cap';
      cap.textContent = p.caption || p.categoryLabel;
      btn.appendChild(cap);

      frag.appendChild(btn);
    });

    grid.appendChild(frag);
    if (countEl) {
      countEl.textContent = shown.length + (shown.length === 1 ? ' photo' : ' photos');
    }
  }

  /* ---------- filters ---------- */
  function buildFilters(cats) {
    if (!filterBar) return;
    filterBar.innerHTML = '';

    var all = [{ id: 'all', label: 'All work', count: photos.length }].concat(cats);

    all.forEach(function (c) {
      if (c.id !== 'all' && !c.count) return; // never show an empty filter
      var b = document.createElement('button');
      b.type = 'button';
      b.setAttribute('aria-pressed', c.id === active ? 'true' : 'false');
      b.setAttribute('data-cat', c.id);
      b.innerHTML = '';
      b.appendChild(document.createTextNode(c.label));
      var n = document.createElement('span');
      n.className = 'n';
      n.textContent = c.count;
      b.appendChild(n);
      filterBar.appendChild(b);
    });

    filterBar.hidden = false;

    filterBar.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-cat]');
      if (!b) return;
      active = b.getAttribute('data-cat');
      Array.prototype.forEach.call(filterBar.querySelectorAll('button'), function (x) {
        x.setAttribute('aria-pressed', x === b ? 'true' : 'false');
      });
      render();
    });
  }

  /* ---------- lightbox ---------- */
  var lb, lbImg, lbCap, lastFocus, idx = 0;

  function buildLightbox() {
    lb = document.createElement('div');
    lb.className = 'lb';
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-modal', 'true');
    lb.setAttribute('aria-label', 'Photo viewer');

    lb.innerHTML =
      '<button class="lb-btn lb-close" type="button" aria-label="Close">' +
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>' +
      '</button>' +
      '<button class="lb-btn lb-prev" type="button" aria-label="Previous photo">' +
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>' +
      '</button>' +
      '<button class="lb-btn lb-next" type="button" aria-label="Next photo">' +
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg>' +
      '</button>' +
      '<figure class="lb-fig"><img alt=""><figcaption class="lb-cap"></figcaption></figure>';

    document.body.appendChild(lb);
    lbImg = lb.querySelector('img');
    lbCap = lb.querySelector('.lb-cap');

    lb.querySelector('.lb-close').addEventListener('click', close);
    lb.querySelector('.lb-prev').addEventListener('click', function () { step(-1); });
    lb.querySelector('.lb-next').addEventListener('click', function () { step(1); });
    lb.addEventListener('click', function (e) { if (e.target === lb) close(); });

    document.addEventListener('keydown', function (e) {
      if (!lb.classList.contains('on')) return;
      if (e.key === 'Escape') close();
      else if (e.key === 'ArrowLeft') step(-1);
      else if (e.key === 'ArrowRight') step(1);
      else if (e.key === 'Tab') {
        // keep focus inside the dialog
        var f = lb.querySelectorAll('button');
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
        else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
      }
    });

    // swipe on touch
    var x0 = null;
    lb.addEventListener('touchstart', function (e) { x0 = e.changedTouches[0].clientX; }, { passive: true });
    lb.addEventListener('touchend', function (e) {
      if (x0 === null) return;
      var dx = e.changedTouches[0].clientX - x0;
      if (Math.abs(dx) > 50) step(dx > 0 ? -1 : 1);
      x0 = null;
    }, { passive: true });
  }

  function show(i) {
    idx = (i + shown.length) % shown.length;
    var p = shown[idx];
    lbImg.src = BASE + p.web;
    lbImg.alt = p.caption || (p.categoryLabel + ' by Decked Out Living');
    lbCap.textContent = (p.caption || p.categoryLabel) +
      '  (' + (idx + 1) + ' of ' + shown.length + ')';
  }

  function open(i) {
    if (!lb) buildLightbox();
    lastFocus = document.activeElement;
    show(i);
    lb.classList.add('on');
    document.body.style.overflow = 'hidden';
    lb.querySelector('.lb-close').focus();
  }

  function close() {
    lb.classList.remove('on');
    document.body.style.overflow = '';
    if (lastFocus) lastFocus.focus();
  }

  function step(d) { show(idx + d); }

  grid.addEventListener('click', function (e) {
    var it = e.target.closest('.gal-item');
    if (!it) return;
    open(parseInt(it.getAttribute('data-i'), 10));
  });

  /* ---------- load ---------- */
  function start(data) {
    photos = (data && data.photos) || [];
    if (!photos.length) return; // designed empty state stays visible

    if (emptyBox) emptyBox.hidden = true;
    grid.hidden = false;
    buildFilters((data && data.categories) || []);
    render();

    var more = document.getElementById('gallery-more');
    if (more && limit > 0 && photos.length > limit) more.hidden = false;
  }

  if (DOL.loadJSON) {
    DOL.loadJSON('photos/gallery.json', start);
  } else if (window.fetch) {
    fetch(BASE + 'photos/gallery.json')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) start(d); })
      .catch(function () {});
  }
})();
