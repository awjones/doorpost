/* Open almanac: running heads along the top of each page and page numbers at the foot.
   Decoration only (aria-hidden); the words and buttons of the screen are never touched. Plain ES5. */
(function () {
  var BOOK = { today: 0, chores: 2, screen: 4, lists: 6, calendar: -4, clock: 0 };
  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  var CUM = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
  var seen = { date: '', family: '' };

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  // The family's name and today's date come with each screen (ctx.family, ctx.today: "2026-10-15").
  function learn(ctx) {
    var p = /^(\d{4})-(\d\d)-(\d\d)$/.exec(ctx.today || '');
    if (p) {
      var d = new Date(Date.UTC(+p[1], +p[2] - 1, +p[3]));
      seen.date = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][d.getUTCDay()] + ', ' +
        MONTHS[+p[2] - 1] + ' ' + (+p[3]) + ', ' + p[1];
    }
    if (ctx.family) seen.family = ctx.family;
  }
  function dayOfYear(label) {
    var m = /(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})/.exec(label || '');
    return m ? CUM[MONTHS.indexOf(m[1])] + parseInt(m[2], 10) : 0;
  }
  function put(el, html) { if (el && el._al !== html) { el.innerHTML = html; el._al = html; } }

  FrameLooks.register('almanac', {
    decorate: function (ctx) {
      if (!BOOK.hasOwnProperty(ctx.screen) || !ctx.root) return;
      learn(ctx);
      var family = seen.family || 'Our Family';
      var right = seen.date;
      put(FrameLooks.ensure(ctx.root, 'al-head'),
        '<span class="al-l">' + esc(family + ' Almanack') + '</span><span class="al-r">' + esc(right) + '</span>');
      var n = dayOfYear(seen.date);
      if (n) {
        n += BOOK[ctx.screen];
        if (n % 2) n -= 1;               // a left-hand page is even
        put(FrameLooks.ensure(ctx.root, 'al-folio'),
          '<span class="al-l">– ' + n + ' –</span><span class="al-r">– ' + (n + 1) + ' –</span>');
      }
    }
  });
})();
