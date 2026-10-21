/* Settings > Email updates (app/email_api.py, app/email_updates.py).
   Draws its own page and keeps its own data; admin.js only asks for html() and wire(). */
(function () {
  'use strict';
  var E = null, D = null, LOADING = false, TEST_TO = '';
  var DAYS = [['sun', 'S', 'Sunday'], ['mon', 'M', 'Monday'], ['tue', 'T', 'Tuesday'], ['wed', 'W', 'Wednesday'], ['thu', 'T', 'Thursday'], ['fri', 'F', 'Friday'], ['sat', 'S', 'Saturday']];
  var PICKS = [['07:00', 'Morning, 7 AM'], ['16:00', 'After school, 4 PM'], ['19:30', 'Evening, 7:30 PM']];
  var PROVIDER = { gmail: 'Gmail or Google Workspace', outlook: 'Outlook or Microsoft 365', icloud: 'iCloud Mail', other: 'Other (SMTP)' };

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
  function clock(hhmm) {
    var p = String(hhmm || '00:00').split(':'), h = +p[0], m = p[1] || '00';
    return (h % 12 || 12) + ':' + m + ' ' + (h < 12 ? 'AM' : 'PM');
  }
  function when(iso) {
    var d = new Date(iso), now = E ? new Date(E.now) : new Date();
    var day = d.toDateString() === now.toDateString() ? 'Today' : d.toLocaleDateString('en-US', { weekday: 'short' });
    return day + ' ' + clock(('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2));
  }
  function dayName(k) { return DAYS.filter(function (d) { return d[0] === k; })[0][2]; }
  function chk(attr, on, label) { return '<label class="check"><input type="checkbox" ' + attr + (on ? ' checked' : '') + '> ' + label + '</label>'; }

  function load() {
    if (LOADING) return;
    LOADING = true;
    api('GET', 'api/admin/email-updates').then(function (v) {
      E = v; D = JSON.parse(JSON.stringify({ daily: v.daily, weekly: v.weekly, reminder: v.reminder, people: v.people }));
      LOADING = false; paint();
    }).catch(function (e) { LOADING = false; var r = document.getElementById('em-root'); if (r) r.innerHTML = '<section class="card"><p class="result bad">' + esc(e.message) + '</p></section>'; });
  }
  function refresh() { return api('GET', 'api/admin/email-updates').then(function (v) { E = v; paint(); }); }

  // ---------------- the page ----------------
  function dailyCard() {
    var d = D.daily, morning = d.time < '12:00';
    var covers = morning
      ? 'Sent in the morning, so it covers <b>yesterday</b>. Chores still waiting from yesterday can be approved any day this week.'
      : 'Sent in the evening, so it covers <b>today</b>. Anything still waiting at bedtime can be approved tomorrow; it counts toward this week.';
    var body = chk('data-em="daily.on"', d.on, '<b>Send the daily chore recap</b>');
    if (d.on) {
      body += '<div class="row">' + '<label class="f">Send at<input type="time" data-em="daily.time" value="' + esc(d.time) + '" step="900"></label>' +
        '<div class="seg" role="group" aria-label="Quick picks">' + PICKS.map(function (p) {
          return '<button type="button" data-em-pick="' + p[0] + '" class="' + (d.time === p[0] ? 'on special' : '') + '" aria-pressed="' + (d.time === p[0]) + '">' + p[1] + '</button>';
        }).join('') + '</div></div>' +
        '<p class="help">' + covers + ' An email with nothing to report is skipped.</p>' +
        '<div class="row">' + chk('data-em="daily.waiting"', d.waiting, 'Waiting to check') + chk('data-em="daily.approved"', d.approved, 'Approved') +
        chk('data-em="daily.not_done"', d.not_done, 'Not done') + chk('data-em="daily.skip_weekend"', d.skip_weekend, 'Skip Saturdays and Sundays') + '</div>' +
        '<div class="item">' + chk('data-em="daily.quick_approve"', d.quick_approve, '<b>Quick approve from the email</b>') +
        '<p class="help">' + (d.quick_approve
          ? 'Each waiting chore gets an <b>Approve</b> button, plus <b>Approve all</b>. No PIN or sign-in: tapping it is the approval, logged under the parent the email went to. ' +
            'Each button works once and stops working after 48 hours; Undo works for 10 minutes. Only parents with a PIN get the buttons.'
          : 'Off: the email only lists the chores. Approve them on the parent page with your PIN.') + '</p>' +
        (!E.frame_url ? '<p class="help result bad">Set “Address for people” on the Overview page so the email’s buttons and links have somewhere to go.</p>' : '') + '</div>';
    }
    return '<section class="card" id="em-daily"><h2>Daily chore recap</h2><p class="help">Chores waiting for you to check, what was approved, and what wasn’t done.</p>' + body + '</section>';
  }

  function weeklyCard() {
    var w = D.weekly, weekend = w.day === 'sat' || w.day === 'sun';
    var line = weekend ? 'This lands on the weekend, after screen time has started. Friday works best for setting devices ahead.'
      : 'Covers the week so far, through ' + dayName(w.day) + '. Chores approved after it goes out still count on the frame.';
    var body = chk('data-em="weekly.on"', w.on, '<b>Send the weekend screen time email</b>');
    if (w.on) {
      body += '<div class="row"><div class="f">Day<div class="seg" role="group" aria-label="Day of the week">' + DAYS.map(function (d) {
          return '<button type="button" data-em-day="' + d[0] + '" aria-label="' + d[2] + '" aria-pressed="' + (w.day === d[0]) + '" class="' + (w.day === d[0] ? 'on special' : '') + '">' + d[1] + '</button>';
        }).join('') + '</div></div>' +
        '<label class="f">Send at<input type="time" data-em="weekly.time" value="' + esc(w.time) + '" step="900"></label></div>' +
        '<p class="help">' + line + '</p>' +
        '<div class="row">' + chk('data-em="weekly.per_kid"', w.per_kid, 'A line per kid (counts “just for” extras)') +
        chk('data-em="weekly.warn_waiting"', w.warn_waiting, 'Warn about chores still waiting') +
        chk('data-em="weekly.update"', w.update, 'Send an update if the total changes before Saturday 8 AM') + '</div>';
    }
    if (!E.screen_time_on) body = '<p class="help">Screen time is turned off in Settings › Modules, so this email has nothing to say.</p>';
    return '<section class="card" id="em-weekly"><h2>Weekend screen time</h2><p class="help">What the kids earned this week, split into Saturday and Sunday, so you can set limits on each device.</p>' + body + '</section>';
  }

  function reminderCard() {
    var nw = E.new_week;
    return '<section class="card" id="em-reminder"><h2>New week reminder</h2>' +
      chk('data-em="reminder.on"', D.reminder.on, '<b>Send the new week reminder</b>') +
      '<p class="help">If nobody has started a new screen time week by <b>' + esc(dayName(nw.day)) + ' ' + esc(clock(nw.time)) + '</b> (set on the <a href="admin/screen-time">Screen time</a> page), ' +
      'email a reminder with last week’s final total. Nothing resets by itself.</p></section>';
  }

  function peopleCard() {
    var rows = D.people.map(function (p, i) {
      return '<div class="item" data-em-person="' + i + '"><div class="row">' +
        (p.parent ? '<b style="flex:0 0 110px;align-self:center">' + esc(p.name) + '</b>'
                  : '<label class="f" style="flex:0 1 160px">Name<input type="text" data-em-p="name" value="' + esc(p.name) + '" maxlength="40"></label>') +
        '<label class="f" style="flex:1 1 220px">Email address<input type="email" data-em-p="email" value="' + esc(p.email) + '" placeholder="' + esc(p.name || 'Their') + '’s email address" autocomplete="off"></label>' +
        (p.parent ? '' : '<button type="button" class="btn danger" data-em-remove="' + i + '">Remove</button>') + '</div>' +
        '<div class="row">' + chk('data-em-p="daily"', p.daily, 'Daily recap') + chk('data-em-p="weekly"', p.weekly, 'Weekend screen time') + chk('data-em-p="reminder"', p.reminder, 'New week reminder') + '</div>' +
        (!p.email ? '<p class="help">Add an email address to send to ' + esc(p.name || 'them') + '.</p>' : '') +
        (p.parent ? '' : '<p class="help">Not a parent: gets the emails, never the quick approve buttons.</p>') + '</div>';
    }).join('');
    return '<section class="card" id="em-people"><h2>Who gets which</h2>' + rows +
      '<div class="actions"><button type="button" class="btn quiet" data-em-add>+ Add someone else</button></div>' +
      '<p class="help">Everyone with a parent PIN is listed (Settings › Parent PINs). Someone else, like a grandparent or a sitter, gets emails only.</p>' +
      '<div class="actions"><button type="button" class="btn primary" data-em-save>Save email updates</button></div></section>';
  }

  function accountCard() {
    var a = E.account, other = a.provider === 'other';
    var status = a.ready ? '<span class="result ok">Ready to send</span>' : (E.demo ? '<span class="help">Demo mode: emails go to the outbox below, never out.</span>' : '<span class="result bad">Not set up yet</span>');
    return '<section class="card" id="em-account"><h2>Sending account</h2>' +
      '<p class="help">The emails come from this account. For Gmail or Google Workspace, turn on 2-Step Verification, then make an <b>app password</b> ' +
      '(Google Account › Security › App passwords) and paste it here. Your normal password won’t work. The password stays on this server and is never shown again.</p>' +
      '<div class="row"><label class="f">Mail service<select data-ea="provider">' + E.account.providers.map(function (p) {
        return '<option value="' + p + '"' + (a.provider === p ? ' selected' : '') + '>' + esc(PROVIDER[p] || p) + '</option>'; }).join('') + '</select></label>' +
      '<label class="f" style="flex:1 1 220px">Account (email address)<input type="email" data-ea="user" value="' + esc(a.user) + '" autocomplete="off"></label>' +
      '<label class="f" style="flex:1 1 200px">' + (a.provider === 'gmail' ? 'App password' : 'Password') + '<input type="password" data-ea="password" placeholder="' + (a.password_set ? 'Saved. Type a new one to change it.' : '16 letters from Google') + '" autocomplete="new-password"></label></div>' +
      (other ? '<div class="row"><label class="f" style="flex:1 1 220px">Mail server (SMTP)<input type="text" data-ea="host" value="' + esc(a.host) + '" placeholder="smtp.example.com"></label>' +
        '<label class="f" style="flex:0 1 110px">Port<input type="number" data-ea="port" value="' + esc(a.port) + '"></label>' +
        '<label class="f">Security<select data-ea="security">' + [['starttls', 'STARTTLS (587)'], ['ssl', 'SSL (465)'], ['none', 'None']].map(function (o) {
          return '<option value="' + o[0] + '"' + (a.security === o[0] ? ' selected' : '') + '>' + o[1] + '</option>'; }).join('') + '</select></label></div>' : '') +
      '<div class="row"><label class="f" style="flex:1 1 200px">From name<input type="text" data-ea="from_name" value="' + esc(a.from_name) + '" placeholder="The app’s name"></label>' +
      '<label class="f" style="flex:1 1 220px">From address (optional)<input type="email" data-ea="from_address" value="' + esc(a.from_address) + '" placeholder="Same as the account"></label></div>' +
      '<div class="actions"><button type="button" class="btn primary" data-ea-save>Save account</button>' + status +
      (a.password_set ? '<button type="button" class="btn danger" data-ea-forget>Forget the password</button>' : '') + '</div></section>';
  }

  function sideCards() {
    var withEmail = D.people.filter(function (p) { return p.email; });
    if (!TEST_TO || !withEmail.some(function (p) { return p.name === TEST_TO; })) TEST_TO = withEmail.length ? withEmail[0].name : '';
    var up = E.upcoming.map(function (u) {
      return '<div class="row" style="align-items:center"><b style="flex:0 0 130px">' + esc(when(u.at)) + '</b><span style="flex:1 1 200px">' + esc(u.title) +
        '<br><span class="help">' + (u.to.length ? 'To ' + esc(u.to.join(' and ')) : 'Nobody yet') + (u.note ? ' · ' + esc(u.note) : '') + '</span></span></div>';
    }).join('') || '<p class="help">All email updates are off.</p>';
    var STATUS = { sent: 'Sent', skipped: 'Skipped', failed: 'Didn’t send', sending: 'Sending' };
    var KIND = { daily: 'Daily recap', weekly: 'Weekend screen time', weekly_update: 'Weekend update', reminder: 'New week reminder', test: 'Test' };
    var logRows = E.log.map(function (l) {
      return '<div class="row" style="align-items:baseline"><span style="flex:1 1 180px">' + esc(KIND[l.kind] || l.kind) + ' · ' + esc(when(l.at)) + '</span>' +
        '<span class="' + (l.status === 'failed' ? 'result bad' : 'help') + '" style="flex:1 1 220px">' + esc(STATUS[l.status] || l.status) +
        (l.recipients ? ' to ' + esc(l.recipients) : '') + (l.note ? ': ' + esc(l.note) : '') + '</span></div>';
    }).join('') || '<p class="help">Nothing sent yet.</p>';
    var outbox = E.demo && E.outbox.length ? '<h3 style="margin:8px 0 0;font-size:16px">Demo outbox</h3>' + E.outbox.map(function (m, i) {
      return '<p class="help"><a href="api/admin/email-updates/outbox/' + i + '" target="_blank" rel="noopener">' + esc(m.subject) + '</a> · to ' + esc(m.to) + '</p>';
    }).join('') : '';
    return '<section class="card" id="em-next"><h2>Coming up</h2>' + up + '</section>' +
      '<section class="card" id="em-test"><h2>Try it</h2><p class="help">Sends today’s real numbers to one person, marked TEST. Save first if you changed anything. ' +
      'Preview shows the email here without sending it.</p>' +
      (withEmail.length ? '<div class="row"><label class="f">Send to<select data-em-test-to>' + withEmail.map(function (p) {
        return '<option' + (p.name === TEST_TO ? ' selected' : '') + '>' + esc(p.name) + '</option>'; }).join('') + '</select></label></div>' : '<p class="help">Add an email address above and save, then send a test.</p>') +
      [['daily', 'Daily recap'], ['weekly', 'Weekend screen time'], ['reminder', 'New week reminder']].map(function (k) {
        return '<div class="actions"><button type="button" class="btn line" data-em-test="' + k[0] + '"' + (withEmail.length ? '' : ' disabled') + '>Send the ' + k[1].toLowerCase() + ' now</button>' +
          '<a class="btn quiet" href="api/admin/email-updates/preview/' + k[0] + '" target="_blank" rel="noopener">Preview</a></div>';
      }).join('') + outbox + '</section>' +
      '<section class="card" id="em-log"><h2>Sent lately</h2>' + logRows + '</section>';
  }

  function inner() {
    if (!E) return '<section class="card"><h2>Email updates</h2><p class="help"><span class="spin" aria-hidden="true"></span> Loading…</p></section>';
    return '<section class="card"><h2>Email updates</h2><p class="help">Short emails to parents about chores and screen time. Nothing is sent to the kids, and an email with nothing to report is skipped.</p></section>' +
      dailyCard() + weeklyCard() + reminderCard() + peopleCard() + accountCard() + sideCards();
  }
  function paint() {
    var r = document.getElementById('em-root');
    if (!r) return;
    var keep = window.scrollY;
    r.innerHTML = inner();
    window.scrollTo(0, keep);
  }

  // ---------------- reading the page back ----------------
  function setPath(path, v) { var p = path.split('.'); D[p[0]][p[1]] = v; }
  function readAll() {
    var r = document.getElementById('em-root');
    if (!r || !D) return;
    Array.prototype.forEach.call(r.querySelectorAll('[data-em]'), function (el) {
      setPath(el.getAttribute('data-em'), el.type === 'checkbox' ? el.checked : el.value);
    });
    Array.prototype.forEach.call(r.querySelectorAll('[data-em-person]'), function (box) {
      var p = D.people[+box.getAttribute('data-em-person')];
      Array.prototype.forEach.call(box.querySelectorAll('[data-em-p]'), function (el) {
        p[el.getAttribute('data-em-p')] = el.type === 'checkbox' ? el.checked : el.value.trim();
      });
    });
    var t = r.querySelector('[data-em-test-to]');
    if (t) TEST_TO = t.value;
  }
  function account() {
    var out = {};
    Array.prototype.forEach.call(document.querySelectorAll('#em-account [data-ea]'), function (el) { out[el.getAttribute('data-ea')] = el.value; });
    var a = E.account;
    return { provider: out.provider, user: out.user || '', password: out.password || '', from_name: out.from_name || '', from_address: out.from_address || '',
      host: out.host != null ? out.host : a.host, port: +(out.port != null ? out.port : a.port) || 587, security: out.security || a.security };
  }

  function save() {
    readAll();
    return api('PUT', 'api/admin/email-updates', D).then(function () { return refresh(); })
      .then(function () { toast('Email updates saved'); }).catch(function (e) { toast(e.message, true); });
  }

  function wire() {
    var r = document.getElementById('em-root');
    if (!r) return;
    if (!E) { load(); return; }
    if (r.getAttribute('data-wired')) return;
    r.setAttribute('data-wired', '1');
    r.addEventListener('change', function (e) {
      var el = e.target;
      if (el.matches('[data-ea="provider"]')) { E.account.provider = el.value; readAll(); paint(); return; }
      if (el.matches('[data-em], [data-em-p], [data-em-test-to]')) { readAll(); paint(); }
    });
    r.addEventListener('click', function (e) {
      var el = e.target.closest('button');
      if (!el) return;
      if (el.hasAttribute('data-em-pick')) { readAll(); D.daily.time = el.getAttribute('data-em-pick'); paint(); return; }
      if (el.hasAttribute('data-em-day')) { readAll(); D.weekly.day = el.getAttribute('data-em-day'); paint(); return; }
      if (el.hasAttribute('data-em-add')) { readAll(); D.people.push({ name: '', email: '', parent: false, other: true, daily: true, weekly: true, reminder: false }); paint(); return; }
      if (el.hasAttribute('data-em-remove')) { readAll(); D.people.splice(+el.getAttribute('data-em-remove'), 1); paint(); return; }
      if (el.hasAttribute('data-em-save')) { el.disabled = true; save().then(function () { el.disabled = false; }); return; }
      if (el.hasAttribute('data-ea-save') || el.hasAttribute('data-ea-forget')) {
        var body = account();
        if (el.hasAttribute('data-ea-forget')) body.forget_password = true;
        el.disabled = true;
        api('PUT', 'api/admin/email-updates/account', body).then(refresh)
          .then(function () { toast(body.forget_password ? 'Password forgotten' : 'Account saved'); })
          .catch(function (err) { el.disabled = false; toast(err.message, true); });
        return;
      }
      if (el.hasAttribute('data-em-test')) {
        readAll();
        var kind = el.getAttribute('data-em-test');
        el.disabled = true;
        api('POST', 'api/admin/email-updates/test', { kind: kind, name: TEST_TO }).then(function (res) {
          toast(res.demo ? 'Demo: put in the outbox below' : 'Sent to ' + res.to);
          return refresh();
        }).catch(function (err) { el.disabled = false; toast(err.message, true); });
      }
    });
  }

  window.EmailAdmin = {
    html: function () { return '<div id="em-root">' + inner() + '</div>'; },
    wire: wire
  };
})();
