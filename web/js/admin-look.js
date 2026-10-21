/* Settings > Overview > Settings look (app/admin_looks.py, docs/themes.md "Settings look").
   Draws its own card and keeps its own data; admin.js only asks for html() and wire(). */
(function () {
  'use strict';
  var D = null, LOADING = false, PICK = null;

  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function api(method, url, body) {
    var opts = { method: method, credentials: 'same-origin', headers: {} };
    if (body !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
    return fetch(url, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) throw new Error(j.detail || ('Error ' + r.status));
        return j;
      });
    });
  }
  function toast(msg, bad) {
    var el = document.getElementById('toast');
    if (!el) return;
    el.textContent = msg; el.className = bad ? 'bad' : ''; el.style.display = 'block';
    clearTimeout(toast.t);
    toast.t = setTimeout(function () { el.style.display = 'none'; }, bad ? 6000 : 2500);
  }
  function load() {
    if (LOADING) return;
    LOADING = true;
    api('GET', 'api/admin/settings-look').then(function (d) {
      D = d; PICK = { look: d.setting.look, frame: d.setting.frame || (d.frames[0] || {}).id || '', phone: d.setting.phone };
      redraw();
    }).catch(function () { /* the card stays as "Loading" */ });
  }
  function redraw() {
    var el = document.getElementById('settings-look');
    if (el) { el.outerHTML = html(); wire(); }
  }

  function html() {
    if (!D) { load(); return '<div id="settings-look"><p class="help">Loading…</p></div>'; }
    var looks = D.looks.map(function (l) {
      var on = PICK.look === l.key;
      return '<label class="al-look' + (on ? ' on' : '') + (l.ready ? '' : ' off') + '"><input type="radio" name="al-look" value="' + esc(l.key) + '"' +
        (on ? ' checked' : '') + (l.ready ? '' : ' disabled') + '><span class="swatches">' +
        l.swatches.map(function (c) { return '<i style="background:' + esc(c) + '"></i>'; }).join('') + '</span><b>' + esc(l.name) + '</b>' +
        (l.ready ? '' : '<small>Not ready for Settings yet</small>') + '</label>';
    }).join('');
    var frames = D.frames.map(function (f) {
      return '<option value="' + esc(f.id) + '"' + (PICK.frame === f.id ? ' selected' : '') + '>' + esc(f.name) + ' (' + esc(f.look_name) + ')</option>';
    }).join('');
    var match = '<label class="al-look' + (PICK.look === 'frame' ? ' on' : '') + '"><input type="radio" name="al-look" value="frame"' +
      (PICK.look === 'frame' ? ' checked' : '') + '><b>Match a frame</b><small>Follows that frame’s look and its options, like its color.</small></label>';
    var why = D.now.reason ? '<p class="warn">Settings uses Navy &amp; gilt for now: ' + esc(D.now.reason) + '.</p>' : '';
    return '<div id="settings-look">' +
      '<p class="help">How Settings and the parent phone page look. A look only changes colors and type: every switch, field and button stays where it is. ' +
      'Add <b>?look=plain</b> to the address, or use the link at the bottom of the page, to see the plain style any time.</p>' + why +
      '<div class="al-looks">' + looks + match + '</div>' +
      (PICK.look === 'frame' ? '<div class="row"><label class="f">Which frame<select data-al="frame">' + frames + '</select></label></div>' : '') +
      '<label class="sp-switch"><input type="checkbox" data-al="phone"' + (PICK.phone ? ' checked' : '') + '><span></span>Use it on the phone page too</label>' +
      '<div class="actions"><button class="btn primary" data-al-save>Save Settings look</button></div></div>';
  }

  function wire() {
    var el = document.getElementById('settings-look');
    if (!el || !D) return;
    Array.prototype.forEach.call(el.querySelectorAll('input[name=al-look]'), function (r) {
      r.onchange = function () { PICK.look = r.value; redraw(); };
    });
    var fr = el.querySelector('[data-al=frame]');
    if (fr) fr.onchange = function () { PICK.frame = fr.value; };
    var ph = el.querySelector('[data-al=phone]');
    ph.onchange = function () { PICK.phone = ph.checked; };
    var save = el.querySelector('[data-al-save]');
    save.onclick = function () {
      save.disabled = true;
      api('PUT', 'api/admin/settings-look', PICK).then(function () {
        toast('Saved');
        setTimeout(function () { location.reload(); }, 400);   // the page is drawn in the look by the server
      }).catch(function (e) { toast(e.message, true); save.disabled = false; });
    };
  }

  function summary() {   // the line on the Overview's folded "Settings look" block
    if (!D || !PICK) return '';
    if (PICK.look === 'frame') return 'Matches a frame' + (PICK.phone ? ' · phone page too' : '');
    var l = D.looks.filter(function (x) { return x.key === PICK.look; })[0];
    return (l ? l.name : PICK.look) + (PICK.phone ? ' · phone page too' : '');
  }
  window.AdminLook = { html: html, wire: wire, summary: summary };
})();
