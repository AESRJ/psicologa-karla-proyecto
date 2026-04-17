"""
email_service.py
Envío de correo de confirmación al paciente tras agendar una cita.

Configuración (variables de entorno):
    SMTP_HOST     — servidor SMTP  (default: smtp.gmail.com)
    SMTP_PORT     — puerto         (default: 587)
    SMTP_USER     — correo remitente (ej: karlasanchez.j@gmail.com)
    SMTP_PASSWORD — contraseña de aplicación de Gmail
    SMTP_FROM     — nombre visible  (default: "Karla Zermeño — Psicóloga")

Para activar el envío real establece las variables de entorno y cambia
ENABLED = True (o exporta SMTP_ENABLED=true).
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────

ENABLED   = os.getenv("SMTP_ENABLED", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "Karla Zermeño — Psicóloga")

THERAPY_LABELS = {
    "individual":   "Terapia Individual",
    "pareja":       "Terapia en Pareja",
    "familia":      "Terapia Familiar",
    "adolescentes": "Terapia para Adolescentes",
    "online":       "Terapia en Línea",
}

MONTHS_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _format_date(d) -> str:
    return f"{d.day} de {MONTHS_ES[d.month]} de {d.year}"


def _format_time(t) -> str:
    h = t.hour
    suffix = "PM" if h >= 12 else "AM"
    h12 = h % 12 or 12
    return f"{h12}:00 {suffix}"


# ── Public API ─────────────────────────────────────────────────────────────

def send_confirmation(appointment) -> None:
    """
    Envía un correo de confirmación al paciente.
    Si SMTP no está configurado, solo registra el intento en el log.
    """
    if not appointment.patient_email:
        return

    subject = "Confirmación de cita — Karla Zermeño Psicóloga"
    body_html = _build_html(appointment)
    body_text = _build_text(appointment)

    if not ENABLED or not SMTP_USER:
        logger.info(
            "[email] SMTP no configurado — confirmación NO enviada a %s | %s %s %s",
            appointment.patient_email,
            _format_date(appointment.appointment_date),
            _format_time(appointment.appointment_time),
            THERAPY_LABELS.get(appointment.therapy_type, appointment.therapy_type),
        )
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{SMTP_FROM} <{SMTP_USER}>"
        msg["To"]      = appointment.patient_email

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html",  "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, appointment.patient_email, msg.as_string())

        logger.info("[email] Confirmación enviada a %s", appointment.patient_email)

    except Exception as exc:
        # No interrumpir el flujo de reserva si el correo falla
        logger.error("[email] Error al enviar confirmación: %s", exc)


# ── Templates ──────────────────────────────────────────────────────────────

def _build_text(appt) -> str:
    return (
        f"Hola {appt.patient_name},\n\n"
        f"Tu cita ha sido recibida exitosamente.\n\n"
        f"  Fecha:     {_format_date(appt.appointment_date)}\n"
        f"  Horario:   {_format_time(appt.appointment_time)}\n"
        f"  Modalidad: {THERAPY_LABELS.get(appt.therapy_type, appt.therapy_type)}\n"
        f"  Total:     ${appt.price:,} MXN\n\n"
        f"Nos pondremos en contacto al {appt.patient_phone} para confirmar.\n\n"
        f"Karla Zermeño — Psicóloga\n"
        f"Tel: (646) 502 5851\n"
    )


def _build_html(appt) -> str:
    label = THERAPY_LABELS.get(appt.therapy_type, appt.therapy_type)
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px;">
      <table width="540" cellpadding="0" cellspacing="0"
             style="background:#0D2461;border-radius:4px;overflow:hidden;max-width:540px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="padding:36px 40px 24px;border-bottom:1px solid rgba(255,255,255,0.15);">
            <p style="margin:0 0 4px;font-size:11px;letter-spacing:4px;text-transform:uppercase;
                      color:rgba(255,255,255,0.6);">PSICÓLOGA</p>
            <h1 style="margin:0;font-size:18px;font-weight:700;letter-spacing:2px;
                       text-transform:uppercase;color:#ffffff;">Karla Zermeño</h1>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px 40px;">
            <p style="margin:0 0 24px;font-size:15px;font-weight:300;color:rgba(255,255,255,0.85);
                      line-height:1.6;">
              Hola <strong style="color:#fff;">{appt.patient_name}</strong>,<br>
              tu solicitud de cita fue recibida correctamente.
            </p>

            <!-- Details box -->
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border:1px solid rgba(255,255,255,0.25);margin-bottom:28px;">
              {_detail_row("Fecha",     _format_date(appt.appointment_date))}
              {_detail_row("Horario",   _format_time(appt.appointment_time))}
              {_detail_row("Modalidad", label)}
              {_detail_row("Total",     f"${appt.price:,} MXN", bold=True)}
            </table>

            <p style="margin:0;font-size:13px;font-weight:300;color:rgba(255,255,255,0.65);
                      line-height:1.7;">
              Nos pondremos en contacto al <strong style="color:#fff;">{appt.patient_phone}</strong>
              para confirmar tu cita.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 40px;border-top:1px solid rgba(255,255,255,0.1);">
            <p style="margin:0;font-size:11px;color:rgba(255,255,255,0.4);letter-spacing:1px;">
              (646) 502 5851 &nbsp;·&nbsp; karlasanchez.j@gmail.com
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _detail_row(label: str, value: str, bold: bool = False) -> str:
    val_style = "font-weight:700;font-size:15px;" if bold else "font-weight:300;"
    return f"""
      <tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
        <td style="padding:12px 16px;font-size:10px;letter-spacing:3px;text-transform:uppercase;
                   color:rgba(255,255,255,0.5);white-space:nowrap;">{label}</td>
        <td style="padding:12px 16px;font-size:13px;{val_style}color:#fff;text-align:right;">
          {value}
        </td>
      </tr>"""
