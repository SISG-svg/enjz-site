/* ENJZ — three small behaviours: the rotating hero, reveals on scroll,
   and the header hairline once the page has moved. Everything degrades
   to a perfectly readable page with JavaScript off. */
(function () {
  'use strict';
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* --- header hairline ------------------------------------------- */
  var head = document.querySelector('header.site');
  if (head) {
    var onScroll = function () { head.classList.toggle('stuck', window.scrollY > 12); };
    addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* --- reveal on scroll ------------------------------------------ */
  var targets = document.querySelectorAll('.r');
  if (targets.length && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    targets.forEach(function (t) { io.observe(t); });
  } else {
    targets.forEach(function (t) { t.classList.add('in'); });
  }

  /* --- rotating hero --------------------------------------------- */
  var hero = document.getElementById('hero');
  if (!hero) return;
  var slides = hero.querySelectorAll('.slide');
  var texts = hero.querySelectorAll('.htext');
  var dots = hero.querySelectorAll('.dots button');
  if (slides.length < 2) return;

  var i = 0, timer = null, HOLD = 6800;

  function paint(n) {
    var s = slides[n];
    ['accent', 'deep', 'glow', 'tint', 'tintish'].forEach(function (k) {
      var v = s.getAttribute('data-' + k);
      if (v) document.documentElement.style.setProperty('--' + k, v);
    });
  }

  function show(n) {
    i = (n + slides.length) % slides.length;
    slides.forEach(function (s, k) { s.classList.toggle('is-on', k === i); });
    texts.forEach(function (t, k) { t.classList.toggle('is-on', k === i); });
    dots.forEach(function (d, k) { d.setAttribute('aria-current', k === i ? 'true' : 'false'); });
    paint(i);
  }

  function play() { if (!calm) { stop(); timer = setInterval(function () { show(i + 1); }, HOLD); } }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }

  dots.forEach(function (d, k) {
    d.addEventListener('click', function () { show(k); play(); });
  });
  hero.addEventListener('mouseenter', stop);
  hero.addEventListener('mouseleave', play);
  hero.addEventListener('focusin', stop);
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { stop(); } else { play(); }
  });

  show(0);
  play();
})();
