/* ГО «Робимо вам нерви» — поведінка сайту. Без бібліотек; сайт працює й без JavaScript. */
(function () {
  'use strict';
  var d = document, root = d.documentElement;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- шапка й мобільне меню */
  var header = d.querySelector('.site-header'), toggle = d.querySelector('.menu-toggle'), nav = d.getElementById('nav');
  function setMenu(open) {
    if (!toggle) return;
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Закрити меню' : 'Меню');
    nav.classList.toggle('open', open);
    root.classList.toggle('menu-open', open);
  }
  if (toggle) {
    toggle.addEventListener('click', function () { setMenu(toggle.getAttribute('aria-expanded') !== 'true'); });
    nav.addEventListener('click', function (ev) { if (ev.target.closest('a')) setMenu(false); });
    d.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') { setMenu(false); toggle.focus(); }
    });
    window.matchMedia('(min-width: 1041px)').addEventListener('change', function (m) { if (m.matches) setMenu(false); });
  }

  /* ---------- прокручування: тінь шапки, прогрес читання, кнопка «вгору» */
  var progress = d.querySelector('.read-progress'), article = d.querySelector('.post-body'), top = d.querySelector('.to-top');
  function onScroll() {
    var y = window.scrollY;
    if (header) header.classList.toggle('scrolled', y > 8);
    if (progress && article) {
      var r = article.getBoundingClientRect(), total = r.height - window.innerHeight * 0.6;
      var p = Math.min(1, Math.max(0, (-r.top + 80) / (total > 0 ? total : 1)));
      progress.style.transform = 'scaleX(' + p + ')';
    }
    if (top) top.classList.toggle('show', y > window.innerHeight * 1.5);
  }
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
  if (top) top.addEventListener('click', function () {
    window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
    var skip = d.querySelector('.skip'); if (skip) skip.focus({ preventScroll: true });
  });

  /* ---------- зміст статті: підсвічування поточного розділу */
  var toc = d.querySelector('.toc');
  if (toc && 'IntersectionObserver' in window) {
    var links = {}; toc.querySelectorAll('a').forEach(function (a) { links[a.hash.slice(1)] = a; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          toc.querySelectorAll('a.on').forEach(function (a) { a.classList.remove('on'); });
          var a = links[en.target.id]; if (a) a.classList.add('on');
        }
      });
    }, { rootMargin: '-90px 0px -70% 0px' });
    Object.keys(links).forEach(function (id) { var h = d.getElementById(id); if (h) io.observe(h); });
  }

  /* ---------- повідомлення */
  var toastEl;
  function toast(msg) {
    if (!toastEl) { toastEl = d.createElement('div'); toastEl.className = 'toast'; toastEl.setAttribute('role', 'status'); d.body.appendChild(toastEl); }
    toastEl.textContent = msg; toastEl.classList.add('show');
    clearTimeout(toastEl._t); toastEl._t = setTimeout(function () { toastEl.classList.remove('show'); }, 2200);
  }
  function copy(text, msg) {
    var done = function () { toast(msg); };
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function () { window.prompt('Скопіюйте:', text); });
    else window.prompt('Скопіюйте:', text);
  }
  d.querySelectorAll('[data-copy]').forEach(function (b) {
    b.hidden = false;
    b.addEventListener('click', function () { copy(b.getAttribute('data-copy'), b.getAttribute('data-copied') || 'Скопійовано'); });
  });
  d.querySelectorAll('[data-share]').forEach(function (b) {
    if (!navigator.share) return;
    b.hidden = false;
    b.addEventListener('click', function () {
      navigator.share({ title: d.title, url: b.getAttribute('data-share') }).catch(function () {});
    });
  });

  /* ---------- карусель */
  d.querySelectorAll('.carousel').forEach(function (c) {
    var t = c.querySelector('.car-track'), s = t.children, n = c.querySelector('.car-count');
    var prev = c.querySelector('.car-prev'), next = c.querySelector('.car-next');
    function step() { return s[0].getBoundingClientRect().width + parseFloat(getComputedStyle(t).columnGap || 0); }
    function idx() { return Math.min(s.length - 1, Math.round(t.scrollLeft / step())); }
    function upd() {
      n.textContent = (idx() + 1) + ' / ' + s.length;
      prev.disabled = t.scrollLeft < 4;
      next.disabled = t.scrollLeft + t.clientWidth >= t.scrollWidth - 4;
    }
    prev.addEventListener('click', function () { t.scrollBy({ left: -step(), behavior: reduce ? 'auto' : 'smooth' }); });
    next.addEventListener('click', function () { t.scrollBy({ left: step(), behavior: reduce ? 'auto' : 'smooth' }); });
    t.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowRight') { ev.preventDefault(); next.click(); }
      if (ev.key === 'ArrowLeft') { ev.preventDefault(); prev.click(); }
    });
    t.addEventListener('scroll', upd, { passive: true }); upd();
  });

  /* ---------- перегляд світлин на весь екран */
  var zoomable = d.querySelectorAll('.post-body figure img, .car-slide img, .photo-grid img, .arch img, .pair img, .mosaic img');
  if (zoomable.length && window.HTMLDialogElement) {
    var dlg = d.createElement('dialog'); dlg.className = 'lightbox'; dlg.setAttribute('aria-label', 'Перегляд світлини');
    dlg.innerHTML = '<figure><img alt=""><figcaption></figcaption></figure>' +
      '<button type="button" class="lb-close" aria-label="Закрити">×</button>' +
      '<button type="button" class="lb-prev" aria-label="Попередня світлина">‹</button>' +
      '<button type="button" class="lb-next" aria-label="Наступна світлина">›</button><p class="lb-count"></p>';
    d.body.appendChild(dlg);
    var big = dlg.querySelector('img'), cap = dlg.querySelector('figcaption'), cnt = dlg.querySelector('.lb-count');
    var group = [], cur = 0, opener = null;
    function largest(img) {
      var set = (img.getAttribute('srcset') || '').split(',').map(function (x) { var p = x.trim().split(/\s+/); return { u: p[0], w: parseInt(p[1], 10) || 0 }; });
      set.sort(function (a, b) { return b.w - a.w; });
      return set.length && set[0].u ? set[0].u : img.currentSrc || img.src;
    }
    function show(i) {
      cur = (i + group.length) % group.length;
      var im = group[cur];
      big.src = largest(im); big.alt = im.alt || '';
      cap.textContent = im.alt || ''; cap.hidden = !im.alt;
      cnt.textContent = group.length > 1 ? (cur + 1) + ' / ' + group.length : '';
      dlg.classList.toggle('single', group.length < 2);
    }
    zoomable.forEach(function (img) {
      img.classList.add('zoomable'); img.tabIndex = 0; img.setAttribute('role', 'button');
      img.setAttribute('aria-label', 'Збільшити світлину' + (img.alt ? ': ' + img.alt : ''));
      function open() {
        var box = img.closest('.carousel, .post-body, .photo-grid, .archive, .pairs, .mosaic') || d.body;
        group = Array.prototype.filter.call(zoomable, function (x) { return box.contains(x); });
        opener = img; show(group.indexOf(img)); dlg.showModal(); root.classList.add('menu-open');
      }
      img.addEventListener('click', function (ev) { if (!img.closest('a')) { ev.preventDefault(); open(); } });
      img.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); open(); } });
    });
    dlg.querySelector('.lb-close').addEventListener('click', function () { dlg.close(); });
    dlg.querySelector('.lb-prev').addEventListener('click', function () { show(cur - 1); });
    dlg.querySelector('.lb-next').addEventListener('click', function () { show(cur + 1); });
    dlg.addEventListener('click', function (ev) { if (ev.target === dlg) dlg.close(); });
    dlg.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowRight') show(cur + 1);
      if (ev.key === 'ArrowLeft') show(cur - 1);
    });
    dlg.addEventListener('close', function () { root.classList.remove('menu-open'); if (opener) opener.focus(); });
    var sx = null;
    dlg.addEventListener('touchstart', function (ev) { sx = ev.touches[0].clientX; }, { passive: true });
    dlg.addEventListener('touchend', function (ev) {
      if (sx === null) return; var dx = ev.changedTouches[0].clientX - sx; sx = null;
      if (Math.abs(dx) > 50) show(cur + (dx < 0 ? 1 : -1));
    });
  }

  /* ---------- блоґ: рубрики й пошук */
  var filters = d.querySelector('.blog-filters');
  if (filters) {
    filters.hidden = false;
    var chips = filters.querySelectorAll('.chip'), q = filters.querySelector('input[type=search]');
    var cards = d.querySelectorAll('.blog-list .card'), empty = d.querySelector('.blog-empty'), found = filters.querySelector('.blog-found');
    var params = new URLSearchParams(location.search), cat = params.get('rubryka') || '';
    function norm(s) { return (s || '').toLowerCase().replace(/[’'ʼ`]/g, '').replace(/ґ/g, 'г'); }
    function apply() {
      var term = norm(q.value.trim()), shown = 0;
      cards.forEach(function (c) {
        var ok = (!cat || c.getAttribute('data-cat') === cat) && (!term || norm(c.textContent).indexOf(term) > -1);
        c.hidden = !ok; if (ok) shown++;
      });
      chips.forEach(function (ch) { ch.setAttribute('aria-pressed', String(ch.getAttribute('data-cat') === cat)); });
      d.querySelector('.blog-list').classList.toggle('filtered', !!(cat || term));
      empty.hidden = shown > 0;
      found.textContent = (cat || term) ? 'Знайдено: ' + shown : '';
      var u = new URL(location.href);
      if (cat) u.searchParams.set('rubryka', cat); else u.searchParams.delete('rubryka');
      history.replaceState(null, '', u);
    }
    chips.forEach(function (ch) { ch.addEventListener('click', function () { cat = ch.getAttribute('data-cat'); apply(); }); });
    q.addEventListener('input', apply);
    filters.addEventListener('submit', function (ev) { ev.preventDefault(); });
    var reset = d.querySelector('.blog-reset');
    if (reset) reset.addEventListener('click', function () { cat = ''; q.value = ''; apply(); q.focus(); });
    apply();
  }
})();
