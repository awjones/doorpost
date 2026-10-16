/* Settings > Frames: the options a look offers (theme.json "options"), shown under the chosen look.
   LookOptions.html(look, values) draws them; LookOptions.read(el) reads them back. See docs/themes.md. */
(function () {
  'use strict';
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  var css = '.lopts{display:grid;gap:14px;margin:6px 0 4px;padding:14px 16px;border:1px solid var(--line,#ddd);border-radius:12px}' +
    '.lopt{display:grid;gap:6px;min-width:0}.lopt>b{font-weight:600}' +
    '.lopt .help{margin:0;white-space:normal;overflow:visible;text-overflow:clip;overflow-wrap:anywhere;max-width:62ch}' +
    '.lopt-ro{display:flex;flex-wrap:wrap;gap:6px 18px;margin:0;font-size:13px}.lopt-ro div{display:flex;gap:6px;align-items:center;min-width:0}' +
    '.lopt-ro dt{font-weight:700;opacity:.75}.lopt-ro dd{margin:0;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}' +
    '.lopt-ro i{display:inline-block;width:14px;height:14px;border-radius:4px;box-shadow:0 0 0 1px rgba(0,0,0,.25)}' +
    '.lopt-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px}.lopt input[type=range]{flex:1;min-width:160px}' +
    '.lopt .chip{border:1px solid var(--line,#ccc);background:transparent;border-radius:999px;padding:4px 12px;cursor:pointer;font:inherit}' +
    '.lopt .chip.on{background:var(--ink,#222);color:var(--a-card,#fff);border-color:var(--ink,#222)}' +
    '.lopt .sw{width:28px;height:28px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,.25);cursor:pointer;padding:0}' +
    '.lopt .sw.on{box-shadow:0 0 0 3px var(--ink,#222)}.lopt input[type=color]{width:44px;height:32px;padding:0;border:0;background:none}' +
    '.lopt output{min-width:3ch;text-align:right;font-variant-numeric:tabular-nums}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  function one(o, v) {
    var head = '<b>' + esc(o.label) + '</b>' + (o.help ? '<p class="help">' + esc(o.help) + '</p>' : '');
    var n = esc(o.name);
    if (o.type === 'range') {
      var chips = (o.presets || []).map(function (p) {
        return '<button type="button" class="chip' + (p[1] === v ? ' on' : '') + '" data-lo-preset="' + p[1] + '">' + esc(p[0]) + '</button>';
      }).join('');
      return head + (chips ? '<div class="lopt-row">' + chips + '</div>' : '') + '<div class="lopt-row"><input type="range" data-lo="' + n + '" data-lot="range" min="' + o.min +
        '" max="' + o.max + '" step="' + (o.step || 1) + '" value="' + v + '" aria-label="' + esc(o.label) + '"><output>' + v + '</output></div>' +
        (o.preview === 'readouts' && (o.readouts || []).length ? '<dl class="lopt-ro" aria-live="polite">' + o.readouts.map(function (r) {
          return '<div><dt>' + esc(r[0]) + '</dt><dd data-ro-var="' + esc(r[1]) + '"></dd></div>';
        }).join('') + '</dl>' : '');
    }
    if (o.type === 'color') {
      var sws = (o.swatches || []).map(function (c) {
        return '<button type="button" class="sw' + (c.toUpperCase() === String(v).toUpperCase() ? ' on' : '') + '" style="background:' + esc(c) + '" data-lo-swatch="' + esc(c) +
          '" aria-label="' + esc(c) + '"></button>';
      }).join('');
      return head + '<div class="lopt-row">' + sws + '<input type="color" data-lo="' + n + '" data-lot="color" value="' + esc(v) + '" aria-label="' + esc(o.label) + ': any color"></div>';
    }
    if (o.type === 'bool') {
      return '<label class="check"><input type="checkbox" data-lo="' + n + '" data-lot="bool"' + (v ? ' checked' : '') + '> ' + esc(o.label) + '</label>' +
        (o.help ? '<p class="help">' + esc(o.help) + '</p>' : '');
    }
    return head + '<select data-lo="' + n + '" data-lot="choice" aria-label="' + esc(o.label) + '">' + (o.choices || []).map(function (c) {
      return '<option value="' + esc(c[0]) + '"' + (c[0] === v ? ' selected' : '') + '>' + esc(c[1]) + '</option>';
    }).join('') + '</select>';
  }

  // look: one entry of /api/admin/frames "looks"; values: this frame's saved values for it (may be empty).
  function html(look, values) {
    if (!look || !look.options || !look.options.length) return '';
    values = values || {};
    return '<h3 class="kick">' + esc(look.name) + ' options</h3><div class="lopts" data-lopts="' + esc(look.key) + '">' + look.options.map(function (o) {
      var v = values.hasOwnProperty(o.name) ? values[o.name] : o.default;
      return '<div class="lopt">' + one(o, v) + '</div>';
    }).join('') + '</div>';
  }

  // Readouts (theme.json "preview": "readouts"): what the look's theme.js works out from these settings, labeled,
  // so a parent sees what a slider does before saving. Needs looks.js and /themes.js on the page.
  function shortValue(v) {
    v = String(v == null ? '' : v).trim();
    return v.length > 48 ? v.slice(0, 46) + '…' : v;
  }
  function refreshReadouts(box) {
    if (!box || !window.FrameLooks || !FrameLooks.derive) return;
    var cells = box.querySelectorAll('[data-ro-var]');
    if (!cells.length) return;
    var vals = {};
    Array.prototype.forEach.call(box.querySelectorAll('[data-lo]'), function (inp) {
      var t = inp.getAttribute('data-lot');
      vals[inp.getAttribute('data-lo')] = t === 'range' ? +inp.value : t === 'bool' ? inp.checked : inp.value;
    });
    var out = FrameLooks.derive(box.getAttribute('data-lopts'), vals, {});
    Array.prototype.forEach.call(cells, function (c) {
      var v = out[c.getAttribute('data-ro-var')];
      var h = (/^#[0-9A-Fa-f]{6}$/.test(String(v)) ? '<i style="background:' + esc(v) + '"></i>' : '') + esc(v == null ? '–' : shortValue(v));
      if (c._h !== h) { c._h = h; c.innerHTML = h; }   // only when it changed (the page watches itself for new options)
    });
  }
  function refreshAll() { Array.prototype.forEach.call(document.querySelectorAll('[data-lopts]'), refreshReadouts); }
  if (window.MutationObserver) new MutationObserver(function () { refreshAll(); }).observe(document.documentElement, { childList: true, subtree: true });

  // {look id, values} from the options shown inside el, or null when there are none.
  function read(el) {
    var box = el && el.querySelector('[data-lopts]');
    if (!box) return null;
    var vals = {};
    Array.prototype.forEach.call(box.querySelectorAll('[data-lo]'), function (inp) {
      var t = inp.getAttribute('data-lot'), k = inp.getAttribute('data-lo');
      vals[k] = t === 'range' ? +inp.value : t === 'bool' ? inp.checked : t === 'color' ? inp.value.toUpperCase() : inp.value;
    });
    return { look: box.getAttribute('data-lopts'), values: vals };
  }

  // Preset chips and swatches set the slider or color; the slider shows its number as it moves.
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('[data-lo-preset], [data-lo-swatch]');
    if (!b) return;
    var row = b.closest('.lopt'), inp = row.querySelector('[data-lo]');
    if (b.hasAttribute('data-lo-preset')) { inp.value = b.getAttribute('data-lo-preset'); row.querySelector('output').textContent = inp.value; }
    else inp.value = b.getAttribute('data-lo-swatch');
    Array.prototype.forEach.call(row.querySelectorAll('.chip, .sw'), function (x) { x.classList.toggle('on', x === b); });
    refreshReadouts(b.closest('[data-lopts]'));
  });
  document.addEventListener('input', function (ev) {
    var inp = ev.target;
    if (!inp.getAttribute || inp.getAttribute('data-lot') !== 'range') return;
    var row = inp.closest('.lopt');
    row.querySelector('output').textContent = inp.value;
    Array.prototype.forEach.call(row.querySelectorAll('.chip'), function (x) { x.classList.toggle('on', x.getAttribute('data-lo-preset') === inp.value); });
    refreshReadouts(inp.closest('[data-lopts]'));
  });
  document.addEventListener('change', function (ev) {
    var box = ev.target && ev.target.closest && ev.target.closest('[data-lopts]');
    if (box) refreshReadouts(box);
  });

  window.LookOptions = { html: html, read: read, refresh: refreshAll };
})();
