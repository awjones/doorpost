/* Doorpost admin panel. Runs in the Home Assistant sidebar (add-on) or at /admin (standalone). */
(function () {
  'use strict';
  var I = window.ICONS;
  var root = document.getElementById('root');
  var toastEl = document.getElementById('toast');
  var S = null, MODS = null, HA = null, PHOTOS = null, GOOG = null, STATUS = null, SP = null, PK = null, PT = null, FAM = null, LISTS = null, FRAMES = null, FRAME_OPEN = -1, STORAGE = null;
  var DAYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];   // the week starts on the Lord's Day, as it always has
  // Each section is its own page: /admin (Overview), /admin/calendars, /admin/chores, ...
  var PAGES = [['overview', 'Overview'], ['modules', 'Modules'], ['frames', 'Frames'], ['calendars', 'Calendars'], ['special-days', 'Special days'], ['art-packs', 'Art packs'], ['photos', 'Photos'],
    ['family', 'Family'], ['chores', 'Chores'], ['lists', 'Lists'], ['screen-time', 'Screen time'], ['house', 'House status'], ['pins', 'Parent PINs']];
  var OLD_HASH = { overview: 'overview', calendars: 'calendars', special: 'special-days', photos: 'photos', kids: 'family', chores: 'chores',
    screen: 'screen-time', house: 'house', display: 'overview', security: 'pins' };
  var PAGE = (function () {
    var m = /\/admin\/([a-z-]+)\/?$/.exec(location.pathname);
    if (m && m[1] === 'kids') { location.replace('admin/family'); return 'family'; }   // the old Kids page
    var p = m && PAGES.some(function (x) { return x[0] === m[1]; }) ? m[1] : 'overview';
    var h = OLD_HASH[location.hash.slice(1)];
    if (h && h !== p) { location.replace(h === 'overview' ? 'admin' : 'admin/' + h); }
    return p;
  })();
  var PLAIN = /[?&]look=plain(&|$)/.test(location.search);   // ?look=plain: the plain Settings look, kept from page to page
  function pageHref(id) { return (id === 'overview' ? 'admin' : 'admin/' + id) + (PLAIN ? '?look=plain' : ''); }
  // Settings > Modules: a page whose module is off leaves the menu (an older server sends no list: all on).
  function modOn(id) { return !S || !S.modules || S.modules.indexOf(id) >= 0; }
  function pageOn(page) { var m = S && S.page_modules && S.page_modules[page]; return !m || modOn(m); }
  var CAL_OPEN = {}, CHORE_KID = null, CHORE_OPEN = -1, CHORE_PICK = {}, PHOTO_SHOWN = 12;
  var FOCUS_ID = null, FOCUS_MODE = 'point', FD = null, FX_DIRTY = false, PHOTO_FILTER = 'all';
  var DAY_LETTERS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function $(sel, el) { return (el || document).querySelector(sel); }
  function $$(sel, el) { return Array.prototype.slice.call((el || document).querySelectorAll(sel)); }
  function toast(msg, bad, stay) {
    toastEl.textContent = msg; toastEl.className = bad ? 'bad' : ''; toastEl.style.display = 'block';
    clearTimeout(toast.t);
    if (!stay) toast.t = setTimeout(function () { toastEl.style.display = 'none'; }, bad ? 6000 : 2500);
  }
  function api(method, url, body, isForm) {
    var opts = { method: method, credentials: 'same-origin', headers: {} };
    if (body !== undefined) {
      if (isForm) opts.body = body;
      else { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
    }
    return fetch(url, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) { var e = new Error(j.detail || ('Error ' + r.status)); e.status = r.status; throw e; }
        return j;
      });
    });
  }
  function av(k, cls) {
    if (k.photo) return '<span class="av ' + cls + ' face" style="background:' + esc(k.color) + ' url(\'' + esc(k.photo) + '\') center/cover no-repeat"></span>';
    return '<span class="av ' + cls + '" style="background:' + esc(k.color) + '">' + esc(k.initial || (k.name || '?')[0]) + '</span>';
  }
  function card(id, title, help, body, saveLabel) {
    return '<section class="card" id="' + id + '"><h2>' + title + '</h2>' + (help ? '<p class="help">' + help + '</p>' : '') + body +
      (saveLabel ? '<div class="actions"><button class="btn primary" data-save="' + id + '">' + saveLabel + '</button></div>' : '') + '</section>';
  }
  function field(label, html) { return '<label class="f">' + label + html + '</label>'; }
  function input(name, value, type, extra) {
    return '<input type="' + (type || 'text') + '" data-k="' + name + '" value="' + esc(value) + '"' + (extra || '') + '>';
  }

  // ---------------- sign-in (standalone only) ----------------
  function showGate(err) {
    if (err.status === 403) {
      root.innerHTML = card('gate', 'Open from Home Assistant', 'Settings can only be changed from the <b>Doorpost</b> link in the Home Assistant sidebar.', '');
      return;
    }
    root.innerHTML = card('gate', 'Parent sign-in', 'Use the parent PIN.',
      '<div class="row">' + field('PIN', '<input id="pin" type="password" inputmode="numeric" maxlength="8">') +
      '<button class="btn primary" id="go">Sign in</button></div><div class="result bad" id="gerr"></div>');
    function go() {
      api('POST', 'api/parent/unlock?remember=1', { pin: $('#pin').value }).then(load)
        .catch(function (e) { $('#gerr').textContent = e.message === 'Error 403' ? 'That PIN didn’t match.' : e.message; });
    }
    $('#go').onclick = go;
    $('#pin').onkeydown = function (e) { if (e.key === 'Enter') go(); };
    $('#pin').focus();
  }

  // ---------------- load + render ----------------
  // The basics first (draw the page right away), then only what this page needs, each on its own.
  var EXTRA = {
    photos: ['api/admin/photos', function (v) { PHOTOS = v; }], house: ['api/admin/ha/entities', function (v) { HA = v; }],
    special: ['api/admin/special', function (v) { SP = v; }], portraits: ['api/admin/portraits', function (v) { PT = v; }], family: ['api/admin/family', function (v) { FAM = v; }], lists: ['api/admin/lists', function (v) { LISTS = v; }],
    modules: ['api/admin/modules', function (v) { MODS = v; }], frames: ['api/admin/frames', function (v) { FRAMES = v; }], storage: ['api/admin/storage', function (v) { STORAGE = v; }], google: ['api/admin/google', function (v) { GOOG = v; }], packs: ['api/admin/packs', function (v) { PK = v; }]
  };
  var PAGE_NEEDS = { modules: ['modules'], overview: ['lists', 'storage'], photos: ['photos', 'google'], house: ['house'], 'special-days': ['special'], 'art-packs': ['packs'], family: ['family'], lists: ['lists'], frames: ['frames', 'storage'] };
  var BLOCKING = { modules: 'modules', photos: 'photos', house: 'house', 'special-days': 'special', 'art-packs': 'packs', family: 'family', lists: 'lists', frames: 'frames' };  // can't draw without it
  function load() {
    return Promise.all([api('GET', 'api/admin/settings'), api('GET', 'api/admin/status')])
      .then(function (r) {
        S = r[0]; STATUS = r[1];
        render();
        return Promise.all((PAGE_NEEDS[PAGE] || []).filter(function (k) { return k !== 'lists' || modOn('lists'); }).map(function (k) {
          return api('GET', EXTRA[k][0]).then(function (v) { EXTRA[k][1](v); render(); })
            .catch(function (e) { if (BLOCKING[PAGE] === k) root.innerHTML = card('err', 'Couldn’t load this page', esc(e.message), ''); });
        }));
      })
      .catch(showGate);
  }
  function waitingFor() {
    var k = BLOCKING[PAGE];
    var have = { modules: MODS, photos: PHOTOS, house: HA, special: SP, family: FAM, lists: LISTS, frames: FRAMES, packs: PK };
    return k && !have[k] ? k : null;
  }

  function render() {
    var keep = window.scrollY;
    var base = (S.display.frame_url || '').replace(/\/$/, '');
    if (base) {
      var links = document.querySelectorAll('.aband .links a');
      links[0].href = base + '/'; links[1].href = base + '/parent';
    }
    var name = PAGES.filter(function (x) { return x[0] === PAGE; })[0][1];
    $('#side').innerHTML = PAGES.filter(function (x) { return pageOn(x[0]); }).map(function (x) {
      return '<a href="' + pageHref(x[0]) + '"' + (x[0] === PAGE ? ' class="on" aria-current="page"' : '') + '>' + x[1] + '</a>';
    }).join('');
    $('.aband .kicker').textContent = 'Settings · ' + name;
    document.title = 'Doorpost · ' + name;
    var BUILD = { overview: function () { return overview() + storageCard() + display() + (window.AdminLook ? window.AdminLook.html() : ''); }, modules: modulesPage, frames: framesPage, calendars: calendars, 'special-days': function () { return special() + (window.FrameBible ? window.FrameBible.html() : ''); }, 'art-packs': artPacks, photos: photos,
      family: family, chores: chores, lists: lists, 'screen-time': screenTime, house: house, pins: security };
    if (waitingFor()) {
      root.innerHTML = card('loading', name, '<span class="spin" aria-hidden="true"></span> Loading…', '');
      return;
    }
    root.innerHTML = BUILD[PAGE]();
    window.scrollTo(0, keep);
    wire();
    wireFocus();
    $$('[data-cal-redraw]').forEach(function (sel) {  // a calendar's source changed: show its steps and fields
      sel.onchange = function () {
        var i = +sel.closest('[data-cal]').getAttribute('data-cal');
        stash();
        if (sel.getAttribute('data-k') === 'provider') S.calendars[i].kind = CAL_PROV[sel.value].kinds[0];
        CAL_OPEN[i] = true; render();
      };
    });
    $$('[data-fk=look], [data-fk=pictures], [data-fk=own_night], [data-fk=home]').forEach(function (inp) { inp.onchange = function () { stashFrames(); render(); }; });
  }

  function overview() {
    var st = STATUS, todo = [];
    Object.keys(st.calendar_errors || {}).forEach(function (k) { todo.push(['Calendar “' + k + '”: ' + st.calendar_errors[k], 'calendars']); });
    S.calendars.forEach(function (c) {
      if (c.public) todo.push([c.label + '’s calendar uses its public address. Paste the secret one so it isn’t readable by anyone.', 'calendars']);
      else if (!c.has_url) todo.push([c.label + ' has no calendar address yet.', 'calendars']);
    });
    if (st.weather_error) todo.push(['Weather: ' + st.weather_error, 'overview']);
    if (st.home_error) todo.push(['Home Assistant: ' + st.home_error, 'house']);
    if (st.screen_new_week_due) todo.push(['Screen time: it’s time to start a new week (on the parent page or the frame).', 'screen-time']);
    (st.photo_sources || []).forEach(function (p) { if (p.error) todo.push(['Photo album: ' + p.error, 'photos']); });
    storageTodo().forEach(function (t) { todo.push([t, 'overview']); });
    if (modOn('lists') && LISTS && LISTS.shown.length && LISTS.sources && LISTS.sources.apple.lists && LISTS.synced_ago > 3600) todo.push(['Lists: the Mac last checked in ' + ago(LISTS.synced_ago) + '. Is it asleep or off?', 'lists']);
    if (modOn('lists') && LISTS && LISTS.sources && LISTS.sources.google.error) todo.push(['Lists: Google Tasks says “' + LISTS.sources.google.error + '”', 'lists']);
    var mode = S.mode.demo ? 'Demo mode: sample data. PINs: 1234 (Dad), 5678 (Mom).' : S.mode.addon ? 'Running as a Home Assistant app.' : 'Running on its own server.';
    var good = S.calendars.filter(function (c) { return c.has_url; }).length;
    return card('overview', 'Overview', mode,
      '<div class="stat"><div><b>' + good + ' of ' + S.calendars.length + '</b><span>calendars connected</span></div>' +
      (modOn('photos') ? '<div><b>' + st.photos + '</b><span>photos in the slideshow</span></div>' : '') +
      '<div><b>' + S.kids.length + '</b><span>kids' + (modOn('chores') ? ' · ' + S.chores.length + ' chores' : '') + '</span></div>' +
      (modOn('screen_time') ? '<div><b>' + esc(st.screen_total) + '</b><span>' + esc(st.screen_headline.toLowerCase()) + '</span></div>' : '') + '</div>' +
      (todo.length ? '<h3 class="kick">Needs attention</h3>' + todo.map(function (t) {
        return '<a class="warn attn" href="' + pageHref(t[1]) + '"><span>' + esc(t[0]) + '</span>' +
          (t[1] !== 'overview' ? '<b>Open ' + esc(PAGES.filter(function (x) { return x[0] === t[1]; })[0][1]) + ' ›</b>' : '') + '</a>';
      }).join('') : '<p class="result ok">Everything is connected.</p>') +
      (st.calendar_refreshed ? '<p class="help">Calendars last read at ' + esc(st.calendar_refreshed.replace('T', ' ')) + '.</p>' : ''));
  }

  // Where a calendar comes from (see docs/calendars.md). kinds: 'ics' is a link, 'caldav' a private sign-in.
  var CAL_PROV = {
    google: { name: 'Google', kinds: ['ics'], steps: [
      'Open Google Calendar on a computer. Click the gear, then <b>Settings</b>.',
      'On the left, under <b>Settings for my calendars</b>, click the calendar.',
      'Click <b>Integrate calendar</b> and copy the <b>Secret address in iCal format</b>.',
      'Paste it below, then press <b>Check</b>.'],
      field: 'Secret address in iCal format', ph: 'https://calendar.google.com/calendar/ical/…/basic.ics',
      note: 'Anyone with this secret address can read the calendar, so keep it private. To cut off an old address, use <b>Reset</b> next to it in Google Calendar.' },
    icloud: { name: 'Apple iCloud', kinds: ['caldav', 'ics'], steps: [
      'On a computer or phone, go to <b>account.apple.com</b> and sign in.',
      'Open <b>Sign-In and Security</b>, then <b>App-Specific Passwords</b>. Make one called “Doorpost” and copy it.',
      'Type your Apple ID email and that password below, then press <b>Find my calendars</b>.',
      'Pick the calendar, then press <b>Check</b>.'],
      linkSteps: [
        'On your iPhone, open <b>Calendar</b>, tap <b>Calendars</b>, then the <b>i</b> next to the calendar.',
        'Turn on <b>Public Calendar</b>, then tap <b>Share Link</b> and copy it.',
        'Paste it below (a webcal:// link is fine), then press <b>Check</b>.'],
      field: 'Public calendar link', ph: 'webcal://p01-caldav.icloud.com/published/2/…',
      note: 'Private: only this server signs in. To cut it off, delete the app-specific password at account.apple.com.',
      linkNote: 'A public link can be read by anyone who has it. Signing in with an app-specific password keeps it private.' },
    outlook: { name: 'Outlook', kinds: ['ics'], steps: [
      'Open Outlook on the web (Outlook.com or Microsoft 365). Go to <b>Settings</b>, <b>Calendar</b>, then <b>Shared calendars</b>.',
      'Under <b>Publish a calendar</b>, pick the calendar and <b>Can view all details</b>, then press <b>Publish</b>.',
      'Copy the <b>ICS</b> link (not the HTML one), paste it below, then press <b>Check</b>.'],
      field: 'ICS link', ph: 'https://outlook.office365.com/owa/calendar/…/calendar.ics',
      note: 'Anyone with this link can read the calendar. To cut it off, press <b>Unpublish</b> in the same place.' },
    other: { name: 'Other', kinds: ['ics', 'caldav'], steps: [
      'In your calendar app, look for <b>Publish</b>, <b>Share</b>, <b>Subscribe</b> or <b>Export as iCal</b>.',
      'Copy the address. It usually ends in .ics or starts with webcal://.',
      'Paste it below, then press <b>Check</b>.'],
      davSteps: [
        'Make an app password in your account’s security settings (Fastmail, Nextcloud and others have one).',
        'Type the CalDAV server address, your sign-in name and that password below.',
        'Press <b>Find my calendars</b>, pick one, then press <b>Check</b>.'],
      field: 'Calendar address (.ics or webcal://)', ph: 'https://example.com/calendar.ics',
      note: 'A link can usually be read by anyone who has it.',
      davNote: 'Private: only this server signs in. To cut it off, delete the app password in your account.' }
  };
  var CAL_FOUND = {};  // calendars listed by Find my calendars, by row
  function calProv(c) { return CAL_PROV[c.provider] ? c.provider : 'other'; }
  function calKind(c) { var k = CAL_PROV[calProv(c)].kinds; return k.indexOf(c.kind) >= 0 ? c.kind : k[0]; }
  function calStatus(c) {
    var err = (STATUS.calendar_errors || {})[c.key];
    if (err) return ['bad', 'Problem: ' + err];
    if (c.public) return ['warn', 'Public address: paste the secret one'];
    if (!c.has_url) return ['warn', !c.key ? 'New' : calKind(c) === 'caldav' ? (c.has_password ? 'Pick a calendar' : 'Not signed in yet') : 'No address yet'];
    return ['ok', 'Connected'];
  }
  function calSource(c, i) {
    var pk = calProv(c), p = CAL_PROV[pk], kind = calKind(c), dav = kind === 'caldav';
    var steps = dav ? (p.davSteps || p.steps) : (p.linkSteps || p.steps);
    var note = dav ? (p.davNote || p.note) : (p.linkNote || p.note);
    var opts = Object.keys(CAL_PROV).map(function (k) {
      return '<option value="' + k + '"' + (k === pk ? ' selected' : '') + '>' + (k === 'other' ? 'Other link or account' : CAL_PROV[k].name) + '</option>';
    }).join('');
    var how = p.kinds.length > 1
      ? field('How', '<select data-k="kind" data-cal-redraw>' + p.kinds.map(function (k) {
          var t = k === 'caldav' ? (pk === 'icloud' ? 'Private: sign in with an app-specific password' : 'Private: a CalDAV account (Fastmail, Nextcloud…)')
            : (pk === 'icloud' ? 'Public link (anyone with it can see)' : 'A link (.ics or webcal://)');
          return '<option value="' + k + '"' + (k === kind ? ' selected' : '') + '>' + t + '</option>';
        }).join('') + '</select>')
      : '<input type="hidden" data-k="kind" value="' + kind + '">';
    var html = '<div class="row">' + field('Calendar from', '<select data-k="provider" data-cal-redraw>' + opts + '</select>') + how + '</div>' +
      '<ol class="steps">' + steps.map(function (t) { return '<li>' + t + '</li>'; }).join('') + '</ol>';
    if (!dav) {
      return html + '<div class="row">' + field(p.field, input('ics_url', c.ics_url_pending || '', 'url',
        ' placeholder="' + (c.has_url && c.kind !== 'caldav' ? 'Saved (' + esc(c.url_hint || 'demo file') + '). Paste a new one to replace it.' : p.ph) + '"')) + '</div>' +
        '<p class="help">' + note + '</p>';
    }
    var found = CAL_FOUND[i], cur = c.caldav_calendar || '';
    var calOpts = found ? found.map(function (f) {
      return '<option value="' + esc(f.url) + '"' + (f.url === cur ? ' selected' : '') + '>' + esc(f.name) + '</option>';
    }).join('') : (cur ? '<option value="' + esc(cur) + '" selected>' + esc(c.caldav_calendar_name || 'Saved calendar') + '</option>' : '<option value="">Press Find my calendars</option>');
    return html +
      (pk === 'icloud' ? '' : '<div class="row">' + field('CalDAV server', input('caldav_server', c.caldav_server || '', 'url', ' placeholder="https://caldav.fastmail.com"')) + '</div>') +
      '<div class="row">' + field(pk === 'icloud' ? 'Apple ID email' : 'Sign-in name', input('caldav_user', c.caldav_user || '', 'text', ' autocomplete="off" placeholder="you@example.com"')) +
      field(pk === 'icloud' ? 'App-specific password' : 'App password', '<input type="password" data-k="caldav_password" autocomplete="new-password" value="' + esc(c.caldav_password_pending || '') + '" placeholder="' +
        (c.has_password ? 'Saved. Type a new one to replace it.' : 'xxxx-xxxx-xxxx-xxxx') + '">') + '</div>' +
      '<div class="row">' + field('Which calendar', '<select data-k="caldav_calendar">' + calOpts + '</select>') +
      '<div class="f" style="justify-content:flex-end"><button class="btn line" data-act="find-cals" data-i="' + i + '">Find my calendars</button></div></div>' +
      '<p class="help">' + note + '</p>';
  }
  function calendars() {
    var rows = S.calendars.map(function (c, i) {
      var st = calStatus(c), open = CAL_OPEN[i] || !c.key;
      var sub = [CAL_PROV[calProv(c)].name + (calKind(c) === 'caldav' ? ' (private)' : '')];
      if (c.who_default) sub.push('Usually for ' + c.who_default);
      return '<section class="fold" data-cal="' + i + '">' +
        '<button type="button" class="fold-head" data-act="cal-fold" data-i="' + i + '" aria-expanded="' + !!open + '">' +
        '<span class="dot" style="background:' + esc(c.color) + '"></span><b>' + esc(c.label || 'New calendar') + '</b>' +
        '<i>' + esc(sub.join(' · ')) + '</i>' +
        '<span class="chip ' + st[0] + '">' + esc(st[1]) + '</span><span class="chev">' + I('chevron-down', 20, 2) + '</span></button>' +
        '<div class="fold-body"' + (open ? '' : ' hidden') + '><div class="row">' +
        field('Name', input('label', c.label)) + field('Color', input('color', c.color, 'color')) +
        field('Usually for', input('who_default', c.who_default, 'text', ' placeholder="e.g. everyone, Dad"')) + '</div>' +
        calSource(c, i) +
        '<div class="row">' + field('Show', '<select data-k="filter_mode"><option value="all"' + (c.filter_mode !== 'family' ? ' selected' : '') +
          '>Every event</option><option value="family"' + (c.filter_mode === 'family' ? ' selected' : '') +
          '>Only events with these people, or that name a family member</option></select>') +
        field('People (emails)', input('filter_emails', c.filter_emails, 'text', ' placeholder="dad@example.com"')) + '</div>' +
        '<div class="actions"><button class="btn line" data-act="test-cal" data-i="' + i + '">Check</button>' +
        '<button class="btn quiet" data-act="cal-move" data-i="' + i + '" data-dir="-1"' + (i ? '' : ' disabled') + '>Move up</button>' +
        '<button class="btn quiet" data-act="cal-move" data-i="' + i + '" data-dir="1"' + (i < S.calendars.length - 1 ? '' : ' disabled') + '>Move down</button>' +
        '<button class="btn danger" data-act="del-cal" data-i="' + i + '">Remove</button><span class="result" data-res></span></div></div></section>';
    }).join('');
    var anyOpen = S.calendars.some(function (c, i) { return CAL_OPEN[i]; });
    var add = Object.keys(CAL_PROV).map(function (k) {
      return '<button class="btn quiet" data-act="add-cal" data-p="' + k + '">+ ' + (k === 'other' ? 'Other link' : CAL_PROV[k].name) + '</button>';
    }).join('');
    return card('calendars', 'Calendars',
      'Tap a calendar to open it. Each one comes from Google, Apple iCloud, Outlook or any other calendar with a link. ' +
      'Addresses and passwords stay on this server and never go to the frame. More help: <b>docs/calendars.md</b>.',
      '<label class="check"><input type="checkbox" id="merge-shared"' + (S.merge_shared_events ? ' checked' : '') +
      '> Show shared events once (an invite between you two, or the same event on two calendars)</label>' +
      '<p class="help">When an event is on more than one calendar, the frame shows it once with everyone’s names, ' +
      'in the color of the calendar <b>higher in this list</b> (use Move up and Move down).</p>' +
      rows + '<div class="actions"><span class="help" style="align-self:center">Add a calendar from:</span>' + add + '</div>' +
      '<div class="actions"><button class="btn quiet" data-act="cal-fold-all">' + (anyOpen ? 'Fold all' : 'Open all') + '</button></div>', 'Save calendars');
  }

  // ---------------- special days ----------------
  // Names for pictures that aren't in a picture group (the rest come from the art packs).
  var LOOK_NAMES = { vacation: 'Beach (older name)' };
  function shortDate(iso) {
    return new Date(iso + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  }
  function lookOptions(cur) {
    var opts = '<option value="">Gold pattern (no picture)</option>';
    if (SP.pictures.length) opts += '<optgroup label="Your pictures">' + SP.pictures.map(function (p) {
      return '<option value="' + esc(p) + '"' + (p === cur ? ' selected' : '') + '>' + esc(p) + '</option>'; }).join('') + '</optgroup>';
    return opts + '<optgroup label="Built-in drawings">' + SP.themes.map(function (t) {
      return '<option value="' + t + '"' + (t === cur ? ' selected' : '') + '>' + esc(spItem(t).name) + '</option>'; }).join('') + '</optgroup>';
  }
  // Tap a picture to copy the line that picks it ("photo: waterpark") for an event's description.
  function themeThumb(name, svg, del) {
    var code = 'photo: ' + name;
    return '<div class="thumb sp-thumb" role="button" tabindex="0" data-act="sp-copy" data-code="' + esc(code) + '" title="Tap to copy “' + esc(code) + '”">' + svg +
      '<small class="pcode">' + esc(code) + '</small>' +
      (del ? '<button data-act="sp-pic-del" data-name="' + esc(name) + '" aria-label="Remove ' + esc(name) + '">Remove</button>' : '') + '</div>';
  }
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    // The Home Assistant sidebar on http:// can't use the clipboard API; the old way still works there.
    var ta = document.createElement('textarea');
    ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    return ok ? Promise.resolve() : Promise.reject(new Error('copy blocked'));
  }
  function artThumb(key, big) {
    var th = window.THEMES || {};
    var svg = (th[key] || '').replace('{{PLACE_SIZE}}', '22').replace('{{PLACE}}', 'Fun Park').replace('{{NAME_SIZE}}', '22')
      .replace('{{NAME}}', 'Birthday').replace('{{PORTRAIT}}', '');
    return big ? svg : svg.replace(/(x(?:Min|Mid|Max))YMax slice/, '$1YMid slice');
  }
  // ---------------- Settings > Art packs ----------------
  // The pictures for special days come in packs (app/packs.py). Built-in packs can be turned off; packs from the list or a zip
  // can be installed, turned off and removed. Changes save right away; the frame reloads its drawings by itself.
  function kb(n) { return n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB'; }
  function pkReload() {
    return api('GET', 'api/admin/packs').then(function (v) { PK = v; SP = null; render(); });
  }
  function pkCall(method, url, body, msg) {
    return api(method, url, body).then(function () { toast(msg); return pkReload(); }).catch(function (e) { toast(e.message, true); return pkReload(); });
  }
  function pkThumb(src) {
    return '<span class="thumb pk-thumb">' + (src ? '<img loading="lazy" alt="" src="' + esc(src) + '">' : '') + '</span>';
  }
  function artPacks() {
    var mine = PK.packs.map(function (p) {
      var upd = PK.index.filter(function (e) { return e.id === p.id && e.update; })[0];
      var dflt = p.where === 'installed' && PK.index.some(function (e) { return e.id === p.id && e.default; });   // the Faith pack
      return '<div class="pk-row' + (p.on ? '' : ' off') + '">' + pkThumb(p.preview) + '<div class="pk-text"><b>' + esc(p.name) + '</b>' +
        '<small>' + (dflt ? 'Comes installed (you can remove it)' : esc(p.where_label)) + ' · version ' + esc(p.version || '?') + ' · ' + p.pictures + ' pictures · ' + kb(p.size) + '</small>' +
        '<span>' + esc(p.description) + '</span>' + (p.license ? '<small>License: ' + esc(p.license) + '</small>' : '') + '</div>' +
        '<div class="pk-acts"><label class="sp-switch"><input type="checkbox" data-act="pk-turn" data-id="' + esc(p.id) + '" data-on="' + (p.on ? '0' : '1') + '"' + (p.on ? ' checked' : '') + '><span></span>' + (p.on ? 'On' : 'Off') + '</label>' +
        (upd ? '<button type="button" class="btn line" data-act="pk-install" data-id="' + esc(p.id) + '">Update to ' + esc(upd.version) + '</button>' : '') +
        (p.removable ? '<button type="button" class="btn quiet" data-act="pk-remove" data-id="' + esc(p.id) + '" data-name="' + esc(p.name) + '">Remove</button>' : '') + '</div></div>';
    }).join('');
    var more = PK.index.filter(function (e) { return !e.installed; }).map(function (e) {
      return '<div class="pk-row">' + pkThumb(e.preview) + '<div class="pk-text"><b>' + esc(e.name) + '</b>' +
        '<small>Version ' + esc(e.version) + (e.pictures ? ' · ' + e.pictures + ' pictures' : '') + (e.size ? ' · ' + kb(e.size) + ' download' : '') + '</small>' +
        '<span>' + esc(e.description) + '</span>' + (e.license ? '<small>License: ' + esc(e.license) + '</small>' : '') + '</div>' +
        '<div class="pk-acts"><button type="button" class="btn primary" data-act="pk-install" data-id="' + esc(e.id) + '">Install</button></div></div>';
    }).join('');
    return card('art-packs', 'Art packs',
      'Art packs hold the pictures for special days and the rules that bring them up: holidays, church days, title words, the seasons and the Sunday pictures. ' +
      'A pack that is off shows nothing on the frame and nothing in Settings.', '<div class="pk-list">' + (mine || '<p class="help">No packs found.</p>') + '</div>') +
      card('pk-more', 'Get more packs', 'Each one is checked before it is installed (a checksum, then every drawing is cleaned of anything that could run code).',
        '<div class="pk-list">' + (more || '<p class="help">Everything in the list is installed.</p>') + '</div>') +
      card('pk-up', 'Install from a zip', 'A pack you made or were given: a .zip with a pack.json and its drawings, up to ' + PK.max_mb + ' MB. See docs/art-packs.md for how to make one.',
        '<div class="row">' + field('Pack zip', '<input type="file" id="pk-file" accept=".zip,application/zip">') + '<button type="button" class="btn primary" data-act="pk-upload">Install</button></div>');
  }

  // ---------------- Settings > Special days ----------------
  // One short page: summary cards for Google's holidays, the church year and your own photos (each opens in a pop-up),
  // the Sunday / season switches, then the built-in pictures in folded groups. Tap a picture for what it is and its
  // rules: the title words that pick it (by itself, or only with a star), its code, and a real photo to use instead.
  // "Rules list" shows every rule in one table instead. Changes save as you make them.
  var SP_VIEW = 'pictures', SP_OPEN = {}, MODAL = null;
  var CATCH_ALL = ['beach', 'vacation'];   // general words stay last: first match wins
  function spItem(key) {
    var it = null;
    (SP.groups || []).forEach(function (g) { g.items.forEach(function (x) { if (x.key === key) it = x; }); });
    return it || { key: key, name: LOOK_NAMES[key] || (SP.look_names || {})[key] || key, about: '', auto: '', code: 'photo: ' + key };
  }
  function wordsFor(key) {
    return SP.words.map(function (w, i) { return { w: w, i: i }; }).filter(function (x) { return x.w.look === key; });
  }
  function hasPhoto(key) { return SP.pictures.indexOf(key) >= 0; }
  function spSave(body, msg) {
    return api('PUT', 'api/admin/special', body).then(function () { return api('GET', 'api/admin/special'); })
      .then(function (v) { SP = v; render(); if (MODAL) MODAL.paint(); toast(msg || 'Saved'); })
      .catch(function (e) { toast(e.message, true); });
  }
  function spRefresh(msg) {
    return api('GET', 'api/admin/special').then(function (v) { SP = v; render(); if (MODAL) MODAL.paint(); if (msg) toast(msg); });
  }
  function insertAt() {
    var at = SP.words.findIndex(function (w) { return CATCH_ALL.indexOf((w.word || '').toLowerCase()) >= 0; });
    return at < 0 ? SP.words.length : at;
  }
  function wordsSave(words, msg) { return spSave({ words: words.map(function (w) { return { word: w.word, look: w.look, picture_only: !!w.picture_only }; }) }, msg); }
  function mini(key) { return '<span class="sp-mini">' + artThumb(key) + '</span>'; }

  function special() {
    var g = SP.google, count = function (m) { return g.filter(function (h) { return h.mode === m; }).length; };
    var nextHol = g.filter(function (h) { return h.mode !== 'hide'; })[0];
    var on = SP.church.filter(function (c) { return c.on; });
    var cards = '<div class="sp-cards">' +
      '<div class="sp-sum"><b>Holidays from Google</b><span>' + count('special') + ' special · ' + count('show') + ' shown · ' + count('hide') + ' hidden' +
        (nextHol ? '. Next: ' + esc(nextHol.name) + ' (' + nextHol.mode + '), ' + esc(shortDate(nextHol.date)) : '') + '</span>' +
        (SP.holiday_error ? '<span class="result bad">' + esc(SP.holiday_error) + '</span>' : '') +
        '<button type="button" class="btn line" data-act="sx-holidays">Edit holidays</button></div>' +
      (SP.church.length ? '<div class="sp-sum"><b>Church year</b><span>' + on.length + ' of ' + SP.church.length + ' on' + (on[0] ? '. Next: ' + esc(on[0].name) + ', ' + esc(shortDate(on[0].date)) : '') + '</span>' +
        '<button type="button" class="btn line" data-act="sx-church">Edit church days</button></div>' : '') +
      '<div class="sp-sum"><b>Your photos</b><span>' + (SP.pictures.length ? SP.pictures.length + ' uploaded: ' + SP.pictures.slice(0, 4).map(esc).join(', ') + (SP.pictures.length > 4 ? '…' : '') : 'None yet. Upload one to use instead of a drawing.') + '</span>' +
        '<button type="button" class="btn line" data-act="sx-photos">' + (SP.pictures.length ? 'See photos' : 'Add a photo') + '</button></div></div>';
    var sw = function (id, onv, label) {
      return '<label class="sp-switch"><input type="checkbox" data-spt="' + id + '"' + (onv ? ' checked' : '') + '><span></span>' + label + '</label>';
    };
    // The Sunday and season switches only show when an art pack has those pictures (Settings > Art packs).
    var toggles = '<div class="sp-toggles">' + (SP.has_sundays ? sw('sundays', SP.sundays, esc(SP.sunday_label)) : '') + (SP.has_seasons ? sw('seasons', SP.seasons, 'First day of each season') : '') +
      '<label class="sp-count">Countdown <input type="number" min="0" max="60" data-spt="countdown_days" value="' + esc(SP.countdown_days) + '"> days before</label></div>';
    var view = '<div class="sp-head"><h3>Pictures and their rules</h3><div class="seg sp-view" role="group" aria-label="View">' +
      ['pictures', 'list'].map(function (v) {
        return '<button type="button" data-act="sp-view" data-view="' + v + '" class="' + (SP_VIEW === v ? 'on special' : '') + '" aria-pressed="' + (SP_VIEW === v) + '">' + (v === 'list' ? 'Rules list' : 'Pictures') + '</button>';
      }).join('') + '</div></div>';
    return card('special', 'Special days',
      'Star an event (⭐) in Google Calendar, or use a title word below, and its day gets a full picture. Tap any picture to see when it comes up and change it. ' +
      'More pictures: <a href="' + pageHref('art-packs') + '"><b>Art packs</b></a>. In an event’s description, <b>photo: waterpark</b> picks a picture and <b>photo: none</b> keeps that one event plain. Birthdays live on the <a href="' + pageHref('family') + '"><b>Family</b></a> page.',
      cards + toggles + view + (SP_VIEW === 'list' ? rulesList() : pictureGroups()));
  }
  function pictureGroups() {
    return (SP.groups || []).map(function (g) {
      return '<details class="pg" data-grp="' + esc(g.name) + '"' + (SP_OPEN[g.name] ? ' open' : '') + '><summary><b>' + esc(g.name) + '</b><small>' + g.items.length + '</small>' +
        '<span class="sp-minis">' + g.items.slice(0, 6).map(function (it) { return mini(it.key); }).join('') + '</span></summary><div class="pg-grid">' +
        g.items.map(function (it) {
          var n = wordsFor(it.key).length;
          return '<div class="pg-item"><button type="button" class="thumb sp-thumb" data-act="pg-open" data-key="' + esc(it.key) + '" aria-label="' + esc(it.name) + ': rules">' +
            (hasPhoto(it.key) ? '<img src="special/' + encodeURIComponent(it.key) + '.jpg?v=' + Date.now() + '" alt="">' : artThumb(it.key)) +
            (n ? '<span class="sp-badge">' + n + ' word' + (n === 1 ? '' : 's') + '</span>' : '') + (it.auto ? '<span class="sp-auto">AUTO</span>' : '') +
            (hasPhoto(it.key) ? '<span class="sp-auto sp-ph">PHOTO</span>' : '') + '</button>' +
            '<b class="pg-name">' + esc(it.name) + '</b><button type="button" class="btn quiet pg-copy" data-act="sp-copy" data-code="' + esc(it.code) + '">Quick copy</button></div>';
        }).join('') + '</div></details>';
    }).join('');
  }
  function rulesList() {
    var rows = SP.words.map(function (w, i) {
      return '<div class="sr-row" data-sr="' + i + '" data-find="' + esc((w.word + ' ' + spItem(w.look).name).toLowerCase()) + '">' +
        '<button type="button" class="sr-thumb" data-act="pg-open" data-key="' + esc(w.look) + '" aria-label="Open ' + esc(spItem(w.look).name) + '">' + mini(w.look) + '</button>' +
        '<b class="sr-word">“' + esc(w.word) + '”</b>' +
        '<select data-srlook="' + i + '" aria-label="Picture for ' + esc(w.word) + '">' + lookOptions(w.look) + '</select>' +
        '<span class="seg sr-mode">' + [[false, 'By itself'], [true, 'Only with ⭐']].map(function (m) {
          return '<button type="button" data-act="sr-mode" data-i="' + i + '" data-po="' + m[0] + '" class="' + (!!w.picture_only === m[0] ? 'on special' : '') + '">' + m[1] + '</button>';
        }).join('') + '</span>' +
        '<span class="sr-move"><button type="button" class="btn quiet" data-act="sr-move" data-i="' + i + '" data-d="-1" aria-label="Move up"' + (i ? '' : ' disabled') + '>▲</button>' +
        '<button type="button" class="btn quiet" data-act="sr-move" data-i="' + i + '" data-d="1" aria-label="Move down"' + (i < SP.words.length - 1 ? '' : ' disabled') + '>▼</button></span>' +
        '<button type="button" class="sr-del" data-act="sr-del" data-i="' + i + '" aria-label="Remove ' + esc(w.word) + '">×</button></div>';
    }).join('');
    return '<div class="sr-tools"><input type="search" id="sr-find" placeholder="Find a word or picture…">' +
      '<input type="text" id="sr-new" placeholder="New word, like “Hayride”" maxlength="40"><select id="sr-newlook">' + lookOptions('') + '</select>' +
      '<button type="button" class="btn primary" data-act="sr-add">+ Add a rule</button></div>' +
      '<div class="sr-headrow"><span></span><span>TITLE HAS</span><span>PICTURE</span><span>TURNS THE DAY SPECIAL</span><span></span><span></span></div>' +
      '<div class="sr-list">' + rows + '</div><p class="help">First match wins, top to bottom: use ▲ ▼ to put specific words (Beach Fun Park) above general ones (Beach). Tap a thumbnail for that picture’s pop-up.</p>';
  }
  function spWire() {
    $$('details.pg').forEach(function (d) { d.ontoggle = function () { SP_OPEN[d.getAttribute('data-grp')] = d.open; }; });
    $$('[data-spt]').forEach(function (inp) {
      inp.onchange = function () {
        var k = inp.getAttribute('data-spt'), body = {};
        body[k] = inp.type === 'checkbox' ? inp.checked : +inp.value;
        spSave(body);
      };
    });
    $$('[data-srlook]').forEach(function (sel) {
      sel.onchange = function () { var w = SP.words.slice(); w[+sel.getAttribute('data-srlook')] = Object.assign({}, w[+sel.getAttribute('data-srlook')], { look: sel.value }); wordsSave(w); };
    });
    var f = $('#sr-find');
    if (f) f.oninput = function () {
      var q = f.value.trim().toLowerCase();
      $$('[data-sr]').forEach(function (r) { r.style.display = !q || r.getAttribute('data-find').indexOf(q) >= 0 ? '' : 'none'; });
    };
  }

  // ---------- pop-ups ----------
  function closeModal() { if (MODAL) { document.removeEventListener('keydown', MODAL.onKey); MODAL.box.remove(); MODAL = null; } }
  function openModal(build, onAct, wide) {
    closeModal();
    var box = document.createElement('div');
    box.className = 'pg-pop';
    var m = { box: box, paint: function () { box.innerHTML = '<div class="pg-card sx-card' + (wide ? ' sx-wide' : '') + '" role="dialog" aria-modal="true">' + build() + '</div>'; } };
    m.onKey = function (e) { if (e.key === 'Escape') closeModal(); };
    box.addEventListener('click', function (e) {
      if (e.target === box) return closeModal();
      var t = e.target.closest('button[data-sx]');
      if (!t) return;
      if (t.getAttribute('data-sx') === 'close') return closeModal();
      onAct(t.getAttribute('data-sx'), t);
    });
    box.addEventListener('change', function (e) {
      var t = e.target.closest('input[data-sx], select[data-sx]');
      if (t) onAct(t.getAttribute('data-sx'), t);
    });
    document.addEventListener('keydown', m.onKey);
    MODAL = m;
    m.paint();
    document.body.appendChild(box);
  }
  function copyCode(c) {
    copyText(c).then(function () { toast('Copied “' + c + '”. Paste it into the event’s description.'); })
      .catch(function () { window.prompt('Copy this line into the event’s description:', c); });
  }
  // A picture: what it is, the title words that pick it, its code, and a real photo to use instead.
  function pictureInfo(key) {
    openModal(function () {
      var it = spItem(key), ws = wordsFor(key);
      return '<div class="pg-art">' + (hasPhoto(key) ? '<img src="special/' + encodeURIComponent(key) + '.jpg?v=' + Date.now() + '" alt="" class="sx-photo">' : artThumb(key, true)) + '</div>' +
        '<div class="pg-text"><h3>' + esc(it.name) + '</h3>' + (it.about ? '<p>' + esc(it.about) + '</p>' : '') +
        '<div class="pg-code"><code>' + esc(it.code) + '</code><button type="button" class="btn primary" data-sx="copy" data-code="' + esc(it.code) + '">Copy the code</button></div>' +
        '<div class="sx-label">When it comes up</div>' + (it.auto ? '<p class="sx-auto">' + esc(it.auto) + '</p>' : '') +
        '<p>An event whose <b>title</b> has:</p><div class="sx-chips">' + (ws.length ? ws.map(function (x) {
          return '<span class="sx-chip' + (x.w.picture_only ? ' star' : '') + '">' + esc(x.w.word) +
            '<button type="button" data-sx="mode" data-i="' + x.i + '" title="Change">' + (x.w.picture_only ? 'only with ⭐' : 'by itself') + '</button>' +
            '<button type="button" class="sx-x" data-sx="del" data-i="' + x.i + '" aria-label="Remove ' + esc(x.w.word) + '">×</button></span>';
        }).join('') : '<i class="help">No words yet.</i>') + '</div>' +
        '<div class="sx-add"><input type="text" id="sx-word" maxlength="40" placeholder="Add a word, like “Hayride”"><select id="sx-po"><option value="">By itself</option><option value="1">Only with ⭐</option></select>' +
        '<button type="button" class="btn line" data-sx="add">Add</button></div>' +
        '<p class="help"><b>By itself</b>: any event with the word turns special. <b>Only with ⭐</b>: the word just picks this picture for an event you star (good for weekly games). ' +
        'Or put <b>' + esc(it.code) + '</b> in one event’s description; <b>photo: none</b> keeps one event plain.</p>' +
        '<div class="sx-label">Use a real photo instead</div>' +
        (hasPhoto(key) ? '<p>Your photo shows wherever this picture would.</p><div class="actions"><label class="btn line">Replace the photo<input type="file" accept="image/*" hidden data-sx="photo"></label>' +
            '<button type="button" class="btn quiet" data-sx="photo-del">Back to the drawing</button></div>'
          : '<div class="actions"><label class="btn line">Choose a photo<input type="file" accept="image/*" hidden data-sx="photo"></label></div>' +
            '<p class="help">It shows everywhere this picture would. For one event only, add a photo under <b>Your photos</b> with its own name and use that code.</p>') +
        '<div class="actions"><button type="button" class="btn quiet" data-sx="close">Close</button></div></div>';
    }, function (a, t) {
      var i = +t.getAttribute('data-i'), w = SP.words.slice();
      if (a === 'copy') copyCode(t.getAttribute('data-code'));
      else if (a === 'mode') { w[i] = Object.assign({}, w[i], { picture_only: !w[i].picture_only }); wordsSave(w); }
      else if (a === 'del') { var gone = w[i].word; w.splice(i, 1); wordsSave(w, 'Removed “' + gone + '”'); }
      else if (a === 'add') {
        var word = $('#sx-word').value.trim();
        if (!word) { toast('Type a word first.', true); return; }
        if (SP.words.some(function (x) { return x.word.toLowerCase() === word.toLowerCase(); })) { toast('“' + word + '” is already a rule (Rules list shows which picture).', true); return; }
        w.splice(insertAt(), 0, { word: word, look: key, picture_only: !!$('#sx-po').value });
        wordsSave(w, 'Added “' + word + '”');
      } else if (a === 'photo') {
        if (!t.files[0]) return;
        var fd = new FormData(); fd.append('file', t.files[0]); fd.append('name', key);
        toast('Saving…', false, true);
        api('POST', 'api/admin/special/pictures', fd, true).then(function () { spRefresh('Your photo now shows instead of the drawing.'); }).catch(function (e) { toast(e.message, true); });
      } else if (a === 'photo-del') {
        if (!confirm('Take your photo off and go back to the drawing? The photo is removed from the frame.')) return;
        api('DELETE', 'api/admin/special/pictures/' + encodeURIComponent(key)).then(function () { spRefresh('Back to the drawing'); }).catch(function (e) { toast(e.message, true); });
      }
    });
  }
  function holidaysModal() {
    openModal(function () {
      var refOn = SP.church.some(function (c) { return c.key === 'reformation' && c.on; });
      return '<div class="pg-text"><h3>Holidays from Google</h3><p class="help"><b>Hide</b> leaves it off the frame. <b>Show</b> puts a small holiday line on the day. <b>Special</b> takes over the whole day.' + (SP.has_church ? ' Easter and Christmas are under Church year, so they show once.' : '') + '</p>' +
        '<div class="hlist">' + (SP.google.map(function (h) {
          var note = h.key === 'halloween' && refOn ? 'Reformation Day is on the same day' : h.observance ? 'observance' : '';
          return '<div class="hrow"><div class="hn"><b>' + esc(h.name) + '</b>' + (note ? '<small>' + esc(note) + '</small>' : '') + '</div><span class="hd">' + esc(shortDate(h.date)) + '</span>' +
            '<div class="seg" role="group" aria-label="' + esc(h.name) + '">' + ['hide', 'show', 'special'].map(function (m) {
              return '<button type="button" data-sx="hol" data-key="' + esc(h.key) + '" data-mode="' + m + '" class="' + (h.mode === m ? 'on ' + m : m) + '" aria-pressed="' + (h.mode === m) + '">' + m.charAt(0).toUpperCase() + m.slice(1) + '</button>';
            }).join('') + '</div></div>';
        }).join('') || '<p class="help">No holidays read yet.</p>') + '</div>' +
        '<details><summary class="help" style="cursor:pointer">Holiday calendar address</summary><div class="row">' + field('Address', '<input type="url" id="sx-url" value="' + esc(SP.holiday_url) + '">') +
        '<button type="button" class="btn line" data-sx="check">Check</button></div><p class="result ' + (SP.holiday_error ? 'bad' : 'ok') + '" id="sx-res">' +
        (SP.holiday_error ? esc(SP.holiday_error) : SP.holiday_count + ' holidays in the next 12 months.') + '</p></details>' +
        '<div class="actions"><button type="button" class="btn quiet" data-sx="close">Done</button></div></div>';
    }, function (a, t) {
      if (a === 'hol') { var m = {}; m[t.getAttribute('data-key')] = t.getAttribute('data-mode'); spSave({ holiday_modes: m }); }
      else if (a === 'check') {
        var r = $('#sx-res'), url = $('#sx-url').value.trim();
        r.className = 'result'; r.textContent = 'Checking…';
        (url !== SP.holiday_url ? api('PUT', 'api/admin/special', { holiday_url: url }) : Promise.resolve())
          .then(function () { return api('POST', 'api/admin/special/check'); })
          .then(function (x) { r.className = 'result ' + (x.ok ? 'ok' : 'bad'); r.textContent = x.message; })
          .catch(function (e) { r.className = 'result bad'; r.textContent = e.message; });
      }
    }, true);
  }
  function churchModal() {
    openModal(function () {
      return '<div class="pg-text"><h3>Church year</h3><p class="help">Doorpost works these dates out every year (Easter by the standard formula; the others count from it or are fixed). Checked days are special.</p>' +
        '<div class="hlist">' + SP.church.map(function (c) {
          return '<label class="hrow check"><input type="checkbox" data-sx="church" data-key="' + c.key + '"' + (c.on ? ' checked' : '') + '>' +
            '<span class="hn"><b>' + esc(c.name) + '</b></span><span class="hd">' + esc(shortDate(c.date)) + '</span></label>';
        }).join('') + '</div><div class="actions"><button type="button" class="btn quiet" data-sx="close">Done</button></div></div>';
    }, function (a, t) {
      if (a === 'church') { var m = {}; SP.church.forEach(function (c) { m[c.key] = c.on; }); m[t.getAttribute('data-key')] = t.checked; spSave({ church: m }); }
    }, true);
  }
  function photosModal() {
    openModal(function () {
      return '<div class="pg-text"><h3>Your photos</h3><p class="help">A real photo to use instead of a drawing. Give it a short name and put <b>photo: that-name</b> in an event’s description, ' +
        'so just that event uses it. A photo named like a built-in picture (for example <b>waterpark</b>) replaces that drawing everywhere; tapping a picture does that for you.</p>' +
        '<div class="row">' + field('Name', '<input type="text" id="sx-pname" maxlength="40" placeholder="hw-2026">') +
        field('Photo', '<input type="file" id="sx-pfile" accept="image/*">') + '<button type="button" class="btn primary" data-sx="up">Upload</button></div>' +
        (SP.pictures.length ? '<div class="pg-grid">' + SP.pictures.map(function (p) {
          return '<div class="pg-item"><span class="thumb sp-thumb"><img loading="lazy" src="special/' + encodeURIComponent(p) + '.jpg?v=' + Date.now() + '" alt=""></span>' +
            '<b class="pg-name">' + esc(p) + '</b><button type="button" class="btn quiet pg-copy" data-sx="copy" data-code="photo: ' + esc(p) + '">Copy code</button>' +
            '<button type="button" class="btn quiet pg-copy" data-sx="rm" data-name="' + esc(p) + '">Remove</button></div>';
        }).join('') + '</div>' : '<p class="help">None yet.</p>') +
        '<div class="actions"><button type="button" class="btn quiet" data-sx="close">Done</button></div></div>';
    }, function (a, t) {
      if (a === 'copy') copyCode(t.getAttribute('data-code'));
      else if (a === 'up') {
        var f = $('#sx-pfile').files[0], name = $('#sx-pname').value.trim();
        if (!f) { toast('Choose a photo first.', true); return; }
        var fd = new FormData(); fd.append('file', f); fd.append('name', name || f.name.replace(/\.[^.]+$/, ''));
        api('POST', 'api/admin/special/pictures', fd, true).then(function (r) { spRefresh('Saved as “' + r.name + '”. Its code: photo: ' + r.name); }).catch(function (e) { toast(e.message, true); });
      } else if (a === 'rm') {
        var n = t.getAttribute('data-name');
        if (!confirm('Remove the photo “' + n + '”? Events that use it go back to the drawing or the gold pattern.')) return;
        api('DELETE', 'api/admin/special/pictures/' + encodeURIComponent(n)).then(function () { spRefresh('Removed'); }).catch(function (e) { toast(e.message, true); });
      }
    }, true);
  }

  // ---------------- birthday portraits (Settings > Special days) ----------------
  // A recent photo of each person for their birthday picture: Apple Photos (the Mac's sync finds the newest photo
  // where only that person's face is in it), Google Photos (pick a few; the frame keeps the newest single-face one),
  // or an upload. Kids without one use their face photo from Settings > Kids.
  var SOURCE_LABEL = { apple: 'From Apple Photos', google: 'From Google Photos', upload: 'Chosen here', 'kid photo': 'Older face photo' };
  // ---------------- the Google sign-in (shared by Photos, Family and Lists) ----------------
  // One "Connect Google" covers the Photos Picker and Google Tasks. A sign-in made before one of them existed gets an
  // "Allow ..." button, which asks Google for just that part on top of the rest.
  var G_NAMES = { photos: 'Google Photos', tasks: 'Google Tasks' };
  function googleSetup(g, need, title, intro) {
    var head = '<h3 class="aside" style="font-size:18px;margin-top:10px">' + (title || 'Google account') + '</h3>' + (intro ? '<p class="help">' + intro + '</p>' : '');
    if (!g) return '';
    if (g.demo) head += '<p class="warn">Demo mode: the Google parts of Settings use sample data. Nothing connects to Google, so the steps below are just to look at.</p>';
    var has = g.granted || [];
    if (g.connected) {
      var missing = need && has.indexOf(need) < 0;
      return '<div class="gsetup">' + head + '<p class="result ok">Google is connected' + (has.length ? ' for ' + has.map(function (f) { return G_NAMES[f]; }).join(' and ') : '') + '.</p>' +
        (missing ? '<p class="help">This sign-in doesn’t include ' + G_NAMES[need] + ' yet. Turn on the ' + (need === 'tasks' ? 'Google Tasks API' : 'Photos Picker API') +
          ' in your Google Cloud project, then press the button.</p>' : '') +
        '<div class="actions">' + (missing ? '<button class="btn primary" data-act="g-connect" data-features="' + need + '">Allow ' + G_NAMES[need] + '</button>' : '') +
        '<button class="btn quiet" data-act="g-disconnect">Disconnect Google</button></div></div>';
    }
    return '<div class="gsetup">' + head + '<details' + (g.client_id ? ' open' : '') + '><summary class="help" style="cursor:pointer"><b>Set up once</b> (about 10 minutes in Google Cloud; one setup covers Google Photos and Google Tasks)</summary><ol class="help">' +
        '<li>At console.cloud.google.com, make a project and turn on the <b>Photos Picker API</b> and the <b>Google Tasks API</b> (only the ones you’ll use).</li>' +
        '<li>Under <b>Google Auth Platform</b>, set it up as <b>External</b>, add the scopes <b>photospicker.mediaitems.readonly</b> and <b>tasks</b>, and add your Google account as a test user (or publish it).</li>' +
        '<li>Make an <b>OAuth client</b> of type <b>Web application</b> with this redirect address: <b>' + esc(g.redirect_uri || '(set the frame’s https address in Overview first)') + '</b></li>' +
        '<li>Paste its client ID and secret here, save, then press <b>Connect Google</b>.</li></ol></details>' +
        '<div class="row">' + field('Client ID', '<input type="text" id="g-id" value="' + esc(g.client_id) + '" placeholder="….apps.googleusercontent.com">') +
        field('Client secret', '<input type="password" id="g-secret" placeholder="' + (g.has_secret ? 'Saved (type to replace)' : '') + '">') + '</div>' +
        '<div class="actions"><button class="btn line" data-act="g-save">Save</button>' +
        (g.client_id && g.has_secret ? '<button class="btn primary" data-act="g-connect" data-features="photos,tasks">Connect Google</button>' : '') + '</div></div>';
  }
  // A row of cards, one per choice (Apple / Google / none), each saying what it needs and how it's doing.
  function choices(rows) {
    return '<div class="provs">' + rows.map(function (r) {
      return '<div class="prov"><b>' + r[0] + '</b><span>' + r[1] + '</span><span class="need"><b>Needs:</b> ' + r[2] + '</span>' +
        (r[3] ? '<span class="pst' + (r[4] ? ' ' + r[4] : '') + '">' + r[3] + '</span>' : '') + '</div>';
    }).join('') + '</div>';
  }
  function ageOn(b) {
    if (!b) return '';
    var p = b.split('-'), now = new Date(), age = now.getFullYear() - +p[0];
    if (now.getMonth() + 1 < +p[1] || (now.getMonth() + 1 === +p[1] && now.getDate() < +p[2])) age--;
    return age >= 0 ? age + (age === 1 ? ' year old' : ' years old') : '';
  }
  // ---------------- Settings > Family ----------------
  // Everyone in one list: name and nicknames (who an event is about), birthday (the birthday card comes up by itself),
  // one photo (Apple Photos cover, Google Photos pick or upload: the chore avatar and the birthday card), and for kids
  // the initial, color and screen-time name.
  function family() {
    var g = FAM.google;
    var rows = FAM.members.map(function (m, i) {
      var when = m.taken ? ' · taken ' + new Date(m.taken).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '';
      var own = m.source && m.source !== 'kid photo';
      var k = m.kid;
      var showInitial = m.use_initial || !m.photo || !modOn('portraits');
      var photo = !showInitial ? '<img class="fam-img" src="' + esc(m.photo) + '" alt="">'
        : '<span class="fam-img fam-initial"' + (k ? ' style="background:' + esc(k.color) + '"' : '') + '>' + esc((k && k.initial) || (m.name || '?')[0]) + '</span>';
      var photoActs = !modOn('portraits') ? '<span class="help">Profile photos are off in Modules. Saved photos are kept.</span>' : m.key ?
          '<label class="btn line">Choose from Photos<input type="file" accept="image/*" hidden data-ptup="' + esc(m.key) + '"></label>' +
          '<button type="button" class="btn line" data-act="' + (g.connected ? 'pt-google' : 'g-setup') + '" data-slug="' + esc(m.key) + '">Pick from Google Photos</button>' +
          '<label class="btn quiet">Upload a file<input type="file" accept=".jpg,.jpeg,.png,.heic,.webp" hidden data-ptup="' + esc(m.key) + '"></label>' +
          (own ? '<button type="button" class="btn quiet" data-act="pt-del" data-slug="' + esc(m.key) + '" data-name="' + esc(m.name) + '">Remove photo</button>' : '')
        : '<span class="help">Save first, then add a photo.</span>';
      var srcLine = m.use_initial ? 'Showing the initial' + (m.photo ? ' (photo kept)' : '') : m.source ? esc(SOURCE_LABEL[m.source] || m.source) + esc(when) : 'No photo yet';
      return '<section class="fam" data-mem="' + i + '">' +
        '<div class="fam-photo">' + photo + '<small>' + srcLine + '</small><div class="pt-acts">' + photoActs + '</div>' +
        '<label class="check fam-useinit"><input type="checkbox" data-k="use_initial"' + (m.use_initial ? ' checked' : '') + '> Use the initial instead</label></div>' +
        '<div class="fam-main"><div class="row">' + field('Name', input('name', m.name, 'text', ' maxlength="30"')) +
          field('Also called', input('aliases', (m.aliases || []).join(', '), 'text', ' placeholder="Nicknames, comma between"')) +
          field('Birthday', input('birthday', m.birthday, 'date') + (m.birthday ? '<small class="help">' + esc(ageOn(m.birthday)) + '</small>' : '')) + '</div>' +
        '<label class="check"><input type="checkbox" data-k="is_kid"' + (k ? ' checked' : '') + ' data-act-change="fam-kid"> Kid: chores, screen time and a color on the frame</label>' +
        (k ? '<div class="row">' + field('Initial', input('initial', k.initial, 'text', ' maxlength="2" style="width:70px"')) + field('Color', input('color', k.color, 'color')) +
          field('Name in screen time', input('screen_time_nickname', k.screen_time_nickname, 'text', ' placeholder="' + esc(m.name || '') + '"')) + '</div>' : '') +
        '<div class="actions"><button class="btn danger" data-act="fam-del" data-i="' + i + '">Remove from the family</button></div></div></section>';
    }).join('');
    return card('family', 'Family',
      'Everyone on the frame. <b>Also called</b> lets the calendar tell who an event is about (“Child 3” or “Buddy”). A <b>birthday</b> brings up the birthday card with their photo by itself; no calendar event needed. ' +
      'The <b>photo</b> shows in a circle on their birthday card and, for kids, everywhere their initial would show. ' +
      '<b>Choose from Photos</b> opens your photo library (on a Mac, pick Photos in the window’s sidebar); <b>Pick from Google Photos</b> works once it’s connected at the bottom of this page; ' +
      '<b>Upload a file</b> takes any picture file. The frame centers the circle on the face. <b>Use the initial instead</b> keeps the photo saved but shows the initial.',
      '<div class="fam-list">' + rows + '</div><div class="actions"><button class="btn quiet" data-act="fam-add">+ Add a person</button><button class="btn primary" data-save="family">Save family</button></div>' +
      googleSetup(g, 'photos', 'Photos from Google Photos (optional)', 'For photos kept in Google Photos instead of Apple Photos. Google doesn’t let apps see who’s in a photo, so you pick: ' +
        'press <b>Pick from Google Photos</b> under someone’s photo, choose a few recent photos of them, and tap <b>Done</b>. ' +
        'The frame keeps the newest one that has a single face in it and centers the picture on that face.'));
  }
  function famStash() {
    if (!FAM) return;
    $$('[data-mem]').forEach(function (el) {
      var m = FAM.members[+el.getAttribute('data-mem')], v = vals(el);
      m.name = v.name; m.aliases = v.aliases.split(',').map(function (a) { return a.trim(); }).filter(Boolean);
      m.birthday = v.birthday; m.use_initial = !!v.use_initial;
      if (m.kid && v.is_kid) { m.kid.initial = v.initial; m.kid.color = v.color; m.kid.screen_time_nickname = v.screen_time_nickname; }
    });
  }
  function collectFamily() {
    famStash();
    return { members: FAM.members.map(function (m) {
      return { key: m.key, name: m.name, aliases: m.aliases, birthday: m.birthday, photos_name: m.photos_name, use_initial: !!m.use_initial, kid: m.kid };
    }) };
  }

  // ---------------- focal points (Settings > Photos) ----------------
  // One point per photo; the Pi crops wide and tall frames around it. Either crop can also be moved on
  // its own, or set to show the whole photo. Apple Photos' faces are the starting point.
  var SHAPE_RATIO = { wide: 1280 / 800, tall: 800 / 1280 };
  function cropRect(w, h, shape, cx, cy) {
    var F = SHAPE_RATIO[shape], cw = 1, ch = 1;
    if (w / h > F) cw = F / (w / h); else ch = (w / h) / F;
    return [Math.min(Math.max(cx - cw / 2, 0), 1 - cw), Math.min(Math.max(cy - ch / 2, 0), 1 - ch), cw, ch];
  }
  function fCenter(d, shape) { return d[shape] || d.point || d.faces || [0.5, 0.4]; }
  function needsFit(p, shape) { return Math.abs((p.w || 3) / (p.h || 2) - SHAPE_RATIO[shape]) > 0.02; }
  function photoFilter(list) {
    if (PHOTO_FILTER === 'needs') return list.filter(function (p) { return !(p.focus && (p.focus.point || p.focus.faces)); });
    if (PHOTO_FILTER === 'tall') return list.filter(function (p) { return p.h > p.w; });
    return list;
  }
  function focusBadge(p) {
    var f = p.focus || {};
    return f.point ? '<small class="fbadge">' + I('crosshair', 12, 2.4) + 'Focal point</small>'
      : f.faces ? '<small class="fbadge">' + I('crosshair', 12, 2.4) + 'Faces</small>'
      : '<small class="fbadge center">Center</small>';
  }
  function fxOverlay(p) {
    var d = FD, w = p.w || 3, h = p.h || 2, H = Math.round(1000 * h / w), out = '';
    function rect(shape, color, solid) {
      if (d[shape + '_fit'] && needsFit(p, shape)) return '';
      var c = fCenter(d, shape), r = cropRect(w, h, shape, c[0], c[1]);
      return '<rect x="' + (r[0] * 1000 + 2) + '" y="' + (r[1] * H + 2) + '" width="' + (r[2] * 1000 - 4) + '" height="' + (r[3] * H - 4) +
        '" fill="none" stroke="' + color + '" stroke-width="' + (solid ? 5 : 4) + '"' + (solid ? '' : ' stroke-dasharray="14 9"') + '></rect>';
    }
    if (FOCUS_MODE === 'point') out = rect('wide', '#C9A55A') + rect('tall', '#FFFFFF');
    else {
      var c = fCenter(d, FOCUS_MODE), r = cropRect(w, h, FOCUS_MODE, c[0], c[1]);
      if (!(d[FOCUS_MODE + '_fit'] && needsFit(p, FOCUS_MODE))) {
        out = '<path fill="rgba(14,22,34,0.55)" fill-rule="evenodd" d="M0 0H1000V' + H + 'H0Z M' + r[0] * 1000 + ' ' + r[1] * H + 'h' + r[2] * 1000 + 'v' + r[3] * H + 'h' + (-r[2] * 1000) + 'Z"></path>' +
          rect(FOCUS_MODE, FOCUS_MODE === 'wide' ? '#C9A55A' : '#FFFFFF', true);
      }
    }
    var pt = FOCUS_MODE === 'point' ? fCenter(d, 'point') : fCenter(d, FOCUS_MODE), x = pt[0] * 1000, y = pt[1] * H;
    return out + '<circle cx="' + x + '" cy="' + y + '" r="26" fill="rgba(22,50,79,0.3)" stroke="#FFFFFF" stroke-width="5"></circle>' +
      '<circle cx="' + x + '" cy="' + y + '" r="7" fill="#FFFFFF"></circle>' +
      '<path d="M' + (x - 44) + ' ' + y + 'h14M' + (x + 30) + ' ' + y + 'h14M' + x + ' ' + (y - 44) + 'v14M' + x + ' ' + (y + 30) + 'v14" stroke="#FFFFFF" stroke-width="5"></path>';
  }
  function previewHTML(p, shape, W, H) {
    var src = 'photos/' + p.id + '.jpg?size=edit', d = FD;
    if (d[shape + '_fit'] && needsFit(p, shape)) {
      return '<div class="fx-prev" style="width:' + W + 'px;height:' + H + 'px"><div class="fx-blur" style="background-image:url(\'' + src + '\')"></div>' +
        '<div class="fx-fit" style="background-image:url(\'' + src + '\')"></div></div>';
    }
    var c = fCenter(d, shape), r = cropRect(p.w || 3, p.h || 2, shape, c[0], c[1]);
    return '<div class="fx-prev" style="width:' + W + 'px;height:' + H + 'px;background-image:url(\'' + src + '\');background-size:' +
      (W / r[2]).toFixed(1) + 'px ' + (H / r[3]).toFixed(1) + 'px;background-position:' + (-r[0] * W / r[2]).toFixed(1) + 'px ' + (-r[1] * H / r[3]).toFixed(1) + 'px"></div>';
  }
  function fxSource() {
    return FD.point ? 'Focal point set by you' : FD.faces ? 'Following the faces Apple Photos found' : 'Centered (nothing set yet)';
  }
  function focusEditor() {
    var all = PHOTOS.photos, list = photoFilter(all), p = all.filter(function (x) { return x.id === FOCUS_ID; })[0];
    if (!p) { FOCUS_ID = null; return photos(); }
    var i = list.indexOf(p), w = p.w || 3, h = p.h || 2;
    var modes = [['point', 'Focal point'], ['wide', 'Wide crop'], ['tall', 'Tall crop']].map(function (m) {
      return '<button class="' + (FOCUS_MODE === m[0] ? 'on' : '') + '" data-act="fx-mode" data-mode="' + m[0] + '">' + m[1] + '</button>';
    }).join('');
    var help = FOCUS_MODE === 'point'
      ? 'Tap or drag on the photo to mark what matters most. <b style="color:#8C7A4E">Gold</b>: what a wide frame shows. <b>White</b>: what a tall frame shows.'
      : 'Drag to move just the ' + FOCUS_MODE + ' crop. The rest of the photo is dimmed.';
    var shapeOpts = FOCUS_MODE === 'point' ? '' : '<div class="actions">' +
      '<label class="check"><input type="checkbox" id="fx-fit"' + (FD[FOCUS_MODE + '_fit'] ? ' checked' : '') + '> Show the whole photo on ' + FOCUS_MODE +
      ' frames (no crop, soft blurred edges)</label>' +
      (FD[FOCUS_MODE] ? '<button class="btn quiet" data-act="fx-follow">Follow the focal point again</button>' : '') + '</div>';
    return card('photos', 'Set the focal point',
      '<a href="#" data-act="fx-close">‹ All photos</a> · ' + esc(p.name.split('/').pop()) + (list.length > 1 && i >= 0 ? ' · ' + (i + 1) + ' of ' + list.length : ''),
      '<div class="fx-modes" role="group" aria-label="What to adjust">' + modes + '</div>' +
      '<p class="help">' + help + '</p>' +
      '<div class="fx-row"><div class="fx-stage" id="fx-stage" style="aspect-ratio:' + w + ' / ' + h + '">' +
      '<img src="photos/' + p.id + '.jpg?size=edit" alt="" draggable="false">' +
      '<svg id="fx-svg" viewBox="0 0 1000 ' + Math.round(1000 * h / w) + '" preserveAspectRatio="none">' + fxOverlay(p) + '</svg></div>' +
      '<div class="fx-side"><div class="kick">Wide frame</div><div id="fx-pw">' + previewHTML(p, 'wide', 256, 160) + '</div>' +
      '<div class="kick">Tall frame</div><div id="fx-pt">' + previewHTML(p, 'tall', 110, 176) + '</div>' +
      '<p class="help" id="fx-src">' + fxSource() + (FX_DIRTY ? ' · not saved yet' : '') + '</p></div></div>' + shapeOpts +
      '<div class="actions"><button class="btn primary" data-act="fx-save">Save</button>' +
      (FD.faces ? '<button class="btn line" data-act="fx-faces">Use the faces Apple Photos found</button>' : '') +
      '<button class="btn quiet" data-act="fx-center">Center</button>' +
      '<span style="margin-left:auto;display:flex;gap:8px"><button class="btn quiet" data-act="fx-step" data-dir="-1"' + (i > 0 ? '' : ' disabled') + '>‹ Previous</button>' +
      '<button class="btn quiet" data-act="fx-step" data-dir="1"' + (i >= 0 && i < list.length - 1 ? '' : ' disabled') + '>Next ›</button></span></div>');
  }
  function fxRedraw() {
    var p = PHOTOS.photos.filter(function (x) { return x.id === FOCUS_ID; })[0];
    $('#fx-svg').innerHTML = fxOverlay(p);
    $('#fx-pw').innerHTML = previewHTML(p, 'wide', 256, 160);
    $('#fx-pt').innerHTML = previewHTML(p, 'tall', 110, 176);
    $('#fx-src').textContent = fxSource() + (FX_DIRTY ? ' · not saved yet' : '');
  }
  function fxOpen(id) {
    var p = PHOTOS.photos.filter(function (x) { return x.id === id; })[0];
    var f = p.focus || {};
    FOCUS_ID = id; FX_DIRTY = false;
    FD = { point: f.point || null, faces: f.faces || null, wide: f.wide || null, tall: f.tall || null, wide_fit: !!f.wide_fit, tall_fit: !!f.tall_fit };
    render(); window.scrollTo(0, 0);
  }
  function fxSave() {
    var p = PHOTOS.photos.filter(function (x) { return x.id === FOCUS_ID; })[0];
    return api('PUT', 'api/admin/photos/' + FOCUS_ID + '/focus', { point: FD.point, wide: FD.wide, tall: FD.tall, wide_fit: FD.wide_fit, tall_fit: FD.tall_fit })
      .then(function (r) { p.focus = r.focus; p.v = r.v; FX_DIRTY = false; toast('Saved. The frames pick it up within a minute.'); });
  }
  function wireFocus() {
    var stage = $('#fx-stage');
    if (!stage) return;
    var down = false;
    function at(e) {
      var r = stage.getBoundingClientRect();
      var pt = [Math.min(Math.max((e.clientX - r.left) / r.width, 0), 1), Math.min(Math.max((e.clientY - r.top) / r.height, 0), 1)];
      pt = [Math.round(pt[0] * 1000) / 1000, Math.round(pt[1] * 1000) / 1000];
      FD[FOCUS_MODE] = pt; FX_DIRTY = true; fxRedraw();
    }
    stage.onpointerdown = function (e) { down = true; stage.setPointerCapture(e.pointerId); at(e); e.preventDefault(); };
    stage.onpointermove = function (e) { if (down) at(e); };
    stage.onpointerup = stage.onpointercancel = function () { down = false; };
    var fit = $('#fx-fit');
    if (fit) fit.onchange = function () { FD[FOCUS_MODE + '_fit'] = fit.checked; FX_DIRTY = true; render(); };
  }

  function photos() {
    if (FOCUS_ID) return focusEditor();
    var srcStatus = {};
    (S.photos.status || []).forEach(function (s) { srcStatus[s.id] = s; });
    var albums = S.photos.sources.map(function (s, i) {
      var st = srcStatus[s.id];
      return '<div class="item" data-src="' + i + '"><div class="row">' +
        field('Album type', '<select data-k="kind"><option value="google_album"' + (s.kind === 'google_album' ? ' selected' : '') + '>Google Photos shared album link</option>' +
          '<option value="icloud_album"' + (s.kind === 'icloud_album' ? ' selected' : '') + '>iCloud shared album (Public Website)</option></select>') +
        field('Name', input('label', s.label, 'text', ' placeholder="Family favorites"')) + '</div>' +
        '<div class="row">' + field('Share link', input('url', s.url, 'url', ' placeholder="https://photos.app.goo.gl/… or https://www.icloud.com/sharedalbum/#…"')) + '</div>' +
        '<div class="actions"><label class="check"><input type="checkbox" data-k="enabled"' + (s.enabled !== false ? ' checked' : '') + '> Use this album</label>' +
        '<button class="btn line" data-act="test-src" data-i="' + i + '">Check</button><button class="btn danger" data-act="del-src" data-i="' + i + '">Remove</button>' +
        '<span class="result' + (st && st.error ? ' bad' : ' ok') + '" data-res>' + (st ? (st.error ? esc(st.error) : st.count + ' photos') : '') + '</span></div></div>';
    }).join('');
    // Only a few at a time: the Pi makes each thumbnail the first time it's asked.
    var shown = photoFilter(PHOTOS.photos);
    var thumbs = shown.slice(0, PHOTO_SHOWN).map(function (p) {
      return '<div class="thumb fthumb" role="button" tabindex="0" data-act="focus-open" data-id="' + p.id + '" aria-label="Set the focal point for ' + esc(p.name) + '">' +
        '<img loading="lazy" src="photos/' + p.id + '.jpg?size=thumb' + (p.v ? '&v=' + p.v : '') + '" alt="">' + focusBadge(p) +
        '<button data-act="del-photo" data-id="' + p.id + '" aria-label="Remove ' + esc(p.name) + '">Remove</button></div>';
    }).join('');
    var counts = { all: PHOTOS.photos.length, needs: 0, tall: 0 };
    PHOTOS.photos.forEach(function (p) { if (!(p.focus && (p.focus.point || p.focus.faces))) counts.needs++; if (p.h > p.w) counts.tall++; });
    var chips = [['all', 'All'], ['needs', 'Needs a focal point'], ['tall', 'Tall photos']].map(function (c) {
      return '<button class="chipf' + (PHOTO_FILTER === c[0] ? ' on' : '') + '" data-act="photo-filter" data-f="' + c[0] + '">' + c[1] + ' · ' + counts[c[0]] + '</button>';
    }).join('');
    var cmd = 'FRAME_URL=' + S.display.lan_url + ' FRAME_UPLOAD_TOKEN=' + S.photos.upload_token + ' \\\n  bash scripts/sync-apple-favorites.sh';
    var g = GOOG || {}, bySrc = {};
    PHOTOS.photos.forEach(function (p) { bySrc[p.source] = (bySrc[p.source] || 0) + 1; });
    var albumsOf = function (kind) { return S.photos.sources.filter(function (x) { return x.kind === kind && x.enabled !== false; }).length; };
    var nAlb = function (n) { return n + ' shared album' + (n === 1 ? '' : 's'); };
    var appleSt = [albumsOf('icloud_album') ? nAlb(albumsOf('icloud_album')) : '', bySrc['apple-favorites'] ? bySrc['apple-favorites'] + ' Favorites from the Mac' : ''].filter(Boolean).join(' · ');
    var googleSt = [albumsOf('google_album') ? nAlb(albumsOf('google_album')) : '', bySrc['google-picks'] ? bySrc['google-picks'] + ' picked photos' : '',
      g.connected ? 'Connected' : ''].filter(Boolean).join(' · ');
    var pick = choices([
      ['Apple', '<b>iCloud Shared Album</b> link (live), or your <b>Favorites</b> from Apple Photos.', 'nothing extra for a shared album. Favorites need a Mac with the Photos library, since Apple has no web service for Photos.', appleSt, appleSt ? 'ok' : 'off'],
      ['Google', '<b>Shared album</b> link (live), or photos you <b>pick</b> in Google Photos.', 'nothing extra for a shared album. Picking needs a Google sign-in (one-time setup below). No extra computer.', googleSt, googleSt ? 'ok' : 'off'],
      ['Your own', '<b>Upload</b> here, or drop files in the photos folder.', 'nothing.', PHOTOS.photos.length ? PHOTOS.photos.length + ' photos in the frame’s folder' : '', 'ok'],
      ['None', 'With no photos there’s no slideshow; the frame stays on the Today screen.', 'nothing.', PHOTOS.photos.length || S.photos.sources.length ? '' : 'In use: no photos yet', 'ok']]);
    var gpick = '<h3 class="aside" style="font-size:18px;margin-top:8px">Pick photos from Google Photos</h3>' +
      '<p class="help">Opens Google Photos in a new tab. Pick as many photos as you like and tap <b>Done</b>; the frame copies them into its folder (up to 2048 pixels wide), so they stay even after Google’s link expires. ' +
      'Picking the same photo again later doesn’t copy it twice. Since March 2025 Google lets apps see only photos you pick by hand or share by link, so this can’t follow your whole library or your Favorites.</p>' +
      '<div class="actions"><button class="btn primary" data-act="' + (g.connected || g.demo ? 'gp-pick' : 'g-setup') + '">Pick photos from Google Photos</button><span class="result" data-res-gp></span></div>' +
      googleSetup(g, 'photos');
    return card('photos', 'Photos',
      'The slideshow mixes everything below and picks a new random order each day. Use Apple, Google, your own uploads, any mix, or none (no photos means no slideshow).',
      pick +
      '<h3 class="aside" style="font-size:18px">Shared albums (live)</h3>' +
      '<p class="help"><b>Google Photos:</b> open an album, then <b>Share</b>, then <b>Create link</b>, and paste it. A <i>live album</i> (Google picks photos of chosen people automatically) works well. ' +
      'Google no longer lets apps read Favorites directly. <b>iPhone:</b> in Photos, open a Shared Album, then <b>People</b>, and turn on <b>Public Website</b>, then copy the link. ' +
      'Both read the album the way a browser does, so if Google or Apple changes their page an error shows here and the frame keeps the photos it has.</p>' +
      albums + '<div class="actions"><button class="btn quiet" data-act="add-src">+ Add an album</button><button class="btn primary" data-save="photos">Save albums</button></div>' +
      '<h3 class="aside" style="font-size:18px;margin-top:8px">Apple Photos Favorites (from the Mac)</h3>' +
      '<p class="help">Your real Favorites live only in the Photos library. A Mac with the library sends new favorites and removes un-favorited ones when the sync script runs (see docs/photos.md to schedule it). To run it by hand in Terminal, inside the doorpost folder:</p>' +
      '<div class="code">' + esc(cmd) + '</div><div class="actions"><button class="btn quiet" data-act="rotate-token">Make a new upload key</button></div>' +
      gpick +
      '<h3 class="aside" style="font-size:18px;margin-top:8px">Upload photos</h3>' +
      '<label class="drop" id="drop">Drop photos here, or <u>choose files</u><input id="files" type="file" accept="image/*" multiple hidden></label>' +
      (PHOTOS.photos.length ? '<p class="help">' + PHOTOS.photos.length + ' photos in the frame’s folder, newest first. <b>Tap a photo to set its focal point</b>: ' +
        'what the frames keep in view, wide or tall. <b>Faces</b> means it follows the faces Apple Photos found; <b>Center</b> means nothing is set.</p>' +
        '<div class="actions">' + chips + '</div>' +
        (thumbs ? '<div class="grid">' + thumbs + '</div>' : '<p class="help">None here.</p>') +
        (shown.length > PHOTO_SHOWN ? '<div class="actions"><button class="btn quiet" data-act="photos-more">Show ' +
          Math.min(24, shown.length - PHOTO_SHOWN) + ' more</button></div>' : '')
        : '<p class="help">No photos in the frame’s own folder yet.</p>'));
  }

  var PRESETS = [['all', 'Every day', DAYS], ['wk', 'Weekdays', ['mon', 'tue', 'wed', 'thu', 'fri']], ['we', 'Weekends', ['sun', 'sat']]];
  var DAY_SHORT = { sun: 'Sun', mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri', sat: 'Sat' };
  function sameDays(a, b) { return a.length === b.length && a.every(function (d) { return b.indexOf(d) >= 0; }); }
  function presetOf(days) {
    for (var i = 0; i < PRESETS.length; i++) if (sameDays(days, PRESETS[i][2])) return PRESETS[i][0];
    return 'pick';
  }
  function daysLabel(days) {
    var p = presetOf(days);
    if (p !== 'pick') return PRESETS.filter(function (x) { return x[0] === p; })[0][1];
    return days.length ? DAYS.filter(function (d) { return days.indexOf(d) >= 0; }).map(function (d) { return DAY_SHORT[d]; }).join(', ') : 'No days';
  }
  function chores() {
    if (!S.kids.length) return card('chores', 'Chores', 'Add a kid first (Family page: check “Kid” next to them).', '', '');
    if (!CHORE_KID || !S.kids.some(function (k) { return k.id === CHORE_KID; })) CHORE_KID = S.kids[0].id;
    var kid = S.kids.filter(function (k) { return k.id === CHORE_KID; })[0];
    var picker = '<div class="kidbar" role="group" aria-label="Pick a kid">' + S.kids.map(function (k) {
      var n = S.chores.filter(function (c) { return c.kid === k.id; }).length;
      return '<button type="button" data-act="chore-kid" data-kid="' + esc(k.id) + '"' + (k.id === CHORE_KID ? ' class="on" aria-pressed="true"' : ' aria-pressed="false"') + '>' +
        av(k, 's') + esc(k.name) + '<small>' + n + '</small></button>';
    }).join('') + '</div>';
    var mine = S.chores.map(function (c, i) { return { c: c, i: i }; }).filter(function (x) { return x.c.kid === CHORE_KID; });
    var rows = mine.map(function (x) {
      var c = x.c, i = x.i, open = CHORE_OPEN === i, pick = CHORE_PICK[i] || presetOf(c.days) === 'pick';
      return '<section class="fold chrow" data-chore="' + i + '">' +
        '<div class="fold-head">' +
        '<button type="button" class="ch-name" data-act="chore-fold" data-i="' + i + '">' + esc(c.title || 'New chore') + '</button>' +
        '<span class="seg mins" role="group" aria-label="Minutes">' + [5, 10, 15, 20].map(function (m) {
          return '<button type="button" data-act="chore-min" data-i="' + i + '" data-m="' + m + '"' + (+c.minutes === m ? ' class="on special" aria-pressed="true"' : ' aria-pressed="false"') + '>' + m + '</button>';
        }).join('') + '<label class="min-own" title="Any number of minutes"><input type="number" inputmode="numeric" min="1" max="240" step="1" data-chore-min="' + i +
          '" value="' + esc(c.minutes) + '" aria-label="Minutes for ' + esc(c.title || 'this chore') + '"' + ([5, 10, 15, 20].indexOf(+c.minutes) < 0 ? ' class="on"' : '') + '>min</label></span>' +
        '<button type="button" class="chip days-chip" data-act="chore-fold" data-i="' + i + '">' + esc(daysLabel(c.days)) + '</button>' +
        '<button type="button" class="chev" data-act="chore-fold" data-i="' + i + '" aria-expanded="' + open + '" aria-label="Change days">' + I('chevron-down', 20, 2) + '</button></div>' +
        (open ? '<div class="fold-body"><div class="presets">' + PRESETS.map(function (p) {
          var on = !pick && presetOf(c.days) === p[0];
          return '<button type="button" data-act="chore-preset" data-i="' + i + '" data-p="' + p[0] + '"' + (on ? ' class="on"' : '') + '>' + p[1] + '</button>';
        }).join('') + '<button type="button" data-act="chore-preset" data-i="' + i + '" data-p="pick"' + (pick ? ' class="on"' : '') + '>Pick days</button></div>' +
        (pick ? '<div class="days">' + DAYS.map(function (d, j) {
          var on = c.days.indexOf(d) >= 0;
          return '<button type="button" data-act="chore-day" data-i="' + i + '" data-day="' + d + '"' + (on ? ' class="on"' : '') + ' aria-pressed="' + on + '" aria-label="' + DAY_SHORT[d] + '">' + DAY_LETTERS[j] + '</button>';
        }).join('') + '</div>' : '') +
        '<div class="row">' + field('Chore', '<input type="text" data-chore-title="' + i + '" value="' + esc(c.title) + '" maxlength="60" placeholder="e.g. Make bed">') +
        '<button class="btn danger" data-act="del-chore" data-i="' + i + '">Remove</button></div></div>' : '') + '</section>';
    }).join('');
    var perDay = DAYS.map(function (d) { return mine.reduce(function (n, x) { return n + (x.c.days.indexOf(d) >= 0 ? +x.c.minutes : 0); }, 0); });
    var others = S.kids.filter(function (k) { return k.id !== CHORE_KID; });
    var aside = '<aside class="ch-sum"><div class="kick">' + esc(kid.name) + '’s week</div><b>' + mine.length + ' chore' + (mine.length === 1 ? '' : 's') + '</b>' +
      (mine.length ? '<p class="help">Up to <b>' + Math.max.apply(null, perDay) + ' min</b> a day to earn, at least ' + Math.min.apply(null, perDay) + ' min.</p>' : '') +
      (mine.length && others.length ? '<label class="f">Copy these chores to<select id="copy-to">' + others.map(function (k) {
        return '<option value="' + esc(k.id) + '">' + esc(k.name) + '</option>'; }).join('') + '</select></label>' +
        '<button class="btn quiet" data-act="chore-copy">Copy</button>' : '') + '</aside>';
    return card('chores', 'Chores', 'Pick a kid. One line per chore: tap 5, 10, 15 or 20 minutes, or type any amount up to 240, and tap the chore to change its days.',
      picker + '<div class="ch-wrap"><div class="ch-list">' + (rows || '<p class="help">No chores for ' + esc(kid.name) + ' yet.</p>') +
      '<div class="actions"><button class="btn quiet" data-act="add-chore" data-kid="' + esc(CHORE_KID) + '">+ Add a chore for ' + esc(kid.name) + '</button></div></div>' + aside + '</div>',
      'Save chores');
  }

  var VIEW_NAMES = [['leader', 'Leaderboard'], ['vault', 'Treasure Vault'], ['rocket', 'Rocket Launch'], ['glass', 'Hourglass']];
  var DAY_NAMES = [['sun', 'Sunday'], ['mon', 'Monday'], ['tue', 'Tuesday'], ['wed', 'Wednesday'], ['thu', 'Thursday'], ['fri', 'Friday'], ['sat', 'Saturday']];
  // ---------------- Modules ----------------
  // One card per module (app/modules.py): a switch, what it does, what it needs, and how it's doing.
  function modulesPage() {
    var cards = MODS.modules.map(function (m) {
      var sw = m.always_on ? '<span class="mod-always">Always on</span>'
        : '<label class="sp-switch" title="' + (m.chosen ? 'Turn off' : 'Turn on') + '"><input type="checkbox" data-act="mod-turn" data-id="' + esc(m.id) + '"' +
          (m.chosen ? ' checked' : '') + ' aria-label="' + esc(m.name) + '"><span></span></label>';
      var st = m.blocked_by.length ? ['amber', 'Waiting for ' + m.blocked_by.join(' and ')] : !m.on ? ['', 'Off. Your settings are kept.'] : [m.status_tone === 'warn' ? 'amber' : 'ok', m.status || 'On'];
      return '<section class="mod' + (m.on ? '' : ' off') + '" data-mod="' + esc(m.id) + '"><div class="mod-head"><span class="mod-ic">' + I(m.icon, 20, 2) + '</span>' +
        '<b>' + esc(m.name) + '</b>' + sw + '</div><p class="mod-desc">' + esc(m.description) + '</p>' +
        '<p class="mod-needs"><i>Needs</i>· ' + esc(m.needs_text) + '</p>' +
        '<div class="mod-badges">' + m.needs.filter(function (n) { return n.key !== 'nothing'; }).map(function (n) {
          return '<span class="mod-badge">' + esc(n.label) + '</span>';
        }).join('') + '</div><p class="mod-st ' + st[0] + '">' + esc(st[1]) + '</p></section>';
    }).join('');
    return '<section class="card" id="modules"><div class="mods-head"><h2>Modules</h2><span>' + MODS.count + ' of ' + MODS.total + ' on</span></div>' +
      '<p class="help">Turn on only what your family uses. A module that is off disappears from every frame, the phone page and these settings. ' +
      'Turning it back on brings back everything you had set up.</p><div class="mods">' + cards + '</div></section>';
  }

  // ---------------- Frames ----------------
  function framesPage() {
    var F = FRAMES;
    var rows = F.frames.map(function (f, i) {
      var open = FRAME_OPEN === i, sv = f.seen || {}, hb = STORAGE && STORAGE.frames && STORAGE.frames[f.id];
      if (hb && (sv.ago == null || hb.ago < sv.ago)) {  // a heartbeat counts as being seen too
        sv = { online: hb.ago < 400 || sv.online, ago: hb.ago, w: sv.w || (hb.screen || {}).w, h: sv.h || (hb.screen || {}).h };
      }
      var status = sv.online ? '<span class="result ok">Online</span>' : sv.ago != null ? '<span class="result">Last seen ' + ago(sv.ago) + '</span>' : '<span class="result">Not seen yet</span>';
      var addr = (F.lan_url || '').replace(/^https?:\/\//, '') + '/frame/' + (f.id || '…');
      var lookList = f.home === 'kids' ? F.looks.filter(function (l) { return l.kids; }).concat(F.looks.filter(function (l) { return !l.kids; })) : F.looks;  // kids' looks first on a Kids frame
      var looks = lookList.map(function (l) {
        return '<label class="lookopt' + (f.look === l.key ? ' on' : '') + '"><input type="radio" name="look-' + i + '" value="' + l.key + '"' + (f.look === l.key ? ' checked' : '') +
          ' data-fk="look"><span class="swatches" aria-hidden="true">' + (l.swatches || []).map(function (c) { return '<i style="background:' + esc(c) + '"></i>'; }).join('') +
          '</span><b>' + esc(l.name) + '</b><small>' + esc(l.note) + (l.kind && l.kind !== 'both' ? ' · for ' + l.kind + ' frames' : '') + '</small></label>';
      }).join('');
      var pics = [['original', 'Original', 'As drawn'], ['match', 'Match the look', 'Recolored and framed to fit the look']].map(function (p) {
        var on = (f.pictures || 'original') === p[0];
        return '<label class="lookopt' + (on ? ' on' : '') + '"><input type="radio" name="pics-' + i + '" value="' + p[0] + '"' + (on ? ' checked' : '') +
          ' data-fk="pictures"><b>' + p[1] + '</b><small>' + p[2] + '</small></label>';
      }).join('');
      var screens = F.screens.map(function (sc) {
        return '<label class="check"><input type="checkbox" data-fscreen="' + sc.key + '"' + (f.screens.indexOf(sc.key) >= 0 ? ' checked' : '') + '> ' + esc(sc.name) + '</label>';
      }).join('');
      var cals = S.calendars.map(function (c) {
        return '<label class="check"><input type="checkbox" data-fcal="' + esc(c.key) + '"' + (f.calendars.indexOf(c.key) >= 0 ? ' checked' : '') + '> ' + esc(c.label) + '</label>';
      }).join('');
      var kidsBox = S.kids.map(function (k) {
        return '<label class="check"><input type="checkbox" data-fkid="' + esc(k.id) + '"' + (f.kids.indexOf(k.id) >= 0 ? ' checked' : '') + '> ' + esc(k.name) + '</label>';
      }).join('');
      var homeOpts = F.homes.map(function (h) {
        var nm = F.screens.filter(function (x) { return x.key === h; })[0].name;
        return '<option value="' + h + '"' + (f.home === h ? ' selected' : '') + '>' + esc(nm) + '</option>';
      }).join('');
      return '<section class="fold" data-frame="' + i + '"><div class="fold-head" data-act="frame-fold" data-i="' + i + '" role="button" tabindex="0">' +
        '<span class="hn"><b>' + esc(f.name || 'New frame') + '</b><small>' + esc(addr) + (sv.w ? ' · ' + sv.w + ' × ' + sv.h : '') + ' · ' +
        esc((F.looks.filter(function (l) { return l.key === f.look; })[0] || {}).name || '') + '</small></span>' + status + '</div>' +
        (open ? '<div class="fold-body">' +
          '<div class="row">' + field('Name', input('name', f.name, 'text', ' data-fk="name" placeholder="Kids’ playroom"')) +
          field('Home screen', '<select data-fk="home">' + homeOpts + '</select>') + '</div>' +
          (f.home === 'kids' ? '<h3 class="kick">Kids screen</h3><p class="help">Big pictures for little readers: each kid’s chores, what’s next today, ' +
            'the weekend screen time picture and a bedtime countdown for the last two hours. Event notes, addresses and taken-away minutes never reach this frame.</p>' +
            '<div class="row">' + field('Bedtime', input('bedtime', f.bedtime || '20:00', 'time', ' data-fk="bedtime"')) +
            field('Screen time picture', '<select data-fk="screen_view">' + VIEW_NAMES.map(function (v) {
              return '<option value="' + v[0] + '"' + ((f.screen_view || 'rocket') === v[0] ? ' selected' : '') + '>' + v[1] + '</option>';
            }).join('') + '</select>') + '</div>' : '') +
          '<h3 class="kick">Look</h3><div class="lookopts">' + looks + '</div>' +
          (window.LookOptions ? LookOptions.html(F.looks.filter(function (l) { return l.key === f.look; })[0], (f.look_options || {})[f.look]) : '') +  // web/js/look-options.js
          '<h3 class="kick">Pictures</h3><p class="help">Special-day, Sunday and screen time pictures. Original shows them as drawn; Match the look recolors them ' +
            'and frames them to fit this frame’s look.</p><div class="lookopts">' + pics + '</div>' +
          '<h3 class="kick">Screens on this frame</h3><div class="row">' + screens + '</div>' +
          '<h3 class="kick">Calendars</h3><p class="help">None ticked means all of them.</p><div class="row">' + cals + '</div>' +
          '<h3 class="kick">Kids on this frame</h3><p class="help">None ticked means everyone.</p><div class="row">' + kidsBox + '</div>' +
          frameDevice(f.id) +
          '<h3 class="kick">On this frame</h3>' +
          '<label class="check"><input type="checkbox" data-fk="approvals"' + (f.approvals ? ' checked' : '') + '> Parents can approve chores here (with a PIN)</label>' +
          '<label class="check"><input type="checkbox" data-fk="own_night"' + (f.night ? ' checked' : '') + '> Its own night hours</label>' +
          (f.night ? '<div class="row">' + field('Night clock starts', input('night_start', f.night.start, 'time', ' data-fk="night_start"')) +
            field('ends', input('night_end', f.night.end, 'time', ' data-fk="night_end"')) + '</div>' : '') +
          '<p class="help">Open it on the frame: <b>' + esc(addr) + '</b>, or on a new frame pick it from the list (parent PIN). The small gear in a frame’s corner switches it later.</p>' +
          '<div class="actions">' + (f.id ? '<a class="btn line" href="frame/' + esc(f.id) + '" target="_blank" rel="noopener">Preview this frame</a>' : '') +
          '<button class="btn quiet" data-act="frame-copy" data-i="' + i + '">Make a copy</button>' +
          (F.frames.length > 1 ? '<button class="btn danger" data-act="frame-del" data-i="' + i + '">Remove</button>' : '') + '</div></div>' : '') + '</section>';
    }).join('');
    return card('frames', 'Frames',
      'Every screen in the house runs the same Doorpost, each with its own look and screens. Calendars, chores, screen time and photos are shared, ' +
      'so a chore approved on one shows done on all of them.',
      rows + '<div class="actions">' + (F.multi === false ? '<span class="help">One frame. To add more, turn on <a href="' + pageHref('modules') + '">Multiple frames</a>.</span>'
        : '<button class="btn quiet" data-act="frame-add">+ Add a frame</button>') + '<button class="btn primary" data-save="frames">Save frames</button></div>');
  }
  function stashFrames() {
    $$('[data-frame]').forEach(function (el) {
      if (!$('.fold-body', el)) return;
      var f = FRAMES.frames[+el.getAttribute('data-frame')];
      $$('[data-fk]', el).forEach(function (inp) {
        var k = inp.getAttribute('data-fk');
        if (k === 'look' || k === 'pictures') { if (inp.checked) f[k] = inp.value; }
        else if (k === 'approvals') f.approvals = inp.checked;
        else if (k === 'own_night') f.night = inp.checked ? (f.night || { start: '20:00', end: '07:00' }) : null;
        else if (k === 'night_start' && f.night) f.night.start = inp.value;
        else if (k === 'night_end' && f.night) f.night.end = inp.value;
        else f[k] = inp.value;
      });
      f.screens = $$('[data-fscreen]', el).filter(function (x) { return x.checked; }).map(function (x) { return x.getAttribute('data-fscreen'); });
      f.calendars = $$('[data-fcal]', el).filter(function (x) { return x.checked; }).map(function (x) { return x.getAttribute('data-fcal'); });
      f.kids = $$('[data-fkid]', el).filter(function (x) { return x.checked; }).map(function (x) { return x.getAttribute('data-fkid'); });
      var lo = window.LookOptions && LookOptions.read(el);
      if (lo) { f.look_options = Object.assign({}, f.look_options); f.look_options[lo.look] = lo.values; }
    });
  }

  // ---------------- storage (Overview card, Frames details) ----------------
  function bytes(n) {
    if (n == null) return '?';
    if (n >= 1073741824) return (n / 1073741824).toFixed(n >= 10737418240 ? 0 : 1) + ' GB';
    if (n >= 1048576) return Math.round(n / 1048576) + ' MB';
    if (n >= 1024) return Math.round(n / 1024) + ' KB';
    return n + ' bytes';
  }
  function diskLine(d, what) {
    return '<div class="disk ' + d.level + '"><div class="disk-top"><b>' + what + '</b><span>' + bytes(d.free) + ' free of ' + bytes(d.total) +
      ' (' + d.free_pct + '%)</span></div><div class="dbar" role="img" aria-label="' + bytes(d.used) + ' used of ' + bytes(d.total) + '">' +
      '<i style="width:' + Math.min(100, Math.round(100 * d.used / d.total)) + '%"></i></div></div>';
  }
  function storageTodo() {
    var out = [], st = STORAGE;
    if (!st) return out;
    [[st.disk, 'The server'], [st.photos_disk, 'The photos disk']].forEach(function (x) {
      var d = x[0];
      if (!d || d.level === 'ok') return;
      out.push(x[1] + ' is ' + (d.level === 'red' ? 'almost full' : 'getting full') + ': ' + bytes(d.free) + ' free. See Storage below.');
    });
    Object.keys(st.frames || {}).forEach(function (id) {
      var h = st.frames[id], ds = h && h.device_storage;
      if (ds && ds.level && ds.level !== 'ok') out.push('Frame “' + id + '” is low on space: ' + bytes(ds.free) + ' free.');
    });
    return out;
  }
  function storageCard() {
    var st = STORAGE;
    if (!st) return card('storage', 'Storage', '<span class="spin" aria-hidden="true"></span> Checking…', '');
    var bd = st.breakdown, rows = '';
    if (bd) {
      rows = '<div class="sizes">' + bd.items.filter(function (it) { return it.bytes > 0 || it.key !== 'other'; }).map(function (it) {
        return '<div class="hrow"><span class="hn"><b>' + esc(it.label) + '</b><small>' + esc(it.note) + '</small></span>' +
          '<span class="sz"><b>' + bytes(it.bytes) + '</b><small>' + it.files.toLocaleString('en-US') + ' file' + (it.files === 1 ? '' : 's') + '</small></span></div>';
      }).join('') + '<div class="hrow total"><span class="hn"><b>Doorpost in all</b></span><span class="sz"><b>' + bytes(bd.total) + '</b></span></div></div>';
    }
    var cache = bd && bd.items.filter(function (it) { return it.key === 'photo_cache'; })[0];
    return card('storage', 'Storage',
      'How full the server’s disk is, and what Doorpost keeps on it. The frames themselves store almost nothing.' + (st.demo ? ' Demo mode: sample numbers.' : ''),
      (st.disk ? diskLine(st.disk, 'Server disk') : '<p class="help">Couldn’t read the server’s disk.</p>') +
      (st.photos_disk ? diskLine(st.photos_disk, 'Photos disk') : '') +
      (st.level !== 'ok' ? '<p class="warn">' + (st.level === 'red' ? 'Almost full. ' : 'Getting full. ') +
        'Free some space soon: remove photos you don’t need, clear the prepared photos, or move the photos to a bigger disk.</p>' : '') +
      '<h3 class="kick">What Doorpost uses</h3>' +
      (bd ? rows : '<p class="help"><span class="spin" aria-hidden="true"></span> Counting the folders. This can take a minute on a big photo library. Reload to see it.</p>') +
      (bd && !st.counting && bd.at && (Date.now() / 1000 - bd.at) > 360 ? '<p class="help">Counted a while ago; a fresh count is on its way.</p>' : '') +
      (cache && cache.bytes > 0 ? '<div class="actions"><button class="btn line" data-act="clear-photo-cache">Clear prepared photos (' + bytes(cache.bytes) + ')</button>' +
        '<span class="result" data-res></span></div>' : '') +
      '<p class="help">Warnings show under <b>Needs attention</b> when a disk has ' + esc(st.warn_at.amber) + ' (amber), or ' + esc(st.warn_at.red) + ' (red).</p>');
  }
  function frameDevice(id) {
    if (!STORAGE || !id) return '';
    var h = (STORAGE.frames || {})[id];
    var note = '<p class="help">A web page can’t see the frame’s own disk. This is what the frame page itself uses, and it is tiny by design: ' +
      'photos and settings stay on the server.</p>';
    if (!h) return '<h3 class="kick">This frame’s device</h3><p class="help">No report yet. A frame checks in a few minutes after it opens.</p>';
    var sc = h.screen || {}, rows = [];
    rows.push(['Last report', ago(h.ago)]);
    if (sc.w) rows.push(['Screen', sc.w + ' × ' + sc.h + ' pixels' + (sc.dpr && sc.dpr !== 1 ? ' (' + sc.dpr + 'x)' : '') + (sc.orientation ? ', ' + sc.orientation.replace('-primary', '').replace('-secondary', ' (flipped)') : '')]);
    if (h.browser) rows.push(['Browser', h.browser]);
    rows.push(['Page storage', h.storage && h.storage.quota ? bytes(h.storage.usage) + ' used of ' + bytes(h.storage.quota) + ' allowed' : 'Not reported (browsers only share this over https)']);
    var mem = [];
    if (h.device_memory_gb) mem.push('about ' + h.device_memory_gb + ' GB on the device');
    if (h.heap && h.heap.used) mem.push('page using ' + bytes(h.heap.used) + (h.heap.limit ? ' of ' + bytes(h.heap.limit) : ''));
    rows.push(['Memory', mem.length ? mem.join(', ') : 'Not reported']);
    if (h.photo_ms) rows.push(['Last photo', (h.photo_ms / 1000).toFixed(1) + ' seconds to load']);
    if (h.uptime_s) rows.push(['Page open for', ago(h.uptime_s).replace(' ago', '')]);
    if (h.device_storage && h.device_storage.total) rows.push(['Device storage', bytes(h.device_storage.free) + ' free of ' + bytes(h.device_storage.total)]);
    return '<h3 class="kick">This frame’s device</h3><dl class="kv">' + rows.map(function (r) {
      return '<dt>' + esc(r[0]) + '</dt><dd>' + esc(r[1]) + '</dd>';
    }).join('') + '</dl>' + note;
  }

  function ago(sec) {
    if (sec == null) return 'never';
    if (sec < 90) return sec + ' seconds ago';
    if (sec < 5400) return Math.round(sec / 60) + ' minutes ago';
    if (sec < 172800) return Math.round(sec / 3600) + ' hours ago';
    return Math.round(sec / 86400) + ' days ago';
  }
  function lists() {
    var L = LISTS, SRC = L.sources || { apple: {}, google: {} }, ap = SRC.apple, gs = SRC.google, g = L.google || {};
    function row(a) {
      var on = L.shown.indexOf(a.id) >= 0;
      var count = a.source === 'google' && !on && !a.count ? 'Turn on to read its tasks' : a.count + ' item' + (a.count === 1 ? '' : 's');
      return '<div class="hrow check" data-list="' + esc(a.id) + '"><input type="checkbox" data-lk="shown"' + (on ? ' checked' : '') + ' aria-label="Show ' + esc(a.name) + '">' +
        '<span class="hn"><b>' + esc(a.name) + '</b><small>' + count + '</small></span>' +
        '<span class="hd"><label class="check" style="font-size:13px"><input type="checkbox" data-lk="sections"' + (L.sections.indexOf(a.id) >= 0 ? ' checked' : '') +
        '> Store sections</label></span></div>';
    }
    function group(src, title) {
      var mine = L.available.filter(function (a) { return a.source === src; });
      return mine.length ? '<h3 class="kick">' + title + '</h3><div class="hlist">' + mine.map(row).join('') + '</div>' : '';
    }
    var rows = group('apple', 'From Apple Reminders') + group('google', 'From Google Tasks');
    var homeOpts = L.available.filter(function (a) { return L.shown.indexOf(a.id) >= 0; }).map(function (a) {
      return '<option value="' + esc(a.id) + '"' + (a.id === L.home ? ' selected' : '') + '>' + esc(a.name) + '</option>';
    }).join('');
    // How each source is doing
    var apSt = ap.synced_ago == null ? ['Not set up', 'off'] : ap.synced_ago > 600 ? ['Mac last checked in ' + ago(ap.synced_ago), 'bad'] : ['Connected · ' + ap.lists + ' lists', 'ok'];
    var gSt = !gs.on ? ['Turned off', 'off'] : gs.error ? [gs.error, 'bad'] : !gs.ready ? ['Not connected', 'off']
      : gs.synced_ago == null ? ['Connected · waiting for the first read', 'ok'] : ['Connected · ' + gs.lists + ' lists' + (g.demo ? ' (sample)' : ''), 'ok'];
    var noneSt = L.shown.length ? null : ['In use: no lists on the frame', 'ok'];
    var pick = choices([
      ['Apple Reminders', 'Lists from the Reminders app on iPhone, iPad and Mac.', 'a Mac that stays on, with the small <b>Doorpost Lists</b> helper. Apple has no web service for Reminders.', apSt[0], apSt[1]],
      ['Google Tasks', 'Lists from Google Tasks (in Gmail, Google Calendar and the Tasks app).', 'a Google sign-in (one-time setup below). No extra computer.', gSt[0], gSt[1]],
      ['None', 'Leave every list off. The Lists screen stays hidden.', 'nothing.', noneSt && noneSt[0], noneSt && noneSt[1]]]);
    var mac = ap.synced_ago != null && ap.synced_ago > 600
      ? '<div class="warn">The Mac last checked in ' + ago(ap.synced_ago) + '. Is it asleep or off? The frame keeps the last Reminders lists and holds their changes until the Mac is back.</div>' : '';
    return card('lists', 'Lists',
      'The frame can show lists from Apple Reminders, Google Tasks, both, or none. Lists you share with Mom in Reminders or Google Tasks work for both of you; private lists stay off unless you turn them on.',
      pick + mac + (rows || '<p class="help">No lists yet: they appear here after the Mac’s first check-in or once Google Tasks is connected.</p>') +
      (homeOpts ? '<div class="row">' + field('On the Today screen', '<select id="list-home">' + homeOpts + '</select>') + '</div>' : '') +
      '<h3 class="kick">On the frame</h3>' +
      '<label class="check"><input type="checkbox" id="list-check"' + (L.anyone_check ? ' checked' : '') + '> Anyone can check items off</label>' +
      '<p class="help">Kids can help: checking off is easy to undo on a phone.</p>' +
      '<label class="check"><input type="checkbox" id="list-add"' + (L.anyone_add ? ' checked' : '') + '> Anyone can add items</label>' +
      '<p class="help">Items added on the frame get the note “Added on the frame” in Reminders or Google Tasks.</p>' +
      '<h3 class="kick">Google Tasks</h3>' +
      '<label class="check"><input type="checkbox" id="list-google"' + (gs.on ? ' checked' : '') + '> Use Google Tasks</label>' +
      '<p class="help">The server reads Google Tasks every minute and sends changes made on the frame right away. Nothing runs on a Mac or phone.</p>' +
      (gs.ready && gs.on ? '<div class="actions"><button class="btn line" data-act="gt-check">Check now</button><span class="result" data-res-gt></span></div>' : '') +
      googleSetup(g, 'tasks') +
      '<h3 class="kick">Apple Reminders: the Mac helper</h3>' +
      '<p class="help">Apple has no web service for Reminders, so a small helper on the Mac passes changes back and forth every 30 seconds while the Mac is on, ' +
      'the same way it sends your Favorites. It needs a one-time Reminders permission (System Settings › Privacy &amp; Security › Reminders › Doorpost Lists). ' +
      'See docs/lists.md to install it. <b>Store sections</b> sorts a grocery list into Produce, Dairy, Bakery and so on by the item’s name; neither Reminders nor Google Tasks shares grocery sections with other apps.</p>',
      'Save lists');
  }

  function screenTime() {
    var st = S.screen_time;
    return card('screen', 'Screen time',
      'Kids earn during the week; the family spends it on the weekend. Approved chores, good days and anything you add or take away go into one family pool. ' +
      'Chore minutes are set on the Chores page.',
      '<div class="row">' + field('Saturday to start (minutes)', input('base_saturday_minutes', st.base_saturday_minutes, 'number', ' min="0" step="5"')) +
      field('Sunday to start (minutes)', input('base_sunday_minutes', st.base_sunday_minutes, 'number', ' min="0" step="5"')) + '</div>' +
      '<div class="row">' + field('A good day is worth (minutes)', input('good_day_minutes', st.good_day_minutes, 'number', ' min="5" step="5"')) +
      field('“Full” vault, fuel tank and hourglass (minutes)', input('full_minutes', st.full_minutes, 'number', ' min="60" step="30"')) + '</div>' +
      '<div class="row">' + field('Remind us to start a new week on', '<select data-k="new_week_day">' + DAY_NAMES.map(function (d) {
        return '<option value="' + d[0] + '"' + (st.new_week_day === d[0] ? ' selected' : '') + '>' + d[1] + '</option>'; }).join('') + '</select>') +
      field('at', input('new_week_time', st.new_week_time, 'time')) + '</div>' +
      '<p class="help">The week never resets by itself. After this time, the parent page and the frame’s parent panel show a <b>New week</b> button.</p>' +
      '<p class="help" style="margin-top:6px"><b>Pictures on the frame’s Screen Time tab.</b> Kids tap to switch; each frame remembers the one it was left on.</p>' +
      '<div class="row">' + VIEW_NAMES.map(function (v) {
        return '<label class="check"><input type="checkbox" data-view="' + v[0] + '"' + (st.views.indexOf(v[0]) >= 0 ? ' checked' : '') + '> ' + v[1] + '</label>';
      }).join('') + '</div>', 'Save screen time');
  }

  function house() {
    var ha = S.home_assistant, chosen = {};
    ha.entities.forEach(function (e) { chosen[e.entity] = e; });
    var body;
    if (!HA.available) {
      body = '<p class="help">' + (S.mode.addon ? 'Couldn’t read Home Assistant: ' + esc(HA.message || '') :
        'Available when Doorpost runs as a Home Assistant add-on.') + '</p>';
    } else {
      body = '<label class="check"><input type="checkbox" id="ha-on"' + (ha.enabled ? ' checked' : '') + '> Show house status on the Today screen</label>' +
        HA.entities.map(function (e) {
          var c = chosen[e.entity];
          return '<div class="row" data-ent="' + esc(e.entity) + '"><label class="check" style="flex:1 1 260px"><input type="checkbox"' + (c ? ' checked' : '') + '> ' +
            esc(e.name) + ' <span class="help">(' + esc(e.state) + ')</span></label>' +
            field('Show as', input('name', c ? c.name : e.name)) + '</div>';
        }).join('') || '<p class="help">No doors, locks or garage doors found in Home Assistant.</p>';
    }
    return card('house', 'House status', 'Small read-only reminders at the bottom of the Today screen, like “Garage open” in red.', body, HA.available ? 'Save house status' : '');
  }

  // Weather source and units (app/weather.py). Open-Meteo's license asks for the attribution line.
  function weatherRow(d) {
    function pick(name, cur, opts) {
      return '<select data-k="' + name + '">' + opts.map(function (o) {
        return '<option value="' + o[0] + '"' + (o[0] === cur ? ' selected' : '') + '>' + esc(o[1]) + '</option>';
      }).join('') + '</select>';
    }
    var auto = 'Automatic (here: ';
    return '<div class="row">' +
      field('Weather from', pick('weather_source', d.weather_source, [['auto', 'Automatic'],
        ['nws', 'U.S. National Weather Service'], ['open-meteo', 'Open-Meteo (worldwide)']])) +
      field('Temperature', pick('weather_temp', d.weather_temp, [['auto', auto + (d.weather_auto_units === 'F, mph' ? '°F)' : '°C)')],
        ['F', 'Fahrenheit (°F)'], ['C', 'Celsius (°C)']])) +
      field('Wind', pick('weather_wind', d.weather_wind, [['auto', auto + (d.weather_auto_units === 'F, mph' ? 'mph)' : 'km/h)')],
        ['mph', 'mph'], ['kmh', 'km/h']])) + '</div>' +
      '<div class="row">' +
      field('Show °F or °C on the frame', pick('weather_unit_letter', d.weather_unit_letter, [['no', 'No: 62°'], ['yes', 'Yes: 62°F or 17°C']])) +
      field('Show wind', pick('weather_show_wind', d.weather_show_wind, [['panel', 'On the Weather panel'],
        ['everywhere', 'Weather panel and the top of Today'], ['off', 'Off']])) + '</div>' +
      '<p class="help">Automatic uses the U.S. National Weather Service in the U.S. and Open-Meteo everywhere else, and switches to Open-Meteo if the U.S. service is down. Both are free and need no account. ' +
      'Weather data by <a href="https://open-meteo.com/" target="_blank" rel="noopener">Open-Meteo.com</a> (CC BY 4.0), free for non-commercial use.</p>';
  }

  function display() {
    var d = S.display;
    return card('display', 'General', 'The family name, addresses, weather, night clock and how long the frame waits before going back to Today or the photos.',
      '<div class="row">' + field('Family name (top of the frame)', input('family_name', d.family_name)) +
        field('Family initial (some looks show it)', input('family_initial', d.family_initial || '', 'text', ' maxlength="1" placeholder="From the name" style="max-width:9em"')) + field('Time zone', input('timezone', d.timezone)) + '</div>' +
      '<div class="row">' + field('Address for people (phones, browsers)', input('frame_url', d.frame_url, 'url')) +
      field('Home-network address (the frame, the Mac photo script)', input('lan_url', d.lan_url, 'url')) + '</div>' +
      '<div class="row">' + field('Latitude (for weather)', input('latitude', d.latitude, 'number', ' step="0.01"')) +
      field('Longitude', input('longitude', d.longitude, 'number', ' step="0.01"')) + '</div>' +
      weatherRow(d) +
      '<div class="row">' + field('Night clock from', input('night_start', d.night_start, 'time')) + field('until', input('night_end', d.night_end, 'time')) + '</div>' +
      '<div class="row">' + field('Photos after (idle minutes)', input('idle_minutes_to_photos', d.idle_minutes_to_photos, 'number')) +
      field('Back to Today after (minutes)', input('return_to_today_minutes', d.return_to_today_minutes, 'number')) +
      field('Seconds per photo', input('photo_seconds', d.photo_seconds, 'number')) + '</div>', 'Save display');
  }

  function security() {
    var sec = S.security;
    var rows = sec.parents.map(function (name) {
      return '<div class="item"><div class="row"><b style="flex:1 1 120px">' + esc(name) + '</b><span class="result ok">PIN set</span></div>' +
        '<div class="row">' + field('New PIN', '<input type="password" inputmode="numeric" maxlength="8" data-pin1>') +
        field('Again', '<input type="password" inputmode="numeric" maxlength="8" data-pin2>') + '</div>' +
        '<div class="actions"><button class="btn line" data-act="pin-set" data-name="' + esc(name) + '">Change PIN</button>' +
        '<button class="btn danger" data-act="pin-del" data-name="' + esc(name) + '">Turn off</button></div></div>';
    }).join('');
    var shared = sec.pin_set
      ? '<div class="item"><div class="row"><b style="flex:1 1 120px">Shared PIN</b><span class="help">Works for either of you; logs as “Parent”.</span></div>' +
        (sec.parents.length ? '<div class="actions"><button class="btn danger" data-act="pin-del" data-name="">Turn off the shared PIN</button></div>' : '') + '</div>'
      : '';
    return card('security', 'Parent PINs',
      (sec.parents.length || sec.pin_set ? '' : (sec.demo_pins ? 'Demo mode: Dad is 1234, Mom is 5678. ' : '<b>No PIN yet:</b> approvals on the frame won’t work until you set one. ')) +
      'Give each parent their own PIN, so the screen time log says who approved what. Kids see the keypad, so pick something they won’t guess. Five wrong tries lock it for five minutes.',
      rows + shared +
      '<div class="item"><div class="row">' + field('Name', '<input type="text" maxlength="20" id="pin-name" placeholder="e.g. Mom">') +
      field('PIN (4–8 digits)', '<input type="password" inputmode="numeric" maxlength="8" id="pin1">') +
      field('Again', '<input type="password" inputmode="numeric" maxlength="8" id="pin2">') + '</div>' +
      '<div class="actions"><button class="btn primary" data-act="pin-add">Add parent PIN</button></div></div>', '');
  }

  // ---------------- reading the forms back ----------------
  function vals(el) {
    var o = {};
    $$('[data-k]', el).forEach(function (i) { o[i.getAttribute('data-k')] = i.type === 'checkbox' ? i.checked : i.value; });
    return o;
  }
  function collect(section) {
    if (section === 'calendars') return $$('[data-cal]').map(function (el) {
      var i = +el.getAttribute('data-cal'), v = vals(el), pick = $('select[data-k=caldav_calendar]', el);
      if (pick && pick.value) v.caldav_calendar_name = pick.options[pick.selectedIndex].text;
      return Object.assign({ key: S.calendars[i].key }, v);
    });
    if (section === 'kids') return $$('[data-kidrow]').map(function (el) {
      return Object.assign({ id: S.kids[+el.getAttribute('data-kidrow')].id }, vals(el));
    });
    if (section === 'chores') return S.chores.map(function (c) {
      return { id: c.id, kid: c.kid, title: c.title, minutes: +c.minutes, days: DAYS.filter(function (d) { return c.days.indexOf(d) >= 0; }) };
    });
    if (section === 'photos') return { sources: $$('[data-src]').map(function (el) {
      return Object.assign({ id: S.photos.sources[+el.getAttribute('data-src')].id }, vals(el));
    }) };
    if (section === 'screen') {
      var o = vals($('#screen'));
      o.views = $$('[data-view]', $('#screen')).filter(function (i) { return i.checked; }).map(function (i) { return i.getAttribute('data-view'); });
      return o;
    }
    if (section === 'display') return vals($('#display'));
    if (section === 'house') return { enabled: $('#ha-on').checked, entities: $$('[data-ent]').filter(function (el) {
      return $('input[type=checkbox]', el).checked; }).map(function (el) { return { entity: el.getAttribute('data-ent'), name: vals(el).name }; }) };
  }
  // keep unsaved edits when we re-render after "add"/"remove"
  function stash() {
    ['calendars', 'kids', 'photos'].forEach(function (sec) {
      if (!$('#' + sec)) return;
      var v = collect(sec);
      if (sec === 'calendars') S.calendars = v.map(function (c, i) { return Object.assign({}, S.calendars[i], c, { ics_url_pending: c.ics_url, caldav_password_pending: c.caldav_password }); });
      if (sec === 'kids') S.kids = v.map(function (k, i) { return Object.assign({}, S.kids[i], k); });
      if (sec === 'photos') S.photos.sources = v.sources;
    });
  }

  var SAVE = {
    calendars: function () {
      var merge = $('#merge-shared').checked;
      return api('PUT', 'api/admin/calendars', collect('calendars'))
        .then(function () { return api('PUT', 'api/admin/calendar_options', { merge_shared_events: merge }); });
    },
    family: function () { return api('PUT', 'api/admin/family', collectFamily()); },
    chores: function () { return api('PUT', 'api/admin/chores', collect('chores')); },
    photos: function () { return api('PUT', 'api/admin/photos', collect('photos')); },
    screen: function () { return api('PUT', 'api/admin/screen_time', collect('screen')); },
    house: function () { return api('PUT', 'api/admin/home_assistant', collect('house')); },
    display: function () { return api('PUT', 'api/admin/display', collect('display')); },
    frames: function () {
      stashFrames();
      return api('PUT', 'api/admin/frames', FRAMES.frames.map(function (f) {
        return { id: f.id, name: f.name, look: f.look, home: f.home, screens: f.screens, calendars: f.calendars, kids: f.kids, approvals: f.approvals, night: f.night, pictures: f.pictures || 'original', look_options: f.look_options || {},
          bedtime: f.home === 'kids' ? f.bedtime || '20:00' : null, screen_view: f.home === 'kids' ? f.screen_view || 'rocket' : null };
      }));
    },
    lists: function () {
      var shown = [], sections = [];
      $$('[data-list]').forEach(function (el) {
        var id = el.getAttribute('data-list');
        if ($('[data-lk=shown]', el).checked) shown.push(id);
        if ($('[data-lk=sections]', el).checked) sections.push(id);
      });
      var home = $('#list-home');
      return api('PUT', 'api/admin/lists', { shown: shown, sections: sections, home: home ? home.value : '',
        anyone_add: $('#list-add').checked, anyone_check: $('#list-check').checked, google: $('#list-google').checked });
    },
  };
  function savePin(name, a, b) {
    if (!name) { toast('Type the parent’s name.', true); return; }
    if (a !== b) { toast('The two PINs don’t match.', true); return; }
    api('POST', 'api/admin/pin', { name: name, pin: a }).then(function () { toast('PIN saved for ' + name); load(); })
      .catch(function (e) { toast(e.message, true); });
  }

  function wire() {
    $$('[data-save]').forEach(function (b) {
      b.onclick = function () {
        var label = b.textContent;
        b.disabled = true; b.innerHTML = '<span class="spin" aria-hidden="true"></span> Saving…';
        toast('Saving…', false, true);
        SAVE[b.getAttribute('data-save')]().then(function () { toast('Saved'); return load(); })
          .catch(function (e) { toast(e.message, true); }).then(function () { b.disabled = false; b.textContent = label; });
      };
    });
    if (PAGE === 'special-days' && SP) spWire();
    if (PAGE === 'special-days' && window.FrameBible) window.FrameBible.wire();   // the Bible translation card (bible-admin.js)
    if (PAGE === 'overview' && window.AdminLook) window.AdminLook.wire();   // Settings look (admin-look.js)
    $$('[data-act-change=fam-kid]').forEach(function (cb) {
      cb.onchange = function () {
        famStash();
        var m = FAM.members[+cb.closest('[data-mem]').getAttribute('data-mem')];
        if (cb.checked) m.kid = m.kid || { id: '', initial: (m.name || '?')[0], color: '#1F7576', screen_time_nickname: '' };
        else if (!m.kid || !m.kid.id || confirm('Stop treating ' + m.name + ' as a kid? Their chores are removed when you save.')) m.kid = null;
        render();
      };
    });
    $$('[data-ptup]').forEach(function (inp) {
      inp.onchange = function () {
        if (!inp.files[0]) return;
        var fd = new FormData(); fd.append('file', inp.files[0]);
        toast('Saving…', false, true);
        api('POST', 'api/admin/portraits/' + encodeURIComponent(inp.getAttribute('data-ptup')), fd, true)
          .then(function (r) { toast(r.face ? 'Saved, centered on the face.' : 'Saved (no face found, so it’s centered).'); load(); })
          .catch(function (e) { toast(e.message, true); });
      };
    });
    // Any number of minutes: type it in, or tap 5 / 10 / 15 / 20.
    $$('[data-chore-min]').forEach(function (inp) {
      inp.oninput = function () {
        var v = parseInt(inp.value, 10);
        if (v >= 1 && v <= 240) S.chores[+inp.getAttribute('data-chore-min')].minutes = v;
        inp.classList.toggle('on', [5, 10, 15, 20].indexOf(v) < 0);
        $$('[data-act=chore-min][data-i="' + inp.getAttribute('data-chore-min') + '"]').forEach(function (b) {
          var on = +b.getAttribute('data-m') === v;
          b.className = on ? 'on special' : ''; b.setAttribute('aria-pressed', on);
        });
      };
      inp.onchange = function () { render(); };   // refresh the per-day totals
    });
    $$('[data-chore-title]').forEach(function (inp) {
      inp.oninput = function () {
        var i = +inp.getAttribute('data-chore-title');
        S.chores[i].title = inp.value;
        var nm = $('[data-chore="' + i + '"] .ch-name'); if (nm) nm.textContent = inp.value || 'New chore';
      };
    });
    $$('.seg button').forEach(function (b) {
      b.onclick = function () {
        $$('button', b.parentNode).forEach(function (x) { x.className = x.getAttribute('data-mode'); x.setAttribute('aria-pressed', 'false'); });
        b.className = 'on ' + b.getAttribute('data-mode'); b.setAttribute('aria-pressed', 'true');
      };
    });
    $$('[data-act]').forEach(function (b) {
      var act = b.getAttribute('data-act');
      if (act === 'kid-photo') { b.onchange = function () { uploadKid(b); }; return; }
      if (act === 'mod-turn') { b.onchange = function () { ACT[act](b); }; return; }
      b.onclick = function (e) { e.preventDefault(); e.stopPropagation(); ACT[act] && ACT[act](b); };
      if (b.getAttribute('role') === 'button') b.onkeydown = function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ACT[act] && ACT[act](b); } };
    });
    var drop = $('#drop'), files = $('#files');
    if (drop) {
      files.onchange = function () { upload(files.files); };
      drop.ondragover = function (e) { e.preventDefault(); drop.classList.add('over'); };
      drop.ondragleave = function () { drop.classList.remove('over'); };
      drop.ondrop = function (e) { e.preventDefault(); drop.classList.remove('over'); upload(e.dataTransfer.files); };
    }
  }

  function result(btn, ok, msg) {
    var r = $('[data-res]', btn.closest('.item') || btn.closest('[data-cal]') || btn.closest('.card'));
    if (r) { r.className = 'result ' + (ok ? 'ok' : 'bad'); r.textContent = msg; }
  }

  var ACT = {
    'clear-photo-cache': function (b) {
      if (!confirm('Clear the prepared photos? Your photos are not touched. These are the cropped copies made for the frame; the server makes each one again the next time it is shown, so the slideshow may be slower for a while. Photos from Google or iCloud albums are downloaded again.')) return;
      b.disabled = true;
      api('POST', 'api/admin/storage/clear-photo-cache').then(function (r) {
        toast(r.demo ? 'Demo mode: nothing was removed.' : 'Cleared ' + r.files + ' prepared photos (' + bytes(r.freed) + ').');
        return api('GET', 'api/admin/storage').then(function (v) { STORAGE = v; render(); });
      }).catch(function (e) { toast(e.message, true); b.disabled = false; });
    },
    'frame-fold': function (b) { stashFrames(); var i = +b.getAttribute('data-i'); FRAME_OPEN = FRAME_OPEN === i ? -1 : i; render(); },
    'frame-add': function () {
      stashFrames();
      FRAMES.frames.push({ id: '', name: '', look: 'navy', home: 'today', screens: ['today', 'calendar', 'chores', 'screen', 'lists', 'photos'],
        calendars: [], kids: [], approvals: true, night: null, seen: {} });
      FRAME_OPEN = FRAMES.frames.length - 1; render();
    },
    'frame-copy': function (b) {
      stashFrames();
      var f = JSON.parse(JSON.stringify(FRAMES.frames[+b.getAttribute('data-i')]));
      f.id = ''; f.name = f.name + ' copy'; f.seen = {};
      FRAMES.frames.push(f); FRAME_OPEN = FRAMES.frames.length - 1; render();
    },
    'frame-del': function (b) {
      var f = FRAMES.frames[+b.getAttribute('data-i')];
      if (!confirm('Remove the “' + f.name + '” frame profile? A frame showing it switches to the first frame on the list. Calendars, chores and photos are not touched. Save frames to keep the change.')) return;
      stashFrames(); FRAMES.frames.splice(+b.getAttribute('data-i'), 1); FRAME_OPEN = -1; render();
    },
    'focus-open': function (b) { FOCUS_MODE = 'point'; fxOpen(b.getAttribute('data-id')); },
    'fx-close': function () {
      if (FX_DIRTY && !confirm('Leave without saving this focal point?')) return;
      FOCUS_ID = null; render();
    },
    'fx-mode': function (b) { FOCUS_MODE = b.getAttribute('data-mode'); render(); },
    'fx-follow': function () { FD[FOCUS_MODE] = null; FX_DIRTY = true; render(); },
    'fx-faces': function () { FD.point = FD.wide = FD.tall = null; FX_DIRTY = true; render(); },
    'fx-center': function () { FD.point = [0.5, 0.5]; FD.wide = FD.tall = null; FX_DIRTY = true; render(); },
    'fx-save': function () { fxSave().then(render).catch(function (e) { toast(e.message, true); }); },
    'fx-step': function (b) {
      var list = photoFilter(PHOTOS.photos), p = PHOTOS.photos.filter(function (x) { return x.id === FOCUS_ID; })[0];
      var next = list[list.indexOf(p) + (+b.getAttribute('data-dir'))];
      if (!next) return;
      (FX_DIRTY ? fxSave() : Promise.resolve()).then(function () { fxOpen(next.id); }).catch(function (e) { toast(e.message, true); });
    },
    'photo-filter': function (b) { PHOTO_FILTER = b.getAttribute('data-f'); PHOTO_SHOWN = 12; render(); },
    'add-cal': function (b) {
      var p = b.getAttribute('data-p') || 'google';
      stash(); S.calendars.push({ key: '', label: '', color: '#2E4A7A', who_default: '', has_url: false, filter_mode: 'all', filter_emails: '',
        provider: p, kind: CAL_PROV[p].kinds[0] });
      render();
    },
    'find-cals': function (b) {
      var el = b.closest('[data-cal]'), i = +el.getAttribute('data-cal'), v = vals(el);
      result(b, true, 'Signing in…');
      api('POST', 'api/admin/test/caldav', Object.assign({ key: S.calendars[i].key }, v)).then(function (r) {
        if (r.ok) {
          stash(); CAL_FOUND[i] = r.calendars;
          if (!r.calendars.some(function (f) { return f.url === S.calendars[i].caldav_calendar; })) S.calendars[i].caldav_calendar = r.calendars[0].url;
          render(); b = $('[data-act="find-cals"][data-i="' + i + '"]');
        }
        result(b, r.ok, r.message);
      }).catch(function (e) { result(b, false, e.message); });
    },
    'del-cal': function (b) { if (confirm('Remove this calendar from the frame? (Nothing changes in the calendar itself.)')) { stash(); S.calendars.splice(+b.getAttribute('data-i'), 1); CAL_FOUND = {}; render(); toast('Removed. Save calendars to keep the change.'); } },
    'test-cal': function (b) {
      var el = b.closest('[data-cal]'), i = +el.getAttribute('data-cal');
      result(b, true, 'Checking…');
      api('POST', 'api/admin/test/calendar', Object.assign({ key: S.calendars[i].key }, vals(el)))
        .then(function (r) { result(b, r.ok, r.message); }).catch(function (e) { result(b, false, e.message); });
    },
    'add-src': function () { stash(); S.photos.sources.push({ id: '', kind: 'google_album', label: '', url: '', enabled: true }); render(); },
    'del-src': function (b) { stash(); S.photos.sources.splice(+b.getAttribute('data-i'), 1); render(); toast('Removed. Save albums to keep the change.'); },
    'test-src': function (b) {
      var v = vals(b.closest('[data-src]'));
      result(b, true, 'Checking…');
      api('POST', 'api/admin/test/photos', { kind: v.kind, url: v.url }).then(function (r) { result(b, r.ok, r.message); })
        .catch(function (e) { result(b, false, e.message); });
    },
    'del-photo': function (b) {
      if (!confirm('Remove this photo from the frame? It’s deleted from the frame’s folder (not from Google or iCloud).')) return;
      api('DELETE', 'api/admin/photos/' + b.getAttribute('data-id')).then(function () { toast('Removed'); load(); }).catch(function (e) { toast(e.message, true); });
    },
    'rotate-token': function () {
      if (!confirm('Make a new upload key? The Mac sync stops working until you update its command.')) return;
      api('POST', 'api/admin/upload-token/rotate').then(load);
    },
    'fam-add': function () { famStash(); FAM.members.push({ key: '', name: '', aliases: [], birthday: '', photos_name: '', use_initial: false, photo: null, source: '', kid: null }); render();
      var all = $$('[data-mem] [data-k=name]'); if (all.length) all[all.length - 1].focus(); },
    'fam-del': function (b) {
      famStash();
      var m = FAM.members[+b.getAttribute('data-i')];
      if (!confirm('Take ' + (m.name || 'this person') + ' off the frame?' + (m.kid ? ' Their chores are removed too when you save; their screen time history stays in the log.' : '') +
        ' Their photo stays saved, so adding them back brings it back.')) return;
      FAM.members.splice(+b.getAttribute('data-i'), 1); render(); toast('Removed. Save family to keep the change.');
    },
    'add-kid': function () { stash(); S.kids.push({ id: '', name: '', initial: '', color: '#1F7576', screen_time_nickname: '', photo: null }); render(); },
    'del-kid': function (b) {
      var k = S.kids[+b.getAttribute('data-i')];
      if (!confirm('Remove ' + (k.name || 'this kid') + ' from the frame? Their chores are removed too when you save. Their screen time history stays in the log.')) return;
      stash(); S.kids.splice(+b.getAttribute('data-i'), 1); render();
    },
    'kid-photo-del': function (b) {
      api('DELETE', 'api/admin/kids/' + b.getAttribute('data-id') + '/photo').then(function () { toast('Back to the initial'); load(); });
    },
    'add-chore': function (b) { S.chores.push({ kid: b.getAttribute('data-kid'), title: '', minutes: 5, days: DAYS.slice(0, 5) }); CHORE_OPEN = S.chores.length - 1; render();
      var t = $('[data-chore-title="' + CHORE_OPEN + '"]'); if (t) t.focus(); },
    'del-chore': function (b) { S.chores.splice(+b.getAttribute('data-i'), 1); CHORE_OPEN = -1; CHORE_PICK = {}; render(); toast('Removed. Save chores to keep the change.'); },
    'chore-kid': function (b) { CHORE_KID = b.getAttribute('data-kid'); CHORE_OPEN = -1; render(); },
    'chore-fold': function (b) { var i = +b.getAttribute('data-i'); CHORE_OPEN = CHORE_OPEN === i ? -1 : i; render(); },
    'chore-min': function (b) { S.chores[+b.getAttribute('data-i')].minutes = +b.getAttribute('data-m'); render(); },
    'chore-preset': function (b) {
      var i = +b.getAttribute('data-i'), p = b.getAttribute('data-p');
      if (p === 'pick') CHORE_PICK[i] = true;
      else { CHORE_PICK[i] = false; S.chores[i].days = PRESETS.filter(function (x) { return x[0] === p; })[0][2].slice(); }
      render();
    },
    'chore-day': function (b) {
      var c = S.chores[+b.getAttribute('data-i')], d = b.getAttribute('data-day'), at = c.days.indexOf(d);
      CHORE_PICK[+b.getAttribute('data-i')] = true;
      if (at >= 0) c.days.splice(at, 1); else c.days.push(d);
      render();
    },
    'chore-copy': function () {
      var to = $('#copy-to').value, toName = S.kids.filter(function (k) { return k.id === to; })[0].name;
      S.chores.filter(function (c) { return c.kid === CHORE_KID; }).forEach(function (c) {
        S.chores.push({ kid: to, title: c.title, minutes: c.minutes, days: c.days.slice() });
      });
      render(); toast('Copied to ' + toName + '. Save chores to keep them.');
    },
    'cal-fold': function (b) {
      var i = +b.getAttribute('data-i'), body = $('.fold-body', b.parentNode);
      CAL_OPEN[i] = body.hidden; body.hidden = !body.hidden; b.setAttribute('aria-expanded', !body.hidden);
      var all = $('[data-act="cal-fold-all"]');
      if (all) all.textContent = S.calendars.some(function (c, j) { return CAL_OPEN[j]; }) ? 'Fold all' : 'Open all';
    },
    'cal-fold-all': function () {
      var anyOpen = S.calendars.some(function (c, i) { return CAL_OPEN[i]; });
      stash(); CAL_OPEN = {}; if (!anyOpen) S.calendars.forEach(function (c, i) { CAL_OPEN[i] = true; }); render();
    },
    'cal-move': function (b) {
      var i = +b.getAttribute('data-i'), j = i + +b.getAttribute('data-dir');
      if (j < 0 || j >= S.calendars.length) return;
      stash(); var t = S.calendars[i]; S.calendars[i] = S.calendars[j]; S.calendars[j] = t; CAL_FOUND = {};
      CAL_OPEN = {}; CAL_OPEN[j] = true; render(); toast('Moved. Save calendars to keep the order.');
    },
    'photos-more': function () { stash(); PHOTO_SHOWN += 24; render(); },
    'pg-open': function (b) { pictureInfo(b.getAttribute('data-key')); },
    'sx-holidays': function () { holidaysModal(); },
    'sx-church': function () { churchModal(); },
    'sx-photos': function () { photosModal(); },
    'sp-view': function (b) { SP_VIEW = b.getAttribute('data-view'); render(); },
    'mod-turn': function (b) {
      var id = b.getAttribute('data-id'), body = {};
      body[id] = b.checked;
      b.disabled = true;
      toast('Saving…', false, true);
      api('PUT', 'api/admin/modules', body).then(function (r) {
        toast((b.checked ? 'Turned on.' : 'Turned off. Nothing was deleted.') + (r.notes && r.notes.length ? ' ' + r.notes.join(' ') : ''), false);
        return load();
      }).catch(function (e) { toast(e.message, true); return load(); });
    },
    'pk-turn': function (b) { pkCall('PUT', 'api/admin/packs/' + b.getAttribute('data-id'), { on: b.getAttribute('data-on') === '1' }, b.getAttribute('data-on') === '1' ? 'Turned on' : 'Turned off'); },
    'pk-install': function (b) {
      b.disabled = true; b.innerHTML = '<span class="spin" aria-hidden="true"></span> Installing…';
      pkCall('POST', 'api/admin/packs/install/' + b.getAttribute('data-id'), null, 'Installed. The frame picks it up within a minute.');
    },
    'pk-remove': function (b) {
      var name = b.getAttribute('data-name');
      if (!confirm('Remove the “' + name + '” pack? Its pictures and rules stop showing on the frame. You can install it again later from this page.')) return;
      pkCall('DELETE', 'api/admin/packs/' + b.getAttribute('data-id'), null, 'Removed “' + name + '”');
    },
    'pk-upload': function () {
      var f = $('#pk-file').files[0];
      if (!f) { toast('Choose a pack zip first.', true); return; }
      var fd = new FormData(); fd.append('file', f);
      toast('Installing…', false, true);
      api('POST', 'api/admin/packs/upload', fd, true).then(function (r) { toast('Installed “' + r.name + '”'); return pkReload(); }).catch(function (e) { toast(e.message, true); });
    },
    'sr-mode': function (b) { var w = SP.words.slice(), i = +b.getAttribute('data-i'); w[i] = Object.assign({}, w[i], { picture_only: b.getAttribute('data-po') === 'true' }); wordsSave(w); },
    'sr-del': function (b) { var w = SP.words.slice(), i = +b.getAttribute('data-i'), gone = w[i].word; w.splice(i, 1); wordsSave(w, 'Removed “' + gone + '”'); },
    'sr-move': function (b) {
      var w = SP.words.slice(), i = +b.getAttribute('data-i'), j = i + +b.getAttribute('data-d');
      if (j < 0 || j >= w.length) return;
      var t = w[i]; w[i] = w[j]; w[j] = t; wordsSave(w, 'Moved');
    },
    'sr-add': function () {
      var word = $('#sr-new').value.trim(), look = $('#sr-newlook').value;
      if (!word || !look) { toast('Type a word and pick its picture.', true); return; }
      if (SP.words.some(function (x) { return x.word.toLowerCase() === word.toLowerCase(); })) { toast('“' + word + '” is already a rule.', true); return; }
      var w = SP.words.slice(); w.splice(insertAt(), 0, { word: word, look: look, picture_only: false }); wordsSave(w, 'Added “' + word + '”');
    },
    'sp-copy': function (b) {
      var code = b.getAttribute('data-code');
      copyText(code).then(function () { toast('Copied “' + code + '”. Paste it into the event’s description.'); })
        .catch(function () { window.prompt('Copy this line into the event’s description:', code); });
    },
    'pt-names': function () {
      var names = {};
      $$('[data-pn]').forEach(function (el) { if (el.value.trim()) names[el.getAttribute('data-pn')] = el.value.trim(); });
      api('PUT', 'api/admin/portraits/names', names).then(function () { toast('Saved'); load(); }).catch(function (e) { toast(e.message, true); });
    },
    'pt-del': function (b) {
      if (!confirm('Take ' + b.getAttribute('data-name') + '’s portrait off? The next photo sync from the Mac can bring a new one from Apple Photos.')) return;
      api('DELETE', 'api/admin/portraits/' + encodeURIComponent(b.getAttribute('data-slug'))).then(function () { toast('Removed'); load(); })
        .catch(function (e) { toast(e.message, true); });
    },
    'pt-google': function (b) {
      var slug = b.getAttribute('data-slug'), win = window.open('', '_blank');  // opened now, so the browser doesn't block it
      api('POST', 'api/admin/portraits/' + encodeURIComponent(slug) + '/google').then(function (sess) {
        if (win) win.location = sess.uri + '/autoclose'; else window.open(sess.uri, '_blank');
        toast('Pick a few recent photos of them in Google Photos, then tap Done.', false, true);
        var tries = 0;
        (function poll() {
          api('GET', 'api/admin/portraits/' + encodeURIComponent(slug) + '/google/' + encodeURIComponent(sess.id)).then(function (r) {
            if (!r.done) { if (++tries < 150) setTimeout(poll, Math.max(3, sess.poll || 4) * 1000); else toast('Stopped waiting for Google Photos. Try again.', true); return; }
            if (!r.ok) { toast(r.message, true); return; }
            toast(r.face ? 'Saved: the newest photo with one face, centered on it.' : 'Saved the newest photo (no single face found, so it’s centered).');
            load();
          }).catch(function (e) { toast(e.message, true); });
        })();
      }).catch(function (e) { if (win) win.close(); toast(e.message, true); });
    },
    'gp-pick': function () {
      if (GOOG && GOOG.demo) { toast('Demo mode doesn’t connect to Google. With a real Google sign-in, this opens Google Photos so you can pick photos.', true); return; }
      var win = window.open('', '_blank'), res = $('[data-res-gp]');  // opened now, so the browser doesn't block it
      api('POST', 'api/admin/photos/google').then(function (sess) {
        if (win) win.location = sess.uri + '/autoclose'; else window.open(sess.uri, '_blank');
        res.className = 'result'; res.textContent = 'Waiting for you to tap Done in Google Photos…';
        var tries = 0;
        (function poll() {
          api('GET', 'api/admin/photos/google/' + encodeURIComponent(sess.id)).then(function (r) {
            if (r.state === 'picking') { if (++tries < 300) setTimeout(poll, Math.max(3, sess.poll || 4) * 1000); else res.textContent = 'Stopped waiting. Press the button to try again.'; return; }
            if (r.state === 'error') { res.className = 'result bad'; res.textContent = r.message; return; }
            if (r.state === 'downloading') { res.textContent = 'Copying ' + (r.added + r.skipped + r.failed) + ' of ' + (r.total || '…') + '…'; setTimeout(poll, 2000); return; }
            res.className = 'result ok';
            res.textContent = 'Added ' + r.added + ' photo' + (r.added === 1 ? '' : 's') + (r.skipped ? ' · ' + r.skipped + ' already here' : '') + (r.failed ? ' · ' + r.failed + ' couldn’t be copied' : '') + '.';
            api('GET', 'api/admin/photos').then(function (v) { PHOTOS = v; var keep = res.textContent; render(); var n = $('[data-res-gp]'); if (n) { n.className = 'result ok'; n.textContent = keep; } });
          }).catch(function (e) { res.className = 'result bad'; res.textContent = e.message; });
        })();
      }).catch(function (e) { if (win) win.close(); toast(e.message, true); });
    },
    'gt-check': function () {
      var res = $('[data-res-gt]'); res.className = 'result'; res.textContent = 'Checking…';
      api('POST', 'api/admin/lists/google/sync').then(function (r) {
        res.className = 'result ' + (r.ok ? 'ok' : 'bad'); res.textContent = r.message;
        api('GET', 'api/admin/lists').then(function (v) { LISTS = v; render(); var n = $('[data-res-gt]'); if (n) { n.className = 'result ' + (r.ok ? 'ok' : 'bad'); n.textContent = r.message; } });
      }).catch(function (e) { res.className = 'result bad'; res.textContent = e.message; });
    },
    'g-setup': function () {
      var d = $('.gsetup details'); if (d) d.open = true;
      var id = $('#g-id'); if (id) { id.scrollIntoView({ block: 'center' }); id.focus(); }
      toast('Google needs a one-time setup first (steps below).');
    },
    'g-save': function () {
      api('PUT', 'api/admin/google', { client_id: $('#g-id').value.trim(), client_secret: $('#g-secret').value.trim() })
        .then(function () { toast('Saved'); load(); }).catch(function (e) { toast(e.message, true); });
    },
    'g-connect': function (b) {
      var win = window.open('', '_blank');
      api('GET', 'api/admin/google/connect?features=' + encodeURIComponent(b.getAttribute('data-features') || 'photos,tasks')).then(function (r) { if (win) win.location = r.url; else location.href = r.url; })
        .catch(function (e) { if (win) win.close(); toast(e.message, true); });
    },
    'g-disconnect': function () {
      if (!confirm('Disconnect Google? Google Tasks lists stop updating and Google Photos picking stops. Photos already copied to the frame stay.')) return;
      api('POST', 'api/admin/google/disconnect').then(function () { toast('Disconnected'); load(); }).catch(function (e) { toast(e.message, true); });
    },
    'pin-add': function () { savePin($('#pin-name').value.trim(), $('#pin1').value, $('#pin2').value); },
    'pin-set': function (b) {
      var it = b.closest('.item');
      savePin(b.getAttribute('data-name'), $('[data-pin1]', it).value, $('[data-pin2]', it).value);
    },
    'pin-del': function (b) {
      var name = b.getAttribute('data-name');
      if (!confirm(name ? 'Turn off ' + name + '’s PIN? They can still sign in on the phone through frame.example.com.' : 'Turn off the shared PIN?')) return;
      api('DELETE', 'api/admin/pin' + (name ? '?name=' + encodeURIComponent(name) : '')).then(function () { toast('PIN turned off'); load(); })
        .catch(function (e) { toast(e.message, true); });
    }
  };

  function upload(fileList) {
    if (!fileList || !fileList.length) return;
    var fd = new FormData();
    Array.prototype.forEach.call(fileList, function (f) { fd.append('files', f); });
    toast('Uploading ' + fileList.length + '…');
    api('POST', 'api/admin/photos', fd, true).then(function (r) {
      toast(r.errors.length ? r.errors.join(' ') : 'Added ' + r.saved.length + ' photo' + (r.saved.length === 1 ? '' : 's'), !!r.errors.length);
      load();
    }).catch(function (e) { toast(e.message, true); });
  }
  function uploadKid(inp) {
    var f = inp.files[0];
    if (!f) return;
    var fd = new FormData();
    fd.append('file', f);
    api('POST', 'api/admin/kids/' + inp.getAttribute('data-id') + '/photo', fd, true)
      .then(function () { toast('Photo added'); load(); }).catch(function (e) { toast(e.message, true); });
  }

  load();
})();
