/**
 * scroll-reveal.js
 * Observa todos los elementos con la clase .reveal y añade .is-visible
 * cuando entran en el viewport, produciendo el efecto de aparición
 * suave (fade + blur + deslizamiento vertical).
 */

'use strict';

(function () {
  // Si el usuario prefiere movimiento reducido, no hacemos nada —
  // el CSS ya los muestra directamente a través de la media query.
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const THRESHOLD = 0.15; // porcentaje del elemento visible para disparar

  const observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        // Añadir al entrar, quitar al salir — el efecto se repite siempre
        entry.target.classList.toggle('is-visible', entry.isIntersecting);
      });
    },
    { threshold: THRESHOLD }
  );

  // Observar todos los elementos marcados al cargar
  document.querySelectorAll('.reveal').forEach(function (el) {
    observer.observe(el);
  });
})();
