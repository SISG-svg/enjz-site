/* ENJZ — the opening curtain, the rotating hero, the works strip, reveals
   on scroll, and the header hairline. Everything here is an enhancement:
   with the script absent the page is still complete and readable. */
(function () {
  'use strict';
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* --- opening curtain -------------------------------------------
     The curtain dismisses itself in CSS, so this only adds skipping. */
  var splash = document.getElementById('splash');
  if (splash) {
    var drop = function () {
      splash.style.transition = 'opacity .6s cubic-bezier(.16,1,.3,1), transform .6s cubic-bezier(.16,1,.3,1)';
      splash.style.opacity = '0';
      splash.style.transform = 'scale(1.03)';
      setTimeout(function () {
        splash.style.display = 'none';
        document.body.style.overflow = 'visible';
      }, 600);
    };
    splash.addEventListener('click', drop);
    document.addEventListener('keydown', function onKey(e) {
      if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
        drop(); document.removeEventListener('keydown', onKey);
      }
    });
    // Belt and braces: if the CSS animation never ran, clear it anyway.
    setTimeout(function () {
      if (splash.style.display !== 'none') {
        splash.style.display = 'none';
        document.body.style.overflow = 'visible';
      }
    }, 6400);
  }

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
  if (hero) {
    var slides = hero.querySelectorAll('.slide');
    var texts = hero.querySelectorAll('.htext');
    var dots = hero.querySelectorAll('.dots button');
    var prev = hero.querySelector('.hero-prev');
    var next = hero.querySelector('.hero-next');

    if (slides.length > 1) {
      var i = 0, timer = null, HOLD = 6800;

      var paint = function (n) {
        var s = slides[n];
        ['accent', 'deep', 'glow', 'tint', 'tintish'].forEach(function (k) {
          var v = s.getAttribute('data-' + k);
          if (v) document.documentElement.style.setProperty('--' + k, v);
        });
      };

      var show = function (n) {
        i = (n + slides.length) % slides.length;
        slides.forEach(function (s, k) { s.classList.toggle('is-on', k === i); });
        texts.forEach(function (t, k) { t.classList.toggle('is-on', k === i); });
        dots.forEach(function (d, k) { d.setAttribute('aria-current', k === i ? 'true' : 'false'); });
        paint(i);
      };

      var stop = function () { if (timer) { clearInterval(timer); timer = null; } };
      var play = function () {
        if (calm) return;
        stop();
        timer = setInterval(function () { show(i + 1); }, HOLD);
      };

      dots.forEach(function (d, k) {
        d.addEventListener('click', function () { show(k); play(); });
      });
      if (prev) prev.addEventListener('click', function () { show(i - 1); play(); });
      if (next) next.addEventListener('click', function () { show(i + 1); play(); });

      hero.addEventListener('mouseenter', stop);
      hero.addEventListener('mouseleave', play);
      hero.addEventListener('focusin', stop);
      document.addEventListener('visibilitychange', function () {
        if (document.hidden) { stop(); } else { play(); }
      });

      show(0);
      play();
    }
  }

  /* --- works strip ------------------------------------------------
     A real scroller, so it can be swiped, dragged and stepped through.
     The automatic drift is just a small nudge to scrollLeft each frame. */
  var wrap = document.querySelector('.strip-wrap');
  var strip = wrap && wrap.querySelector('.strip');
  if (strip) {
    // Browsers truncate a fractional scrollLeft, so sub-pixel nudges round
    // away to nothing. Carry the remainder and move whole pixels, paced by
    // elapsed time so the speed is the same on a 60Hz and a 120Hz screen.
    var PPS = 55, running = !calm, raf = null, half = 0, carry = 0, last = 0;

    var measure = function () { half = strip.scrollWidth / 2; };
    measure();
    addEventListener('resize', measure);

    // The track is the catalogue twice over, so passing the halfway mark
    // can jump back silently. Only the forward case belongs here: at rest
    // scrollLeft is 0, and wrapping that forward each frame would fight
    // the drift and the strip would never move.
    var wrapRound = function () {
      if (half && strip.scrollLeft >= half) strip.scrollLeft -= half;
    };

    var tick = function (ts) {
      if (!last) last = ts;
      var dt = Math.min(ts - last, 100);
      last = ts;
      if (running) {
        carry += PPS * dt / 1000;
        var whole = Math.floor(carry);
        if (whole) { carry -= whole; strip.scrollLeft += whole; wrapRound(); }
      }
      raf = requestAnimationFrame(tick);
    };

    var setRunning = function (on) {
      running = on;
      last = 0; carry = 0;
      wrap.classList.toggle('paused', !on);
      var b = wrap.querySelector('.strip-play');
      if (b) b.setAttribute('aria-label', on ? 'Pause the strip' : 'Play the strip');
    };

    var step = function (dir) {
      var card = strip.querySelector('a');
      var by = card ? card.getBoundingClientRect().width + 19 : 240;
      setRunning(false);
      // Stepping back from the start jumps a lap forward first, so the
      // strip runs backwards without stopping at the beginning.
      if (dir < 0 && half && strip.scrollLeft - by < 0) strip.scrollLeft += half;
      strip.scrollBy({ left: dir * by, behavior: calm ? 'auto' : 'smooth' });
      setTimeout(wrapRound, calm ? 0 : 420);
    };

    var back = wrap.querySelector('.strip-back');
    var fwd = wrap.querySelector('.strip-fwd');
    var playBtn = wrap.querySelector('.strip-play');
    if (back) back.addEventListener('click', function () { step(-1); });
    if (fwd) fwd.addEventListener('click', function () { step(1); });
    if (playBtn) playBtn.addEventListener('click', function () { setRunning(!running); });

    // Hovering or touching pauses; leaving resumes, unless it was paused
    // deliberately with the button.
    var held = false;
    strip.addEventListener('mouseenter', function () { if (running) { held = true; setRunning(false); } });
    strip.addEventListener('mouseleave', function () { if (held) { held = false; setRunning(true); } });
    strip.addEventListener('touchstart', function () { setRunning(false); }, { passive: true });
    strip.addEventListener('focusin', function () { setRunning(false); });

    document.addEventListener('visibilitychange', function () {
      if (document.hidden) { if (raf) { cancelAnimationFrame(raf); raf = null; } }
      else if (!raf) { last = 0; raf = requestAnimationFrame(tick); }
    });

    setRunning(running);
    raf = requestAnimationFrame(tick);
  }
})();
