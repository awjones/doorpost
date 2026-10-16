/* The Kids home screen (a frame profile with home = "Kids", Settings > Frames).
   Plain ES2017 for the frame's Chrome 106 WebView; no emoji (Android 6 shows boxes), only drawn pictures.
   app.js hands in its helpers and calls render() for #screen-kids. The server already took out
   everything that is only for parents (app/kidsview.py), so this screen can't show it by mistake. */
window.KidsView = function (H) {
  'use strict';
  var esc = H.esc, I = H.I;

  // Simple pictures for chores and events (24x24, drawn with lines), named by app/kidsview.py.
  var P = {
    bed: '<path d="M3 19V6M3 15h18v4M21 15v-2.5a3 3 0 0 0-3-3h-8V15"/><circle cx="6.5" cy="11.5" r="2"/>',
    tooth: '<path d="M7.5 3C5 3 3 4.8 3 7.8c0 3 1.6 5 2.1 8 .4 2.4 1 5.2 2.4 5.2s1.9-2.8 2.3-4.8c.3-1.4 1-2 2.2-2s1.9.6 2.2 2c.4 2 .9 4.8 2.3 4.8s2-2.8 2.4-5.2c.5-3 2.1-5 2.1-8C21 4.8 19 3 16.5 3c-1.9 0-2.8 1-4.5 1S9.4 3 7.5 3z"/>',
    doctor: '<path d="M12 20.5s-7.5-4.6-9.2-9.4A4.7 4.7 0 0 1 12 7.4a4.7 4.7 0 0 1 9.2 3.7C19.5 15.9 12 20.5 12 20.5z"/><path d="M12 10.5v5M9.5 13h5"/>',
    school: '<path d="M2.5 21h19M5 21V10.5l7-4.5 7 4.5V21"/><path d="M12 6V2.5l4 1.5-4 1.5"/><path d="M10 21v-5h4v5"/><path d="M8 12.5h.01M16 12.5h.01"/>',
    swim: '<circle cx="16" cy="5.5" r="2"/><path d="M6.5 12l4-4 3.5 3.5"/><path d="M2.5 15c1.6 0 1.6 1.2 3.2 1.2s1.6-1.2 3.2-1.2 1.6 1.2 3.2 1.2 1.6-1.2 3.2-1.2 1.6 1.2 3.2 1.2 1.5-1.2 2.9-1.2"/><path d="M2.5 19.5c1.6 0 1.6 1.2 3.2 1.2s1.6-1.2 3.2-1.2 1.6 1.2 3.2 1.2 1.6-1.2 3.2-1.2 1.6 1.2 3.2 1.2 1.5-1.2 2.9-1.2"/>',
    music: '<path d="M9 18V5.5l11-2.5v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
    ball: '<circle cx="12" cy="12" r="9"/><path d="M12 7.5l4 2.9-1.5 4.6h-5L8 10.4z"/><path d="M12 7.5V3M16 10.4l4.2-1.5M14.5 15l2.6 3.8M9.5 15l-2.6 3.8M8 10.4 3.8 8.9"/>',
    dishes: '<circle cx="15" cy="12.5" r="6.5"/><circle cx="15" cy="12.5" r="3"/><path d="M3 3.5v5a2 2 0 0 0 4 0v-5M5 10.5v10M5 3.5v5"/>',
    dog: '<path d="M7.5 17.5c0-2.8 2.2-5.5 4.5-5.5s4.5 2.7 4.5 5.5c0 2-2 3-4.5 3s-4.5-1-4.5-3z"/><circle cx="5.5" cy="10.5" r="1.9"/><circle cx="18.5" cy="10.5" r="1.9"/><circle cx="9.2" cy="5.5" r="1.9"/><circle cx="14.8" cy="5.5" r="1.9"/>',
    broom: '<path d="M20 3l-8.5 8.5"/><path d="M11.5 11.5c-3 0-6 2-7 6.5L3.5 21l3-1c4.5-1 6.5-4 6.5-7z"/><path d="M5.5 17.5l3-3M8 20l3-3"/>',
    shoes: '<path d="M2.5 17.5V9.5l4.5-1 2.5 3.5h2.5l8.5 3a2.2 2.2 0 0 1 1.5 2.1v.4z"/><path d="M2.5 20.5h19M6.5 12l1.5-.5M8 14l1.5-.5"/>',
    laundry: '<path d="M8.5 3 3 6l2.2 4.3L7 9.5V21h10V9.5l1.8.8L21 6l-5.5-3c0 1.6-1.4 3-3.5 3S8.5 4.6 8.5 3z"/>',
    toys: '<rect x="3" y="13" width="8" height="8" rx="1.5"/><rect x="13" y="13" width="8" height="8" rx="1.5"/><rect x="8" y="3.5" width="8" height="8" rx="1.5"/>',
    trash: '<path d="M4 7h16M10 3.5h4M6 7l1 14h10l1-14"/><path d="M10 11v6M14 11v6"/>',
    plant: '<path d="M12 21v-9"/><path d="M12 12c0-4.2 3-7.5 8.5-7.5 0 4.2-3 7.5-8.5 7.5z"/><path d="M12 15.5c0-3.2-2.6-5.8-7.5-5.8 0 3.2 2.6 5.8 7.5 5.8z"/><path d="M7 21h10"/>',
    food: '<path d="M7 3v8M5 3v5a2 2 0 0 0 4 0V3M7 11v10"/><path d="M17.5 21V3c-2.2 1.6-3.5 4.4-3.5 8.5h3.5"/>',
    book: '<path d="M2.5 5c3-1.2 6.8-1 9.5 1 2.7-2 6.5-2.2 9.5-1v14c-3-1.2-6.8-1-9.5 1-2.7-2-6.5-2.2-9.5-1z"/><path d="M12 6v14"/>',
    party: '<path d="M12 2.5a6 6 0 0 1 6 6c0 4.3-3.4 7.5-6 7.5s-6-3.2-6-7.5a6 6 0 0 1 6-6z"/><path d="M11 16l-.7 1.8h3.4L13 16M12 17.8c0 2-2.2 2.2-2.2 4"/><path d="M9.5 6.5a3 3 0 0 1 2-1.5"/>',
    tv: '<rect x="2.5" y="6.5" width="19" height="13" rx="2.5"/><path d="M8 2.5l4 4 4-4"/>',
    people: '<circle cx="8" cy="8" r="3.2"/><circle cx="17" cy="9" r="2.6"/><path d="M2 20.5c0-3.6 2.7-6.2 6-6.2s6 2.6 6 6.2M14.5 15c3.4-.6 7 1.2 7 5.5"/>',
    car: '<path d="M3 16.5v-4.2l2.2-5.3h13.6l2.2 5.3v4.2z"/><path d="M3 12.3h18"/><circle cx="7.5" cy="17" r="2.2"/><circle cx="16.5" cy="17" r="2.2"/>',
    star: '<path d="M12 2.8l2.8 6 6.6.8-4.9 4.5 1.3 6.6L12 17.4l-5.8 3.3 1.3-6.6-4.9-4.5 6.6-.8z"/>',
    moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z"/>',
    sun: '<circle cx="12" cy="12" r="4.2"/><path d="M12 2v2.2M12 19.8V22M4.9 4.9l1.6 1.6M17.5 17.5l1.6 1.6M2 12h2.2M19.8 12H22M4.9 19.1l1.6-1.6M17.5 6.5l1.6-1.6"/>',
    sunrise: '<path d="M3 18h18M7 18a5 5 0 0 1 10 0"/><path d="M12 3.5v4M4.9 10.9l1.6 1.6M19.1 10.9l-1.6 1.6M9.5 6l2.5-2.5L14.5 6"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>'
  };
  var COLOR = { bed: '#6C63FF', tooth: '#29B6F6', doctor: '#E5484D', school: '#F59E0B', swim: '#0EA5E9', music: '#E85D9E',
    ball: '#22A55A', dishes: '#14B8A6', dog: '#B7791F', broom: '#8B5CF6', shoes: '#F97316', laundry: '#3B82F6',
    toys: '#EF4444', trash: '#64748B', plant: '#16A34A', food: '#FF8A3D', book: '#A0522D', party: '#EC4899', tv: '#7C3AED',
    people: '#0891B2', car: '#2563EB', star: '#F4B400' };

  function pic(name, size, stroke) {
    var s = size || 32;
    return '<svg class="kpic" width="' + s + '" height="' + s + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="' +
      (stroke || 2.2) + '" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (P[name] || P.star) + '</svg>';
  }
  function bubble(name, cls) {
    return '<span class="kbub ' + (cls || '') + '" style="background:' + (COLOR[name] || COLOR.star) + '">' + pic(name, 0) + '</span>';
  }
  function minutesWords(m) {
    if (m <= 0) return 'now';
    var h = Math.floor(m / 60), r = m % 60;
    if (!h) return r + (r === 1 ? ' minute' : ' minutes');
    return h + (h === 1 ? ' hour' : ' hours') + (r ? ' ' + r + ' min' : '');
  }
  function timeParts(label) {  // "5:30 PM" -> ["5:30", "PM"]
    var m = /^(\d+:\d\d)\s*([AP]M)$/i.exec(label || '');
    return m ? [m[1], m[2].toUpperCase()] : [label || '', ''];
  }
  // Minutes until bedtime, worked out on the frame so the countdown moves between server checks.
  function bedtimeLeft(kv) {
    var b = kv.bedtime, n = H.localNow(), p = (b.at || '20:00').split(':');
    return (+p[0] * 60 + +p[1]) - (n.getUTCHours() * 60 + n.getUTCMinutes());
  }

  // ---------------- pieces ----------------
  function header(eve) {
    var d = H.data(), c = H.clock(), h = H.localNow().getUTCHours(), w = d.weather;
    var part = h < 12 ? ['sunrise', 'Good morning!'] : h < 17 ? ['sun', 'Good afternoon!'] : ['moon', 'Good evening!'];
    var dl = (d.date_label || '').split(' · ');
    return '<header class="khead' + (eve ? ' eve' : '') + '">' +
      '<span class="kpart" aria-hidden="true">' + pic(part[0], 0, 2) + '</span>' +
      '<div class="kday"><div class="khi">' + part[1] + '</div><div class="kdow">' + esc(dl[0] || '') + '</div><div class="kdate">' + esc(dl[1] || '') + '</div></div>' +
      '<div class="kclock">' + (w && w.temp != null ? '<div class="kwx">' + I(w.icon, 40, 2) + '<b>' + w.temp + '°' + (w.display && w.display.letter ? ((w.units && w.units.temp) || 'F') : '') + '</b><span>' + esc(w.text) + '</span></div>' : '') +
      '<div class="kt' + (c.t.length > 4 ? ' long' : '') + '">' + c.t + '<span>' + c.ap + '</span></div></div></header>';
  }
  function bedtimeCard(kv) {
    var left = bedtimeLeft(kv), b = kv.bedtime;
    if (left > 120 || left < -90) return '';
    var pct = Math.max(4, Math.min(100, Math.round((120 - Math.max(0, left)) / 120 * 100)));
    var steps = [['laundry', 'Pajamas'], ['tooth', 'Brush teeth'], ['book', 'Story'], ['moon', 'Lights out']].map(function (s) {
      return '<span class="kstep">' + pic(s[0], 0, 2) + '<i>' + s[1] + '</i></span>';
    }).join('');
    return '<section class="kbed" aria-label="Bedtime">' +
      '<div class="kbed-top"><span class="kmoon">' + pic('moon', 0, 2) + '</span><div class="kbed-t">' +
      (left > 0 ? '<small>Bedtime in</small><b>' + esc(minutesWords(left)) + '</b>' : '<small>It’s ' + esc(b.label) + '</small><b>Bedtime!</b>') +
      '</div><span class="kbed-at">' + esc(b.label) + '</span></div>' +
      '<div class="kbar"><span style="width:' + pct + '%"></span><i>' + pic('moon', 0, 2.4) + '</i></div>' +
      '<div class="ksteps">' + steps + '</div></section>';
  }
  function todaySpecial() {
    var day = H.data().calendar.rolling.days[0];
    var sp = day && day.special;
    return sp && sp.kind !== 'sunday' ? sp : null;
  }
  function takeover(sp, kv) {
    var nxt = kv.next.filter(function (x) { return !x.bedtime; }).slice(0, 2).map(function (x) {
      return '<span class="ktk-chip">' + pic(x.picture, 0, 2.2) + esc(x.time + ' ' + x.title) + '</span>';
    }).join('');
    return '<section class="ktake' + (sp.solemn ? ' solemn' : '') + '" aria-label="' + esc(sp.title) + '">' + H.spArt(sp, 'wide', 'ktake') +
      '<div class="ktk-shade"></div><div class="ktk-txt"><span class="ktk-today">' + pic('star', 0, 2.2) + 'Today</span>' +
      '<div class="ktk-script">' + esc(sp.script) + '</div><div class="ktk-ti">' + esc(sp.title) + '</div>' +
      (nxt ? '<div class="ktk-next">' + nxt + '</div>' : '') + '</div></section>';
  }
  function ribbon() {
    var u = H.data().calendar.upcoming;
    if (!u || u.days_until < 1 || u.solemn) return '';
    var n = u.days_until;
    return '<section class="krib" aria-label="' + esc(u.title) + '"><span class="krib-art">' + H.spArt(u, 'mid', 'krib') + '</span>' +
      '<div class="krib-t"><small>' + (n === 1 ? 'Tomorrow!' : n + ' sleeps until') + '</small><b>' + esc(u.title) + '</b></div>' +
      '<span class="krib-n" aria-hidden="true">' + n + '</span></section>';
  }
  function kidDots(ids) {
    var d = H.data(), all = d.kids.length > 1 && ids.length === d.kids.length;
    if (all) return '<span class="kdots"><i class="all">Everyone</i></span>';
    return '<span class="kdots">' + ids.map(function (id) {
      var k = H.kidById(id);
      return k && k.id === id ? '<i style="background:' + esc(k.color) + '">' + esc(k.initial) + '</i>' : '';
    }).join('') + '</span>';
  }
  function nextStrip(kv, room, compact) {  // compact: a tall frame at bedtime, the countdown card already shows bedtime
    var items = kv.next.filter(function (x) { return !(compact && x.bedtime); }).slice(0, room);
    if (compact && !items.length) return '';
    var cards = items.map(function (x) {
      var tp = timeParts(x.time);
      return '<div class="knc' + (x.next ? ' next' : '') + (x.now ? ' now' : '') + (x.bedtime ? ' bed' : '') + '">' +
        (x.now ? '<span class="ktag now">Now</span>' : x.next ? '<span class="ktag">Next</span>' : '') +
        bubble(x.picture) + '<div class="knct"><div class="knt">' + esc(tp[0]) + '<span>' + esc(tp[1]) + '</span></div>' +
        '<div class="knti">' + esc(x.title) + '</div>' + kidDots(x.kids) + '</div></div>';
    }).join('');
    if (!items.length) cards = '<p class="knone">' + pic('star', 0, 2) + 'Nothing else on the calendar today</p>';
    return '<section class="knext' + (compact ? ' compact' : '') + '" aria-label="What’s next today"><h2>' + pic('clock', 0, 2.4) + 'What’s next today</h2>' +
      '<div class="kncards" style="grid-template-columns:repeat(' + Math.max(items.length, 1) + ',minmax(0,1fr))">' + cards + '</div></section>';
  }
  function chore(k, c) {
    var st = c.status;
    var badge = st === 'done' ? pic('check', 0, 3) : st === 'waiting' ? pic('clock', 0, 2.6) : '<b>+' + c.minutes + '</b>';
    var said = st === 'done' ? 'done' : st === 'waiting' ? 'waiting for a grown-up' : 'tap when done, ' + c.minutes + ' minutes';
    var inner = '<span class="kcp" style="color:' + (COLOR[c.picture] || COLOR.star) + '">' + pic(c.picture || 'star', 0, 2.2) + '</span>' +
      '<span class="kct">' + esc(c.title) + '</span><span class="kcb">' + badge + '</span>';
    if (st === 'todo') {
      return '<button class="kch todo" data-act="kclaim" data-kid="' + esc(k.id) + '" data-id="' + esc(c.id) + '" aria-label="' +
        esc(c.title + ': ' + said) + '">' + inner + '</button>';
    }
    return '<div class="kch ' + st + '" aria-label="' + esc(c.title + ': ' + said) + '">' + inner + '</div>';
  }
  function progress(k) {
    return '<span class="kprog" aria-label="' + k.done + ' of ' + k.total + ' done">' + k.chores.map(function (c) {
      return '<i class="' + c.status + '"></i>';
    }).join('') + '</span>';
  }
  function kidHead(k, more) {  // tap a kid's name for all of their chores (the Chores screen)
    var left = k.chores.filter(function (c) { return c.status === 'todo'; }).length;
    var sub = !k.total ? 'No chores today' : left ? left + ' to go' : k.waiting_count ? 'All tapped!' : 'All done!';
    return '<button class="kkh" data-act="kid" data-kid="' + esc(k.id) + '" aria-label="All of ' + esc(k.name) + '’s chores">' + H.av(k, 'kx') +
      '<span class="kkn"><b>' + esc(k.name) + '</b><span>' + sub + '</span><span class="kprow">' + progress(k) +
      (more ? '<i class="kmore">+' + more + ' more</i>' : '') + '</span></span></button>';
  }
  function kidColumns(max) {
    var d = H.data();
    return '<section class="kkids cols" style="grid-template-columns:repeat(' + d.kids.length + ',minmax(0,1fr))" aria-label="Chores">' +
      d.kids.map(function (k) {
        var list = k.chores.slice(0, max).map(function (c) { return chore(k, c); }).join('');
        if (!k.chores.length) list = '<p class="knone">' + pic('star', 0, 2) + 'Free day!</p>';
        return '<div class="kkid" style="--kc:' + esc(k.color) + '">' + kidHead(k, Math.max(0, k.chores.length - max)) + '<div class="kchs">' + list + '</div></div>';
      }).join('') + '</section>';
  }
  function kidPicker(max) {  // four or more kids: faces in a row, the picked one's chores below
    var d = H.data(), k = H.kidById(H.selKid());
    var faces = d.kids.map(function (x) {
      return '<button class="kface' + (x.id === k.id ? ' on' : '') + '" data-act="kpick" data-kid="' + esc(x.id) + '" style="--kc:' + esc(x.color) + '">' +
        H.av(x, 'kx') + '<b>' + esc(x.name) + '</b>' + progress(x) + '</button>';
    }).join('');
    var list = k.chores.slice(0, max * 2).map(function (c) { return chore(k, c); }).join('') || '<p class="knone">' + pic('star', 0, 2) + 'Free day!</p>';
    return '<section class="kkids pick" aria-label="Chores"><div class="kfaces">' + faces + '</div>' +
      '<div class="kkid" style="--kc:' + esc(k.color) + '"><div class="kchs two">' + list + '</div></div></section>';
  }
  function screenCard(kv) {
    var d = H.data(), sc = d.screen, v = kv.view, dark = v === 'vault' || v === 'rocket';
    if (!sc) return '';   // Screen time is off (Settings > Modules)
    var who = d.kids.map(function (k) {
      return '<span class="ksw">' + H.av(k, 'kx s') + '<b>+' + esc(H.shortMin(k.earned)) + '</b></span>';
    }).join('');
    var when = sc.weekend ? (sc.day === 'Sat' ? 'Saturday ' + H.shortMin(sc.saturday) : 'Sunday ' + H.shortMin(sc.sunday)) :
      sc.sleeps + (sc.sleeps === 1 ? ' sleep' : ' sleeps') + ' until the weekend';
    return '<section class="kscreen ' + (dark ? 'dark' : 'light') + '"' + (H.shows('screen') ? ' data-act="go" data-to="screen"' : '') +
      ' aria-label="Weekend screen time">' +
      '<svg class="ks-art" viewBox="0 0 470 576" preserveAspectRatio="xMidYMid meet" role="img" aria-label="' + esc(H.shortMin(sc.total)) + '">' +
      H.draw(v, sc, d.kids) + '</svg><div class="ks-info"><small>' + (sc.weekend ? 'Screen time this weekend' : 'Weekend screen time') + '</small>' +
      '<b class="ks-total">' + esc(H.shortMin(sc.total)) + '</b><span class="ks-when">' + pic(sc.weekend ? 'star' : 'moon', 0, 2.2) + esc(when) + '</span>' +
      '<div class="ks-who">' + who + '</div></div></section>';
  }
  function nav() {
    var f = H.frame();
    return '<nav class="knav">' + H.tabs('kids') +
      (f.approvals && (!H.on || H.on('chores')) ? '<button class="kgrown" data-act="open-pin" aria-label="Grown-ups (parent PIN)">' + pic('lock', 0, 2.2) + '<span>' + esc(H.word ? H.word('kids_grownups') : 'Grown-ups') + '</span></button>' : '') + '</nav>';
  }

  // ---------------- the screen ----------------
  function render() {
    var d = H.data(), kv = d.kidsview;
    if (!kv) return '<div class="kv"><p class="knone">Loading…</p></div>';
    var tall = H.tall(), sp = todaySpecial(), bed = bedtimeCard(kv), eve = !!bed;
    var many = d.kids.length > 3, chores = !H.on || H.on('chores');   // Chores off: no chore buttons
    var top = sp ? takeover(sp, kv) : '';
    var rib = sp ? '' : ribbon();
    var html;
    if (tall) {
      var max = (bed || rib || sp) ? 3 : 4;
      html = header(eve) + '<div class="kv-body">' + (bed || '') + (bed ? '' : rib) + (sp ? top : nextStrip(kv, bed ? 3 : 4, !!bed)) +
        (!chores ? '' : many ? kidPicker(max) : kidColumns(max)) + screenCard(kv) + '</div>';
    } else {
      var maxW = 3;
      html = header(eve) + '<div class="kv-body"><div class="kv-left">' + (sp ? top : nextStrip(kv, 5)) +
        (!chores ? '' : many ? kidPicker(maxW) : kidColumns(maxW)) + '</div><div class="kv-right">' + bed + (bed ? '' : rib) + screenCard(kv) + '</div></div>';
    }
    return '<div class="kv' + (eve ? ' eve' : '') + (sp ? ' sp' : '') + '">' + html + nav() + '</div>';
  }
  return { render: render };
};
