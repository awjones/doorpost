/* Tonal View: one seed color makes the whole scheme (primary, secondary, tertiary, surfaces, outlines and the
   colors that sit on them). A "tone" here is lightness the eye sees (CIE L*, 0 black to 100 white), so text and
   its background are a set number of tones apart for any seed: dark text on tone 88+ and light text on tone 40-
   always clear 4.5:1. Plain ES5 for Chrome 106. FrameLooks.tones() gives the seed's own HSL scale; this look
   searches each tone on real luminance instead, so a yellow or a blue seed come out equally readable. */
(function () {
  var DEF = '#2F7A68';

  function scheme(seed) {
    var hsl = FrameLooks.toHsl(/^#[0-9A-Fa-f]{6}$/.test(seed || '') ? seed : DEF), h = hsl[0], s = hsl[1];
    function rgb(H, S, L) {
      var c = FrameLooks.hexToRgb(FrameLooks.fromHsl(H, S, L));
      return [c[0] / 255, c[1] / 255, c[2] / 255];
    }
    function lin(c) { return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
    function lum(a) { return 0.2126 * lin(a[0]) + 0.7152 * lin(a[1]) + 0.0722 * lin(a[2]); }
    // the HSL lightness whose luminance matches tone Tn (L*), found by halving
    function tone(H, S, Tn) {
      var Y = Tn > 8 ? Math.pow((Tn + 16) / 116, 3) : Tn / 903.3, lo = 0, hi = 1;
      for (var i = 0; i < 22; i++) { var mid = (lo + hi) / 2; if (lum(rgb(H, S, mid)) < Y) lo = mid; else hi = mid; }
      return FrameLooks.fromHsl(H, S, (lo + hi) / 2);
    }
    function harm(H) { var dd = ((h - H + 540) % 360) - 180; return (H + dd * 0.1 + 360) % 360; }
    var ps = Math.max(0.42, Math.min(0.78, s)), th = h + 60;
    return {
      pri: tone(h, ps, 40), priC: tone(h, ps * 0.9, 90), onPriC: tone(h, ps, 10), pri80: tone(h, ps * 0.8, 80), pri30: tone(h, ps, 30),
      secC: tone(h, 0.34, 88), onSecC: tone(h, 0.3, 12),
      ter: tone(th, ps * 0.7, 40), terC: tone(th, ps * 0.8, 90), onTerC: tone(th, ps, 12),
      surf: tone(h, 0.3, 98), sLow: tone(h, 0.28, 96), sCont: tone(h, 0.26, 94), sHigh: tone(h, 0.24, 92), sHighest: tone(h, 0.22, 89),
      on: tone(h, 0.15, 10), onV: tone(h, 0.14, 30), muted: tone(h, 0.12, 40), outl: tone(h, 0.1, 50), outlV: tone(h, 0.16, 80),
      err: tone(4, 0.72, 40), errC: tone(4, 0.75, 90), onErrC: tone(4, 0.7, 14),
      ok: tone(harm(140), 0.45, 34), okC: tone(harm(140), 0.5, 90), onOkC: tone(harm(140), 0.5, 14),
      warnC: tone(40, 0.9, 87), onWarnC: tone(32, 0.8, 22), warn: tone(40, 0.9, 70),
      inv: tone(h, 0.12, 20), onInv: tone(h, 0.15, 95), invC: tone(h, 0.14, 28), onInvV: tone(h, ps * 0.6, 80),
      nBg: tone(h, 0.3, 3), nCard: tone(h, 0.28, 8), nRing: tone(h, ps * 0.6, 22), nPri: tone(h, ps * 0.6, 62),
      nOn: tone(h, 0.15, 56), nOnV: tone(h, 0.12, 42)
    };
  }

  // scheme name -> CSS variable; the app's own variables (frame.css) follow, so every screen picks the tones up
  var VARS = {
    pri: '--tv-pri', priC: '--tv-pri-c', onPriC: '--tv-on-pri-c', pri80: '--tv-pri-80', pri30: '--tv-pri-30',
    secC: '--tv-sec-c', onSecC: '--tv-on-sec-c', ter: '--tv-ter', terC: '--tv-ter-c', onTerC: '--tv-on-ter-c',
    surf: '--tv-surf', sLow: '--tv-s-low', sCont: '--tv-s-cont', sHigh: '--tv-s-high', sHighest: '--tv-s-highest',
    on: '--tv-on', onV: '--tv-on-v', muted: '--tv-muted', outl: '--tv-outl', outlV: '--tv-outl-v',
    err: '--tv-err', errC: '--tv-err-c', onErrC: '--tv-on-err-c', ok: '--tv-ok', okC: '--tv-ok-c', onOkC: '--tv-on-ok-c',
    warnC: '--tv-warn-c', onWarnC: '--tv-on-warn-c', warn: '--tv-warn',
    inv: '--tv-inv', onInv: '--tv-on-inv', invC: '--tv-inv-c', onInvV: '--tv-on-inv-v',
    nBg: '--tv-n-bg', nCard: '--tv-n-card', nRing: '--tv-n-ring', nPri: '--tv-n-pri', nOn: '--tv-n-on', nOnV: '--tv-n-on-v'
  };

  // Who gets which shape: kids in family order (flower, clover, pentagon, then round again), calendars by name.
  var SHAPES = ['flower', 'clover', 'penta', 'sunny', 'squircle', 'arch'];
  var seen = { ids: [], colors: {} };
  function kidShape(i) { return 'tv-sh-' + SHAPES[i % SHAPES.length]; }
  function setShape(el, cls) {
    var c = String(el.className || '');
    if (c.indexOf(cls) >= 0) return;
    el.className = c.replace(/\s*tv-sh-[a-z]+/g, '') + ' ' + cls;
  }
  function colorOf(el) { return (el.style && el.style.backgroundColor) || ''; }

  function shapeKids(root) {
    var i, owners = root.querySelectorAll('[data-kid]');
    for (i = 0; i < owners.length; i++) {
      var id = owners[i].getAttribute('data-kid'), av = owners[i].querySelector('.av');
      if (!id || id === 'all') continue;
      if (seen.ids.indexOf(id) < 0) seen.ids.push(id);
      if (av && colorOf(av)) seen.colors[colorOf(av)] = seen.ids.indexOf(id);
    }
    var avs = root.querySelectorAll('.av');
    for (i = 0; i < avs.length; i++) {
      var a = avs[i];
      if (a.classList.contains('all')) { setShape(a, 'tv-sh-cookie'); continue; }
      var col = colorOf(a), n = seen.colors[col];
      if (n === undefined && col) {   // not seen next to a name yet: next free place
        n = 0;
        for (var k in seen.colors) if (seen.colors.hasOwnProperty(k)) n++;
        seen.colors[col] = n;
      }
      if (n !== undefined) setShape(a, kidShape(n));
    }
  }
  // A light tint of each kid's own color behind their tile or column (the kid colors are the family's, set in Settings).
  function hexOf(c) {
    var m = /rgb\((\d+),\s*(\d+),\s*(\d+)/.exec(c || '');
    if (!m) return /^#[0-9A-Fa-f]{6}$/.test(c || '') ? c : '';
    function h(v) { v = (+v).toString(16); return v.length < 2 ? '0' + v : v; }
    return '#' + h(m[1]) + h(m[2]) + h(m[3]);
  }
  function tint(el, color) {
    var hx = hexOf(color);
    if (hx) el.style.setProperty('--tv-tint', FrameLooks.mix(hx, '#FFFFFF', 0.8));
  }
  function tintKids(root) {
    var i, els = root.querySelectorAll('.kkid, .kface');
    for (i = 0; i < els.length; i++) tint(els[i], (els[i].style.getPropertyValue('--kc') || '').replace(/\s/g, ''));
    els = root.querySelectorAll('.ktile');
    for (i = 0; i < els.length; i++) { var a = els[i].querySelector('.av'); if (a) tint(els[i], colorOf(a)); }
  }
  var CAL_SHAPE = { mom: 'tv-sh-arch', dad: 'tv-sh-squircle', kids: 'tv-sh-flower', family: 'tv-sh-cookie' };
  function shapeLegend(root) {
    var spans = root.querySelectorAll('.legend span');
    for (var i = 0; i < spans.length; i++) {
      var dot = spans[i].querySelector('i'), name = (spans[i].textContent || '').replace(/^\s+|\s+$/g, '').toLowerCase();
      if (dot && CAL_SHAPE[name]) setShape(dot, CAL_SHAPE[name]);
    }
  }

  FrameLooks.register('tonal', {
    derive: function (options) {
      var t = scheme(options.seed), out = {}, k;
      for (k in VARS) if (VARS.hasOwnProperty(k)) out[VARS[k]] = t[k];
      out['--paper'] = t.surf; out['--card'] = t.sLow; out['--tile'] = t.sCont; out['--line'] = t.outlV; out['--line-soft'] = t.sHigh;
      out['--ink'] = t.on; out['--soft'] = t.onV; out['--muted'] = t.muted;
      out['--navy'] = t.pri; out['--gilt'] = t.pri; out['--gilt-soft'] = t.onV; out['--gilt-dim'] = t.pri;
      out['--tv-glass'] = FrameLooks.rgba(t.surf, 0.9);
      out['--red'] = t.err; out['--next-bg'] = t.priC;
      out['--amber'] = t.onWarnC; out['--amber-bg'] = t.warnC; out['--green'] = t.ok; out['--green-bg'] = t.okC;
      // Match the look: the pictures' sky, ink, shadows, paper, greens and blues follow the seed. The default seed keeps
      // the hand-picked palette in theme.json; the warm families (gold, red, orange, brown, pink) always stay as drawn there.
      var seed = String(options.seed || DEF).toUpperCase();
      if (seed !== DEF) out.art = { night: t.inv, navy: t.invC, deep: t.nCard, paper: t.sLow, green: t.pri, sky: FrameLooks.mix(t.ter, '#FFFFFF', 0.55) };
      return out;
    },
    decorate: function (ctx) {
      shapeKids(ctx.root);
      shapeLegend(ctx.root);
      tintKids(ctx.root);
      watchOverlay();
    }
  });
  // Pop-ups (the PIN pad, parent tools) are drawn without a new screen, so shape their faces as they appear.
  var watching = false;
  function watchOverlay() {
    var ov = document.getElementById('overlay');
    if (watching || !ov || !window.MutationObserver) return;
    watching = true;
    new MutationObserver(function () {
      if (FrameLooks.current().id === 'tonal') { shapeKids(ov); shapeLegend(ov); }
    }).observe(ov, { childList: true });
    shapeKids(ov);
  }
  // for tests and the curious: the scheme for a seed
  FrameLooks.tonalScheme = scheme;
})();
