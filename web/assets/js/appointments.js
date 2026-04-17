/**
 * appointments.js
 * Widget de agendamiento de citas — calendario interactivo multi-paso.
 *
 * Pasos:
 *  1 → Seleccionar fecha (calendario con colores de disponibilidad)
 *  2 → Seleccionar horario
 *  3 → Seleccionar modalidad de terapia
 *  4 → Ingresar nombre y teléfono
 *  5 → Resumen + botón "Reservar Cita"
 */

'use strict';

/* ================================================================
   CONFIG
   ================================================================ */

const CFG = {
  hours: {
    weekday: { start: 16, end: 21 },  // lunes–viernes  4 pm – 9 pm
    weekend: { start:  9, end: 21 },  // sáb–dom        9 am – 9 pm
  },
  prices: {
    individual:   600,
    pareja:       800,
    familia:      1000,
    adolescentes: 600,
    online:       600,
  },
  labels: {
    individual:   'Terapia Individual',
    pareja:       'Terapia en Pareja',
    familia:      'Terapia Familiar',
    adolescentes: 'Terapia para Adolescentes',
    online:       'Terapia en Línea',
  },
  // Green when ≥ 60 % of slots are free; Yellow when at least one is free
  greenThreshold: 0.6,
  // Si la página se abre desde el servidor usa ruta relativa,
  // si se abre como archivo usa la URL completa del servidor local.
  API: window.location.protocol === 'file:'
    ? 'http://localhost:8000/api'
    : '/api',
};

const MONTHS = [
  'Enero','Febrero','Marzo','Abril','Mayo','Junio',
  'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre',
];
const WDAYS = ['Lu','Ma','Mi','Ju','Vi','Sa','Do'];

/* ================================================================
   STATE
   ================================================================ */

const S = {
  year:    new Date().getFullYear(),
  month:   new Date().getMonth(),
  date:    null,   // 'YYYY-MM-DD'
  slot:    null,   // 'HH:MM'
  therapy: null,   // 'individual' | 'pareja' | 'familia' | 'adolescentes' | 'online'
  name:    '',
  phone:   '',
  email:   '',
  step:    1,
  avail:   {},     // { 'YYYY-MM-DD': 'available' | 'limited' | 'unavailable' }
  slots:   [],     // [{ time: 'HH:MM', available: bool }]
};

/* ================================================================
   HELPERS
   ================================================================ */

const $  = id => document.getElementById(id);
const pad = n  => String(n).padStart(2, '0');

function isoDate(y, m, d) {
  return `${y}-${pad(m + 1)}-${pad(d)}`;
}

function isWeekend(dateStr) {
  const dow = new Date(dateStr + 'T00:00:00').getDay();
  return dow === 0 || dow === 6;
}

function formatTime(hhmm) {
  const h = parseInt(hhmm.split(':')[0], 10);
  if (h === 0)  return '12:00 AM';
  if (h < 12)   return `${h}:00 AM`;
  if (h === 12) return '12:00 PM';
  return `${h - 12}:00 PM`;
}

function formatDateES(dateStr) {
  const [y, m, d] = dateStr.split('-').map(Number);
  return `${d} de ${MONTHS[m - 1]} de ${y}`;
}

function getSlotsForDate(dateStr) {
  const { start, end } = isWeekend(dateStr)
    ? CFG.hours.weekend
    : CFG.hours.weekday;
  const slots = [];
  for (let h = start; h < end; h++) slots.push(`${pad(h)}:00`);
  return slots;
}

function todayMidnight() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

/* ================================================================
   STEP NAVIGATION
   ================================================================ */

function goTo(step) {
  S.step = step;

  document.querySelectorAll('.bk-panel').forEach(p => {
    p.classList.toggle('active', Number(p.dataset.step) === step);
  });

  document.querySelectorAll('.bk-step').forEach(el => {
    const n = Number(el.dataset.step);
    el.classList.toggle('bk-step--active', n === step);
    el.classList.toggle('bk-step--done',   n < step);
  });

  $('booking-widget').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ================================================================
   PASO 1 — CALENDARIO
   ================================================================ */

function renderCalendar() {
  const root  = $('cal-root');
  const today = todayMidnight();

  // Prevent navigation to past months
  const nowYear  = new Date().getFullYear();
  const nowMonth = new Date().getMonth();
  const isPrevDisabled = (S.year < nowYear) ||
                         (S.year === nowYear && S.month <= nowMonth);

  const firstDow = (new Date(S.year, S.month, 1).getDay() + 6) % 7; // 0 = Monday
  const lastDay  = new Date(S.year, S.month + 1, 0).getDate();

  let html = `
    <div class="cal-header">
      <button class="cal-nav" id="cal-prev" ${isPrevDisabled ? 'disabled' : ''}>&#8592;</button>
      <span class="cal-month-label">${MONTHS[S.month]} ${S.year}</span>
      <button class="cal-nav" id="cal-next">&#8594;</button>
    </div>
    <div class="cal-weekdays">
      ${WDAYS.map(d => `<span>${d}</span>`).join('')}
    </div>
    <div class="cal-grid">
  `;

  // Empty leading cells
  for (let i = 0; i < firstDow; i++) {
    html += `<div class="cal-day cal-day--empty"></div>`;
  }

  // Day cells
  for (let d = 1; d <= lastDay; d++) {
    const ds   = isoDate(S.year, S.month, d);
    const date = new Date(ds + 'T00:00:00');
    const past = date < today;
    const isToday    = date.getTime() === today.getTime();
    const isSelected = ds === S.date;
    const avail      = S.avail[ds] || 'available';

    let cls = 'cal-day';
    if (past)            cls += ' cal-day--past';
    else if (isSelected) cls += ' cal-day--selected';
    else                 cls += ` cal-day--${avail}`;
    if (isToday)         cls += ' cal-day--today';

    const interactive = !past && avail !== 'unavailable';

    html += `
      <div class="${cls}"
        data-date="${ds}"
        ${interactive ? 'role="button" tabindex="0"' : 'aria-disabled="true"'}>
        <span class="cal-day__num">${d}</span>
        ${!past ? '<span class="cal-day__dot"></span>' : ''}
      </div>
    `;
  }

  html += `</div>
    <div class="cal-legend">
      <span class="cal-legend__item cal-legend__item--available">Disponible</span>
      <span class="cal-legend__item cal-legend__item--limited">Poca disponibilidad</span>
      <span class="cal-legend__item cal-legend__item--unavailable">Sin disponibilidad</span>
    </div>
  `;

  root.innerHTML = html;

  // Navigation
  $('cal-prev').addEventListener('click', () => {
    if (S.month === 0) { S.year--; S.month = 11; } else { S.month--; }
    renderCalendar();
    fetchAvailability();
  });

  $('cal-next').addEventListener('click', () => {
    if (S.month === 11) { S.year++; S.month = 0; } else { S.month++; }
    renderCalendar();
    fetchAvailability();
  });

  // Day click
  root.querySelectorAll('.cal-day[role="button"]').forEach(cell => {
    cell.addEventListener('click', () => onDayClick(cell.dataset.date));
    cell.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') onDayClick(cell.dataset.date);
    });
  });
}

async function fetchAvailability() {
  try {
    const res = await fetch(
      `${CFG.API}/appointments/calendar?year=${S.year}&month=${S.month + 1}`
    );
    if (!res.ok) throw new Error('API error');
    S.avail = await res.json();
  } catch {
    // API not running — use deterministic mock
    S.avail = mockAvailability(S.year, S.month);
  }
  renderCalendar();
}

/** Deterministic mock so the calendar looks realistic during dev. */
function mockAvailability(year, month) {
  const data   = {};
  const days   = new Date(year, month + 1, 0).getDate();
  const today  = todayMidnight();

  for (let d = 1; d <= days; d++) {
    const ds   = isoDate(year, month, d);
    if (new Date(ds + 'T00:00:00') < today) continue;

    const hash = (year * 31 + (month + 1) * 7 + d) % 10;
    if      (hash < 1) data[ds] = 'unavailable';
    else if (hash < 4) data[ds] = 'limited';
    else               data[ds] = 'available';
  }
  return data;
}

function onDayClick(dateStr) {
  S.date = dateStr;
  renderSlots();
  goTo(2);
}

/* ================================================================
   PASO 2 — HORARIOS
   ================================================================ */

async function renderSlots() {
  const root     = $('slots-root');
  const allSlots = getSlotsForDate(S.date);
  let takenSet   = new Set();

  try {
    const res = await fetch(`${CFG.API}/appointments/slots?date=${S.date}`);
    if (res.ok) {
      const data = await res.json();
      data.slots
        .filter(s => !s.available)
        .forEach(s => takenSet.add(s.time));
    }
  } catch { /* no API — all slots available */ }

  let html = `
    <button class="bk-back" id="slots-back">&#8592; Cambiar fecha</button>
    <p class="slots-date-title">${formatDateES(S.date)}</p>
    <p class="bk-step-subtitle">Selecciona un horario disponible</p>
    <div class="slots-grid">
  `;

  allSlots.forEach(t => {
    const taken    = takenSet.has(t);
    const selected = t === S.slot;
    let cls = 'slot-btn';
    if (taken)    cls += ' slot-btn--taken';
    if (selected) cls += ' slot-btn--selected';

    html += `
      <button class="${cls}" data-time="${t}" ${taken ? 'disabled' : ''}>
        ${formatTime(t)}
      </button>
    `;
  });

  html += `</div>`;
  root.innerHTML = html;

  $('slots-back').addEventListener('click', () => goTo(1));

  root.querySelectorAll('.slot-btn:not(:disabled)').forEach(btn => {
    btn.addEventListener('click', () => {
      root.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('slot-btn--selected'));
      btn.classList.add('slot-btn--selected');
      S.slot = btn.dataset.time;
      setTimeout(() => goTo(3), 220);
    });
  });
}

/* ================================================================
   PASO 3 — MODALIDAD
   (HTML estático en index.html, solo listeners)
   ================================================================ */

function initTherapyStep() {
  document.querySelectorAll('.therapy-option').forEach(opt => {
    const handler = () => {
      document.querySelectorAll('.therapy-option')
        .forEach(o => o.classList.remove('therapy-option--selected'));
      opt.classList.add('therapy-option--selected');
      S.therapy = opt.dataset.therapy;
      setTimeout(() => goTo(4), 250);
    };
    opt.addEventListener('click', handler);
    opt.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') handler();
    });
  });

  $('therapy-back').addEventListener('click', () => goTo(2));
}

/* ================================================================
   PASO 4 — DATOS PERSONALES
   ================================================================ */

function initPersonalStep() {
  $('personal-back').addEventListener('click', () => goTo(3));

  $('personal-next').addEventListener('click', () => {
    const nameVal  = $('input-name').value.trim();
    const phoneVal = $('input-phone').value.trim();
    const emailVal = $('input-email').value.trim();
    let valid = true;

    if (!nameVal || nameVal.length < 2) {
      setFieldError('input-name', 'Ingresa tu nombre completo');
      valid = false;
    }
    if (!phoneVal || phoneVal.replace(/\D/g, '').length < 7) {
      setFieldError('input-phone', 'Ingresa un número de contacto válido');
      valid = false;
    }
    if (emailVal && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailVal)) {
      setFieldError('input-email', 'Ingresa un correo válido');
      valid = false;
    }

    if (!valid) return;
    S.name  = nameVal;
    S.phone = phoneVal;
    S.email = emailVal;
    renderSummary();
    goTo(5);
  });
}

function setFieldError(inputId, msg) {
  const input = $(inputId);
  input.classList.add('bk-input--error');
  const errEl = input.closest('.bk-field').querySelector('.field-error');
  if (errEl) errEl.textContent = msg;
  input.addEventListener('input', () => {
    input.classList.remove('bk-input--error');
    if (errEl) errEl.textContent = '';
  }, { once: true });
}

/* ================================================================
   PASO 5 — RESUMEN
   ================================================================ */

function renderSummary() {
  $('sum-date').textContent    = formatDateES(S.date);
  $('sum-time').textContent    = formatTime(S.slot);
  $('sum-therapy').textContent = CFG.labels[S.therapy];
  $('sum-name').textContent    = S.name;
  $('sum-phone').textContent   = S.phone;
  $('sum-email').textContent   = S.email || '—';
  $('sum-price').textContent   = `$${CFG.prices[S.therapy].toLocaleString('es-MX')} MXN`;
}

/* ================================================================
   ENVÍO
   ================================================================ */

async function submitAppointment() {
  const btn    = $('btn-reserve');
  const errEl  = $('reserve-error');
  btn.disabled = true;
  btn.textContent = 'Enviando…';
  errEl.textContent = '';

  const payload = {
    patient_name:  S.name,
    patient_phone: S.phone,
    patient_email: S.email || null,
    therapy_type:  S.therapy,
    date:          S.date,
    slot:          S.slot,
    price:         CFG.prices[S.therapy],
  };

  try {
    const res = await fetch(`${CFG.API}/appointments/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });

    if (res.ok) {
      showConfirmation();
    } else {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error del servidor');
    }
  } catch (e) {
    btn.disabled = false;
    btn.textContent = 'Reservar Cita';

    // "Failed to fetch" significa que el servidor no está corriendo
    const isNetworkError = e instanceof TypeError && e.message.includes('fetch');
    errEl.textContent = isNetworkError
      ? 'No se pudo conectar con el servidor. Por favor contáctanos directamente al (646) 502 5851.'
      : (e.message || 'Ocurrió un error. Por favor intenta de nuevo.');
  }
}

function showConfirmation() {
  $('booking-widget').innerHTML = `
    <div class="bk-confirmation">
      <div class="bk-confirm__icon">&#10003;</div>
      <h3 class="bk-confirm__title">¡Cita reservada!</h3>
      <p class="bk-confirm__msg">
        Tu solicitud fue recibida. Nos pondremos en contacto al número
        <strong>${S.phone}</strong> para confirmar tu cita.
      </p>
      <div class="bk-confirm__detail">
        <p>${formatDateES(S.date)} &mdash; ${formatTime(S.slot)}</p>
        <p>${CFG.labels[S.therapy]}</p>
        <p>$${CFG.prices[S.therapy].toLocaleString('es-MX')} MXN</p>
      </div>
      <button class="bk-confirm__new" onclick="window.location.reload()">
        Agendar otra cita
      </button>
    </div>
  `;
}

/* ================================================================
   INIT
   ================================================================ */

function init() {
  if (!$('booking-widget')) return;

  renderCalendar();
  fetchAvailability();
  initTherapyStep();
  initPersonalStep();

  $('summary-back').addEventListener('click', () => goTo(4));
  $('btn-reserve').addEventListener('click', submitAppointment);
}

document.addEventListener('DOMContentLoaded', init);
