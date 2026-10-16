/* Modern: one accent color (the "accent" option) drives the family mark (the typeset initial, theme.json "monogram"), today, what's next and the special days.
   Chrome 106 can't mix colors in CSS, so the tints are worked out here. Plain ES5. */
(function () {
  FrameLooks.register('modern', {
    derive: function (options) {
      var a = options.accent || '#C8102E';
      if (!/^#[0-9a-fA-F]{6}$/.test(a)) a = '#C8102E';
      var L = FrameLooks;
      return {
        '--mo-accent': a,
        '--mo-accent-tint': L.mix(a, '#FFFFFF', 0.9),     // the "next" row, the lock tile on the PIN pad
        '--mo-accent-deep': L.mix(a, '#000000', 0.2),     // accent words on white that need more weight
        '--red': a,
        '--next-bg': L.mix(a, '#FFFFFF', 0.9)
      };
    }
  });
})();
