/* Doorpost client. Plain ES2017 for the frame's Chrome 106 WebView.
   Polls /api/frame every 30s and renders one of seven screens:
   Today, Chores, Calendar, Screen Time, Lists, Photos (idle) and Night.
   Lays out wide (1280x800) or tall (800x1280): a frame hung on its side
   gets the tall layout by itself (or force one with ?layout=tall / ?layout=wide). */
(function () {
  'use strict';

  var I = window.ICONS;
  var stage = document.getElementById('stage');
  var overlay = document.getElementById('overlay');
  var S = {
    data: null, screen: 'today', kid: null, calView: 'week',
    calOffset: { week: 0, rolling: 0, month: 0 }, calAlt: {}, calLoading: {}, calShown: null, dayDate: null, dayEvent: null,
    skew: 0, lastTouch: Date.now(), wakeUntil: 0, swallowClick: false,
    overlay: null, pin: '', msg: '', token: null, tokenUntil: 0, busy: false,
    photoIdx: -1, photoLayer: 0, photoTimer: null, photos: [], photosVersion: null, photosLoading: false, photoPending: 0,
    view: readView(), who: '', ok: '', adj: { kid: 'all', minutes: 0, scope: 'family', why: '' }, confirmWeek: false,
    home: readHome(), list: null, addText: '', addList: null, addMsg: '', tall: false,
    frameId: '', frames: null, pinNext: '', pendingFrame: '', newLook: 'navy', showName: 0
  };
  // Each frame remembers which picture the kids left the Screen Time panel on.
  function readView() { try { return localStorage.getItem('ff.screenView') || ''; } catch (e) { return ''; } }
  function saveView(v) { try { localStorage.setItem('ff.screenView', v); } catch (e) { /* storage off: just don't remember */ } }
  // ...and which Home panel (Chores, Groceries, Weather, Screen time) and which view inside it.
  function readHome() { try { return JSON.parse(localStorage.getItem('ff.home') || '{}') || {}; } catch (e) { return {}; } }
  function saveHome() { try { localStorage.setItem('ff.home', JSON.stringify(S.home)); } catch (e) { /* don't remember */ } }
  var LAYOUT = (/[?&]layout=(tall|wide)/.exec(location.search) || [])[1] || '';
  // Which frame this is (Settings > Frames): from the address (/frame/kids) or remembered on the frame.
  var PATH_FRAME = (/\/frame\/([a-z0-9-]+)\/?$/.exec(location.pathname) || [])[1] || '';
  function readFrame() { try { return localStorage.getItem('ff.frame') || ''; } catch (e) { return ''; } }
  function saveFrame(id) { try { localStorage.setItem('ff.frame', id); } catch (e) { /* not remembered */ } }
  function hasOtherState() { try { return !!(localStorage.getItem('ff.home') || localStorage.getItem('ff.screenView')); } catch (e) { return true; } }
  function frameOf() { return (S.data && S.data.frame) || { id: '', name: '', look: 'navy', home: 'today', screens: ['today', 'calendar', 'chores', 'screen', 'lists', 'photos'], approvals: true }; }
  function homeScreen() { return frameOf().home || 'today'; }
  function shows(screen) { return frameOf().screens.indexOf(screen) >= 0; }
  // Settings > Modules: the ones that are on come with every payload (an older server sends none: all on).
  function on(mod) { var m = S.data && S.data.modules; return !m || m.indexOf(mod) >= 0; }
  S.frameId = PATH_FRAME || readFrame();
  function isTall() { return LAYOUT ? LAYOUT === 'tall' : window.innerHeight > window.innerWidth * 1.05; }
  var NUMBERS = ['nothing scheduled', 'one thing', 'two things', 'three things', 'four things', 'five things',
    'six things', 'seven things', 'eight things', 'nine things', 'ten things'];

  // ---------------- helpers ----------------
  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function $(id) { return document.getElementById(id); }
  // Only touch the page when a screen's content actually changed: rebuilding unchanged screens
  // (with their picture panels) every few seconds made taps feel slow on the frame's tablet.
  function setHTML(el, html) {
    if (el._html === html) return;
    el._html = html;
    el.innerHTML = html;
  }
  // Lay out at 800 px on the short side and stretch the long side to the screen's shape
  // (16:10 like the kitchen frame, or 16:9 like most 15.6" and 21.5" frames), then scale to fit.
  function fit() {
    var tall = isTall(), r = tall ? window.innerHeight / window.innerWidth : window.innerWidth / window.innerHeight;
    var long = Math.round(Math.min(Math.max(800 * (r || 1.6), 1200), 1440));
    var w = tall ? 800 : long, h = tall ? long : 800;
    stage.style.width = w + 'px'; stage.style.height = h + 'px';
    if (tall !== S.tall) {  // turned on its side: lay every screen out again
      S.tall = tall;
      document.body.classList.toggle('vert', tall);
      Array.prototype.forEach.call(document.querySelectorAll('.screen, #ph-over'), function (el) { el._html = null; });
      if (S.data) render();
    }
    var s = Math.min(window.innerWidth / w, window.innerHeight / h);
    stage.style.transform = 'translate(' + (window.innerWidth - w * s) / 2 + 'px,' +
      (window.innerHeight - h * s) / 2 + 'px) scale(' + s + ')';
  }
  function localNow() {
    var off = S.data ? S.data.tz_offset_min : -new Date().getTimezoneOffset();
    return new Date(Date.now() + S.skew + off * 60000); // read with getUTC*
  }
  function clock() {
    var d = localNow(), h = d.getUTCHours(), m = d.getUTCMinutes();
    return { t: ((h % 12) || 12) + ':' + (m < 10 ? '0' : '') + m, ap: h < 12 ? 'AM' : 'PM' };
  }
  function kidById(id) {
    var ks = S.data.kids;
    for (var i = 0; i < ks.length; i++) if (ks[i].id === id) return ks[i];
    return ks[0];
  }
  function sources() {
    var m = {};
    S.data.calendar.sources.forEach(function (s) { m[s.key] = s; });
    return m;
  }
  // A kid's face photo if one was added in Admin, otherwise their initial on their color.
  function av(k, cls) {
    if (k.photo) {
      return '<span class="av ' + cls + ' face" role="img" aria-label="' + esc(k.name) + '" style="background:' + esc(k.color) +
        ' url(\'' + esc(k.photo) + '\') center/cover no-repeat"></span>';
    }
    return '<span class="av ' + cls + '" style="background:' + esc(k.color) + '">' + esc(k.initial) + '</span>';
  }
  function api(method, url, body) {
    var headers = { 'Content-Type': 'application/json' };
    if (S.token) headers['X-Parent-Token'] = S.token;
    return fetch(url, { method: method, headers: headers, body: body ? JSON.stringify(body) : undefined })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) { j._status = r.status; return j; });
      });
  }

  // ---------------- what a look can change (theme.json, docs/themes.md) ----------------
  // A look's own words for a few places ("words" in theme.json). Each key's text without a look's words is here.
  var WORDS = { today_title: 'Today', tomorrow: 'Tomorrow', next_prefix: 'Next', things_count: '{words}', night_title: '', night_sub: '',
    pin_title: 'Parent tools', pin_sub: 'Enter the parent PIN.', kids_grownups: 'Grown-ups', chores_title: '{name}’s Chores', kids_hi: 'Hi, {name}!',
    tod_morning: 'Good morning', tod_afternoon: 'Good afternoon', tod_evening: 'Good evening' };
  function word(key, fill) {   // plain text: esc() it before it goes on the page
    var w = (frameOf().look_words || {})[key];
    fill = fill || {};
    return (typeof w === 'string' ? w : WORDS[key] || '').replace(/\{(\w+)\}/g, function (m, k) { return fill.hasOwnProperty(k) ? String(fill[k]) : m; });
  }
  // "Thursday · October 15", or "Thursday, the Fifteenth of October" for a look with "date_style": "long".
  function dateLabel() { var d = S.data; return frameOf().look_date_style === 'long' && d.date_long ? d.date_long : d.date_label; }
  function timeOfDay() { var h = localNow().getUTCHours(); return word(h < 12 ? 'tod_morning' : h < 17 ? 'tod_afternoon' : 'tod_evening'); }
  // The family monogram: the drawn monogram, with the family's letter inside for a look that shows a typeset initial
  // (theme.json "monogram": "initial" puts body.mono-initial on the frame). size: its width in px (CSS var --ms).
  function mono(size, cls, label) {
    var ini = (S.data && S.data.initial) || '';
    return '<span class="mono' + (cls ? ' ' + cls : '') + '" data-initial="' + esc(ini) + '"' +
      (label ? ' role="img" aria-label="Family monogram"' : ' aria-hidden="true"') + (size ? ' data-size style="--ms:' + size + 'px"' : '') +
      '><i class="mono-i" aria-hidden="true">' + esc(ini) + '</i></span>';
  }
  // A kids' look (theme.json "kids": true): a Grown-ups button in the nav opens the parent PIN.
  function grownups() {
    var f = frameOf();
    return f.look_kids && f.approvals ? '<button class="btn-chip grownups" data-act="open-pin">' + I('lock', 18) + '<span>' + esc(word('kids_grownups')) + '</span></button>' : '';
  }

  // ---------------- shared pieces ----------------
  function band(left, right, tall) {
    return '<header class="band' + (tall ? ' tall' : '') + '"><div class="band-left">' + left +
      '</div><div class="band-right">' + right + '</div></header>';
  }
  function bandTitle(size, script, kicker) {
    return mono(size, '', true) +
      '<div><div class="script">' + esc(script) + '</div><div class="kicker">' + esc(kicker) + '</div></div>';
  }
  function tabs(active) {
    var items = [['today', 'home', 'Today'], ['kids', 'home', 'Home'], ['clock', 'clock', 'Clock'], ['calendar', 'calendar', 'Calendar'], ['chores', 'chores', 'Chores'],
      ['screen', 'hourglass', 'Screen Time']];
    var L = S.data.lists, hl = homeList();
    if (L && L.lists.length) items.push(['lists', 'list', 'Lists']);
    items.push(['photos', 'photos', 'Photos']);
    items = items.filter(function (t) { return shows(t[0]); });  // this frame's screens (Settings > Frames)
    return '<div class="tabs" role="tablist">' + items.map(function (t) {
      var badge = t[0] === 'lists' && hl && hl.open && active !== 'lists' ? '<span class="badge">' + hl.open + '</span>' : '';
      return '<button class="tab' + (t[0] === active ? ' on' : '') + '" data-act="go" data-to="' + t[0] + '"' +
        (t[0] === active ? ' aria-current="page"' : '') + '>' + I(t[1]) + '<span>' + t[2] + '</span>' + badge + '</button>';
    }).join('') + '</div>';
  }
  function homebar() {
    var home = S.data.home || [];
    if (!home.length) return '';
    return '<div class="homebar" aria-label="Home status">' + home.map(function (h) {
      return '<span class="' + (h.alert ? 'alert' : '') + '">' + I(h.icon, 18) + esc(h.text) + '</span>';
    }).join('') + '</div>';
  }

  // ---------------- Today (Home) ----------------
  // Settings > General: 62° or 62°F, and where wind shows (panel / everywhere / off).
  function deg(w) { return '°' + (w && w.display && w.display.letter ? ((w.units && w.units.temp) || 'F') : ''); }
  function windText(w, where) {
    var show = (w && w.display && w.display.wind) || 'panel';
    if (!w || w.wind == null || show === 'off' || (where === 'top' && show !== 'everywhere')) return '';
    return 'Wind ' + w.wind + ' ' + esc((w.units && w.units.wind_label) || 'mph');
  }
  function weatherBand(w) {
    if (!w) return '';
    var wind = windText(w, 'top');
    return '<span class="vrule"></span><div class="wx">' + I(w.icon, 46, 1.4) +
      '<span class="temp">' + (w.temp == null ? '–' : w.temp + deg(w)) + '</span><div><div class="txt">' + esc(w.text) +
      '</div><div class="sub">' + (w.high != null ? 'H ' + w.high + '° · ' : '') + (w.low != null ? 'L ' + w.low + '° · ' : '') +
      esc(w.phrase) + (wind ? ' · ' + wind : '') + '</div></div></div>';
  }
  function homeList() {
    var L = S.data && S.data.lists;
    if (!L || !L.home) return null;
    for (var i = 0; i < L.lists.length; i++) if (L.lists[i].id === L.home) return L.lists[i];
    return null;
  }
  function allChoresDone() {
    return S.data.kids.every(function (k) { return k.chores.every(function (c) { return c.status !== 'todo'; }); });
  }
  function homeTabs() {
    var hl = homeList(), out = on('chores') ? [['chores', 'Chores']] : [];
    if (hl) out.push(['groceries', hl.name]);
    if (S.data.weather) out.push(['weather', 'Weather']);
    return on('screen_time') && S.data.screen ? out.concat([['screen', 'Screen time']]) : out;
  }
  // The panel the frame remembers. Once every chore is done for the day, Weather takes over,
  // unless the grocery list was picked today (it holds for the day) or a panel was picked after that.
  function homeTab() {
    var h = S.home, keys = homeTabs().map(function (t) { return t[0]; }), tab = h.tab || 'chores';
    if (keys.indexOf(tab) < 0) tab = keys[0] || '';
    if (allChoresDone() && keys.indexOf('weather') >= 0) {
      var today = h.day === S.data.now.slice(0, 10);
      if (!(today && (tab === 'groceries' || h.after))) tab = 'weather';
    }
    return tab;
  }
  function seg(act, a, b, on) {
    return '<span class="seg2" role="group">' + [a, b].map(function (x, i) {
      return '<button class="' + (on === i ? 'on' : '') + '" data-act="' + act + '" data-v="' + x[0] + '" aria-pressed="' + (on === i) + '">' + x[1] + '</button>';
    }).join('') + '</span>';
  }
  function choresPanel() {
    var mode = S.home.chores === 'done' ? 'done' : 'todo', d = S.data, todo = 0, done = 0, max = S.tall ? 4 : 3;
    d.kids.forEach(function (k) { k.chores.forEach(function (c) { if (c.status === 'todo') todo++; else done++; }); });
    var rows = d.kids.map(function (k) {
      var mine = k.chores.filter(function (c) { return mode === 'todo' ? c.status === 'todo' : c.status !== 'todo'; });
      var chips;
      if (!k.chores.length) chips = '<i class="hp-none">No chores today</i>';
      else if (!mine.length) chips = mode === 'todo' ? '<span class="chip good">All done!</span>' : '<i class="hp-none">Nothing yet today</i>';
      else {
        chips = mine.slice(0, max).map(function (c) {
          return c.status === 'waiting' ? '<span class="hchip wait">' + I('clock', 14, 2.2) + esc(c.title) + '</span>'
            : c.status === 'done' ? '<span class="hchip done">' + I('check', 14, 2.6) + esc(c.title) + ' <b>+' + c.minutes + '</b></span>'
            : '<span class="hchip">' + esc(c.title) + ' <b>+' + c.minutes + '</b></span>';
        }).join('') + (mine.length > max ? '<span class="hchip more">+' + (mine.length - max) + '</span>' : '');
      }
      return '<button class="hp-kid" data-act="kid" data-kid="' + esc(k.id) + '">' + av(k, 's') + '<b>' + esc(k.name) + '</b><span class="hp-chips">' + chips + '</span></button>';
    }).join('');
    return '<div class="hp-head"><h3>' + (mode === 'todo' ? (todo ? 'Still to do' : 'Everything’s done!') : 'Done today') + '</h3>' +
      seg('hchores', ['todo', 'To do · ' + todo], ['done', 'Done · ' + done], mode === 'todo' ? 0 : 1) + '</div><div class="hp-body">' + rows + '</div>';
  }
  function listItemRow(it, canCheck) {
    return '<div class="li' + (it.waiting ? ' waiting' : '') + '">' +
      (canCheck ? '<button class="ring" data-act="list-toggle" data-id="' + esc(it.id) + '" aria-label="Check off ' + esc(it.title) + '"></button>' : '<span class="ring"></span>') +
      '<div class="li-t"><b>' + esc(it.title) + '</b>' + (it.notes && !it.frame ? ' <small>' + esc(it.notes) + '</small>' : '') +
      (it.frame ? ' <small class="ff">added on the frame</small>' : '') + '</div>' +
      (it.waiting ? '<span class="li-wait" title="Waiting to sync">' + I('clock', 16, 2) + '</span>' : '') + '</div>';
  }
  function groceriesPanel() {
    var L = S.data.lists, hl = homeList(), max = S.tall ? 4 : S.data.calendar.upcoming ? 3 : 4;
    var items = hl.items.slice(0, max).map(function (it) { return listItemRow(it, L.can_check); }).join('');
    if (!hl.items.length) items = '<p class="empty">Nothing on the list. Nice.</p>';
    var more = hl.items.length > max ? '<p class="hp-more">and ' + (hl.items.length - max) + ' more</p>' : '';
    return '<div class="hp-head"><h3>' + esc(hl.name) + (hl.open ? ' · ' + hl.open + ' to buy' : '') + '</h3><span class="hp-sync">' +
      esc(shortSync(hl.synced !== undefined ? hl : L, hl.source)) + '</span></div>' +
      '<div class="hp-body">' + items + more + '</div><div class="hp-btns">' +
      (L.can_add ? '<button class="btn-primary" data-act="list-add" data-list="' + esc(hl.id) + '">' + I('plus', 20, 2.4) + 'Add</button>' : '') +
      '<button class="btn-outline" data-act="go" data-to="lists">Open Lists ' + I('chevron-right', 18, 2.2) + '</button></div>';
  }
  function weatherPanel() {
    var w = S.data.weather, days = S.home.weather === 'days';
    var head = '<div class="hp-head"><h3>' + (days ? 'Next 3 days' : 'Today') + '</h3>' +
      seg('hweather', ['today', 'Today'], ['days', '3 days'], days ? 1 : 0) + '</div>';
    if (days) {
      var rolling = S.data.calendar.rolling.days;
      var cards = (w.days || []).slice(0, 3).map(function (x, i) {
        var sp = rolling[i] && rolling[i].special && rolling[i].special.kind !== 'sunday' ? rolling[i].special : null;
        return '<div class="wday' + (sp ? ' sp' : '') + '"><b>' + esc(x.name) + '</b>' + I(x.icon, 46, 1.4) +
          '<div><span class="hi">' + (x.high == null ? '–' : x.high + '°') + '</span> <span class="lo">' + (x.low == null ? '' : x.low + '°') + '</span></div>' +
          '<span class="wt">' + esc(x.text) + '</span><span class="wr">' + x.rain + '% rain</span>' +
          (sp ? '<span class="wsp">' + spIcon(sp, 12) + esc(sp.title) + '</span>' : '') + '</div>';
      }).join('');
      return head + '<div class="hp-body"><div class="wdays">' + (cards || '<p class="empty">No forecast right now.</p>') + '</div></div>';
    }
    var hours = (w.hours || []).map(function (h) {
      return '<div class="wh"><span>' + esc(h.label) + '</span>' + I(h.icon, 30, 1.5) + '<b>' + (h.temp == null ? '–' : h.temp + '°') + '</b></div>';
    }).join('');
    return head + '<div class="hp-body"><div class="wnow">' + I(w.icon, 58, 1.3) + '<span class="wtemp">' + (w.temp == null ? '–' : w.temp + deg(w)) + '</span>' +
      '<div><div class="wtxt">' + esc(w.text) + '</div><div class="wsub">' + (w.high != null ? 'High ' + w.high + '° · ' : '') +
      (w.low != null ? 'Low ' + w.low + '° · ' : '') + esc(w.phrase) +
      (windText(w, 'panel') ? ' · ' + windText(w, 'panel') : '') + '</div></div></div>' +
      (hours ? '<div class="whours">' + hours + '</div>' : '') +
      (w.note ? '<div class="wnote">' + I('alert', 18, 2) + esc(w.note) + '</div>' : '') + '</div>';
  }
  function screenMini() {
    var sc = S.data.screen;
    var rows = S.data.kids.map(function (k) {
      return '<div class="st-row">' + av(k, 's') + '<span class="nm">' + esc(k.name) + '</span>' +
        '<span class="bar"><span style="width:' + k.bar + '%;background:' + esc(k.color) + '"></span></span>' +
        (k.earned ? '<span class="amt">+' + esc(k.earned_label) + '</span>' : '<span class="amt none">none yet</span>') + '</div>';
    }).join('');
    return '<div class="hp-head"><h3>' + esc(sc.headline) + '</h3><span class="hp-total">' + esc(sc.total_label) + '</span></div>' +
      '<div class="hp-body tap" data-act="go" data-to="screen">' + (sc.error ? '<p class="aside">' + esc(sc.error) + '</p>' : '') + rows + '</div>';
  }
  function renderToday() {
    var d = S.data, c = clock(), src = sources();
    var right = '<div class="clock"><span class="t">' + c.t + '</span><span class="ap">' + c.ap + '</span><span class="tod">' + esc(timeOfDay()) + '</span></div>' +
      weatherBand(d.weather);
    var html = band(bandTitle(86, d.family_name, dateLabel()), right, true) + specialRibbon();

    var evs = d.calendar.today, room = S.tall ? 4 : (d.calendar.upcoming ? 6 : 7), shown = evs.slice(0, room);
    var list = shown.map(function (e) {
      var s = src[e.cal] || {};
      var cls = 'ev' + (e.next ? ' next' : e.past ? ' past' : '');
      var who = e.who ? '<div class="who">' + esc(e.who) + '</div>' : '';
      var body = e.next
        ? '<div class="row"><div style="min-width:0"><div class="ti">' + esc(e.title) + '</div>' + who + '</div>' +
          '<span class="pill-next">' + esc(word('next_prefix')) + ' · ' + esc(e.in) + '</span></div>'
        : '<div style="min-width:0"><div class="ti">' + esc(e.title) + '</div>' + who + '</div>';
      return '<div class="' + cls + '"><span class="tm">' + esc(e.time) + '</span><span class="dot" style="background:' +
        esc(s.color) + '"></span>' + body + '</div>';
    }).join('');
    if (!evs.length) list = '<p class="empty">Nothing on the calendar today.</p>';
    if (evs.length > shown.length) list += '<p class="aside" style="padding-top:6px">and ' + (evs.length - shown.length) + ' more on the Calendar</p>';
    var t = d.calendar.tomorrow_first;
    var foot = t ? '<div class="foot"><b>' + esc(word('tomorrow')) + '</b> · <i>' + esc(t.all_day ? t.title : t.time + ' ' + t.title) + '</i></div>' : '';

    // The flip panel: Chores · Groceries · Weather · Screen time
    var tab = homeTab();
    var flip = '<div class="htabs" role="tablist">' + homeTabs().map(function (x) {
      return '<button class="' + (x[0] === tab ? 'on' : '') + '" data-act="htab" data-tab="' + x[0] + '" aria-selected="' + (x[0] === tab) + '">' + esc(x[1]) + '</button>';
    }).join('') + '</div>';
    var panel = tab === 'groceries' ? groceriesPanel() : tab === 'weather' ? weatherPanel() : tab === 'screen' ? screenMini() : tab === 'chores' ? choresPanel() : '';

    var tiles = d.kids.map(function (k) {
      var ct = !k.total ? 'No chores' : k.done === k.total ? 'All done!' : k.done + ' of ' + k.total + ' done';
      var pct = k.total ? Math.round(100 * k.done / k.total) : 0;
      // .kbar (how much is done) and .kwbadge ("1 waiting") are hidden unless a look shows them (docs/themes.md)
      return '<button class="ktile' + (k.total && k.done === k.total ? ' all-done' : '') + (k.waiting_count ? ' has-waiting' : '') + '" data-act="kid" data-kid="' + esc(k.id) +
        '" style="--kc:' + esc(k.color) + ';--kpct:' + pct + '%"><span class="kav">' + av(k, 'k') +
        (k.waiting_count ? '<span class="kwait" aria-label="' + k.waiting_count + ' waiting for a parent">' + k.waiting_count + '</span>' : '') +
        '</span><b>' + esc(k.name) + '</b><span class="kct' + (k.total && k.done === k.total ? ' good' : '') + '">' + ct + '</span>' +
        '<span class="kbar" aria-hidden="true"><i style="width:' + pct + '%"></i></span>' +
        (k.waiting_count ? '<span class="kwbadge">' + k.waiting_count + ' waiting</span>' :
          k.total > 1 && k.total - k.done === 1 ? '<span class="kwbadge almost">Almost!</span>' : '') + '</button>';
    }).join('');

    var side = !!(tab || on('chores'));
    html += '<div class="body"><div class="main home-main"' + (side ? '' : ' style="grid-template-columns:minmax(0,1fr)"') + '>' +
      '<section class="card today-card" aria-label="Today\'s schedule"><div class="card-head" style="padding-bottom:4px"><h2>' + esc(word('today_title')) + '</h2>' +
      '<span class="aside">' + esc(word('things_count', { n: evs.length, words: NUMBERS[evs.length] || evs.length + ' things' })) + '</span></div>' + list + foot + '</section>' +
      (side ? '<div class="home-side">' +   // a module that is off leaves its piece out (Settings > Modules)
      (tab ? '<section class="card hpanel" aria-label="' + esc(tab) + '">' + flip + panel + '</section>' : '') +
      (on('chores') ? '<section class="card krow" aria-label="Chores by kid"><div class="card-head"><h2>Tap your name for your chores</h2>' +
      (d.kids.some(function (k) { return k.waiting_count; }) ? '<span class="aside">yellow = waiting for a parent</span>' : '') +
      '</div><div class="ktiles">' + tiles + '</div></section>' : '') + '</div>' : '') + '</div>' +
      '<nav class="nav">' + tabs('today') + homebar() + grownups() + '</nav></div>';
    setHTML($('screen-today'), html);
    fitWeather($('screen-today'));
  }
  // The 3-day weather cards in a short panel (a tall frame, a look with big type): drop the words ("Partly cloudy"),
  // then the picture, before the last line would be cut off. Classes .tight and .tighter on .wdays.
  function fitWeather(root) {
    var w = root.querySelector('.wdays');
    if (!w || w._fit === w.innerHTML) return;
    w._fit = w.innerHTML;
    function over() {
      return Array.prototype.some.call(w.querySelectorAll('.wday'), function (c) { return c.scrollHeight > c.clientHeight + 1; });
    }
    w.classList.remove('tight', 'tighter');
    if (over()) w.classList.add('tight');
    if (over()) w.classList.add('tighter');
  }

  // ---------------- Chores ----------------
  function renderChores() {
    var d = S.data, k = kidById(S.kid), sc = d.screen;
    var picker = '<div class="picker" role="group" aria-label="Pick a kid">' + d.kids.map(function (x) {
      var on = x.id === k.id;
      return '<button class="pick' + (on ? ' on' : '') + '" data-act="kid" data-kid="' + esc(x.id) + '" aria-pressed="' + on + '">' +
        av(x, '') + esc(x.name) + '</button>';
    }).join('') + '</div>';
    var html = band(bandTitle(70, word(frameOf().look_kids ? 'kids_hi' : 'chores_title', { name: k.name }), dateLabel()), picker);

    var list = k.chores.map(function (c) {
      var action;
      if (c.status === 'todo') action = '<button class="btn-primary" data-act="claim" data-id="' + esc(c.id) + '">I did it</button>';
      else if (c.status === 'waiting') action = '<span class="state wait">' + I('clock', 18, 2) + 'Waiting for Mom or Dad</span>';
      else action = '<span class="state done">' + I('check', 18, 2.4) + 'Done · +' + c.minutes + ' min</span>';
      return '<div class="chore ' + c.status + '"><div class="medal" style="--kt:' + esc(k.tint) + ';--kc:' + esc(k.color) + '"><b>' + c.minutes +
        '</b><small>min</small></div><span class="ti">' + esc(c.title) + '</span>' + action + '</div>';
    }).join('');
    if (!k.chores.length) list = '<p class="empty">No chores today. Enjoy it!</p>';

    var maxDay = Math.max.apply(null, k.days.concat([20]));
    var bars = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].map(function (lbl, i) {
      var v = k.days[i];
      return '<div><span class="b" style="height:' + Math.max(6, Math.round(v / maxDay * 62)) + 'px;background:' +
        (v ? esc(k.color) : 'var(--minibar-empty, #E6DDCB)') + '"></span><span class="l">' + lbl + '</span></div>';
    }).join('');
    var allWaiting = d.kids.reduce(function (n, x) { return n + x.waiting_count; }, 0);

    html += '<div class="body"><div class="main chores-main">' +
      '<section class="card" aria-label="Chore list" style="padding:18px 22px">' +
      '<p class="intro">Tap “I did it” when you finish. Mom or Dad will check, and then your minutes are added.</p>' +
      list + '</section>' +
      '<div class="chores-side">' + (!sc ? '' :
      '<section class="card" aria-label="Weekend screen time" style="gap:8px;padding:18px 22px">' +
      '<h2 style="font-family:var(--serif);font-size:24px;font-weight:600">Weekend screen time</h2>' +
      '<div><div class="big-total">' + esc(sc.total_label) + '</div><div class="aside">' + esc(sc.headline) + '</div></div>' +
      '<div style="border-top:1px solid var(--line);padding-top:10px;display:flex;flex-direction:column;gap:6px">' +
      '<div class="leader"><span class="l">' + esc(k.name) + ' added this week</span><span class="dots"></span><span class="v">' +
      (k.earned ? '+' : '') + esc(k.earned_label) + '</span></div>' +
      (k.bonus ? '<div class="leader"><span class="l">' + esc(k.name) + '’s own bonus</span><span class="dots"></span><span class="v">' +
        (k.bonus > 0 ? '+' : '') + k.bonus + ' min</span></div>' : '') +
      (k.waiting_minutes ? '<div class="waitline"><span>Waiting for approval</span><span>+' + k.waiting_minutes + ' min</span></div>' : '') +
      '</div><p class="aside" style="margin-top:auto">Chores approved on the frame this week</p>' +
      '<div class="minibars" style="margin-top:0" aria-hidden="true">' + bars + '</div></section>') +
      (frameOf().approvals ? '<button class="btn-outline" data-act="open-pin">' + I('lock', 20) + 'Parent: approve here' +
      (allWaiting ? ' <span class="count">' + allWaiting + '</span>' : '') + '</button>' : '') + '</div></div>' +
      '<nav class="nav">' + tabs('chores') + homebar() + grownups() + '</nav></div>';
    setHTML($('screen-chores'), html);
  }

  // ---------------- Screen Time ----------------
  var VIEWS = [['leader', 'Leaderboard'], ['vault', 'Vault'], ['rocket', 'Rocket'], ['glass', 'Hourglass']];
  var C = { navy: '#16324F', gilt: '#C9A55A', gs: '#B9A06E', gd: '#8C7A4E', line: '#E2D8C3', soft: '#5E5547',
    card: '#FFFDF8', red: '#C8102E', extra: '#8FA3B8' };
  // font-family="sans" / "serif" are markers: drawVars() turns them into the look's drawing fonts (--draw-sans, --draw-serif).
  var SANS = 'font-family="sans"', SERIF = 'font-family="serif"';
  var FONT = { sans: "var(--draw-sans, 'Libre Franklin', 'Helvetica Neue', Arial, sans-serif)", serif: "var(--draw-serif, 'Playfair Display', Georgia, serif)" };
  var DRAW_NAMES = { '16324F': 'navy', 'C9A55A': 'gilt', 'B9A06E': 'gilt-soft', '8C7A4E': 'gilt-dim', 'E2D8C3': 'line', '5E5547': 'soft',
    'FFFDF8': 'card', 'C8102E': 'red', '8FA3B8': 'extra' };
  var svgN = 0, drawMemo = {}, drawMemoN = 0;
  // The screen time drawings, ready for any look (docs/themes.md): each fixed color becomes
  // fill:var(--draw-navy, var(--art-16324F, #16324F)), so a look can recolor it (--draw-<name>, or --draw-<HEX> for
  // the colors without a name), Match the look recolors it (--art-<HEX>), and with neither it is exactly as drawn.
  function drawVars(svg) {
    if (drawMemo.hasOwnProperty(svg)) return drawMemo[svg];
    var out = svg.replace(/<[a-zA-Z][^<>]*>/g, function (tg) {
      var decl = '';
      tg = tg.replace(/\s(fill|stroke|stop-color)="#([0-9a-fA-F]{6})"/g, function (m, a, h) {
        h = h.toUpperCase();
        decl += a + ':var(--draw-' + (DRAW_NAMES[h] || h) + ',var(--art-' + h + ',#' + h + '));';
        return '';
      }).replace(/\sfont-family="(sans|serif)"/, function (m, f) { decl += 'font-family:' + FONT[f] + ';'; return ''; });
      if (!decl) return tg;
      return / style="/.test(tg) ? tg.replace(' style="', ' style="' + decl) : tg.replace(/\s*(\/?)>$/, ' style="' + decl + '"$1>');
    });
    if (++drawMemoN > 40) { drawMemo = {}; drawMemoN = 0; }
    drawMemo[svg] = out;
    return out;
  }

  function shortMin(m) {        // "6 hr 40", "45 min", "3 hr"
    var h = Math.floor(m / 60), r = m % 60;
    return h ? h + ' hr' + (r ? ' ' + r : '') : r + ' min';
  }
  function views() {
    var on = (S.data.screen.views || []);
    return VIEWS.filter(function (v) { return on.indexOf(v[0]) >= 0; }).concat(on.length ? [] : VIEWS);
  }
  function currentView() {
    var vs = views(), keys = vs.map(function (v) { return v[0]; });
    if (keys.indexOf(S.view) < 0) S.view = keys[0];
    return S.view;
  }
  function t(x, y, txt, attrs) { return '<text x="' + x + '" y="' + y + '" ' + attrs + '>' + txt + '</text>'; }
  function stars() {
    var s = '', pts = [[30, 120], [110, 108], [400, 130], [440, 210], [60, 250], [200, 112], [350, 96], [440, 330], [24, 380],
      [452, 440], [150, 200], [420, 500], [30, 520], [240, 130], [380, 270]];
    pts.forEach(function (p, i) {
      s += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="' + (i % 3 ? 1.5 : 2.4) + '" fill="' + C.gilt + '" opacity="' + (i % 2 ? 0.5 : 0.9) + '"/>';
    });
    return s;
  }
  function kidDot(k, x, y, r, id) {   // a face photo if there is one, else the initial
    var s = '<circle cx="' + x + '" cy="' + y + '" r="' + (r + 3) + '" fill="none" stroke="' + C.gilt + '" stroke-width="1.5"/>' +
      '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="' + esc(k.color) + '"/>';
    if (k.photo) {
      return s + '<clipPath id="kc' + id + '"><circle cx="' + x + '" cy="' + y + '" r="' + r + '"/></clipPath>' +
        '<image href="' + esc(k.photo) + '" x="' + (x - r) + '" y="' + (y - r) + '" width="' + 2 * r + '" height="' + 2 * r +
        '" preserveAspectRatio="xMidYMid slice" clip-path="url(#kc' + id + ')"/>';
    }
    return s + t(x, y + r * 0.36, esc(k.initial), SERIF + ' text-anchor="middle" font-style="italic" font-size="' + r + '" fill="#FFFFFF"');
  }

  function drawLeader(sc, kids, id) {
    var r = 110, cx = 235, cy = 252, circ = 2 * Math.PI * r;
    var segs = [[sc.parts[0].minutes, C.gilt], [sc.parts[1].minutes, C.navy]];
    kids.forEach(function (k) { segs.push([k.earned, k.color]); });
    segs.push([sc.family_extra, C.extra]);
    var sum = segs.reduce(function (a, b) { return a + Math.max(0, b[0]); }, 0) || 1, off = 0;
    var s = '<rect y="-300" width="470" height="1176" fill="' + C.card + '"/>' +
      '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + C.line + '" stroke-width="38"/>';
    segs.forEach(function (g) {
      if (g[0] <= 0) return;
      var len = g[0] / sum * circ;
      s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + g[1] + '" stroke-width="38" stroke-dasharray="' +
        Math.max(len - 3, 0).toFixed(1) + ' ' + circ.toFixed(1) + '" stroke-dashoffset="' + (-off).toFixed(1) + '" transform="rotate(-90 ' + cx + ' ' + cy + ')"/>';
      off += len;
    });
    s += t(235, 226, sc.weekend ? 'THIS WEEKEND' : 'SO FAR', SANS + ' text-anchor="middle" font-size="12" font-weight="700" letter-spacing="2.5" fill="' + C.gd + '"');
    s += t(235, 268, shortMin(sc.total), SERIF + ' text-anchor="middle" font-size="' + (sc.total >= 600 ? 38 : 42) + '" font-weight="700" fill="' + C.navy + '"');
    s += t(235, 294, 'to share', SERIF + ' text-anchor="middle" font-style="italic" font-size="16" fill="' + C.soft + '"');
    var gap = Math.min(80, 400 / Math.max(1, kids.length));
    kids.forEach(function (k, i) {
      var x = 235 + (i - (kids.length - 1) / 2) * gap;
      s += kidDot(k, x, 408, 22, id + '-' + i);
      s += t(x, 454, k.earned ? '+' + k.earned : '–', SANS + ' text-anchor="middle" font-size="15" font-weight="700" fill="' + C.soft + '"');
    });
    var keys = [[C.gilt, sc.parts[0]], [C.navy, sc.parts[1]], ['kids', { minutes: kids.reduce(function (a, k) { return a + k.earned; }, 0), short: 'by the kids' }]];
    keys.forEach(function (kk, i) {
      var x = 26 + i * 148;
      if (kk[0] === 'kids') { kids.slice(0, 4).forEach(function (k, j) { s += '<rect x="' + x + '" y="' + (476 + j * 3) + '" width="12" height="3" fill="' + esc(k.color) + '"/>'; }); }
      else s += '<rect x="' + x + '" y="476" width="12" height="12" rx="2" fill="' + kk[0] + '"/>';
      s += t(x + 18, 487, '<tspan font-weight="700" fill="' + C.navy + '">' + esc(shortMin(kk[1].minutes)) + '</tspan> ' + esc(kk[1].short), SANS + ' font-size="13" fill="' + C.soft + '"');
    });
    return s;
  }
  function drawVault(sc, kids, id) {
    var s = '<defs><radialGradient id="glow' + id + '" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#F2D27A" stop-opacity=".55"/>' +
      '<stop offset="1" stop-color="#F2D27A" stop-opacity="0"/></radialGradient><linearGradient id="gold' + id + '" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="#F3D684"/><stop offset="1" stop-color="#B28A3E"/></linearGradient></defs>';
    s += '<rect y="-300" width="470" height="1176" fill="' + C.navy + '"/>' + stars();
    s += t(235, 152, shortMin(sc.total), SERIF + ' text-anchor="middle" font-size="58" font-weight="700" fill="' + C.gilt + '"');
    s += t(235, 180, 'in the treasure vault', SERIF + ' text-anchor="middle" font-style="italic" font-size="17" fill="' + C.gs + '"');
    s += '<ellipse cx="235" cy="300" rx="200" ry="110" fill="url(#glow' + id + ')"/>';
    var lidY = sc.weekend ? 200 : 214;
    s += '<path d="M105,300 L365,300 L350,' + lidY + ' L120,' + lidY + ' Z" fill="#5E361A" stroke="' + C.gilt + '" stroke-width="3"/>';
    s += '<path d="M125,294 L345,294 L334,' + (lidY + 11) + ' L136,' + (lidY + 11) + ' Z" fill="#7E4C25"/>';
    var rows = Math.round(sc.pct / 100 * 6);
    function coin(cx, cy) { return '<ellipse cx="' + cx + '" cy="' + cy + '" rx="17" ry="7.5" fill="url(#gold' + id + ')" stroke="#8C6A2A" stroke-width="1"/>'; }
    for (var r = 0; r < rows; r++) for (var c = 0; c < 9 - (r % 2); c++) s += coin(128 + c * 27 + (r % 2) * 13, 306 - r * 11);
    if (sc.pct >= 100) s += coin(170, 232) + coin(235, 226) + coin(300, 232) + coin(204, 240) + coin(268, 240);
    s += '<rect x="95" y="300" width="280" height="150" rx="10" fill="#7A4A22" stroke="' + C.gilt + '" stroke-width="3"/>';
    s += '<rect x="95" y="300" width="280" height="14" fill="' + C.gilt + '"/><rect x="138" y="300" width="14" height="150" fill="' + C.gilt + '"/>' +
      '<rect x="318" y="300" width="14" height="150" fill="' + C.gilt + '"/>';
    s += '<rect x="218" y="334" width="34" height="42" rx="6" fill="' + C.gilt + '"/><circle cx="235" cy="352" r="5.5" fill="' + C.navy + '"/>' +
      '<rect x="233" y="352" width="4" height="12" fill="' + C.navy + '"/>';
    s += '<rect x="70" y="466" width="330" height="10" rx="5" fill="rgba(201,165,90,.22)"/><rect x="70" y="466" width="' +
      (330 * sc.pct / 100).toFixed(1) + '" height="10" rx="5" fill="' + C.gilt + '"/>';
    var txt = sc.pct >= 100 ? 'Full! The vault is ' + (sc.weekend ? 'open' : 'full') : sc.pct + '% full · ' + shortMin(sc.full) + ' fills the vault';
    s += t(235, 498, txt, SERIF + ' text-anchor="middle" font-style="italic" font-size="16" fill="' + C.gilt + '"');
    return s;
  }
  function drawRocket(sc, kids, id) {
    var s = '<defs><linearGradient id="fuel' + id + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F0C766"/>' +
      '<stop offset="1" stop-color="#C8102E"/></linearGradient></defs>';
    s += '<rect y="-300" width="470" height="1176" fill="' + C.navy + '"/>' + stars();
    var top = 124, h = 350, fh = Math.max(12, h * sc.pct / 100);
    s += t(62, 114, 'FUEL', SANS + ' text-anchor="middle" font-size="11" font-weight="700" letter-spacing="2" fill="' + C.gs + '"');
    s += '<rect x="40" y="' + top + '" width="44" height="' + h + '" rx="22" fill="rgba(255,255,255,.06)" stroke="' + C.gd + '" stroke-width="2"/>';
    s += '<rect x="45" y="' + (top + h - fh + 5).toFixed(1) + '" width="34" height="' + (fh - 10).toFixed(1) + '" rx="17" fill="url(#fuel' + id + ')"/>';
    [['FULL', top + 6], ['½', top + h / 2 + 4], ['E', top + h]].forEach(function (l) {
      s += t(92, l[1], l[0], SANS + ' font-size="11" font-weight="700" fill="' + C.gs + '"');
    });
    s += t(285, 150, shortMin(sc.total), SERIF + ' text-anchor="middle" font-size="52" font-weight="700" fill="' + C.gilt + '"');
    s += t(285, 176, 'of fuel for the weekend', SERIF + ' text-anchor="middle" font-style="italic" font-size="16" fill="' + C.gs + '"');
    var fly = sc.weekend, lift = fly ? -34 : 0;
    s += '<g transform="translate(' + (285 - 112 * 1.5) + ' ' + (110 + lift) + ') scale(1.5)">' +
      '<path d="M112,74 C128,94 132,124 130,172 L94,172 C92,124 96,94 112,74 Z" fill="#F3E9D2" stroke="' + C.gilt + '" stroke-width="1.5"/>' +
      '<circle cx="112" cy="120" r="10" fill="' + C.navy + '" stroke="' + C.gilt + '" stroke-width="2.5"/>' +
      '<path d="M95,148 L80,182 L95,174 Z" fill="' + C.red + '"/><path d="M129,148 L144,182 L129,174 Z" fill="' + C.red + '"/>' +
      '<rect x="102" y="172" width="20" height="8" fill="' + C.gd + '"/>' +
      (fly ? '<path d="M100,180 Q112,240 124,180 Z" fill="#F0C766"/><path d="M105,180 Q112,214 119,180 Z" fill="' + C.red + '"/>'
           : '<path d="M105,180 Q112,194 119,180 Z" fill="#F0C766" opacity=".85"/>') + '</g>';
    s += '<rect x="215" y="402" width="140" height="8" rx="3" fill="' + C.gilt + '"/><rect x="352" y="250" width="6" height="152" fill="' + C.gd + '"/>' +
      '<path d="M352,280 L330,280 M352,330 L330,330" stroke="' + C.gd + '" stroke-width="3"/>';
    var big = fly ? (sc.day === 'Sat' ? 'Launch day!' : 'Still flying!') : sc.sleeps + (sc.sleeps === 1 ? ' sleep' : ' sleeps');
    s += t(285, 456, big, SERIF + ' text-anchor="middle" font-size="30" font-weight="600" fill="' + C.gilt + '"');
    s += t(285, 482, fly ? 'enjoy it together' : 'until launch', SANS + ' text-anchor="middle" font-size="14" fill="' + C.gs + '"');
    return s;
  }
  function drawGlass(sc, kids, id) {
    var g = 'M28,22 C28,92 78,120 82,150 C78,180 28,208 28,278 L142,278 C142,208 92,180 88,150 C92,120 142,92 142,22 Z';
    var lvl = 278 - sc.pct / 100 * 116;
    var s = '<defs><clipPath id="gl' + id + '"><path d="' + g + '"/></clipPath><linearGradient id="sand' + id + '" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="#D9B86C"/><stop offset="1" stop-color="#B28A3E"/></linearGradient></defs>';
    s += '<rect y="-300" width="470" height="1176" fill="' + C.card + '"/>';
    s += t(235, 150, shortMin(sc.total), SERIF + ' text-anchor="middle" font-size="52" font-weight="700" fill="' + C.navy + '"');
    s += t(235, 176, 'for the whole family to share', SERIF + ' text-anchor="middle" font-style="italic" font-size="16" fill="' + C.soft + '"');
    s += '<g transform="translate(150 186)"><g clip-path="url(#gl' + id + ')"><rect width="170" height="300" fill="#F3ECDD"/>' +
      '<path d="M0,300 L0,' + (lvl + 26) + ' C40,' + (lvl + 16) + ' 70,' + (lvl + 4) + ' 85,' + lvl + ' C100,' + (lvl + 4) + ' 130,' +
      (lvl + 16) + ' 170,' + (lvl + 26) + ' L170,300 Z" fill="url(#sand' + id + ')"/>';
    if (sc.pct < 100) s += '<path d="M44,22 L126,22 L126,52 C110,70 96,84 85,96 C74,84 60,70 44,52 Z" fill="url(#sand' + id + ')" opacity=".55"/>' +
      '<rect x="84" y="140" width="2" height="' + Math.max(0, lvl - 140) + '" fill="' + C.gilt + '"/>';
    s += '</g><path d="' + g + '" fill="none" stroke="' + C.gd + '" stroke-width="2.5"/>' +
      '<rect x="10" y="8" width="150" height="14" rx="4" fill="' + C.navy + '"/><rect x="10" y="278" width="150" height="14" rx="4" fill="' + C.navy + '"/>' +
      '<rect x="10" y="12" width="150" height="2" fill="' + C.gilt + '"/><rect x="10" y="286" width="150" height="2" fill="' + C.gilt + '"/></g>';
    function lab(x, y, p, anchor) {
      return t(x, y, (p.minutes < 0 ? '−' : '') + esc(shortMin(Math.abs(p.minutes))), SERIF + ' text-anchor="' + anchor + '" font-size="24" font-weight="700" fill="' + C.navy + '"') +
        t(x, y + 20, esc(p.short), SERIF + ' text-anchor="' + anchor + '" font-style="italic" font-size="15" fill="' + C.soft + '"');
    }
    s += lab(138, 300, sc.parts[0], 'end') + lab(332, 262, sc.parts[1], 'start') + lab(332, 382, sc.parts[2], 'start');
    if (sc.parts[3]) s += lab(138, 392, sc.parts[3], 'end');
    return s;
  }
  var DRAW = { leader: drawLeader, vault: drawVault, rocket: drawRocket, glass: drawGlass };
  // meet (the whole picture) or slice (fills the panel): theme.json "picture_fit", else slice when wide, meet when tall.
  function pictureFit() {
    var f = frameOf().look_picture_fit || {}, k = S.tall ? 'tall' : 'wide';
    return f[k] === 'meet' || f[k] === 'slice' ? f[k] : S.tall ? 'meet' : 'slice';
  }

  function screenPanel() {
    var d = S.data, sc = d.screen, v = currentView(), dark = v === 'vault' || v === 'rocket', strip = S.tall ? 56 : 48;
    var pills = views().map(function (x) {
      return '<button class="vp' + (x[0] === v ? ' on' : '') + '" data-act="view" data-view="' + x[0] + '" aria-pressed="' + (x[0] === v) + '">' + x[1] + '</button>';
    }).join('');
    var bottom = '';
    if (sc.weekend) {
      var sat = (sc.day === 'Sat' ? 'Today · ' : '') + 'Saturday ' + shortMin(sc.saturday);
      var sun = (sc.day === 'Sun' ? 'Today · ' : '') + 'Sunday ' + shortMin(sc.sunday);
      bottom = '<div class="pv-share"><span>' + sat + '</span><span>' + sun + '</span></div>';
    } else if (sc.waiting_minutes) {
      bottom = '<div class="waitline pv-wait"><span>Waiting for Mom or Dad</span><span>+' + sc.waiting_minutes + ' min</span></div>';
    }
    return '<section class="card pv ' + (dark ? 'dark' : 'light') + '" aria-label="' + esc(sc.headline) + '">' +
      // The drawing starts below a strip kept for the title and the picture buttons (its background runs up behind them).
      '<svg class="pv-art" data-act="nextview" viewBox="0 ' + (-strip) + ' 470 ' + (576 + strip) + '" preserveAspectRatio="xMidYMid ' + pictureFit() +
      '" role="img" aria-label="' + esc(shortMin(sc.total)) + '">' + drawVars(DRAW[v](sc, d.kids, ++svgN)) + '</svg>' +
      '<div class="pv-top"><div class="card-head"><h2>' + (sc.weekend ? 'Our weekend' : 'Our weekend so far') + '</h2>' +
      '<span class="aside">tap to switch</span></div><div class="vpick" role="group" aria-label="Pick a picture">' + pills + '</div></div>' +
      (bottom ? '<div class="pv-bot">' + bottom + '</div>' : '') + '</section>';
  }

  function renderScreen() {
    var d = S.data, sc = d.screen, c = clock();
    var right = '<div class="clock"><span class="t">' + c.t + '</span><span class="ap">' + c.ap + '</span></div><span class="vrule"></span>' +
      '<div class="count"><div class="big">' + (sc.weekend ? 'It’s the weekend!' : sc.sleeps + (sc.sleeps === 1 ? ' sleep' : ' sleeps')) +
      '</div><div class="sm">' + (sc.weekend ? 'earning starts again Monday' : 'until Saturday') + '</div></div>';
    var who = d.kids.map(function (k) {
      return '<div class="wrow">' + av(k, 'm') + '<span class="nm">' + esc(k.name) + '</span>' +
        '<span class="bar"><span style="width:' + k.bar + '%;background:' + esc(k.color) + '"></span></span>' +
        (k.earned ? '<span class="mn">+' + esc(shortMin(k.earned)) + '</span>' : '<span class="mn none">none yet</span>') + '</div>';
    }).join('');
    var feed = (sc.feed || []).slice(0, S.tall ? 2 : 4).map(function (e) {
      var k = e.kid ? kidById(e.kid) : null;
      return '<div class="fe"><span class="d">' + esc(e.dow) + '</span>' + (k ? av(k, 's') : '<span class="av s all">ALL</span>') +
        '<span class="w">' + esc(e.title) + ' <em>· ' + esc(e.by) + '</em></span><span class="m' + (e.minutes < 0 ? ' neg' : '') + '">' +
        (e.minutes > 0 ? '+' : '') + e.minutes + '</span></div>';
    }).join('') || '<p class="empty">Nothing yet this week. Chores and good days show up here.</p>';
    var html = band(bandTitle(76, 'Screen Time', dateLabel()), right) +
      '<div class="body"><div class="main st-main">' + screenPanel() +
      '<div class="right-col"><section class="card" aria-label="Who filled it this week"><div class="card-head"><h2>Who filled it this week</h2>' +
      '<span class="aside">thank you!</span></div><div class="who">' + who + '</div></section>' +
      '<section class="card" aria-label="How we got here"><div class="card-head"><h2>How we got here</h2><span class="aside">newest first</span></div>' +
      '<div class="feed">' + feed + '</div></section></div></div>' +
      '<nav class="nav">' + tabs('screen') + '<div class="navr">' + homebar() +
      (frameOf().look_kids ? grownups() : frameOf().approvals ? '<button class="btn-chip" data-act="open-pin">' + I('lock', 18) + 'Parent</button>' : '') + '</div></nav></div>';
    setHTML($('screen-screen'), html);
  }

  // ---------------- Calendar ----------------
  function calData(v) {
    var off = S.calOffset[v];
    if (!off) return S.data.calendar[v];
    return S.calAlt[v + ':' + off] || null;  // false = still loading
  }
  // Fetch one week or month (offset from now). A page already on screen stays on screen until
  // the new copy arrives, so nothing ever flashes back to this week while it loads.
  function fetchCal(v, o, delay) {
    var key = v + ':' + o;
    if (S.calLoading[key]) return;
    S.calLoading[key] = true;
    setTimeout(function () {
      fetch('api/calendar?view=' + v + '&offset=' + o + '&frame=' + encodeURIComponent(frameOf().id), { cache: 'no-store' })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (data) {
          delete S.calLoading[key];
          S.calAlt[key] = data;
          if (S.screen === 'calendar' && S.calView === v && S.calOffset[v] === o) render();  // it's the one being looked at
        })
        .catch(function () { delete S.calLoading[key]; if (S.calOffset[v] === o) $('offline').classList.add('on'); });
    }, delay || 0);
  }
  // The weeks or months on either side, ahead of time, so the arrows feel instant.
  function prefetchCal(v) {
    var off = S.calOffset[v];
    [off - 1, off + 1].forEach(function (o) {
      if (o && !S.calAlt[v + ':' + o] && o >= -24 && o <= 60) fetchCal(v, o, 600);
    });
  }
  function loadCal(v) {
    var off = S.calOffset[v];
    if (off && !S.calAlt[v + ':' + off]) fetchCal(v, off);
    render();
  }
  function shortTime(e) {
    return e.all_day ? e.title : e.time.replace(':00', '').replace(' ', '').toLowerCase() + ' ' + e.title;
  }
  // In today's day header and month cell; hidden unless a look shows it (docs/themes.md).
  var DAY_TAG = '<span class="day-tag">Today</span>';
  function renderCalendar() {
    var d = S.data, cal = d.calendar, v = S.calView, src = sources(), data = calData(v);
    // Not here yet (it's on its way): keep showing what's on screen, dimmed, rather than jumping back to this week.
    var waiting = !data;
    if (waiting) data = S.calShown && S.calShown.view === v ? S.calShown : cal[v];
    else S.calShown = data;
    var legend = '<div class="legend" aria-label="Calendars">' + cal.sources.map(function (s) {
      return '<span><i style="background:' + esc(s.color) + '"></i>' + esc(s.label) + '</span>';
    }).join('') + '</div>';
    var toggle = '<div class="toggle" role="group" aria-label="Calendar view">' +
      [['week', 'Sun – Sat'], ['rolling', 'Next 7 days'], ['month', 'Month']].map(function (b) {
        return '<button class="' + (b[0] === v ? 'on' : '') + '" data-act="calview" data-view="' + b[0] + '" aria-pressed="' +
          (b[0] === v) + '">' + b[1] + '</button>';
      }).join('') + '</div>';
    var title = data.title || ({ week: 'This Week', rolling: 'The Next Seven Days' })[v] || data.label;
    var html = band(bandTitle(70, title, v === 'month' ? 'Family calendar – Month view' : data.label), legend + toggle);

    var inner;
    if (v === 'month') {
      var weeks = data.weeks;
      inner = '<div class="month" style="grid-template-rows:20px repeat(' + weeks.length + ',minmax(0,1fr))">' +
        ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(function (x) { return '<div class="mhead">' + x + '</div>'; }).join('') +
        weeks.map(function (wk) {
          return wk.map(function (day) {
            if (day.special) return specialCell(day);
            var hols = (day.holidays || []).map(function (h) { return '<div class="me hol">' + STAR(11) + esc(h) + '</div>'; });
            var items = hols.concat(day.events.map(function (e) {
              var s = src[e.cal] || {};
              return '<div class="me"><i style="background:' + esc(s.color) + '"></i>' + esc(shortTime(e)) + '</div>';
            }));
            var tag = items.length ? 'button' : 'div';
            return '<' + tag + ' class="mcell' + (day.in_month ? '' : ' out') + (day.today ? ' today' : '') + '"' +
              (items.length ? ' data-act="day" data-date="' + day.date + '" aria-label="' +
                esc(day.dow_long + ' ' + day.month + ' ' + day.num + ', ' + day.events.length + ' events') + '"' : '') +
              '><div class="mn">' + day.num + '</div>' + (day.today ? DAY_TAG : '') + items.slice(0, S.tall ? 5 : 3).join('') +
              (items.length > (S.tall ? 5 : 3) ? '<div class="me more-link">+' + (items.length - (S.tall ? 5 : 3)) + ' more</div>' : '') +
              '</' + tag + '>';
          }).join('');
        }).join('') + '</div>';
    } else {
      var groups = dayGroups(data.days), cols = [];
      groups.forEach(function (g) {
        g.forEach(function (day) {
          cols.push(g.length > 1 ? '1.12fr' : day.special ? '1.6fr' : day.today && v === 'rolling' && !S.calOffset.rolling ? '1.45fr' : '1fr');
        });
      });
      inner = '<div class="week-panel ' + v + '">' + '<div class="days' + (v === 'rolling' ? ' rolling' : '') + '" style="grid-template-columns:' +
        cols.map(function (c) { return 'minmax(0,' + c + ')'; }).join(' ') + '">' +
        groups.map(function (g) {
          if (g.length > 1) return spanPanel(g);
          var day = g[0];
          if (day.special) return specialPanel(day, v);
          var hols = (day.holidays || []).map(function (h) { return '<div class="hol">' + STAR(13) + '<span>' + esc(h) + '</span></div>'; }).join('');
          // A very busy day shows what fits and "and N more" (a tap opens the whole day).
          var limit = Math.max(1, (S.tall ? (day.events.length + (day.holidays || []).length > 3 ? 2 : 3) : day.today && v === 'rolling' ? 7 : 6) - (day.holidays || []).length);
          var shown = day.events.slice(0, limit);
          var more = day.events.length > limit;
          return '<section class="day' + (day.today ? ' today' : '') + '" data-date="' + day.date + '" aria-label="' + esc(day.dow_long + ' ' + day.month + ' ' + day.num) + '">' +
            '<div class="dh"><div class="dw">' + (day.today && v === 'rolling' ? 'Today · ' : '') + esc(day.dow) + '</div><div class="dn">' + day.num + '</div>' +
            (day.today ? DAY_TAG : '') + '</div>' +
            '<div class="evs">' + hols + shown.map(function (e) {
              var s = src[e.cal] || {};
              return '<div class="ce' + (e.past || day.past ? ' past' : '') + '" style="--ct:' + esc(s.tint) + '"><div class="ct"><i style="background:' +
                esc(s.color) + '"></i>' + esc(e.time) + '</div><div class="t">' + esc(e.title) + '</div>' +
                (e.who ? '<div class="w">' + esc(e.who) + '</div>' : '') + '</div>';
            }).join('') + (more ? '<button class="more more-link" data-act="day" data-date="' + day.date + '" data-more="' + (day.events.length - limit) +
              '">and ' + (day.events.length - limit) + ' more</button>' : '') +
            (!day.events.length && !hols && S.tall ? '<span class="nothing">Nothing on the calendar</span>' : '') + '</div></section>';
        }).join('') + '</div></div>';
    }
    var off = S.calOffset[v], unit = v === 'month' ? 'month' : 'week';
    var near = neighbors(v, data);
    var pager = '<div class="pager" role="group" aria-label="Browse the calendar">' +
      '<button class="step" data-act="calnav" data-dir="-1" aria-label="Previous ' + unit + ', ' + esc(near[0]) + '">' +
      I('chevron-left', 22, 2.2) + '<span>' + esc(near[0]) + '</span></button>' +
      '<button class="mid' + (off ? ' back' : '') + '" data-act="calnav" data-dir="0"' + (off ? '' : ' disabled') + '>' +
      (off ? 'Back to this ' + unit : 'This ' + unit) + '</button>' +
      '<button class="step" data-act="calnav" data-dir="1" aria-label="Next ' + unit + ', ' + esc(near[1]) + '">' +
      '<span>' + esc(near[1]) + '</span>' + I('chevron-right', 22, 2.2) + '</button></div>';
    html += '<div class="body' + (waiting ? ' loading' : '') + '">' + inner + '<nav class="nav">' + tabs('calendar') + pager + grownups() + '</nav></div>';
    setHTML($('screen-calendar'), html);
    if (v !== 'month') fitDays($('screen-calendar'));
    prefetchCal(v);
  }

  // A day with more than its column holds (bigger type in some looks): hide events from the end until it fits,
  // and say how many more there are. Tapping "and N more" opens the whole day.
  function fitDays(root) {
    Array.prototype.forEach.call(root.querySelectorAll('.day:not(.sp) .evs'), function (evs) {
      if (evs.scrollHeight <= evs.clientHeight + 1) return;
      var items = Array.prototype.filter.call(evs.querySelectorAll('.ce'), function (x) { return x.style.display !== 'none'; });
      var more = evs.querySelector('.more'), n = more ? +more.getAttribute('data-more') : 0;
      if (!more) {
        more = document.createElement('button');
        more.className = 'more more-link'; more.setAttribute('data-act', 'day'); more.setAttribute('data-date', evs.parentNode.getAttribute('data-date'));
        evs.appendChild(more);
      }
      while (items.length > 1) {
        items.pop().style.display = 'none'; n++;
        more.textContent = 'and ' + n + ' more';
        if (evs.scrollHeight <= evs.clientHeight + 1) break;
      }
    });
  }

  // Labels for the arrows: where they lead. Months: "Sep" / "Nov". Weeks: the start date, "Oct 4" / "Oct 18".
  var SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function neighbors(v, data) {
    if (v === 'month') {
      var first = null;
      data.weeks.forEach(function (wk) { wk.forEach(function (d) { if (d.in_month && !first) first = d.date; }); });
      var m = +first.slice(5, 7) - 1;
      return [SHORT[(m + 11) % 12], SHORT[(m + 1) % 12]];
    }
    var p = data.days[0].date.split('-'), base = Date.UTC(+p[0], +p[1] - 1, +p[2]);
    return [-7, 7].map(function (n) {
      var d = new Date(base + n * 86400000);
      return SHORT[d.getUTCMonth()] + ' ' + d.getUTCDate();
    });
  }

  function findDay(date) {
    var v = S.calView, data = calData(v) || S.data.calendar[v];
    var hit = dayIn(data, date);
    if (hit) return hit;
    // A trip can run past the week on screen (Friday to Sunday): look in everything loaded.
    var all = [S.data.calendar.week, S.data.calendar.rolling, S.data.calendar.month];
    Object.keys(S.calAlt).forEach(function (k) { if (S.calAlt[k]) all.push(S.calAlt[k]); });
    for (var i = 0; i < all.length; i++) { hit = dayIn(all[i], date); if (hit) return hit; }
    return null;
  }
  function dayIn(data, date) {
    if (!data) return null;
    var days = data.weeks ? [].concat.apply([], data.weeks) : data.days;
    for (var i = 0; i < days.length; i++) if (days[i].date === date) return days[i];
    return null;
  }
  function addDays(date, n) {
    var p = date.split('-'), d = new Date(Date.UTC(+p[0], +p[1] - 1, +p[2]) + n * 86400000);
    return d.getUTCFullYear() + '-' + ('0' + (d.getUTCMonth() + 1)).slice(-2) + '-' + ('0' + d.getUTCDate()).slice(-2);
  }

  // ---------------- special days ----------------
  // A flagged event (⭐ in the title), a chosen holiday or a church-year day takes over its day (app/special.py).
  function STAR(n) {
    return '<svg width="' + n + '" height="' + n + '" viewBox="0 0 24 24" fill="#C9A55A" aria-hidden="true" class="star">' +
      '<path d="M12 2l2.9 6.6 7.1.6-5.4 4.7 1.6 7L12 17.3 5.8 21l1.6-7L2 9.2l7.1-.6z"></path></svg>';
  }
  function CROSS(n) {
    return '<svg width="' + n + '" height="' + n + '" viewBox="0 0 24 24" fill="#C9A55A" aria-hidden="true" class="star">' +
      '<path d="M10.5 2h3v6h5v3h-5v11h-3V11h-5V8h5z"></path></svg>';
  }
  function spIcon(sp, n) { return sp.icon === 'cross' ? CROSS(n) : sp.icon === 'star' ? STAR(n) : ''; }
  // The picture: an uploaded photo, or a drawing from an art pack (art.js, app/packs.py). how: '' tall, 'mid' centered, 'wide' banner.
  // The amusement park picture's sign says the park's name, sized to fit.
  function fillPlace(svg, place) {
    if (svg.indexOf('{{PLACE}}') < 0) return svg;
    place = place || 'Park day';
    return svg.replace('{{PLACE_SIZE}}', String(Math.min(26, Math.round(150 / (0.5 * place.length))))).replace('{{PLACE}}', esc(place));
  }
  // The birthday picture: the person's name on the banner and their photo in the round window (app/portraits.py).
  function fillPerson(svg, sp) {
    if (svg.indexOf('{{NAME}}') >= 0) {
      var name = sp.name || '';
      svg = svg.replace('{{NAME_SIZE}}', String(Math.min(24, Math.round(260 / Math.max(5, name.length))))).replace('{{NAME}}', esc(name));
    }
    if (svg.indexOf('{{PORTRAIT}}') >= 0) {
      // Its own name for the round window each time: a copy in a hidden panel would otherwise leave the photo unclipped.
      svg = svg.split('bdwin').join('bdwin' + (++fillPerson.n));
      svg = svg.replace('{{PORTRAIT}}', sp.portrait ? '<image href="' + esc(sp.portrait) + '" x="76" y="190" width="148" height="148" preserveAspectRatio="xMidYMid slice"></image>' : '');
    }
    return svg;
  }
  fillPerson.n = 0;
  // place: where this copy goes ('day', 'cell', 'rib', 'pop', ...). Each copy's ids get it as a suffix, so two copies of a
  // drawing on the page never share gradients or clip paths (a copy in a hidden screen would blank the other's).
  function spArt(sp, how, place) {
    var tag = ((place || how || 'x') + '-' + (sp.date || '') + (sp.key || sp.theme || '')).replace(/[^\w-]/g, '');
    return artMatch(uniqIds(fillPerson(fillPlace(spArt0(sp, how), sp.place), sp), tag));
  }
  function uniqIds(svg, tag) {
    var ids = svg.match(/\sid="[^"]+"/g);
    if (!ids) return svg;
    ids.forEach(function (m) {
      var id = m.slice(5, -1), to = id + '-' + tag;
      svg = svg.split('id="' + id + '"').join('id="' + to + '"').split('#' + id + ')').join('#' + to + ')').split('"#' + id + '"').join('"#' + to + '"');
    });
    return svg;
  }
  // Pictures: Match the look (Settings > Frames; themes/, app/themes.py). Each fixed color in a picture becomes a CSS
  // variable its look sets in /themes.css, with the color as drawn as the fallback. Original: left exactly as drawn.
  var artMemo = {}, artMemoN = 0;
  function artMatch(svg) {
    if (frameOf().pictures !== 'match' || !svg || svg.charAt(0) !== '<') return svg;
    if (artMemo.hasOwnProperty(svg)) return artMemo[svg];
    var out = svg.replace(/<[a-zA-Z][^<>]*>/g, function (t) {
      var decl = '';
      t = t.replace(/\s(fill|stroke|stop-color)="#([0-9a-fA-F]{6})"/g, function (m, a, h) {
        h = h.toUpperCase();
        decl += a + ':var(--art-' + h + ',#' + h + ');';
        return '';
      });
      if (!decl) return t;
      return / style="/.test(t) ? t.replace(' style="', ' style="' + decl) : t.replace(/\s*(\/?)>$/, ' style="' + decl + '"$1>');
    });
    if (++artMemoN > 60) { artMemo = {}; artMemoN = 0; }
    artMemo[svg] = out;
    return out;
  }
  function spArt0(sp, how) {
    var th = window.THEMES || {};
    if (sp.photo) return '<span class="sp-photo" style="background-image:url(\'' + esc(sp.photo) + '\')"></span>';
    if (sp.svg) return how ? sp.svg.replace(/(x(?:Min|Mid|Max))YMax slice/, '$1YMid slice') : sp.svg;  // Lord's Day pictures come with the day
    if (how === 'wide' && th[sp.theme + '-wide']) return th[sp.theme + '-wide'];
    var svg = th[sp.theme] || th.pattern || '';
    if (how) svg = svg.replace(/(x(?:Min|Mid|Max))YMax slice/, '$1YMid slice');   // keep the picture's own left/right anchor
    return svg + (sp.theme === 'pattern' ? mono(0, 'sp-mono') : '');
  }
  function spEvent(day) {
    var sp = day.special;
    if (!sp || sp.kind !== 'event') return null;
    for (var i = 0; i < day.events.length; i++) if (day.events[i].uid === sp.uid) return day.events[i];
    return null;
  }
  function spOthers(day) {
    var own = spEvent(day);
    return day.events.filter(function (e) { return e !== own; });
  }
  function toMin(label) {  // "9:30 AM" -> 570
    var m = /(\d+):(\d+)\s*([AP])M/i.exec(label || '');
    return m ? (+m[1] % 12) * 60 + +m[2] + (m[3].toUpperCase() === 'P' ? 720 : 0) : null;
  }
  // Does this event clash with the day's special event (so someone may need to change plans)?
  function overlaps(day, e) {
    var own = spEvent(day);
    if (!own || e === own) return false;
    if (own.all_day || e.all_day) return true;
    var a = toMin(own.time), b = toMin(own.end_time) || a + 60, c = toMin(e.time), d = toMin(e.end_time) || c + 30;
    return a == null || c == null || (c < b && d > a);
  }
  function spAlso(day) {
    return (day.holidays || []).concat(spOthers(day).slice(0, 3).map(function (e) {
      return shortTime(e) + (e.who && e.who !== 'everyone' ? ' (' + e.who + ')' : '');
    }));
  }
  function spCard(sp, also) {
    return '<div class="sp-card"><div class="sp-ti">' + spIcon(sp, 16) + '<span>' + esc(sp.title) + '</span></div>' +
      sp.lines.map(function (l) { return '<div class="sp-l">' + esc(l) + '</div>'; }).join('') +
      (sp.countdown ? '<span class="sp-pill">' + esc(sp.countdown) + '</span>' : '') +
      (sp.verse ? '<div class="sp-verse">' + esc(sp.verse) + '</div>' : '') +
      (also.length ? '<div class="sp-also">Also: ' + esc(also.join(' · ')) + '</div>' : '') + '</div>';
  }
  function specialPanel(day, v) {
    var sp = day.special;
    return '<button class="day sp' + (sp.solemn ? ' solemn' : '') + '" data-act="day" data-date="' + day.date + '" aria-label="' +
      esc(day.dow_long + ' ' + day.month + ' ' + day.num + ', ' + sp.title) + '">' + spArt(sp, S.tall ? 'wide' : '', 'day') +
      '<div class="sp-top"><div class="dw">' + (day.today ? 'Today · ' : '') + esc(day.dow) + '</div><div class="dn">' + day.num + '</div>' + (day.today ? DAY_TAG : '') +
      '<div class="sp-script">' + esc(sp.script) + '</div></div>' + spCard(sp, spAlso(day)) + '</button>';
  }
  // A special event over several days (a vacation) becomes one panel across those columns.
  function dayGroups(days) {
    var out = [], i = 0;
    while (i < days.length) {
      var sp = days[i].special, n = 1;
      if (sp && sp.kind === 'event' && sp.span[1] > 1) {
        while (i + n < days.length && days[i + n].special && days[i + n].special.key === sp.key) n++;
      }
      out.push(days.slice(i, i + n));
      i += n;
    }
    return out;
  }
  function spanPanel(days) {
    var sp = days[0].special, a = days[0], b = days[days.length - 1];
    var strip = days.map(function (day) {
      var o = spOthers(day)[0], k = day.special.span;
      return '<div class="sp-mini' + (day.today ? ' today' : '') + '"><div class="sp-mh"><b>' + esc(day.today ? 'Today' : day.dow) + '</b><span class="n">' + day.num +
        '</span><span class="of">Day ' + (k[0] + 1) + ' of ' + k[1] + '</span></div>' +
        '<div class="sp-mt">' + esc(o ? o.title : 'Free day') + '</div>' +
        (o ? '<div class="sp-ms">' + esc(o.all_day ? (o.who || '') : o.time + (o.who ? ' · ' + o.who : '')) + '</div>' : '') + '</div>';
    }).join('');
    var pill = sp.span[0] === 0 ? sp.countdown : 'Day ' + (sp.span[0] + 1) + ' of ' + sp.span[1];
    return '<button class="day sp span" style="grid-column:span ' + days.length + ';--n:' + days.length + '" data-act="day" data-date="' + a.date + '" aria-label="' +
      esc(a.dow_long + ' ' + a.month + ' ' + a.num + ' to ' + b.dow_long + ' ' + b.month + ' ' + b.num + ', ' + sp.title) + '">' + spArt(sp, 'wide', 'span') +
      '<div class="sp-head"><div class="sp-k">' + esc(a.dow_long + ', ' + a.month + ' ' + a.num + ' – ' + b.dow_long + ', ' + b.month + ' ' + b.num) + '</div>' +
      '<div class="sp-script big">' + esc(sp.script) + '</div>' +
      '<div class="sp-ti big">' + spIcon(sp, 22) + '<span>' + esc(sp.title) + '</span></div>' +
      (sp.lines[1] ? '<div class="sp-l">' + esc(sp.lines[1]) + '</div>' : '') +
      (pill ? '<span class="sp-pill">' + esc(pill) + '</span>' : '') + '</div>' +
      '<div class="sp-strip" style="grid-template-columns:repeat(' + days.length + ',minmax(0,1fr))">' + strip + '</div></button>';
  }
  function specialCell(day) {
    var sp = day.special;
    return '<button class="mcell sp' + (day.in_month ? '' : ' out') + (day.today ? ' today' : '') + (sp.solemn ? ' solemn' : '') +
      '" data-act="day" data-date="' + day.date + '" aria-label="' + esc(day.dow_long + ' ' + day.month + ' ' + day.num + ', ' + sp.title) + '">' +
      spArt(sp, 'mid', 'cell') + '<div class="mn">' + day.num + '</div>' + (day.today ? DAY_TAG : '') + '<div class="sp-mscript">' + esc(sp.script) + '</div>' +
      '<div class="sp-mlabel">' + spIcon(sp, 12) + '<span>' + esc(sp.title) + '</span></div></button>';
  }
  // Today screen: a countdown to the next special day (Settings > Special days sets how far ahead).
  function specialRibbon() {
    var u = S.data.calendar.upcoming;
    if (!u) return '';
    var n = u.days_until, when = n === 0 ? 'Today:' : n === 1 ? 'Tomorrow:' : n + ' days until';
    if (u.solemn) when = n === 0 ? 'Today' : u.dow_long;
    // Slots a look can rearrange (docs/themes.md): .rb-count (.rb-n the number, .rb-unit "days"), .rb-date and .rb-lines in
    // .rb-sub, .rb-icon and .rb-more ("Details"). .rb-count, .rb-icon and .rb-more are hidden unless a look shows them.
    var unit = n === 0 ? 'today' : n === 1 ? 'day' : 'days';
    return '<button class="ribbon' + (u.solemn ? ' solemn' : '') + '" data-act="special-day" data-date="' + u.date + '" data-days="' + n + '">' +
      '<span class="rb-art">' + spArt(u, 'mid', 'rib') + '</span>' + (u.icon ? '<span class="rb-icon">' + spIcon(u, 22) + '</span>' : '') +
      '<span class="rb-count"><b class="rb-n">' + n + '</b><span class="rb-unit">' + unit + '</span></span>' +
      '<span class="rb-script">' + esc(when) + '</span>' +
      '<span class="rb-ti">' + esc(u.title) + (u.solemn ? '' : '!') + '</span>' +
      '<span class="rb-sub"><span class="rb-date">' + esc(u.dow_long + ', ' + u.month + ' ' + u.num) + '</span>' +
      (u.lines.length ? '<span class="rb-lines">' + esc(' · ' + u.lines.join(' · ')) + '</span>' : '') + '</span>' +
      (u.icon ? '<span class="rb-stars">' + spIcon(u, 14) + spIcon(u, 14) + spIcon(u, 14) + '</span>' : '') +
      '<span class="rb-more">Details' + I('chevron-right', 16, 2.2) + '</span></button>';
  }

  // ---------------- Lists (Apple Reminders through the Mac, or Google Tasks) ----------------
  function curList() {
    var L = S.data.lists, ids = L.lists.map(function (x) { return x.id; });
    if (ids.indexOf(S.list) < 0) S.list = L.home && ids.indexOf(L.home) >= 0 ? L.home : ids[0];
    return L.lists[ids.indexOf(S.list)];
  }
  // Each list says where it comes from: Apple Reminders (through the Mac) or Google Tasks (read by the server).
  function shortSync(x, source) {
    var mac = source !== 'google';
    if (x.stale) return x.synced ? (mac ? 'Mac' : 'Google') + ' last synced ' + x.synced : mac ? 'Waiting for the Mac' : 'Waiting for Google';
    return 'synced ' + x.synced;
  }
  function syncLine(x) {
    if (x.source === 'google') {
      if (!x.synced) return 'Waiting for Google Tasks (Settings > Lists)';
      return x.stale ? 'Google Tasks last synced ' + x.synced + '. Changes made here wait for it.' : 'Synced with Google Tasks ' + x.synced;
    }
    if (!x.synced) return 'Waiting for the Mac to connect (Settings > Lists)';
    return x.stale ? 'The Mac last checked in ' + x.synced + '. Changes made here wait for it.' : 'Synced with Reminders ' + x.synced;
  }
  function renderLists() {
    var L = S.data.lists;
    if (!L || !L.lists.length) { go(homeScreen()); return; }
    var lst = curList();
    var picker = L.lists.length > 1 ? '<div class="picker" role="group" aria-label="Pick a list">' + L.lists.map(function (x) {
      var on = x.id === lst.id;
      return '<button class="pick lpick' + (on ? ' on' : '') + '" data-act="list-pick" data-list="' + esc(x.id) + '" aria-pressed="' + on + '">' +
        esc(x.name) + (x.open ? ' <span class="lcount">' + x.open + '</span>' : '') + '</button>';
    }).join('') + '</div>' : '';
    var html = band(bandTitle(70, 'Lists', lst.name + ' · from ' + (lst.from || 'Apple Reminders')), picker);
    var body = '', last = null;
    lst.items.forEach(function (it) {
      if (lst.sections && it.section !== last) { body += '<h4 class="lsec">' + esc(it.section) + '</h4>'; last = it.section; }
      body += listItemRow(it, L.can_check);
    });
    if (!lst.items.length) body = '<p class="empty">Nothing on ' + esc(lst.name) + ' right now.</p>';
    var done = lst.done.map(function (it) {
      return '<div class="li done">' + (L.can_check ? '<button class="ring on" data-act="list-toggle" data-id="' + esc(it.id) + '" aria-label="Put ' +
        esc(it.title) + ' back on the list">' + I('check', 18, 2.6) + '</button>' : '<span class="ring on">' + I('check', 18, 2.6) + '</span>') +
        '<div class="li-t"><b>' + esc(it.title) + '</b> <small>' + esc(it.when || '') + '</small></div></div>';
    }).join('') || '<p class="aside">Nothing checked off yet today.</p>';
    html += '<div class="body"><div class="main lists-main">' +
      '<section class="card litems" aria-label="' + esc(lst.name) + '"><div class="card-head"><h2>' + esc(lst.name) + '</h2>' +
      '<span class="aside">' + (lst.open ? lst.open + ' to get' : 'all clear') + '</span></div><div class="lcols' + (lst.sections ? ' secs' : '') + '">' + body + '</div></section>' +
      '<div class="lside">' + (L.can_add ? '<button class="btn-primary ladd-btn" data-act="list-add" data-list="' + esc(lst.id) + '">' + I('plus', 22, 2.4) +
        'Add to ' + esc(lst.name) + '</button>' : '') +
      '<section class="card" aria-label="Done today"><div class="card-head"><h2>Done today</h2></div><div class="ldone">' + done + '</div></section>' +
      '<p class="lnote' + ((lst.synced !== undefined ? lst : L).stale ? ' stale' : '') + '">' + esc(syncLine(lst.synced !== undefined ? lst : L)) + '</p>' +
      '<p class="aside">Tap a circle to check it off. It’s checked off on everyone’s phone too.</p></div></div>' +
      '<nav class="nav">' + tabs('lists') + homebar() + grownups() + '</nav></div>';
    setHTML($('screen-lists'), html);
  }
  var KEYROWS = ['1234567890', 'QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM'];
  function renderListAdd() {
    var L = S.data.lists, ids = L.lists.map(function (x) { return x.id; });
    if (ids.indexOf(S.addList) < 0) S.addList = L.home || ids[0];
    var lst = L.lists[ids.indexOf(S.addList)], text = S.addText;
    var q = text.trim().toLowerCase(), have = {};
    lst.items.forEach(function (it) { have[it.title.toLowerCase()] = 1; });
    var sugg = lst.bought.filter(function (b) {
      var t = b.toLowerCase();
      return !have[t] && (!q || t.indexOf(q) === 0 || t.indexOf(' ' + q) >= 0);
    }).slice(0, S.tall ? 8 : 10);
    var to = L.lists.length > 1 ? '<div class="la-to"><span>Add to</span>' + L.lists.map(function (x) {
      return '<button class="chip2 r' + (x.id === lst.id ? ' sel' : '') + '" data-act="la-list" data-list="' + esc(x.id) + '">' + esc(x.name) + '</button>';
    }).join('') + '</div>' : '<div class="la-to"><span>Adding to <b>' + esc(lst.name) + '</b></span></div>';
    var keys = KEYROWS.map(function (row, r) {
      return '<div class="kb-row">' + row.split('').map(function (k) {
        return '<button data-act="lk" data-k="' + k + '">' + k + '</button>';
      }).join('') + (r === 3 ? '<button class="wide" data-act="lk" data-k="del" aria-label="Delete">' + I('delete-key', 24, 1.8) + '</button>' : '') + '</div>';
    }).join('') + '<div class="kb-row"><button class="wide" data-act="lk" data-k="-">-</button><button class="space" data-act="lk" data-k=" ">space</button>' +
      '<button class="wide ok" data-act="la-go"' + (q ? '' : ' disabled') + '>Add</button></div>';
    overlay.innerHTML = '<div class="sheet ladd" role="document"><div class="la-top"><div class="la-input' + (text ? '' : ' empty') + '">' +
      (text ? esc(text) : 'Type what to add') + '<span class="caret"></span></div><button class="btn-ghost" data-act="close">Done</button></div>' + to +
      (sugg.length ? '<div class="la-sugg"><span class="lbl">' + (q ? 'Had before' : 'Bought before') + '</span>' + sugg.map(function (b) {
        return '<button class="chip2 r" data-act="la-pick" data-t="' + esc(b) + '">' + esc(b) + '</button>';
      }).join('') + '</div>' : '') +
      '<div class="msg' + (S.addMsg.indexOf('Added') === 0 ? ' good' : '') + '" role="status">' + esc(S.addMsg) + '</div>' +
      '<div class="kb" role="group" aria-label="Keyboard">' + keys + '</div></div>';
  }
  function listAdd(title) {
    title = title.replace(/\s+/g, ' ').trim();
    if (!title || S.busy) return;
    S.busy = true;
    api('POST', 'api/lists/' + encodeURIComponent(S.addList) + '/add', { title: title }).then(function (r) {
      S.busy = false;
      if (r._status >= 400) { S.addMsg = r.detail || 'That didn’t work.'; renderOverlay(); return; }
      var to = (S.data.lists.lists || []).filter(function (x) { return x.id === S.addList; })[0];
      S.addText = ''; S.addMsg = 'Added ' + r.title + '. It reaches ' + (to && to.source === 'google' ? 'Google Tasks' : 'Reminders') + ' within a minute.';
      refresh();
    }).catch(function () { S.busy = false; S.addMsg = 'Can’t reach the server.'; renderOverlay(); });
  }
  function listToggle(id) {
    // Show it right away; the server and then Reminders or Google Tasks catch up.
    (S.data.lists.lists || []).forEach(function (l) {
      var i, found = false;
      for (i = 0; i < l.items.length && !found; i++) if (l.items[i].id === id) {
        var it = l.items.splice(i, 1)[0]; it.when = 'just now'; l.done.unshift(it); l.open--; found = true;
      }
      for (i = 0; i < l.done.length && !found; i++) if (l.done[i].id === id) { l.items.push(l.done.splice(i, 1)[0]); l.open++; found = true; }
    });
    render();
    api('POST', 'api/lists/item/' + encodeURIComponent(id) + '/toggle').then(refresh, refresh);
  }

  // ---------------- which frame is this (Settings > Frames) ----------------
  // A brand-new frame in a house with several frame profiles asks which one it is (parent PIN).
  // The kitchen frame, and any house with a single profile, just remembers the one it got.
  function firstFrame(d) {
    if (S.frameId || S.firstChecked) return;
    S.firstChecked = true;
    fetch('api/frames', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (j) {
      S.frames = j.frames; setLooks(j.looks);
      if (j.frames.length > 1 && !hasOtherState() && !d.demo) { S.overlay = 'firstrun'; renderOverlay(); }  // demo: the kitchen
      else { S.frameId = d.frame.id; saveFrame(S.frameId); }
    }).catch(function () { S.firstChecked = false; });
  }
  function loadFrames() {
    fetch('api/frames', { cache: 'no-store' }).then(function (r) { return r.json(); })
      .then(function (j) { S.frames = j.frames; setLooks(j.looks); renderOverlay(); }).catch(function () { /* menu shows what it has */ });
  }
  function useFrame(id) {
    S.frameId = id; saveFrame(id); S.pinNext = ''; S.pendingFrame = '';
    S.showName = Date.now() + 10000;
    closeOverlay();
    S.screen = '';  // the new profile's home screen comes with the next payload
    refresh().then(function () { go(homeScreen()); showName(); });
  }
  // Top-left hot corner: have the Pi read the calendars now, then pull everything fresh.
  function ftoast(msg, ms) {
    var el = $('ftoast');
    el.textContent = msg; el.classList.add('on');
    clearTimeout(ftoast.t);
    if (ms) ftoast.t = setTimeout(function () { el.classList.remove('on'); }, ms);
  }
  function refreshNow() {
    if (S.refreshing) return;
    S.refreshing = true;
    ftoast('Checking the calendars…');
    api('POST', 'api/refresh-now').then(function (r) {
      S.calAlt = {};
      return refresh().then(function () {
        var c = clock(), bad = r.errors && Object.keys(r.errors).length;
        ftoast(bad ? 'Up to date, but a calendar didn’t answer (see Settings)' : 'Calendars up to date · ' + c.t + ' ' + c.ap, 4000);
      });
    }).catch(function () { ftoast('Can’t reach the Pi right now', 4000); })
      .then(function () { S.refreshing = false; });
  }
  function showName() {
    var el = $('frame-name');
    el.textContent = frameOf().name;
    el.classList.add('on');
    setTimeout(function () { el.classList.remove('on'); }, 10000);
  }
  // The looks come from the server (themes/<id>/theme.json, via /api/frames): id -> [name, blurb, usual home screen].
  var LOOK_NAMES = {};
  function setLooks(list) {
    if (!list || !list.length) return;
    LOOK_NAMES = {};
    list.forEach(function (l) { LOOK_NAMES[l.key] = [l.name, l.note, l.home]; });
    if (!LOOK_NAMES[S.newLook]) S.newLook = list[0].key;
  }
  function lookName(k) { return (LOOK_NAMES[k] || [k])[0]; }
  var SCREEN_LABEL = { today: 'Today', kids: 'Kids', clock: 'Clock', calendar: 'Calendar', chores: 'Chores', screen: 'Screen Time', lists: 'Lists', photos: 'Photos' };
  function renderFrameMenu() {
    var first = S.overlay === 'firstrun', px = window.devicePixelRatio || 1;
    var w = Math.round(window.innerWidth * px), h = Math.round(window.innerHeight * px);
    var cards = (S.frames || []).map(function (f) {
      var on = !first && f.id === frameOf().id;
      return '<button class="fcard' + (on ? ' on' : '') + '" data-act="' + (first ? 'frame-ask' : 'frame-use') + '" data-id="' + esc(f.id) + '">' +
        '<b>' + esc(f.name) + (on ? ' ' + I('check', 18, 2.6) : '') + '</b><span>' + esc(lookName(f.look)) + ' · ' +
        f.screens.map(function (x) { return SCREEN_LABEL[x]; }).join(', ') + '</span></button>';
    }).join('') || '<p class="aside">Loading the frames…</p>';
    overlay.innerHTML = '<div class="sheet fmenu" role="document"><div class="fm-head"><div><h1>' + mono() +
      (first ? 'Hello, new frame' : 'This frame') + '</h1><p class="sub">' +
      (first ? 'Which frame is it? A parent PIN is needed to choose.' : 'Unlocked' + (S.who ? ' by ' + esc(S.who) + '’s PIN' : '') + '. Which frame is this?') +
      '</p></div>' + (first ? '' : '<button class="btn-primary" data-act="close">Done</button>') + '</div>' +
      '<p class="fm-size">This screen is <b>' + w + ' × ' + h + ', ' + (S.tall ? 'tall' : 'wide') + '</b>. Every frame fits itself to it.</p>' +
      '<div class="fcards">' + cards + (!on('multi_frame') ? '' : '<button class="fcard new" data-act="' + (first ? 'frame-new-ask' : 'frame-new') + '"><b>' + I('plus', 20, 2.4) +
      ' A new frame here</b><span>Name it and pick a look; finish the details in Settings › Frames</span></button>') + '</div>' +
      (first ? '<p class="aside">Change it any time: tap the small gear in the corner, then the parent PIN.</p>'
        : '<div class="fm-foot"><button class="btn-ghost" data-act="frame-reload">Reload the frame</button>' +
          '<button class="btn-ghost" data-act="frame-name">Show its name for 10 seconds</button></div>') + '</div>';
  }
  function renderFrameNew() {
    var keys = KEYROWS.map(function (row, r) {
      return '<div class="kb-row">' + row.split('').map(function (k) {
        return '<button data-act="lk" data-k="' + k + '">' + k + '</button>';
      }).join('') + (r === 3 ? '<button class="wide" data-act="lk" data-k="del" aria-label="Delete">' + I('delete-key', 24, 1.8) + '</button>' : '') + '</div>';
    }).join('') + '<div class="kb-row"><button class="wide" data-act="lk" data-k="’">’</button><button class="space" data-act="lk" data-k=" ">space</button>' +
      '<button class="wide ok" data-act="fn-go"' + (S.addText.trim() ? '' : ' disabled') + '>Make it</button></div>';
    var looks = Object.keys(LOOK_NAMES).map(function (k) {
      return '<button class="chip2 r' + (S.newLook === k ? ' sel' : '') + '" data-act="fn-look" data-look="' + esc(k) + '">' + esc(LOOK_NAMES[k][0]) + '</button>';
    }).join('');
    overlay.innerHTML = '<div class="sheet ladd" role="document"><div class="la-top"><div class="la-input' + (S.addText ? '' : ' empty') + '">' +
      (S.addText ? esc(S.addText) : 'Name this frame, like Kids’ playroom') + '<span class="caret"></span></div><button class="btn-ghost" data-act="close">Cancel</button></div>' +
      '<div class="la-to"><span>Look</span>' + looks + '</div>' +
      '<div class="la-to"><span>Starts on</span>' + HOME_CHOICES.map(function (h) {
        return '<button class="chip2 r' + (newHome() === h[0] ? ' sel' : '') + '" data-act="fn-home" data-home="' + h[0] + '">' + h[1] + '</button>';
      }).join('') + '</div><div class="msg" role="status">' + esc(S.addMsg) + '</div>' +
      '<div class="kb" role="group" aria-label="Keyboard">' + keys + '</div></div>';
  }
  // What a new frame starts on; the look picks the usual one until a parent picks another.
  var HOME_CHOICES = [['today', 'Today'], ['kids', 'Kids'], ['clock', 'Clock'], ['chores', 'Chores']];
  function newHome() {
    var usual = (LOOK_NAMES[S.newLook] || [])[2];
    return S.newHome || (HOME_CHOICES.some(function (h) { return h[0] === usual; }) ? usual : 'today');
  }
  function frameNew() {
    var name = S.addText.trim();
    if (!name || S.busy) return;
    S.busy = true;
    api('POST', 'api/parent/frames', { name: name, look: S.newLook, home: newHome() }).then(function (r) {
      S.busy = false;
      if (r._status >= 400) { S.addMsg = r.detail || 'That didn’t work.'; if (r._status === 401) { S.pinNext = 'frame-new'; S.overlay = 'pin'; } renderOverlay(); return; }
      S.addText = '';
      useFrame(r.id);
    }).catch(function () { S.busy = false; S.addMsg = 'Can’t reach the server.'; renderOverlay(); });
  }

  // ---------------- Kids (a playroom frame; web/js/kids.js) ----------------
  var KV = null;
  function renderKids() {
    KV = KV || window.KidsView({
      esc: esc, I: I, clock: clock, localNow: localNow, av: av, spArt: spArt, shortMin: shortMin, kidById: kidById, shows: shows, on: on,
      data: function () { return S.data; }, frame: frameOf, tall: function () { return S.tall; }, selKid: function () { return S.kid; },
      tabs: tabs, draw: function (v, sc, kids) { return drawVars((DRAW[v] || DRAW.rocket)(sc, kids, ++svgN)); },
      word: word, grownups: grownups, fit: pictureFit
    });
    setHTML($('screen-kids'), KV.render());
  }

  // ---------------- Clock & today (a bedroom frame) ----------------
  function renderClock() {
    var d = S.data, c = clock(), w = d.weather, src = sources();
    var tomorrow = (d.calendar.rolling.days[1] || { events: [] });
    var morning = tomorrow.events.filter(function (e) { return e.all_day || e.sort < '12:00'; }).slice(0, 5);
    var verses = d.clock_verses || [];   // from the faith art pack; none without it
    var verse = verses.length ? verses[localNow().getUTCDay() % verses.length] : null;
    var tw = w && w.days && w.days[1];
    var u = d.calendar.upcoming;
    var list = morning.map(function (e) {
      var s = src[e.cal] || {};
      return '<div class="ck-ev"><span class="tm">' + esc(e.all_day ? 'All day' : e.time) + '</span><span class="dot" style="background:' + esc(s.color) +
        '"></span><div><div class="ti">' + esc(e.title) + '</div>' + (e.who ? '<div class="who">' + esc(e.who) + '</div>' : '') + '</div></div>';
    }).join('') || '<p class="empty">Nothing on the calendar tomorrow morning.</p>';
    var html = '<div class="ck"><div class="ck-main"><div class="ck-date">' + esc(dateLabel()) + '</div>' +
      '<div class="ck-time">' + c.t + '<span>' + c.ap + '</span></div>' +
      (w ? '<div class="ck-wx">' + I(w.icon, 34, 1.4) + '<b>' + (w.temp == null ? '–' : w.temp + deg(w)) + ' now</b>' +
        (tw ? '<span>Tomorrow ' + (tw.high == null ? '' : tw.high + '° / ') + (tw.low == null ? '' : tw.low + '°, ') + esc(tw.text.toLowerCase()) + '</span>' : '') + '</div>' : '') +
      (verse ? '<blockquote class="ck-verse">“' + esc(verse[0]) + '”<cite>' + esc(verse[1]) + '</cite></blockquote>' : '') + '</div>' +
      '<div class="ck-side"><h2>Tomorrow morning</h2>' + list +
      (u ? '<button class="ck-count" data-act="special-day" data-date="' + u.date + '">' + spIcon(u, 16) + '<span>' +
        (u.days_until === 0 ? 'Today: ' : u.days_until === 1 ? 'Tomorrow: ' : u.days_until + ' days until ') + '<b>' + esc(u.title) + '</b></span></button>' : '') +
      '</div></div><div class="body ck-body"><nav class="nav">' + tabs('clock') + homebar() + '</nav></div>';
    setHTML($('screen-clock'), html);
  }

  // ---------------- Photos ----------------
  function renderPhotoOverlay() {
    var d = S.data, c = clock(), w = d.weather;
    var nextEv = null;
    d.calendar.today.forEach(function (e) { if (e.next) nextEv = e; });
    var photos = S.photos;
    var html;
    if (!d.photos_count) {
      html = '<div class="ph-empty">' + mono(0, '', true) +
        '<p>Add photos to the frame’s photos folder to fill this screen.</p></div>';
    } else {
      html = '';
    }
    html += '<div class="ph-panel">' + mono(64) + '<div>' +
      '<div class="clock"><span class="t">' + c.t + '</span><span class="ap">' + c.ap + '</span></div>' +
      '<div class="d">' + esc(dateLabel()) + (w && w.temp != null ? ' · ' + w.temp + '° ' + esc(w.text.toLowerCase()) : '') + '</div>' +
      (nextEv ? '<div class="n"><b>Next</b> · ' + esc(nextEv.time + ' ' + nextEv.title) + (nextEv.who ? ' (' + esc(nextEv.who) + ')' : '') + '</div>' : '') +
      '</div></div>';
    var cur = photos[S.photoIdx];
    if (cur && cur.caption) html += '<div class="ph-cap">' + esc(cur.caption) + '</div>';
    setHTML($('ph-over'), html);
  }
  // The photo list comes separately from /api/photos, only when the server says it changed.
  function loadPhotos() {
    if (!S.data || S.photosVersion === S.data.photos_version || S.photosLoading) return Promise.resolve();
    S.photosLoading = true;
    return fetch('api/photos', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (p) {
      S.photos = p.photos || []; S.photosVersion = p.version; S.photosLoading = false;
      if (S.photoIdx >= S.photos.length) S.photoIdx = -1;
      if (window.FrameLooks) FrameLooks.photoChanged();
    }).catch(function () { S.photosLoading = false; });
  }
  function nextPhoto() {
    var photos = S.photos;
    if (!photos.length) { loadPhotos().then(function () { if (S.photos.length && S.screen === 'photos') nextPhoto(); }); renderPhotoOverlay(); return; }
    // One photo at a time: don't start another while the last is still on its way.
    if (S.photoPending && Date.now() - S.photoPending < 15000) return;
    S.photoIdx = (S.photoIdx + 1) % photos.length;
    var show = S.photoLayer ? $('ph-b') : $('ph-a'), hide = S.photoLayer ? $('ph-a') : $('ph-b');
    S.photoPending = Date.now();
    show.onload = function () {
      S.photoMs = Date.now() - S.photoPending;  // for the heartbeat
      S.photoPending = 0; S.photoLayer = 1 - S.photoLayer;
      show.classList.add('on'); hide.classList.remove('on'); renderPhotoOverlay();
      if (window.FrameLooks) FrameLooks.photoChanged();   // a look's photo behind the screens follows along
    };
    show.onerror = function () { S.photoPending = 0; setTimeout(nextPhoto, 1000); };  // skip a photo that won't load
    show.src = photoUrl(photos[S.photoIdx]);
  }
  // The Pi crops each photo for this frame's shape around its focal point (or fits it whole), so the tablet only shows it.
  function photoUrl(ph) {
    var q = [];
    var hd = Math.max(window.innerWidth, window.innerHeight) * (window.devicePixelRatio || 1) >= 1700;
    var shape = (S.tall ? 'tall' : 'wide') + (hd ? '-hd' : '');
    if (shape !== 'wide') q.push('shape=' + shape);
    if (ph.v) q.push('v=' + ph.v);
    return 'photos/' + ph.id + '.jpg' + (q.length ? '?' + q.join('&') : '');
  }
  function startPhotos() {
    stopPhotos();
    nextPhoto();
    renderPhotoOverlay();
    S.photoTimer = setInterval(nextPhoto, (S.data.settings.photo_seconds || 20) * 1000);
    loadPhotos();
  }
  function stopPhotos() { if (S.photoTimer) clearInterval(S.photoTimer); S.photoTimer = null; }

  // ---------------- Night ----------------
  function renderNight() {
    var d = S.data, c = clock(), t = d.calendar.tomorrow_first, w = d.weather, tw = w && w.days && w.days[1];
    var title = word('night_title'), sub = word('night_sub');
    // .ap (AM/PM), .wx (the weather) and the night_title / night_sub words are hidden or empty unless a look uses them.
    setHTML($('screen-night'), mono() + (title ? '<div class="nt">' + esc(title) + '</div>' : '') +
      '<div class="t">' + c.t + '<span class="ap">' + c.ap + '</span></div>' +
      '<div class="d">' + esc(frameOf().look_date_style === 'long' ? dateLabel() : d.date_label.replace(' · ', ', ')) + '</div>' +
      (sub ? '<div class="ns">' + esc(sub) + '</div>' : '') +
      (w ? '<div class="nwx">' + I(w.icon, 26, 1.6) + '<span>' + (w.temp == null ? '–' : w.temp + deg(w)) + ' ' + esc(w.text) +
        (tw && tw.high != null ? ' · ' + esc(word('tomorrow')) + ' ' + tw.high + '°' : '') + '</span></div>' : '') +
      (t ? '<div class="n">' + esc(word('tomorrow')) + ' · ' + esc(t.all_day ? t.title : t.time + ' ' + t.title) + '</div>' : ''));
  }

  // ---------------- Parent overlay ----------------
  function waitingList() {
    var out = [];
    S.data.kids.forEach(function (k) {
      k.chores.forEach(function (c) { if (c.status === 'waiting') out.push({ k: k, c: c }); });
    });
    return out;
  }
  function renderOverlay() {
    if (!S.overlay) { overlay.classList.remove('on'); overlay.innerHTML = ''; return; }
    overlay.classList.add('on');
    if (S.overlay === 'day') { renderDayPopup(); return; }
    if (S.overlay === 'listadd') { renderListAdd(); return; }
    if (S.overlay === 'frame' || S.overlay === 'firstrun') { renderFrameMenu(); return; }
    if (S.overlay === 'framenew') { renderFrameNew(); return; }
    var items = waitingList();
    if (S.overlay === 'pin') {
      var dots = '';
      for (var i = 0; i < Math.max(4, S.pin.length); i++) dots += '<i class="' + (i < S.pin.length ? 'f' : '') + '"></i>';
      var keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9'].map(function (n) {
        return '<button data-act="key" data-key="' + n + '">' + n + '</button>';
      }).join('') + '<button class="fn" data-act="key" data-key="clear">Clear</button><button data-act="key" data-key="0">0</button>' +
        '<button class="ok" data-act="key" data-key="ok">OK</button>';
      var forFrame = S.pinNext.indexOf('frame') === 0, kidsLook = !!frameOf().look_kids;
      // A kids' look leaves out the list of chores waiting for a parent (the words come from the look: pin_title, pin_sub).
      overlay.innerHTML = '<div class="sheet pinpad' + (kidsLook ? ' kids-look' : '') + '"><div style="display:flex;flex-direction:column">' +
        '<h1>' + mono() + esc(forFrame ? 'This frame' : word('pin_title')) + '</h1>' +
        '<p class="sub">' + (S.data.pin_configured ? esc(word('pin_sub')) : 'No parent PIN is set up yet. Run python -m app.tools set-pin on the server.') + '</p>' +
        (forFrame ? '<p class="sub">A parent PIN is needed to change which frame this is.</p><div class="wlist"></div>' : '') +
        '<div class="wlist"' + (forFrame || kidsLook ? ' style="display:none"' : '') + '>' + (items.length ? items.map(function (x) {
          return '<div class="witem">' + av(x.k, 's') + '<span class="ti">' + esc(x.c.title) + '<small>' + esc(x.k.name) + '</small></span><span class="mins">+' + x.c.minutes + '</span></div>';
        }).join('') : '<p class="empty" style="padding:6px 0">Nothing is waiting right now.</p>') + '</div>' +
        '<div class="pindots" aria-label="' + S.pin.length + ' digits entered">' + dots + '</div><div class="msg" role="alert">' + esc(S.msg) + '</div>' +
        '<div class="sheet-actions" style="margin-top:auto"><button class="btn-ghost" data-act="close">Cancel</button></div></div>' +
        '<div class="keys" role="group" aria-label="PIN keypad">' + keys + '</div></div>';
    } else {
      renderParent(items);
    }
  }
  var AMOUNTS = [-15, -10, -5, 5, 10, 15, 30];
  var REASONS = [['Kind to a sibling', 1], ['Extra help', 1], ['Great attitude', 1], ['Not listening', -1], ['Unkind words', -1], ['Fighting', -1]];
  function renderParent(items) {
    var sc = S.data.screen, a = S.adj;
    var todo = [];
    S.data.kids.forEach(function (k) { k.chores.forEach(function (c) { if (c.status === 'todo') todo.push({ k: k, c: c }); }); });
    function row(x, waitingRow) {
      return '<div class="witem">' + av(x.k, 's') + '<span class="ti">' + esc(x.c.title) + '<small>' + esc(x.k.name) +
        (waitingRow ? '' : ' · not tapped yet') + '</small></span><span class="mins">+' + x.c.minutes + '</span>' +
        '<button class="btn-small ok" data-act="approve" data-id="' + esc(x.c.id) + '">Approve</button>' +
        (waitingRow ? '<button class="btn-small no" data-act="sendback" data-id="' + esc(x.c.id) + '">Not yet</button>' : '') + '</div>';
    }
    var week = '', good = '';
    if (sc && sc.new_week_due) {
      week = S.confirmWeek
        ? '<div class="nwk"><div><b>Start a new week?</b><small>This week’s ' + esc(shortMin(sc.total)) + ' is done. The log keeps everything.</small></div>' +
          '<button class="btn-small no" data-act="week-cancel">Not yet</button><button class="btn-small ok" data-act="week-go">Start it</button></div>'
        : '<div class="nwk"><div><b>Time for a new week</b><small>Earning starts again from zero. Nothing resets until you say so.</small></div>' +
          '<button class="btn-small ok" data-act="week-ask">New week</button></div>';
    }
    if (sc) good = sc.good_today
      ? '<div class="gday done">' + I('check', 22, 2.4) + '<div><b>Good day given today</b><small>+' + sc.good_day_minutes + ' min for everyone</small></div></div>'
      : '<button class="gday" data-act="goodday"><div><b>A good day for everyone</b><small>Adds ' + sc.good_day_minutes + ' min to the family pool</small></div><span class="plus">+' + sc.good_day_minutes + '</span></button>';
    var kid = a.kid !== 'all' ? kidById(a.kid) : null;
    var who = '<button class="av m all' + (a.kid === 'all' ? ' sel' : '') + '" data-act="adj-kid" data-kid="all" aria-label="Everyone">ALL</button>' +
      S.data.kids.map(function (k) {
        return '<button class="pickav' + (a.kid === k.id ? ' sel' : '') + '" data-act="adj-kid" data-kid="' + esc(k.id) + '" aria-label="' + esc(k.name) + '">' + av(k, 'm') + '</button>';
      }).join('');
    var amts = AMOUNTS.map(function (m) {
      return '<button class="chip2' + (m < 0 ? ' neg' : '') + (a.minutes === m ? ' sel' : '') + '" data-act="adj-min" data-min="' + m + '">' + (m > 0 ? '+' : '−') + Math.abs(m) + '</button>';
    }).join('');
    var where = kid ? '<div class="lbl">Where it goes</div><div class="chips">' +
      '<button class="chip2 r' + (a.scope === 'family' ? ' sel' : '') + '" data-act="adj-scope" data-scope="family">' + (a.minutes < 0 ? 'From the family pool' : 'Family pool, ' + esc(kid.name) + ' gets credit') + '</button>' +
      '<button class="chip2 r' + (a.scope === 'kid' ? ' sel' : '') + '" data-act="adj-scope" data-scope="kid">' + (a.minutes < 0 ? 'Just from ' : 'Just for ') + esc(kid.name) + '</button></div>' : '';
    var why = REASONS.map(function (r) {
      return '<button class="chip2 r' + (a.why === r[0] ? ' sel' : '') + '" data-act="adj-why" data-why="' + esc(r[0]) + '">' + esc(r[0]) + '</button>';
    }).join('');
    var summary = !a.minutes ? 'Pick how much'
      : (a.minutes > 0 ? '+' : '−') + Math.abs(a.minutes) + ' min ' + (!kid ? (a.minutes > 0 ? 'for everyone' : 'from everyone') : a.scope === 'kid' ? (a.minutes > 0 ? 'just for ' : 'just from ') + kid.name :
      a.minutes > 0 ? 'to the family pool, credited to ' + kid.name : 'from the family pool, because of ' + kid.name);
    overlay.innerHTML = '<div class="sheet ptools"><div class="pcol">' +
      '<h1>' + mono() + 'Parent tools</h1>' +
      '<p class="sub">' + (S.who ? 'Signed in as ' + esc(S.who) + '. ' : '') + 'Closes after two minutes.</p>' + week + good +
      '<div class="lbl">Chores</div><div class="wlist">' + (items.length ? items.map(function (x) { return row(x, true); }).join('') :
        '<p class="empty" style="padding:4px 0">Nothing is waiting.</p>') +
      (todo.length ? '<p class="aside" style="margin-top:6px">Not tapped yet</p>' + todo.map(function (x) { return row(x, false); }).join('') : '') +
      '</div></div>' + (!sc ? '<div class="pcol adj"><div class="pfoot"><div class="msg' + (S.ok ? ' good' : '') + '" role="alert">' + esc(S.ok || S.msg) + '</div>' +
      '<button class="btn-primary" data-act="close">Done</button></div></div></div>' : '<div class="pcol adj"><h2>Add or take away</h2>' +
      '<div class="lbl">Who</div><div class="pick2">' + who + '</div>' +
      '<div class="lbl">How much</div><div class="chips">' + amts + '</div>' + where +
      '<div class="lbl">Why</div><div class="chips">' + why + '</div>' +
      '<div class="confirm"><span>' + esc(summary) + '</span><button class="btn-small ok" data-act="adj-go"' + (a.minutes ? '' : ' disabled') + '>' +
      (a.minutes > 0 ? 'Add ' + a.minutes + ' min' : a.minutes < 0 ? 'Take away ' + (-a.minutes) + ' min' : 'Add') + '</button></div>' +
      '<div class="pfoot"><div class="msg' + (S.ok ? ' good' : '') + '" role="alert">' + esc(S.ok || S.msg) + '</div>' +
      '<button class="btn-primary" data-act="close">Done</button></div></div></div>');
  }
  function renderDayPopup() {
    var day = findDay(S.dayDate), src = sources();
    if (!day) { closeOverlay(); return; }
    if (S.dayEvent != null && day.events[S.dayEvent]) { renderEventDetail(day, day.events[S.dayEvent]); return; }
    var sp = day.special, own = spEvent(day);
    var hol = (day.holidays || []).map(function (h) {
      return '<div class="dp-row"><span class="tm">All day</span>' + STAR(13) + '<div class="ti">' + esc(h) + '</div></div>';
    }).join('');
    var list = sp ? spOthers(day) : day.events;
    function rowsFor(dd, items) {
      return items.map(function (e) {
        var s = src[e.cal] || {};
        return '<button class="dp-row tap' + (e.past || dd.past ? ' past' : '') + '" data-act="event" data-date="' + dd.date + '" data-i="' + dd.events.indexOf(e) + '">' +
          '<span class="tm">' + esc(e.time) + '</span><span class="dot" style="background:' + esc(s.color) + '"></span>' +
          '<div style="min-width:0"><div class="ti">' + esc(e.title) + '</div><div class="who">' +
          esc([e.who, [s.label].concat(e.also || []).join(' + ')].filter(Boolean).join(' · ')) + '</div></div>' +
          (overlaps(dd, e) ? '<span class="dp-tag">Overlaps</span>' : '<span></span>') + I('chevron-right', 20, 2) + '</button>';
      }).join('');
    }
    var rows = list.map(function (e) {
      var s = src[e.cal] || {};
      return '<button class="dp-row tap' + (e.past || day.past ? ' past' : '') + '" data-act="event" data-date="' + day.date + '" data-i="' + day.events.indexOf(e) + '">' +
        '<span class="tm">' + esc(e.time) + '</span><span class="dot" style="background:' + esc(s.color) + '"></span>' +
        '<div style="min-width:0"><div class="ti">' + esc(e.title) + '</div><div class="who">' +
        esc([e.who, [s.label].concat(e.also || []).join(' + ')].filter(Boolean).join(' · ')) + '</div></div>' +
        (overlaps(day, e) ? '<span class="dp-tag">Overlaps</span>' : '<span></span>') + I('chevron-right', 20, 2) + '</button>';
    }).join('');
    var dateLine = (day.today ? 'Today, ' : '') + day.dow_long + ', ' + MONTH_NAMES[day.month] + ' ' + day.num;
    if (!sp) {
      overlay.innerHTML = '<div class="sheet daypop" role="document"><div class="dp-head"><div>' +
        '<div class="kick">' + (day.today ? 'Today' : esc(day.dow_long)) + '</div>' +
        '<h1>' + esc((day.today ? day.dow_long + ', ' : '') + MONTH_NAMES[day.month] + ' ' + day.num) + '</h1></div>' +
        '<button class="btn-primary" data-act="close">Close</button></div>' +
        '<div class="dp-list">' + hol + rows + '</div></div>';
      return;
    }
    var clashes = list.filter(function (e) { return overlaps(day, e); }).length;
    var facts = [], also = (hol || rows) ? '<div class="dp-sub">Also that day</div><div class="dp-list">' + hol + rows + '</div>' : '<p class="aside">Nothing else on the calendar that day.</p>';
    // Several days (a campout, a trip): what else is on, day by day, for the whole stretch.
    var multi = own && own.span && own.span[1] > 1;
    if (multi) {
      var first = addDays(day.date, -own.span[0]), last = addDays(first, own.span[1] - 1), fd = findDay(first), ld = findDay(last);
      var nice = function (dd, date) { return dd ? dd.dow_long + ', ' + MONTH_NAMES[dd.month] + ' ' + dd.num : date; };
      dateLine = nice(fd, first) + ' – ' + nice(ld, last);
      clashes = 0; also = '';
      for (var n = 0; n < own.span[1]; n++) {
        var date = addDays(first, n), dd = findDay(date);
        var head = '<div class="dp-day' + (date === day.date ? ' on' : '') + '">' + esc(nice(dd, date)) + ' · day ' + (n + 1) + ' of ' + own.span[1] + '</div>';
        if (!dd) { also += head + '<p class="aside">Page the calendar ahead to see this day.</p>'; continue; }
        var others = spOthers(dd);
        clashes += others.filter(function (e) { return overlaps(dd, e); }).length;
        var dh = (dd.holidays || []).map(function (h) {
          return '<div class="dp-row"><span class="tm">All day</span>' + STAR(13) + '<div class="ti">' + esc(h) + '</div></div>';
        }).join('');
        also += head + ((dh || others.length) ? '<div class="dp-list">' + dh + rowsFor(dd, others) + '</div>' : '<p class="aside">Nothing else that day.</p>');
      }
      also = '<div class="dp-sub">During ' + esc(sp.title) + '</div>' + also;
    }
    if (own) {
      facts.push(['When', own.all_day ? (multi ? 'All day, ' + own.span[1] + ' days' : 'All day') :
        (multi ? MONTH_NAMES[fd ? fd.month : 'Jan'].slice(0, 3) + ' ' + (fd ? fd.num : '') + ', ' + own.time + (own.end_time ? ' – ' + (ld ? ld.dow : '') + ' ' + own.end_time : '')
          : own.time + (own.end_time ? ' – ' + own.end_time : ''))]);
      if (own.where) facts.push(['Where', own.where]);
      if (own.who) facts.push(['Who', own.who]);
      if (own.notes) facts.push(['Notes', own.notes]);
    }
    // The picture fills a tall panel on the left (the drawings are tall); everything else is on the right.
    overlay.innerHTML = '<div class="sheet daypop spop' + (sp.solemn ? ' solemn' : '') + '" role="document">' +
      '<div class="sp-side">' + spArt(sp, 'mid', 'pop') + '<div class="sp-sshade"></div><div class="sp-sscript">' + esc(sp.script) + '</div></div>' +
      '<div class="sp-main"><button class="sp-x" data-act="close" aria-label="Close">×</button>' +
      '<div class="sp-head2"><div class="sp-k">' + esc(dateLine) + (sp.countdown && sp.days_until > 1 ? ' · ' + esc(sp.countdown.toLowerCase()) : '') + '</div>' +
      '<div class="sp-bti">' + spIcon(sp, 26) + '<span>' + esc(sp.title) + '</span></div></div>' +
      '<div class="sp-body">' +
      (facts.length ? '<div class="dp-facts">' + facts.map(function (f) { return '<b>' + f[0] + '</b><span>' + esc(f[1]) + '</span>'; }).join('') + '</div>' : '') +
      (sp.about ? '<div class="dp-about"><div class="dp-sub">About this picture</div><p>' + esc(sp.about) + '</p>' +
        (sp.lines && sp.lines[0] ? '<p class="aside">' + esc(sp.lines[0]) + '</p>' : '') + '</div>' : '') +
      (sp.verse ? '<div class="dp-verse">' + esc(sp.verse) + '</div>' : '') +
      (clashes ? '<div class="sp-warn">' + I('alert', 20, 2) + (clashes === 1 ? '1 other thing is' : clashes + ' other things are') +
        ' on the calendar during ' + esc(sp.title) + '. Tap one to see it.</div>' : '') +
      also +
      '<p class="aside sp-foot">Change these in Google Calendar on your phone. The frame catches up within about 5 minutes (or tap the top-left corner).</p></div></div></div>';
  }
  function renderEventDetail(day, e) {
    var src = sources(), c = src[e.cal] || {}, sp = day.special, own = spEvent(day);
    var facts = [['When', day.dow_long + ', ' + MONTH_NAMES[day.month] + ' ' + day.num + ' · ' +
      (e.all_day ? 'All day' : e.time + (e.end_time ? ' – ' + e.end_time : ''))]];
    if (e.who) facts.push(['Who', e.who]);
    if (e.where) facts.push(['Where', e.where]);
    facts.push(['Calendar', [c.label].concat(e.also || []).join(' + ')]);
    if (e.notes) facts.push(['Notes', e.notes]);
    var clash = overlaps(day, e) ? '<div class="sp-warn"><span><b>Overlaps ' + esc(sp.title) + '.</b> ' +
      esc(own.all_day ? sp.title + ' is all day.' : sp.title + ' runs ' + own.time + (own.end_time ? ' – ' + own.end_time : '') + '.') +
      ' If plans need to change, change it in Google Calendar.</span></div>' : '';
    overlay.innerHTML = '<div class="sheet daypop" role="document"><div class="dp-head"><div>' +
      '<button class="btn-back" data-act="event-back">' + I('chevron-left', 20, 2) + (sp ? esc(sp.title) : 'Back to the day') + '</button>' +
      '<h1 style="display:flex;align-items:center;gap:12px;margin-top:10px"><span class="dot" style="width:14px;height:14px;border-radius:7px;background:' +
      esc(c.color) + '"></span>' + esc(e.title) + '</h1></div>' +
      '<button class="btn-primary" data-act="close">Close</button></div>' +
      '<div class="dp-facts big">' + facts.map(function (f) { return '<b>' + f[0] + '</b><span>' + esc(f[1]) + '</span>'; }).join('') + '</div>' +
      clash + '</div>';
  }
  var MONTH_NAMES = { Jan: 'January', Feb: 'February', Mar: 'March', Apr: 'April', May: 'May', Jun: 'June', Jul: 'July',
    Aug: 'August', Sep: 'September', Oct: 'October', Nov: 'November', Dec: 'December' };

  function pressKey(k) {
    if (k === 'clear') { S.pin = ''; S.msg = ''; }
    else if (k === 'ok') { submitPin(); return; }
    else if (S.pin.length < 8) S.pin += k;
    renderOverlay();
  }
  function submitPin() {
    if (S.busy || S.pin.length < 4) return;
    S.busy = true;
    api('POST', 'api/parent/unlock', { pin: S.pin }).then(function (r) {
      S.busy = false; S.pin = '';
      if (r.ok && r.token) {
        S.token = r.token; S.who = r.name || ''; S.tokenUntil = Date.now() + 115000; S.msg = ''; S.ok = '';
        if (S.pinNext === 'frame-pick') { useFrame(S.pendingFrame); return; }
        S.overlay = S.pinNext === 'frame' ? 'frame' : S.pinNext === 'frame-new' ? 'framenew' : 'parent';
        S.pinNext = '';
        if (S.overlay === 'frame') loadFrames();
      }
      else S.msg = r.message || 'That PIN didn’t match.';
      renderOverlay();
    }).catch(function () { S.busy = false; S.msg = 'Can’t reach the server.'; renderOverlay(); });
  }
  function parentAction(kind, id) {
    var url = kind === 'approve' || kind === 'sendback'
      ? 'api/parent/chores/' + encodeURIComponent(id) + (kind === 'approve' ? '/approve' : '/send-back')
      : 'api/parent/screen/' + kind;
    parentPost(url, null, '');
  }
  function parentPost(url, body, okMsg) {
    if (!S.token || Date.now() > S.tokenUntil) { S.token = null; S.overlay = 'pin'; S.msg = 'Enter the PIN again.'; renderOverlay(); return; }
    S.lastTouch = Date.now();
    api('POST', url, body).then(function (r) {
      S.ok = ''; S.msg = '';
      if (r._status === 401) { S.token = null; S.overlay = 'pin'; S.msg = 'Enter the PIN again.'; }
      else if (r._status >= 400) S.msg = r.detail || 'Something went wrong.';
      else S.ok = okMsg;
      refresh();
    }).catch(function () { S.msg = 'Can’t reach the server.'; renderOverlay(); });
  }
  function sendAdjust() {
    var a = S.adj;
    if (!a.minutes) return;
    var kid = a.kid === 'all' ? null : a.kid, k = kid ? kidById(kid) : null;
    var msg = (a.minutes > 0 ? 'Added ' : 'Took away ') + Math.abs(a.minutes) + ' min' + (k ? (a.minutes > 0 ? ' for ' : ' from ') + k.name : '') + '.';
    parentPost('api/parent/screen/adjust', { minutes: a.minutes, kid: kid, scope: kid ? a.scope : 'family', note: a.why }, msg);
    S.adj = { kid: 'all', minutes: 0, scope: 'family', why: '' };
  }

  // ---------------- screens + actions ----------------
  var SCREEN_MODULE = { chores: 'chores', screen: 'screen_time', lists: 'lists', photos: 'photos', kids: 'kids_view' };
  function render() {
    if (!S.data) return;
    if (SCREEN_MODULE[S.screen] && !on(SCREEN_MODULE[S.screen])) {   // its module was just turned off
      if (S.screen === 'photos') stopPhotos();
      S.screen = homeScreen();
    }
    ['today', 'kids', 'clock', 'chores', 'calendar', 'screen', 'lists', 'photos', 'night'].forEach(function (n) {
      $('screen-' + n).classList.toggle('on', n === S.screen);
    });
    $('gear').style.display = $('hotcorner').style.display = S.screen === 'photos' || S.screen === 'night' ? 'none' : '';
    if (S.screen === 'today') renderToday();
    else if (S.screen === 'kids') renderKids();
    else if (S.screen === 'clock') renderClock();
    else if (S.screen === 'chores') renderChores();
    else if (S.screen === 'calendar') renderCalendar();
    else if (S.screen === 'screen') renderScreen();
    else if (S.screen === 'lists') renderLists();
    else if (S.screen === 'photos') renderPhotoOverlay();
    else if (S.screen === 'night') renderNight();
    if (S.overlay) renderOverlay();
    if (window.FrameLooks) FrameLooks.after({ screen: S.screen, root: $('screen-' + S.screen), layout: S.tall ? 'tall' : 'wide', kids: homeScreen() === 'kids' || !!frameOf().look_kids,
      today: S.data.now.slice(0, 10), family: S.data.family_name, initial: S.data.initial || '' });
  }
  function go(screen) {
    if (screen === S.screen) return;
    if (S.screen === 'photos') stopPhotos();
    if (screen === homeScreen()) { S.calOffset = { week: 0, rolling: 0, month: 0 }; S.calAlt = {}; }
    S.screen = screen;
    if (screen !== 'chores' && screen !== 'screen' && S.overlay !== 'listadd') closeOverlay();
    render();
    if (screen === 'photos') startPhotos();
  }
  function closeOverlay() {
    S.overlay = null; S.pin = ''; S.msg = ''; S.ok = ''; S.token = null; S.who = ''; S.confirmWeek = false;
    S.adj = { kid: 'all', minutes: 0, scope: 'family', why: '' };
    S.addText = ''; S.addMsg = ''; S.pinNext = '';
    renderOverlay();
  }

  function onClick(ev) {
    if (S.swallowClick) { S.swallowClick = false; ev.preventDefault(); return; }
    if (ev.target === overlay && (S.overlay === 'day' || S.overlay === 'listadd')) { closeOverlay(); render(); return; }  // tap outside the pop-up
    var el = ev.target.closest ? ev.target.closest('[data-act]') : null;
    if (!el) return;
    var act = el.getAttribute('data-act');
    if (act === 'go') go(el.getAttribute('data-to'));
    else if (act === 'kid') { S.kid = el.getAttribute('data-kid'); if (S.screen !== 'chores') go('chores'); else render(); }
    else if (act === 'calview') { S.calView = el.getAttribute('data-view'); render(); }
    else if (act === 'calnav') {
      var dir = +el.getAttribute('data-dir'), v = S.calView;
      S.calOffset[v] = dir === 0 ? 0 : Math.max(-24, Math.min(60, S.calOffset[v] + dir));
      loadCal(v);
    }
    else if (act === 'day') { S.dayDate = el.getAttribute('data-date'); S.dayEvent = null; S.overlay = 'day'; renderOverlay(); }
    else if (act === 'event') { S.dayDate = el.getAttribute('data-date') || S.dayDate; S.dayEvent = +el.getAttribute('data-i'); renderOverlay(); }
    else if (act === 'event-back') { S.dayEvent = null; renderOverlay(); }
    else if (act === 'special-day') {  // the Today ribbon: open that day on the calendar
      S.calView = 'rolling'; S.calOffset.rolling = 0; go('calendar');
      S.dayDate = el.getAttribute('data-date'); S.dayEvent = null;
      if (findDay(S.dayDate)) { S.overlay = 'day'; renderOverlay(); }
    }
    else if (act === 'claim') claim(el.getAttribute('data-id'));
    else if (act === 'open-pin') { S.overlay = 'pin'; S.pin = ''; S.msg = ''; renderOverlay(); }
    else if (act === 'key') pressKey(el.getAttribute('data-key'));
    else if (act === 'close') { closeOverlay(); render(); }
    else if (act === 'approve' || act === 'sendback') parentAction(act, el.getAttribute('data-id'));
    else if (act === 'view' || act === 'nextview') {
      var keys = views().map(function (v) { return v[0]; });
      S.view = act === 'view' ? el.getAttribute('data-view') : keys[(keys.indexOf(currentView()) + 1) % keys.length];
      saveView(S.view);
      render();
    }
    else if (act === 'goodday') parentPost('api/parent/screen/good-day', null, 'Good day added for everyone.');
    else if (act === 'week-ask') { S.confirmWeek = true; renderOverlay(); }
    else if (act === 'week-cancel') { S.confirmWeek = false; renderOverlay(); }
    else if (act === 'week-go') { S.confirmWeek = false; parentPost('api/parent/screen/new-week', null, 'New week started.'); }
    else if (act === 'adj-kid') { S.adj.kid = el.getAttribute('data-kid'); if (S.adj.kid === 'all') S.adj.scope = 'family'; renderOverlay(); }
    else if (act === 'adj-min') { S.adj.minutes = +el.getAttribute('data-min'); renderOverlay(); }
    else if (act === 'adj-scope') { S.adj.scope = el.getAttribute('data-scope'); renderOverlay(); }
    else if (act === 'adj-why') { var w = el.getAttribute('data-why'); S.adj.why = S.adj.why === w ? '' : w; renderOverlay(); }
    else if (act === 'adj-go') sendAdjust();
    // Home flip panel: remember the panel and its view on this frame
    else if (act === 'htab') {
      S.home.tab = el.getAttribute('data-tab'); S.home.day = S.data.now.slice(0, 10); S.home.after = allChoresDone();
      saveHome(); render();
    }
    else if (act === 'hchores') { S.home.chores = el.getAttribute('data-v'); saveHome(); render(); }
    else if (act === 'hweather') { S.home.weather = el.getAttribute('data-v'); saveHome(); render(); }
    // Lists
    else if (act === 'list-pick') { S.list = el.getAttribute('data-list'); render(); }
    else if (act === 'list-toggle') listToggle(el.getAttribute('data-id'));
    else if (act === 'list-add') { S.addList = el.getAttribute('data-list'); S.addText = ''; S.addMsg = ''; S.overlay = 'listadd'; renderOverlay(); }
    else if (act === 'la-list') { S.addList = el.getAttribute('data-list'); renderOverlay(); }
    else if (act === 'la-pick') listAdd(el.getAttribute('data-t'));
    // this frame: gear menu, first-run picker, new frame
    else if (act === 'gear') { S.pinNext = 'frame'; S.overlay = 'pin'; S.pin = ''; S.msg = ''; renderOverlay(); }
    else if (act === 'frame-use') useFrame(el.getAttribute('data-id'));
    else if (act === 'frame-ask') { S.pendingFrame = el.getAttribute('data-id'); S.pinNext = 'frame-pick'; S.overlay = 'pin'; S.pin = ''; S.msg = ''; renderOverlay(); }
    else if (act === 'frame-new') { S.addText = ''; S.addMsg = ''; S.newHome = ''; S.overlay = 'framenew'; renderOverlay(); }
    else if (act === 'frame-new-ask') { S.pinNext = 'frame-new'; S.overlay = 'pin'; S.pin = ''; S.msg = ''; renderOverlay(); }
    else if (act === 'fn-look') { S.newLook = el.getAttribute('data-look'); renderOverlay(); }
    else if (act === 'fn-home') { S.newHome = el.getAttribute('data-home'); renderOverlay(); }
    else if (act === 'kclaim') { S.kid = el.getAttribute('data-kid'); claim(el.getAttribute('data-id')); }   // Kids screen
    else if (act === 'kpick') { S.kid = el.getAttribute('data-kid'); render(); }
    else if (act === 'fn-go') frameNew();
    else if (act === 'frame-reload') location.reload();
    else if (act === 'refresh-now') refreshNow();
    else if (act === 'frame-name') { closeOverlay(); render(); showName(); }
    else if (act === 'la-go') listAdd(S.addText);
    else if (act === 'lk') {
      var k = el.getAttribute('data-k');
      if (k === 'del') S.addText = S.addText.slice(0, -1);
      else if (S.addText.length < 60) {
        var start = !S.addText || S.addText.slice(-1) === ' ';
        S.addText += /[A-Z]/.test(k) && !(start && !S.addText) ? k.toLowerCase() : k;
      }
      S.addMsg = ''; renderOverlay();
    }
  }
  function claim(id) {
    var k = kidById(S.kid);
    k.chores.forEach(function (c) { if (c.id === id) c.status = 'waiting'; }); // show it right away
    render();
    api('POST', 'api/chores/' + encodeURIComponent(id) + '/claim').then(refresh, refresh);
  }

  // Wake from photos/night on the first touch, without also "clicking" what's underneath.
  function onTouch() {
    S.lastTouch = Date.now();
    S.wakeUntil = Date.now() + 120000; // at night, a touch keeps the day screens up for 2 minutes
    if (S.screen === 'photos' || S.screen === 'night') { S.swallowClick = true; go(homeScreen()); }
  }

  function tick() {
    if (!S.data) return;
    var idle = Date.now() - S.lastTouch, st = S.data.settings;
    if (S.data.is_night && Date.now() > S.wakeUntil) { if (S.screen !== 'night') { closeOverlay(); go('night'); } }
    else if (S.screen === 'night' && !S.data.is_night) go(homeScreen());
    else if (S.overlay && idle > 120000) { closeOverlay(); render(); }
    else if (S.screen !== homeScreen() && S.screen !== 'photos' && S.screen !== 'night' && idle > st.return_to_today_minutes * 60000) go(homeScreen());
    else if (S.screen === homeScreen() && shows('photos') && idle > st.idle_minutes_to_photos * 60000 && S.data.photos_count) go('photos');
  }

  function refresh() {
    var px = window.devicePixelRatio || 1;
    return fetch('api/frame?frame=' + encodeURIComponent(S.frameId) + '&w=' + Math.round(window.innerWidth * px) + '&h=' + Math.round(window.innerHeight * px),
      { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (d) {
      // After an update the server's files change: reload once so the frame runs the new screens.
      if (d.asset_version && S.assets && d.asset_version !== S.assets && !S.overlay) { location.reload(); return; }
      S.assets = S.assets || d.asset_version;
      S.skew = d.epoch_ms - Date.now();
      var lookWas = S.data && S.data.frame && S.data.frame.look + '/' + S.data.frame.pictures;
      S.data = d;
      firstFrame(d);
      if (d.frame.look + '/' + d.frame.pictures !== lookWas) {   // the look, and its picture style (themes/, app/themes.py)
        document.body.className = document.body.className.replace(/\b(look-[\w-]+|pics-\w+)/g, '').replace(/\s+/g, ' ').trim() +
          ' look-' + d.frame.look + ' pics-' + (d.frame.pictures || 'original');
        Array.prototype.forEach.call(document.querySelectorAll('.screen'), function (el) { el._html = null; });
      }
      var lookKey = JSON.stringify([d.frame.look, d.frame.pictures, d.frame.look_options, d.frame.look_background, d.frame.look_kids]);
      if (window.FrameLooks && lookKey !== S.lookKey) { S.lookKey = lookKey; FrameLooks.apply(d.frame); }   // web/js/looks.js
      if (S.screen === 'today' && homeScreen() !== 'today' && !S.started) { S.screen = homeScreen(); }
      S.started = true;
      loadPhotos();
      if (!S.kid || !d.kids.some(function (k) { return k.id === S.kid; })) S.kid = d.kids.length ? d.kids[0].id : null;
      $('offline').classList.remove('on');
      if (S.screen === 'calendar' && S.calOffset[S.calView]) {
        // Calendars changed on the server, maybe: get a fresh copy of the page being looked at, but keep
        // showing the one we have until it arrives. Other cached pages are dropped and fetched again later.
        var v = S.calView, key = v + ':' + S.calOffset[v], keep = S.calAlt[key];
        S.calAlt = {};
        if (keep) S.calAlt[key] = keep;
        fetchCal(v, S.calOffset[v]);
      }
      if (S.data.is_night && Date.now() > S.wakeUntil && S.screen !== 'night') go('night');
      else render();
    }).catch(function () { $('offline').classList.add('on'); });
  }

  // Heartbeat for Settings > Frames: screen, browser, what this page stores, memory. Every 5 minutes,
  // and never in the way: any error is ignored. A web page can't see the frame's own disk; a kiosk app
  // that can may offer window.FamilyFrameKiosk.deviceStorage() returning '{"total": bytes, "free": bytes}'.
  var BOOT = Date.now();
  function heartbeat() {
    try {
      var o = (screen.orientation && screen.orientation.type) || (window.innerWidth >= window.innerHeight ? 'landscape' : 'portrait');
      var px = window.devicePixelRatio || 1;
      var b = { frame: S.frameId, ua: navigator.userAgent, uptime_s: Math.round((Date.now() - BOOT) / 1000),
        screen: { w: Math.round(window.innerWidth * px), h: Math.round(window.innerHeight * px), dpr: px, orientation: o } };
      if (navigator.deviceMemory) b.device_memory = navigator.deviceMemory;
      if (window.performance && performance.memory) b.heap = { used: performance.memory.usedJSHeapSize, limit: performance.memory.jsHeapSizeLimit };
      if (S.photoMs) b.photo_ms = S.photoMs;
      var k = window.FamilyFrameKiosk;
      if (k && typeof k.deviceStorage === 'function') { try { b.device_storage = JSON.parse(k.deviceStorage()); } catch (e) { /* not offered */ } }
      var send = function () {
        fetch('api/frame/heartbeat?frame=' + encodeURIComponent(S.frameId), { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(b) })['catch'](function () {});
      };
      // Only on https: plain http pages have no navigator.storage.
      if (navigator.storage && navigator.storage.estimate) {
        navigator.storage.estimate().then(function (e) { b.storage = { usage: e.usage, quota: e.quota }; send(); }, send);
      } else send();
    } catch (e) { /* never break the frame */ }
  }
  setTimeout(heartbeat, 20000);
  setInterval(heartbeat, 300000);

  if (window.FrameLooks) FrameLooks.host({   // the photo behind every screen, for a look that has one
    photos: function () { return S.photos; }, index: function () { return S.photoIdx; }, url: photoUrl,
    seconds: function () { return S.data ? S.data.settings.photo_seconds || 20 : 20; },
    advance: function () { if (S.screen !== 'photos' && S.photos.length) S.photoIdx = (S.photoIdx + 1) % S.photos.length; }
  });
  window.addEventListener('resize', fit);
  stage.addEventListener('pointerdown', onTouch, true);
  stage.addEventListener('click', onClick);
  fit();
  refresh();
  setInterval(refresh, 30000);
  setInterval(tick, 5000);
  setInterval(function () { if (S.screen !== 'photos' || S.data) render(); }, 15000);
})();
