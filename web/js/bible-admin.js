/* Settings > Special days > Bible translation (app/bible_api.py, docs/bible-translations.md).
   Draws its own card under Special days and keeps its own data; admin.js only asks for html() and wire(). */
(function () {
  'use strict';
  var B = null, LOADING = false, BUSY = '';

  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function api(method, url, body, isForm) {
    var opts = { method: method, credentials: 'same-origin', headers: {} };
    if (body !== undefined) {
      if (isForm) opts.body = body;
      else { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
    }
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

  var STATE_PILL = { 'built-in': 'Built in', downloaded: 'Downloaded', download: 'Not downloaded', yours: 'Added', key: 'Needs fetching', 'needs-text': 'Needs your text' };

  function links(t) {
    return t.links.length ? '<p class="bt-links">' + t.links.map(function (l) {
      return '<a href="' + esc(l[1]) + '" target="_blank" rel="noopener">' + esc(l[0]) + '</a>';
    }).join(' · ') + '</p>' : '';
  }
  function actions(t) {
    var busy = BUSY === t.code;
    var spin = '<span class="spin" aria-hidden="true"></span> ';
    if (t.code === 'bsb') {
      return '<div class="bt-acts">' + (t.state === 'downloaded'
        ? '<button type="button" class="btn quiet" data-bt="dl-bsb"' + (busy ? ' disabled' : '') + '>' + (busy ? spin + 'Getting it…' : 'Download again') + '</button>' +
          '<button type="button" class="btn danger" data-bt="rm" data-code="bsb">Remove</button>'
        : '<button type="button" class="btn line" data-bt="dl-bsb"' + (busy ? ' disabled' : '') + '>' + (busy ? spin + 'Getting it…' : 'Download BSB') + '</button>') +
        '<span class="bt-small">' + (t.when ? 'Last downloaded ' + esc(t.when) + '. ' : '') + (B.demo ? 'Demo mode uses a small sample instead of the real file.' : 'About 4 MB; only the verses the pictures use are kept.') + '</span></div>';
    }
    if (t.code === 'nasb') {
      var ab = B.apibible;
      return '<div class="bt-acts">' +
        '<label class="btn line bt-file">Add your text (JSON)<input type="file" accept=".json,application/json" data-bt="import" hidden></label>' +
        '<a class="btn quiet" href="api/admin/bible/template.json" download>List of verses to fill in</a>' +
        (t.state === 'yours' ? '<button type="button" class="btn danger" data-bt="rm" data-code="nasb">Remove</button>' : '') +
        '<div class="seg bt-ed" role="group" aria-label="NASB edition">' + ['2020', '1995'].map(function (e) {
          return '<button type="button" data-bt="edition" data-ed="' + e + '" class="' + (B.nasb_edition === e ? 'on special' : '') + '" aria-pressed="' + (B.nasb_edition === e) + '">NASB ' + e + '</button>';
        }).join('') + '</div></div>' +
        '<details class="bt-key"' + (ab.key_set ? ' open' : '') + '><summary>Or fetch it with your own API.Bible key</summary>' +
        '<p class="bt-small">API.Bible (American Bible Society) licenses the NASB to apps. Your plan has to include it. Your key stays on this server and is never shown again.</p>' +
        '<div class="row bt-row"><label class="f">API.Bible key<input type="password" data-bt-k="key" placeholder="' + (ab.key_set ? 'Saved. Type a new one to change it.' : 'Your key') + '" autocomplete="off"></label>' +
        '<label class="f">Bible ID for the NASB<input type="text" data-bt-k="bible_id" value="' + esc(ab.bible_id) + '" placeholder="From your API.Bible dashboard"></label></div>' +
        '<div class="bt-acts"><button type="button" class="btn quiet" data-bt="save-key">Save key</button>' +
        (ab.key_set ? '<button type="button" class="btn line" data-bt="fetch"' + (busy || B.demo ? ' disabled' : '') + '>' + (busy ? spin + 'Fetching…' : 'Fetch the verses') + '</button>' : '') +
        (B.demo ? '<span class="bt-small">Fetching is off in demo mode.</span>' : '') + '</div></details>';
    }
    return '';
  }
  function row(t) {
    var usable = t.state === 'built-in' || t.state === 'downloaded' || t.state === 'yours';
    return '<div class="bt-tr' + (t.chosen ? ' on' : '') + '">' +
      '<label class="bt-pick"><input type="radio" name="bt-pick" value="' + t.code + '"' + (t.chosen ? ' checked' : '') + '>' +
      '<span><b>' + esc(t.name) + '</b> <span class="bt-abbr">' + esc(t.abbr) + '</span></span>' +
      '<span class="bt-pill bt-' + esc(t.state) + '">' + esc(STATE_PILL[t.state] || t.state) + '</span></label>' +
      '<p class="bt-state">' + esc(t.label) + (t.chosen && !usable ? '. Until then the frame shows the KJV.' : '') + '</p>' +
      '<p class="bt-notice">' + esc(t.notice) + '</p>' +
      '<p class="bt-note">' + esc(t.note) + '</p>' + links(t) + actions(t) + '</div>';
  }
  function preview() {
    if (!B.preview.length) return '';
    var ref = B.preview[0].cite.replace(/\s*\(.*\)$/, '');
    return '<div class="bt-prev"><h3>' + esc(ref) + ' in each one</h3>' + B.preview.map(function (p) {
      var fell = p.from !== p.code;
      return '<div class="bt-pv"><b>' + esc(p.code.toUpperCase()) + '</b><span>“' + esc(p.text) + '” <i>' + esc(p.cite) + '</i>' +
        (fell ? ' <small>(not on hand yet, so this falls back)</small>' : '') + '</span></div>';
    }).join('') + '</div>';
  }
  function html() {
    if (!B) {
      if (!LOADING) load();
      return '<div id="bible"><p class="help"><span class="spin" aria-hidden="true"></span> Loading…</p></div>';
    }
    if (!B.has_verses) return '';
    return '<div id="bible">' +
      '<p class="help">The verses on the Sunday pictures, church days, Thanksgiving and the bedtime clock use the translation you pick. ' +
      'If a verse isn’t on hand in it, the frame uses the <b>KJV</b>, then the text in the Faith pack. Shortened verses are shortened the same way in every translation, so the pictures still fit. ' +
      '<b>Which translation the public release uses is still an open question</b>; the ESV stays the default for now.</p>' +
      '<div class="bt-list">' + B.translations.map(row).join('') + '</div>' + preview() + '</div>';
  }
  function repaint() {
    var el = document.getElementById('bible');
    if (!el) return;
    var wrap = document.createElement('div');
    wrap.innerHTML = html();
    var blk = el.closest('.blk');   // it sits in a folding block on the Special days page
    if (wrap.firstChild) el.parentNode.replaceChild(wrap.firstChild, el);
    else if (blk) blk.hidden = true;
    else el.parentNode.removeChild(el);
    var line = blk && blk.querySelector('.fold-head > i');
    if (line) line.textContent = summary();
    wire();
  }
  function load() {
    LOADING = true;
    return api('GET', 'api/admin/bible').then(function (v) { B = v; LOADING = false; repaint(); })
      .catch(function (e) { LOADING = false; toast(e.message, true); });
  }
  function act(p, msg) {
    return p.then(function (r) { toast(typeof msg === 'function' ? msg(r) : msg); BUSY = ''; return load(); })
      .catch(function (e) { BUSY = ''; toast(e.message, true); repaint(); });
  }
  function wire() {
    var el = document.getElementById('bible');
    if (!el) return;
    Array.prototype.forEach.call(el.querySelectorAll('input[name=bt-pick]'), function (r) {
      r.onchange = function () {
        act(api('PUT', 'api/admin/bible', { translation: r.value }), 'Verses now show in the ' + r.value.toUpperCase() + ' where it’s on hand.');
      };
    });
    Array.prototype.forEach.call(el.querySelectorAll('[data-bt]'), function (b) {
      var k = b.getAttribute('data-bt');
      if (k === 'import') {
        b.onchange = function () {
          if (!b.files.length) return;
          var fd = new FormData(); fd.append('file', b.files[0]);
          act(api('POST', 'api/admin/bible/nasb/import', fd, true), function (r) { return 'Added ' + r.verses + ' verses.'; });
        };
        return;
      }
      b.onclick = function () {
        if (k === 'dl-bsb') { BUSY = 'bsb'; repaint(); act(api('POST', 'api/admin/bible/bsb/download'), function (r) { return 'Saved ' + r.verses + ' BSB verses.'; }); }
        if (k === 'rm') {
          var code = b.getAttribute('data-code');
          if (!window.confirm('Remove the ' + code.toUpperCase() + ' text from this server? The frame falls back to the KJV. You can get it again any time.')) return;
          act(api('DELETE', 'api/admin/bible/' + code), 'Removed');
        }
        if (k === 'edition') act(api('PUT', 'api/admin/bible', { nasb_edition: b.getAttribute('data-ed') }), 'Saved');
        if (k === 'save-key') {
          act(api('PUT', 'api/admin/bible/apibible', { key: el.querySelector('[data-bt-k=key]').value, bible_id: el.querySelector('[data-bt-k=bible_id]').value }), 'Saved');
        }
        if (k === 'fetch') { BUSY = 'nasb'; repaint(); act(api('POST', 'api/admin/bible/nasb/fetch'), function (r) { return 'Fetched ' + r.verses + ' verses.'; }); }
      };
    });
  }
  function summary() {   // the line on the folded "Bible translation" block
    var t = B && B.translations.filter(function (x) { return x.chosen; })[0];
    return t ? (t.abbr || t.code.toUpperCase()) + ' · ' + t.name : '';
  }
  window.FrameBible = { html: html, wire: wire, reload: load, summary: summary };
})();
