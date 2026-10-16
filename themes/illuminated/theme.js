/* Illuminated: ringed initials. Each numeral avatar gets the il-ring class and its kid's color as --il-kc, so
   theme.css can draw it as a parchment circle ringed in that color (faces and "ALL" are left as they are). */
FrameLooks.register('illuminated', {
  decorate: function (ctx) {
    var list = ctx.root.querySelectorAll('.av');
    for (var i = 0; i < list.length; i++) {
      var el = list[i];
      if (el.classList.contains('face') || el.classList.contains('all') || el.classList.contains('il-ring')) continue;
      var c = el.style.backgroundColor;
      if (!c) continue;
      el.style.setProperty('--il-kc', c);
      el.classList.add('il-ring');
    }
  }
});
