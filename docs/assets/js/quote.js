/* ============================================================
   Decked Out Living - multi-step quote form

   Degrades in three stages, worst case first:
     1. No JavaScript      -> every step is visible as one plain
                              form that posts normally.
     2. JS, no Formspree   -> the form collects answers, then hands
                              them to tap-to-call / tap-to-email
                              with the message pre-written.
     3. JS + Formspree     -> posts in the background, success
                              message appears without a page load.
   ============================================================ */
(function () {
  'use strict';

  var form = document.getElementById('quote-form');
  if (!form) return;

  var PHONE = form.getAttribute('data-phone') || '';
  var EMAIL = form.getAttribute('data-email') || '';
  var action = form.getAttribute('action') || '';
  var configured = action.indexOf('YOUR_FORM_ID') === -1 && action.indexOf('formspree.io/f/') !== -1;

  var steps = Array.prototype.slice.call(form.querySelectorAll('.qf-step'));
  var bar = form.querySelector('.qf-bar i');
  var stepNum = form.querySelector('[data-step-num]');
  var stepName = form.querySelector('[data-step-name]');
  var btnBack = form.querySelector('[data-back]');
  var btnNext = form.querySelector('[data-next]');
  var btnSend = form.querySelector('[data-send]');
  var fallback = form.querySelector('.qf-fallback');

  if (!steps.length) return;

  // Switching the form into stepped mode is what hides steps 2..n.
  // Until this runs, CSS shows them all, so a no-JS visitor gets a
  // long-but-working form rather than a blank box.
  form.classList.add('stepped');

  // With the wizard running, this file owns validation. Native validation
  // is turned off only now, so a visitor without JavaScript still gets the
  // browser's own required-field checks on the plain long form. It also
  // avoids the browser refusing to submit because a required field on a
  // hidden step cannot be focused to show its message against.
  form.noValidate = true;

  var at = 0;
  var total = steps.length;

  /* ---------- navigation ---------- */
  function paint() {
    steps.forEach(function (s, i) { s.classList.toggle('on', i === at); });

    if (bar) bar.style.width = Math.round(((at + 1) / total) * 100) + '%';
    if (stepNum) stepNum.textContent = 'Step ' + (at + 1) + ' of ' + total;
    if (stepName) stepName.textContent = steps[at].getAttribute('data-name') || '';

    if (btnBack) btnBack.hidden = at === 0;
    if (btnNext) btnNext.hidden = at === total - 1;
    if (btnSend) btnSend.hidden = at !== total - 1;

    if (at === total - 1) summarise();

    // Move focus to the step heading so screen readers announce it.
    var h = steps[at].querySelector('h3');
    if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); }

    var top = form.getBoundingClientRect().top + window.pageYOffset - 90;
    if (window.pageYOffset > top) window.scrollTo({ top: top, behavior: 'smooth' });
  }

  function validate(i) {
    var ok = true;
    var scope = steps[i];

    // required text inputs
    Array.prototype.forEach.call(scope.querySelectorAll('[required]'), function (el) {
      var field = el.closest('.field');
      var good = el.checkValidity() && String(el.value).trim() !== '';
      if (field) field.classList.toggle('err', !good);
      if (!good && ok) { el.focus(); ok = false; }
    });

    // Optional fields are allowed to be empty, but not to be wrong. A typo in
    // the email address would otherwise send a quote nobody can reply to.
    var optional = scope.querySelectorAll('input:not([required]), textarea:not([required])');
    Array.prototype.forEach.call(optional, function (el) {
      if (!el.name || el.name.charAt(0) === '_') return;
      if (String(el.value).trim() === '') {
        var f0 = el.closest('.field');
        if (f0) f0.classList.remove('err');
        return;
      }
      var field = el.closest('.field');
      var good = el.checkValidity();
      if (field) field.classList.toggle('err', !good);
      if (!good && ok) { el.focus(); ok = false; }
    });

    // required radio groups. The message sits just after the group of
    // chips rather than inside it, so check both places.
    Array.prototype.forEach.call(scope.querySelectorAll('[data-require-group]'), function (g) {
      var name = g.getAttribute('data-require-group');
      var picked = form.querySelector('input[name="' + name + '"]:checked');
      var msg = g.querySelector('.msg');
      if (!msg && g.nextElementSibling && g.nextElementSibling.classList.contains('msg')) {
        msg = g.nextElementSibling;
      }
      if (msg) msg.style.display = picked ? 'none' : 'block';
      if (!picked) {
        if (ok) {
          var first = g.querySelector('input');
          if (first) first.focus();
        }
        ok = false;
      }
    });

    return ok;
  }

  if (btnNext) btnNext.addEventListener('click', function () {
    if (!validate(at)) return;
    if (at < total - 1) { at++; paint(); }
  });

  if (btnBack) btnBack.addEventListener('click', function () {
    if (at > 0) { at--; paint(); }
  });

  // Picking a radio on a single-question step advances automatically.
  form.addEventListener('change', function (e) {
    var input = e.target;
    if (input.type !== 'radio') return;
    var step = input.closest('.qf-step');
    if (!step || !step.hasAttribute('data-advance')) return;
    if (steps.indexOf(step) !== at) return;
    setTimeout(function () {
      if (validate(at) && at < total - 1) { at++; paint(); }
    }, 220);
  });

  form.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter') return;
    if (e.target.tagName === 'TEXTAREA') return;
    if (at < total - 1) { e.preventDefault(); if (btnNext) btnNext.click(); }
  });

  /* ---------- summary on the last step ---------- */
  function answers() {
    var out = [];
    var seen = {};
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.name.charAt(0) === '_') return;
      if ((el.type === 'radio' || el.type === 'checkbox') && !el.checked) return;
      var label = el.getAttribute('data-label') || el.name;
      var value = el.type === 'radio' || el.type === 'checkbox'
        ? (el.getAttribute('data-text') || el.value)
        : el.value;
      if (!String(value).trim()) return;
      if (seen[label]) { seen[label].value += ', ' + value; return; }
      var row = { label: label, value: value };
      seen[label] = row;
      out.push(row);
    });
    return out;
  }

  function summarise() {
    var box = form.querySelector('[data-summary]');
    if (!box) return;
    var dl = document.createElement('dl');
    answers().forEach(function (a) {
      if (/^(Name|Phone|Email|Anything else)$/i.test(a.label)) return;
      var dt = document.createElement('dt'); dt.textContent = a.label;
      var dd = document.createElement('dd'); dd.textContent = a.value;
      dl.appendChild(dt); dl.appendChild(dd);
    });
    box.innerHTML = '';
    if (dl.childNodes.length) box.appendChild(dl);
    box.hidden = !dl.childNodes.length;
  }

  function messageText() {
    var lines = ['Quote request from the website:', ''];
    answers().forEach(function (a) { lines.push(a.label + ': ' + a.value); });
    return lines.join('\n');
  }

  /* ---------- unconfigured: hand off to phone / email ---------- */
  function wireFallback() {
    if (!fallback) return;
    fallback.hidden = false;

    var mail = fallback.querySelector('[data-mailto]');
    if (mail) {
      mail.addEventListener('click', function () {
        mail.href = 'mailto:' + EMAIL +
          '?subject=' + encodeURIComponent('Quote request - Decked Out Living') +
          '&body=' + encodeURIComponent(messageText());
      });
    }
  }

  function done(heading, body) {
    var wrap = form.querySelector('.qf-body');
    var head = form.querySelector('.qf-head');
    if (head) head.hidden = true;
    if (fallback) fallback.hidden = true;
    if (!wrap) return;
    wrap.innerHTML =
      '<div class="qf-done">' +
        '<div class="tick"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg></div>' +
        '<h3></h3><p></p>' +
        '<a class="btn btn-dark" href="tel:' + PHONE + '">Call ' + PHONE + '</a>' +
      '</div>';
    wrap.querySelector('h3').textContent = heading;
    wrap.querySelector('p').textContent = body;
    wrap.querySelector('h3').setAttribute('tabindex', '-1');
    wrap.querySelector('h3').focus();
  }

  /* ---------- submit ---------- */
  form.addEventListener('submit', function (e) {
    if (!validate(at)) { e.preventDefault(); return; }

    if (!configured) {
      e.preventDefault();
      // No Formspree yet - do not pretend the message was sent.
      var mail = 'mailto:' + EMAIL +
        '?subject=' + encodeURIComponent('Quote request - Decked Out Living') +
        '&body=' + encodeURIComponent(messageText());
      window.location.href = mail;
      return;
    }

    if (!window.fetch) return; // let the browser post normally

    e.preventDefault();
    if (btnSend) { btnSend.disabled = true; btnSend.textContent = 'Sending...'; }

    var fd = new FormData(form);
    fd.append('_summary', messageText());

    fetch(action, { method: 'POST', body: fd, headers: { Accept: 'application/json' } })
      .then(function (r) {
        if (r.ok) {
          done('Request sent', 'Thanks - your request is in. You will hear back about your project shortly. If it is urgent, calling is fastest.');
        } else {
          throw new Error('bad response');
        }
      })
      .catch(function () {
        if (btnSend) { btnSend.disabled = false; btnSend.textContent = 'Send my request'; }
        var err = form.querySelector('[data-error]');
        if (err) {
          err.hidden = false;
          err.textContent = 'That did not go through. Please call ' + PHONE + ' or email ' + EMAIL + ' instead.';
        }
        wireFallback();
      });
  });

  if (!configured) wireFallback();
  paint();
})();
