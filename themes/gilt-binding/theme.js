FrameLooks.register('gilt-binding', {
  // The spine's crest: screens without a header (Clock & today) get the family monogram at the top of the spine too.
  // An empty element only; theme.css places it. The other screens move their own header monogram there with CSS.
  decorate: function (ctx) {
    if (ctx.screen !== 'clock' || !ctx.root) return;
    var nav = ctx.root.querySelector('.nav');
    if (!nav) return;
    var crest = FrameLooks.ensure(nav, 'gb-crest', 'span');
    crest.classList.add('mono');
    crest.setAttribute('aria-hidden', 'true');
  }
});
