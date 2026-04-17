/**
 * gallery.js
 * Hero slideshow — auto-advances every 5 s, supports dot navigation.
 */

(function () {
  'use strict';

  const INTERVAL_MS = 5000;

  const slides = document.querySelectorAll('.slide');
  const dots   = document.querySelectorAll('.dot');

  if (!slides.length) return;

  let current = 0;
  let timer   = null;

  function goTo(index) {
    slides[current].classList.remove('active');
    dots[current].classList.remove('active');

    current = (index + slides.length) % slides.length;

    slides[current].classList.add('active');
    dots[current].classList.add('active');
  }

  function next() {
    goTo(current + 1);
  }

  function startTimer() {
    clearInterval(timer);
    timer = setInterval(next, INTERVAL_MS);
  }

  // Dot click — reset timer so the full interval starts from the click
  dots.forEach(function (dot) {
    dot.addEventListener('click', function () {
      goTo(Number(dot.dataset.index));
      startTimer();
    });
  });

  startTimer();
})();
