/* Glass View: glass panels over the family photo. The Glass option (frost, 0 to 100) sets how much the panels
   blur and tint the photo, and which way the text goes: dark text on white glass when frosted, white text with a
   soft shadow over a dark scrim when clear. Pop-ups (PIN, special day, keyboard) never go below about 50.
   "Reduce glass effects" swaps the blur for a plain see-through fill, for a slow frame. Plain ES5 (Chrome 106). */
FrameLooks.register('glass', {
  derive: function (options) {
    var ACC = [31, 106, 224];   // the glass blue: buttons, the picked tab, links
    var f = Number(options.frost);
    if (!isFinite(f)) f = 60;
    f = Math.max(0, Math.min(100, f));
    var reduce = !!options.reduce_effects;

    function n(x) { return Math.round(x * 1000) / 1000; }
    function acc(a) { return 'rgba(' + ACC.join(', ') + ', ' + a + ')'; }
    function lift(t) {   // the accent toward white, for accent text on dark glass
      return 'rgb(' + Math.round(ACC[0] + (255 - ACC[0]) * t) + ', ' + Math.round(ACC[1] + (255 - ACC[1]) * t) + ', ' +
        Math.round(ACC[2] + (255 - ACC[2]) * t) + ')';
    }

    // One set of glass values for a frost level (0 to 100). Same curve as the approved boards.
    function glass(frost) {
      var g = frost / 100, light = g >= 0.42;
      var blurPx = n(2 + 38 * Math.pow(g, 1.15));
      var tint, t, s;
      if (light) {
        t = (g - 0.42) / 0.58;
        tint = 'rgba(255, 255, 255, ' + n(reduce ? 0.86 : 0.40 + 0.42 * t) + ')';
      } else {
        s = 1 - g / 0.42;
        tint = reduce ? 'rgba(16, 20, 30, 0.74)' :
          'linear-gradient(rgba(10, 14, 24, ' + n(0.20 + 0.16 * s) + '), rgba(10, 14, 24, ' + n(0.26 + 0.16 * s) + ')), rgba(255, 255, 255, 0.03)';
      }
      // a soft sheen: brighter top-left, a little bright bottom-right (the glass edge catching light)
      var sheen = 'linear-gradient(135deg, rgba(255, 255, 255, ' + (light ? 0.38 : 0.24) + ') 0%, rgba(255, 255, 255, 0) 34%, ' +
        'rgba(255, 255, 255, 0) 66%, rgba(255, 255, 255, ' + (light ? 0.16 : 0.12) + ') 100%)';
      var drop = n(0.16 + 0.10 * (1 - g));
      return {
        light: light,
        glass: sheen + ', ' + tint,
        blur: reduce ? 'none' : 'blur(' + Math.round(blurPx) + 'px) saturate(' + Math.round(125 + 55 * g) + '%)',
        edge: light ? 'rgba(255, 255, 255, 0.58)' : 'rgba(255, 255, 255, 0.34)',
        shadow: 'inset 1.5px 1.5px 0 rgba(255, 255, 255, ' + (light ? 0.9 : 0.75) + '), inset -1px -1px 0 rgba(255, 255, 255, ' +
          (light ? 0.3 : 0.22) + '), inset 0 0 22px rgba(255, 255, 255, ' + (light ? 0.28 : 0.14) + '), 0 1px 2px rgba(0, 0, 0, 0.10), ' +
          '0 14px 34px rgba(10, 8, 20, ' + drop + ')',
        tshadow: light ? 'none' : '0 1px 2px rgba(0, 0, 0, 0.45)',
        ink: light ? '#15171C' : '#FFFFFF',
        ink2: light ? '#3B3F48' : 'rgba(255, 255, 255, 0.88)',
        ink3: light ? '#545964' : 'rgba(255, 255, 255, 0.72)',
        line: light ? 'rgba(25, 30, 40, 0.14)' : 'rgba(255, 255, 255, 0.24)',
        fill: light ? 'rgba(255, 255, 255, 0.42)' : 'rgba(255, 255, 255, 0.14)',
        sub: light ? 'rgba(255, 255, 255, ' + n(0.46 + 0.2 * g) + ')' : 'rgba(255, 255, 255, 0.12)',
        subShadow: light ? 'inset 1px 1px 0 rgba(255, 255, 255, 0.8), inset 0 0 0 1px rgba(255, 255, 255, 0.35)' :
          'inset 1px 1px 0 rgba(255, 255, 255, 0.4), inset 0 0 0 1px rgba(255, 255, 255, 0.14)',
        ring: light ? 'rgba(25, 30, 40, 0.34)' : 'rgba(255, 255, 255, 0.6)',
        segOn: light ? 'rgba(255, 255, 255, 0.92)' : 'rgba(255, 255, 255, 0.30)',
        segShadow: light ? 'inset 1px 1px 0 #FFFFFF, 0 1px 3px rgba(0, 0, 0, 0.14)' : 'inset 1px 1px 0 rgba(255, 255, 255, 0.55), 0 1px 3px rgba(0, 0, 0, 0.2)',
        green: light ? '#0F6B3B' : '#93F2BA',
        greenBg: light ? 'rgba(52, 168, 83, 0.22)' : 'rgba(70, 210, 120, 0.24)',
        amber: light ? '#6B4500' : '#FFDA8F',
        amberBg: light ? 'rgba(255, 186, 0, 0.30)' : 'rgba(255, 190, 40, 0.26)',
        red: light ? '#C42B30' : '#FFB3B5',
        acct: light ? '#1A5BC4' : lift(0.6),
        accTint: light ? acc(0.16) : 'rgba(' + Math.round(ACC[0] + (255 - ACC[0]) * 0.5) + ', ' + Math.round(ACC[1] + (255 - ACC[1]) * 0.5) + ', ' +
          Math.round(ACC[2] + (255 - ACC[2]) * 0.5) + ', 0.24)',
        accBtn: 'linear-gradient(180deg, rgba(255, 255, 255, 0.34) 0%, rgba(255, 255, 255, 0.06) 52%, rgba(255, 255, 255, 0) 100%), ' +
          acc(reduce || light ? 1 : 0.86),
        btnShadow: 'inset 1px 1.5px 0 rgba(255, 255, 255, 0.6), inset 0 -1px 0 rgba(0, 0, 0, 0.14), 0 4px 12px ' + acc(0.30),
        key: light ? 'rgba(255, 255, 255, 0.82)' : 'rgba(255, 255, 255, 0.24)',
        keyMod: light ? 'rgba(255, 255, 255, 0.40)' : 'rgba(255, 255, 255, 0.10)',
        field: light ? 'rgba(255, 255, 255, 0.85)' : 'rgba(255, 255, 255, 0.18)',
        dark: 'linear-gradient(135deg, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0) 40%), rgba(18, 20, 30, ' + n(0.5 + 0.3 * g) + ')'
      };
    }

    var NAMES = ['glass', 'blur', 'edge', 'shadow', 'tshadow', 'ink', 'ink2', 'ink3', 'line', 'fill', 'sub', 'subShadow', 'ring', 'segOn',
      'segShadow', 'green', 'greenBg', 'amber', 'amberBg', 'red', 'acct', 'accTint', 'accBtn', 'btnShadow', 'key', 'keyMod', 'field', 'dark'];
    function vars(g, prefix, out) {
      for (var i = 0; i < NAMES.length; i++) out[prefix + NAMES[i].replace(/([A-Z])/g, '-$1').toLowerCase()] = g[NAMES[i]];
      return out;
    }
    var g = glass(f), p = glass(Math.max(f, 50 + f / 2));   // pop-ups: never below about 50
    var out = vars(p, '--glp-', vars(g, '--gl-', {}));
    // The frame's own color settings (web/css/frame.css), so every rule this look doesn't touch still fits.
    out['--ink'] = g.ink; out['--soft'] = g.ink2; out['--muted'] = g.ink3;
    out['--line'] = g.line; out['--line-soft'] = g.line;
    out['--card'] = g.sub; out['--tile'] = g.sub;
    out['--navy'] = '#1F6AE0'; out['--gilt'] = g.acct; out['--gilt-soft'] = g.ink2; out['--gilt-dim'] = g.ink3;
    out['--red'] = g.red; out['--next-bg'] = g.accTint;
    out['--amber'] = g.amber; out['--amber-bg'] = g.amberBg; out['--green'] = g.green; out['--green-bg'] = g.greenBg;
    out['--gl-mode'] = g.light ? 'light' : 'dark';
    // for Settings' readouts under the Glass slider (theme.json "readouts"), in words (FV-Glass-Settings)
    out['--gl-ro-blur'] = reduce ? 'off' : Math.round(2 + 38 * Math.pow(f / 100, 1.15)) + ' px';
    out['--gl-ro-tint'] = reduce ? (g.light ? 'plain white fill' : 'plain dark fill') :
      (g.light ? 'white, ' + Math.round((0.40 + 0.42 * Math.max(0, (f / 100 - 0.42) / 0.58)) * 100) + '%' : 'clear, soft dark scrim');
    out['--gl-ro-text'] = g.light ? 'dark text' : 'white text, soft shadow';
    // the photo behind: a touch dimmer when the glass is clear and the text is white
    out['--look-photo-dim'] = g.light ? 0.04 : 0.16;
    return out;
  }
});
