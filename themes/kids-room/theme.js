/* Kids room: small decorations only (docs/themes.md). Sleeps are counted in moons. The night clock's
   "Time to sleep" and the PIN pad's "Grown-ups only" are the look's words (theme.json "words").
   No words or buttons change; everything added is an empty element. */
FrameLooks.register('kids-room', {
  decorate: function (ctx) {
    var root = ctx.root;
    if (!root) return;

    // A row of moons, one per sleep (up to three), next to a number the screen already shows.
    function moons(parent, before, text) {
      if (!parent) return;
      var m = /(\d+)/.exec(text || ''), n = m ? +m[1] : 0;
      var el = FrameLooks.ensure(parent, 'kr-moons', 'span');
      el.className = 'kr-moons ' + (n > 3 ? 'kr-many' : 'kr-n' + n);
      if (before && el.nextSibling !== before && before.parentNode === parent) parent.insertBefore(el, before);
    }

    // Today: the countdown ribbon ("2 days until ...")
    var rib = root.querySelector('.ribbon:not(.solemn)');
    if (rib) {
      var when = rib.querySelector('.rb-script');
      moons(rib, rib.querySelector('.rb-stars'), when && /until/.test(when.textContent) ? when.textContent : '');
    }
    // Kids home: "2 sleeps until ..." with the big number
    var krib = root.querySelector('.krib');
    if (krib) {
      var kn = krib.querySelector('.krib-n');
      moons(krib, kn, kn ? kn.textContent : '');
    }
    // Screen Time: "2 sleeps / until Saturday"
    var cnt = root.querySelector('.band-right .count');
    if (cnt) {
      var big = cnt.querySelector('.big');
      moons(cnt.parentNode, cnt, big && /sleep/.test(big.textContent) ? big.textContent : '');
    }
  }
});
