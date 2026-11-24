/* Settings > Cruise ship tracker (app/trip.py). Draws its own page and keeps its own data; admin.js only asks for html() and wire(). */
(function () {
  'use strict';
  var T = null, D = null, LOADING = false, POLL = null;

  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function api(method, url, body) {
    var opts = { method: method, credentials: 'same-origin', headers: {} };
    if (body !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
    return fetch(url, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok) throw new Error(j.detail || ('Error ' + r.status)); return j; });
    });
  }
  function toast(msg, bad) {
    var el = document.getElementById('toast');
    if (!el) return;
    el.textContent = msg; el.className = bad ? 'bad' : ''; el.style.display = 'block';
    clearTimeout(toast.t);
    toast.t = setTimeout(function () { el.style.display = 'none'; }, bad ? 7000 : 2800);
  }
  function when(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    return d.toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' });
  }
  function take(v) {
    T = v;
    D = { name: v.name, traveler: v.traveler, ship: v.ship, mmsi: v.mmsi, page_url: v.page_url || '', show_from: v.show_from, show_until: v.show_until,
      check_minutes: v.check_minutes, ports: v.ports.map(function (r) { return Object.assign({}, r); }) };
  }
  function load() {
    if (LOADING) return;
    LOADING = true;
    api('GET', 'api/admin/trip').then(function (v) { LOADING = false; take(v); paint(); wire(); })   // the buttons get wired once the page has its data
      .catch(function (e) { LOADING = false; var r = document.getElementById('tr-root'); if (r) r.innerHTML = '<section class="card"><p class="result bad">' + esc(e.message) + '</p></section>'; });
  }
  function f(label, html) { return '<label class="f">' + label + html + '</label>'; }
  function inp(k, v, type, extra) { return '<input type="' + (type || 'text') + '" data-tr="' + k + '" value="' + esc(v) + '"' + (extra || '') + '>'; }

  function tripBody() {
    return '<p class="help">The frame shows the trip only between these dates: a <b>' + esc(D.name) + '</b> tab, and a map panel first on Today. ' +
      'Before and after, nothing shows and nothing is checked. Turn the whole thing off in Settings › Modules.</p>' +
      '<div class="row">' + f('Name on the frame', inp('name', D.name)) + f('Who’s traveling (on the map)', inp('traveler', D.traveler)) + '</div>' +
      '<div class="row">' + f('Show from', inp('show_from', D.show_from, 'date')) + f('until (the last day)', inp('show_until', D.show_until, 'date')) + '</div>';
  }
  function shipBody() {
    var last = T.last_fix;
    return '<div class="row">' + f('Ship', inp('ship', D.ship)) + f('MMSI (9 digits, from the ship’s AIS)', inp('mmsi', D.mmsi, 'text', ' inputmode="numeric" maxlength="9"')) + '</div>' +
      '<div class="row">' + f('The ship’s CruiseMapper page', inp('page_url', D.page_url, 'url', ' placeholder="https://www.cruisemapper.com/ships/…"')) + '</div>' +
      '<p class="help">' + (last ? 'Last heard ' + esc(when(last.at)) + ' at ' + last.lat.toFixed(3) + ', ' + last.lon.toFixed(3) +
        (last.sog != null ? ' · ' + last.sog + ' knots' : '') + (T.last_source === 'aisstream' ? ' (from AISStream)' : '') : 'No position heard yet.') +
      (T.destination ? ' · the ship says it’s heading for “' + esc(T.destination) + '”' : '') + ' · ' + T.fixes + ' positions saved.</p>' +
      (T.fixes ? '<div class="actions"><a class="btn quiet" href="api/admin/trip/export.geojson" download>Download the route (GeoJSON)</a>' +
        '<a class="btn quiet" href="api/admin/trip/export.csv" download>Download the positions (CSV)</a></div>' +
        '<p class="help">Every position with its time, for drawing the route later. GeoJSON opens in Google Earth, QGIS or geojson.io.</p>' : '');
  }
  function portsBody() {
    var opts = T.ports_list;
    var rows = D.ports.map(function (r, i) {
      var sel = '<select data-trp="port"><option value="">At sea</option>' + opts.map(function (p) {
        return '<option value="' + esc(p.key) + '"' + (p.key === r.port ? ' selected' : '') + '>' + esc(p.name + ' · ' + p.place) + '</option>';
      }).join('') + '</select>';
      return '<div class="row" data-tr-row="' + i + '">' + f('Day', '<input type="date" data-trp="day" value="' + esc(r.day) + '">') + f('Port', sel) +
        f('Arrives', '<input type="time" data-trp="arrive" value="' + esc(r.arrive) + '">') + f('Sails', '<input type="time" data-trp="depart" value="' + esc(r.depart) + '">') +
        f('Note', '<input type="text" data-trp="note" maxlength="60" value="' + esc(r.note) + '">') +
        '<button type="button" class="btn quiet" data-tr-del="' + i + '">Remove</button></div>';
    }).join('');
    return '<p class="help">One row per stop, with the times from the cruise planner. Days with no row show as <i>At sea</i>. ' +
      'When the ship’s position is old, the map estimates where the ship is from these times and says so.</p>' + rows +
      '<div class="actions"><button type="button" class="btn quiet" data-tr-add>Add a port</button></div>';
  }
  function sourceBody() {
    var status = T.last_error ? '<p class="result bad">' + esc(T.last_error) + '</p>' : T.last_try ? '<p class="result ok">Last check ' + esc(when(T.last_try)) + '</p>' : '';
    var next = T.next_check ? '<p class="help">Next check about ' + esc(when(T.next_check)) + '.</p>' : '';
    var can = (T.page_url || T.key_set) && !T.checking;
    return '<p class="help">The ship’s position comes from its public page on <a href="https://www.cruisemapper.com" target="_blank" rel="noopener">CruiseMapper</a> ' +
      '(put the page in The ship, above). The frame reads it <b>about once an hour, day and night</b>, at a slightly different time each hour. ' +
      'Out at sea the position can be a few hours old; the map then shows an estimate from the ports of call and says so.</p>' +
      '<p class="help">Backup: if CruiseMapper can’t be read, a free <a href="https://aisstream.io" target="_blank" rel="noopener">AISStream.io</a> key is tried instead. Its receivers often miss the ship.</p>' +
      '<div class="row">' + f('AISStream key (optional)' + (T.key_set ? ' <span class="help">(saved; paste a new one to change it)</span>' : ''),
        '<input type="password" data-tr="aisstream_key" autocomplete="off" placeholder="' + (T.key_set ? '••••••••' : 'Paste the key') + '">') + '</div>' + status + next +
      '<div class="actions"><button type="button" class="btn quiet" data-tr-check' + (can ? '' : ' disabled') + '>' +
      (T.checking ? 'Checking… (up to 4 minutes)' : 'Check now') + '</button></div>' +
      '<p class="help">Only the ship’s public position is used. Nothing about the family leaves the house.</p>';
  }
  function inner() {
    if (!T) return '<section class="card"><h2>Cruise ship tracker</h2><p class="help"><span class="spin" aria-hidden="true"></span> Loading…</p></section>';
    var P = T.preview, B = window.AdminBlocks;
    var stops = D.ports.filter(function (r) { return r.port; }).length;
    var specs = [
      { key: 'trip', name: 'The trip', chip: T.showing ? 'Showing now' : 'Not showing', tone: T.showing ? 'ok' : 'none', body: tripBody(), sum: D.show_from + ' to ' + D.show_until },
      { key: 'ship', name: 'The ship', chip: T.last_fix ? (P.estimated ? 'Estimated' : 'Heard ' + (P.heard || '')) : 'No position', tone: T.last_fix && !P.estimated ? 'ok' : 'warn', body: shipBody(), sum: D.ship },
      { key: 'ports', name: 'Ports of call', chip: stops + ' stops', tone: stops ? 'ok' : 'warn', body: portsBody(), sum: P.headline },
      { key: 'source', name: 'Where the position comes from', chip: (T.page_url || T.key_set) ? (T.last_error ? 'Problem' : 'Hourly, day and night') : 'Needs the ship’s page', tone: (T.page_url || T.key_set) ? (T.last_error ? 'warn' : 'ok') : 'bad', body: sourceBody(), sum: 'CruiseMapper' }
    ];
    return '<section class="card"><h2>Cruise ship tracker</h2><p class="help">Right now the frame says: <b>' + esc(P.headline) + '</b>' + (P.sub ? ' · ' + esc(P.sub) : '') + '.</p>' +
      B.blocks(specs) + '<div class="actions"><button type="button" class="btn primary" data-tr-save>Save the trip</button></div></section>';
  }
  function paint() {
    var r = document.getElementById('tr-root');
    if (!r) return;
    var keep = window.scrollY;
    r.innerHTML = inner();
    window.scrollTo(0, keep);
    clearTimeout(POLL);
    if (T && T.checking) POLL = setTimeout(function () { api('GET', 'api/admin/trip').then(function (v) { readAll(); var d = D; take(v); D = d; paint(); }); }, 8000);
  }
  function readAll() {
    var r = document.getElementById('tr-root');
    if (!r || !D) return;
    Array.prototype.forEach.call(r.querySelectorAll('[data-tr]'), function (el) { if (el.getAttribute('data-tr') !== 'aisstream_key') D[el.getAttribute('data-tr')] = el.value; });
    Array.prototype.forEach.call(r.querySelectorAll('[data-tr-row]'), function (row) {
      var p = D.ports[+row.getAttribute('data-tr-row')];
      Array.prototype.forEach.call(row.querySelectorAll('[data-trp]'), function (el) { p[el.getAttribute('data-trp')] = el.value; });
    });
  }
  function wire() {
    var r = document.getElementById('tr-root');
    if (!r) return;
    if (!T) { load(); return; }
    if (r.getAttribute('data-wired')) return;
    r.setAttribute('data-wired', '1');
    r.addEventListener('click', function (e) {
      var t = e.target.closest('[data-tr-save], [data-tr-add], [data-tr-del], [data-tr-check]');
      if (!t) return;
      e.preventDefault();
      readAll();
      if (t.hasAttribute('data-tr-add')) {
        var lastDay = D.ports.length ? D.ports[D.ports.length - 1].day : D.show_from;
        D.ports.push({ day: lastDay, port: '', arrive: '07:00', depart: '17:00', note: '' });
        paint();
      } else if (t.hasAttribute('data-tr-del')) {
        D.ports.splice(+t.getAttribute('data-tr-del'), 1);
        paint();
      } else if (t.hasAttribute('data-tr-check')) {
        api('POST', 'api/admin/trip/check').then(function (v) { var d = D; take(v); D = d; paint(); toast('Listening for the ship…'); }).catch(function (e2) { toast(e2.message, true); });
      } else {
        var key = r.querySelector('[data-tr="aisstream_key"]');
        var body = Object.assign({}, D, { check_minutes: +D.check_minutes || 10 });
        if (key && key.value.trim()) body.aisstream_key = key.value.trim();
        t.disabled = true;
        api('PUT', 'api/admin/trip', body).then(function (v) { take(v); paint(); toast('Trip saved'); })
          .catch(function (e2) { toast(e2.message, true); }).then(function () { t.disabled = false; });
      }
    });
  }

  window.TripAdmin = {
    html: function () { return '<div id="tr-root">' + inner() + '</div>'; },
    wire: wire
  };
})();
