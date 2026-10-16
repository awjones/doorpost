/* Mica View: the accent color option drives every tint (Chrome 106 can't mix colors in CSS). */
FrameLooks.register('mica', {
  derive: function (options) {
    var a = /^#[0-9A-Fa-f]{6}$/.test(options.accent || '') ? options.accent.toUpperCase() : '#1F6FC5';
    function lum(hex) {
      var n = parseInt(hex.slice(1), 16), c = [(n >> 16) & 255, (n >> 8) & 255, n & 255], i;
      for (i = 0; i < 3; i++) { c[i] = c[i] / 255; c[i] = c[i] <= 0.03928 ? c[i] / 12.92 : Math.pow((c[i] + 0.055) / 1.055, 2.4); }
      return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    }
    function contrast(x, y) { var p = lum(x), q = lum(y); return (Math.max(p, q) + 0.05) / (Math.min(p, q) + 0.05); }
    // Text in the accent color has to read on the light cards (4.5:1): darken a light pick until it does.
    var ink = a, n = 0;
    while (contrast(ink, '#F4F6F9') < 4.6 && n < 20) { ink = FrameLooks.shift(ink, 0, 0, -0.03); n++; }
    // White text on an accent fill: same check, so a pale pick still gets readable buttons.
    var fill = a; n = 0;
    while (contrast(fill, '#FFFFFF') < 4.5 && n < 20) { fill = FrameLooks.shift(fill, 0, 0, -0.03); n++; }
    return {
      '--mica-accent': fill,
      '--mica-ink': ink,
      '--mica-soft': FrameLooks.rgba(a, 0.12),
      '--mica-line': FrameLooks.rgba(a, 0.35),
      '--mica-faint': FrameLooks.rgba(a, 0.06),
      '--mica-tint': FrameLooks.mix(a, '#FFFFFF', 0.86),
      '--mica-wash': FrameLooks.rgba(FrameLooks.mix(a, '#FFFFFF', 0.62), 0.9),
      '--mica-night': FrameLooks.mix(a, '#000000', 0.82),
      '--navy': ink
    };
  }
});
