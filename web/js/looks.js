/* FrameLooks: what a look (themes/<id>/) can do on the frame beyond its CSS. See docs/themes.md.
   Loaded before /themes.js (each look's theme.js) and app.js. Chrome 106 safe, plain ES5.

   A look's theme.js calls:
     FrameLooks.register('harbor', {
       derive: function (options) { return { '--harbor-tint': FrameLooks.tones(options.seed)[90] }; },
       decorate: function (ctx) { ... }   // ctx: {screen, root, layout: 'wide'|'tall', kids: bool, options, look}
     });
   app.js calls FrameLooks.apply(frame) when the frame's look or options change, FrameLooks.after(ctx) after
   every screen is drawn, and FrameLooks.host(...) once, so the photo behind the screens can follow the slideshow. */
(function () {
  'use strict';
  var looks = {}, cur = { id: '', options: {}, set: [], attrs: [], frame: null }, host = null;

  function warn(id, e) { try { if (window.console) console.warn('look ' + id, e); } catch (x) { /* nothing */ } }
  function dash(name) { return String(name).replace(/_/g, '-'); }

  // ---------------- colors: plain HSL math (Chrome 106 has no CSS color mixing) ----------------
  function hexToRgb(hex) {
    var m = /^#?([0-9a-f]{6})$/i.exec(String(hex || ''));
    if (!m) return null;
    var n = parseInt(m[1], 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function rgbToHex(r, g, b) {
    function h(v) { v = Math.max(0, Math.min(255, Math.round(v))); return (v < 16 ? '0' : '') + v.toString(16); }
    return ('#' + h(r) + h(g) + h(b)).toUpperCase();
  }
  function toHsl(hex) {
    var c = hexToRgb(hex) || [22, 50, 79], r = c[0] / 255, g = c[1] / 255, b = c[2] / 255;
    var mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, h = 0, s = 0, d = mx - mn;
    if (d) {
      s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
      h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
      h *= 60;
    }
    return [h, s, l];
  }
  function fromHsl(h, s, l) {
    h = ((h % 360) + 360) % 360; s = Math.max(0, Math.min(1, s)); l = Math.max(0, Math.min(1, l));
    var q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
    function f(t) {
      t = (t + 1) % 1;
      return t < 1 / 6 ? p + (q - p) * 6 * t : t < 0.5 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p;
    }
    return rgbToHex(f(h / 360 + 1 / 3) * 255, f(h / 360) * 255, f(h / 360 - 1 / 3) * 255);
  }
  // A tonal scale from one color, like Material's: tones[0] is black, tones[100] white, tones[40] about the seed's
  // own strength. Keys 0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 98, 99, 100.
  function tones(hex, chroma) {
    var hsl = toHsl(hex), out = {}, keys = [0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 98, 99, 100];
    var s = chroma == null ? hsl[1] : chroma;
    for (var i = 0; i < keys.length; i++) {
      var t = keys[i], sat = s * (t > 90 ? 0.6 : t < 10 ? 0.8 : 1);   // very light and very dark tones calm down
      out[t] = fromHsl(hsl[0], sat, t / 100);
    }
    return out;
  }
  // Mix two colors (w: 0 is a, 1 is b) and add transparency; for what newer CSS color mixing would do.
  function mix(a, b, w) {
    var x = hexToRgb(a) || [0, 0, 0], y = hexToRgb(b) || [0, 0, 0];
    return rgbToHex(x[0] + (y[0] - x[0]) * w, x[1] + (y[1] - x[1]) * w, x[2] + (y[2] - x[2]) * w);
  }
  function rgba(hex, alpha) { var c = hexToRgb(hex) || [0, 0, 0]; return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + alpha + ')'; }
  function shift(hex, dh, ds, dl) { var c = toHsl(hex); return fromHsl(c[0] + (dh || 0), c[1] + (ds || 0), c[2] + (dl || 0)); }

  // ---------------- Match the look, from a look's script (the same math as app/artcolor.py remap) ----------------
  function lin(c) { return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
  function gam(c) { return c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055; }
  function oklch(hex) {
    var c = hexToRgb(hex) || [0, 0, 0], r = lin(c[0] / 255), g = lin(c[1] / 255), b = lin(c[2] / 255);
    var l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b), m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b),
      s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    var L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
      B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s;
    return [L, Math.sqrt(A * A + B * B), ((Math.atan2(B, A) * 180 / Math.PI) + 360) % 360];
  }
  function fromOklch(L, C, H) {
    L = Math.max(0, Math.min(1, L)); C = Math.max(0, C);
    var rgb, i;
    for (i = 0; i < 40; i++) {
      var a = C * Math.cos(H * Math.PI / 180), b = C * Math.sin(H * Math.PI / 180);
      var l = Math.pow(L + 0.3963377774 * a + 0.2158037573 * b, 3), m = Math.pow(L - 0.1055613458 * a - 0.0638541728 * b, 3),
        s = Math.pow(L - 0.0894841775 * a - 1.2914855480 * b, 3);
      rgb = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s];
      if (rgb.every(function (x) { return x >= -1e-4 && x <= 1 + 1e-4; })) break;
      C *= 0.92;
    }
    return rgbToHex(gam(Math.max(0, Math.min(1, rgb[0]))) * 255, gam(Math.max(0, Math.min(1, rgb[1]))) * 255, gam(Math.max(0, Math.min(1, rgb[2]))) * 255);
  }
  // A drawn color moved to a look's color for its family, keeping its shade (app/artcolor.py remap).
  function remap(hex, fam, target) {
    var anchor = (FL.artAnchors || {})[fam];
    if (!anchor) return target;
    if (hex.toUpperCase() === anchor.toUpperCase()) return target.toUpperCase();
    var c = oklch(hex), a = oklch(anchor), t = oklch(target);
    var nL = t[0] + (c[0] - a[0]) * 0.7, nC = t[1] * Math.max(0.55, Math.min(1.4, a[1] > 0.01 ? c[1] / a[1] : 1));
    if (fam === 'paper' && c[0] > 0.99) nL = Math.max(nL, Math.min(1, t[0] + 0.03));
    return fromOklch(nL, nC, t[2]);
  }
  // {--art-C9A55A: color, ...} for every drawn color in the families a look's derive() returned as {art: {gold: '#hex'}}.
  function artVars(art) {
    var out = {}, fams = FL.artFamilies || {};
    Object.keys(fams).forEach(function (h) {
      var f = fams[h], to = art[f];
      if (to && /^#[0-9A-Fa-f]{6}$/.test(to)) out['--art-' + h] = remap('#' + h, f, to);
    });
    return out;
  }

  // ---------------- options -> CSS variables and attributes on body ----------------
  function apply(frame) {
    frame = frame || {};
    var body = document.body, id = frame.look || '', opts = frame.look_options || {}, i;
    for (i = 0; i < cur.set.length; i++) body.style.removeProperty(cur.set[i]);
    for (i = 0; i < cur.attrs.length; i++) body.removeAttribute(cur.attrs[i]);
    cur = { id: id, options: opts, set: [], attrs: [], frame: frame };
    function setVar(k, v) {
      if (k.indexOf('--') !== 0 || v == null) return;
      body.style.setProperty(k, String(v)); cur.set.push(k);
    }
    Object.keys(opts).forEach(function (k) {
      var v = opts[k], a = 'data-opt-' + dash(k);
      if (typeof v === 'boolean') { body.setAttribute(a, v ? '1' : '0'); cur.attrs.push(a); setVar('--opt-' + dash(k), v ? 1 : 0); }
      else if (typeof v === 'number') setVar('--opt-' + dash(k), v);
      else if (/^#[0-9A-Fa-f]{6}$/.test(v)) setVar('--opt-' + dash(k), v);
      else { body.setAttribute(a, String(v)); cur.attrs.push(a); }
    });
    var extra = derive(id, opts, frame);
    Object.keys(extra).forEach(function (k) { setVar(k, extra[k]); });
    // derive() may return art: {family: color} to recolor pictures on a frame set to Match the look.
    if (extra.art && typeof extra.art === 'object' && frame.pictures === 'match') {
      var av = artVars(extra.art);
      Object.keys(av).forEach(function (k) { setVar(k, av[k]); });
    }
    body.classList.toggle('mono-initial', frame.look_monogram === 'initial');
    body.classList.toggle('look-photo', frame.look_background === 'photo');
    body.classList.toggle('look-for-kids', !!frame.look_kids);
    background();
  }

  // What a look's derive() returns for these options ({} when it has none or it fails). Settings uses it for readouts.
  function derive(id, opts, frame) {
    var L = looks[id];
    if (!L || !L.derive) return {};
    try { return L.derive(opts || {}, frame || {}) || {}; } catch (e) { warn(id, e); return {}; }
  }

  function after(ctx) {
    var L = looks[cur.id];
    if (!L || !L.decorate || !ctx || !ctx.root) return;
    ctx.options = cur.options; ctx.look = cur.id;
    try { L.decorate(ctx); } catch (e) { warn(cur.id, e); }
  }

  // Add a decorative element once (it stays put through re-renders that keep it). Returns it.
  function ensure(parent, cls, tag) {
    if (!parent) return null;
    for (var i = 0; i < parent.children.length; i++) if (parent.children[i].classList.contains(cls)) return parent.children[i];
    var el = document.createElement(tag || 'div');
    el.className = cls; el.setAttribute('aria-hidden', 'true');
    parent.appendChild(el);
    return el;
  }

  // ---------------- the photo behind every screen ----------------
  // host: { photos(): [{id, v}], index(): number, url(photo): string, seconds(): number }, from app.js.
  var bg = { el: null, layer: 0, shown: '', timer: null, idx: 0 };
  function bgEl() {
    if (bg.el) return bg.el;
    var stage = document.getElementById('stage');
    if (!stage) return null;
    bg.el = document.createElement('div');
    bg.el.id = 'look-bg'; bg.el.setAttribute('aria-hidden', 'true');
    bg.el.innerHTML = '<img alt=""><img alt="">';
    stage.insertBefore(bg.el, stage.firstChild);
    return bg.el;
  }
  function pickPhoto() {
    if (!host) return null;
    var list = host.photos() || [];
    if (!list.length) return null;
    var mode = cur.options.background || 'slideshow';
    if (mode === 'favorite') {   // the same photo all day: today's pick
      var day = Math.floor(Date.now() / 86400000);
      return list[day % list.length];
    }
    if (mode === 'one') return list[0];
    var i = host.index();
    return list[(i < 0 ? 0 : i) % list.length];
  }
  function background() {
    var on = cur.frame && cur.frame.look_background === 'photo';
    if (!on) { if (bg.timer) { clearInterval(bg.timer); bg.timer = null; } return; }
    var el = bgEl();
    if (!el) return;
    if (!bg.timer && host) bg.timer = setInterval(tickBg, Math.max(5, host.seconds() || 20) * 1000);
    var ph = pickPhoto();
    if (!ph || !host) return;
    var src = host.url(ph);
    if (src === bg.shown) return;
    bg.shown = src;
    var imgs = el.getElementsByTagName('img'), show = imgs[bg.layer], hide = imgs[1 - bg.layer];
    show.onload = function () { show.classList.add('on'); hide.classList.remove('on'); bg.layer = 1 - bg.layer; };
    show.onerror = function () { bg.shown = ''; };
    show.src = src;
  }
  // Off the Photos screen the slideshow doesn't move, so the background moves it along itself (same order).
  function tickBg() {
    if (!host || !cur.frame || cur.frame.look_background !== 'photo') return;
    if ((cur.options.background || 'slideshow') === 'slideshow' && host.advance) host.advance();
    background();
  }

  var FL = window.FrameLooks = {
    register: function (id, hooks) { looks[id] = hooks || {}; if (cur.id === id && cur.frame) apply(cur.frame); },
    apply: apply, after: after, ensure: ensure, photoChanged: background,
    host: function (h) { host = h; background(); },
    current: function () { return { id: cur.id, options: cur.options }; },
    derive: derive, artVars: artVars, remap: remap, oklch: oklch,
    tones: tones, mix: mix, rgba: rgba, shift: shift, hexToRgb: hexToRgb, toHsl: toHsl, fromHsl: fromHsl
  };
})();
