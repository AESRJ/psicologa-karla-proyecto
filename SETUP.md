# Agente-Mama — Guía de Configuración

Sistema de agente IA para el consultorio de psicología de Karla.  
Agente: **Ast-titox** | Modelo: **Gemma 4 (Google AI)**

---

## Flujo del sistema

```
Cliente escribe en WhatsApp
        ↓
Saludo automático (buenos días/tardes/noches)
        ↓
Notificación a Karla con botones:
   [Lo atiendo yo] / [Que lo atienda Titox]
        ↓
┌───────────────────┬──────────────────────────┐
│   Karla atiende   │   Ast-titox atiende      │
│   directamente    │   (Gemma 4 + parámetros) │
└───────────────────┴──────────────────────────┘
        ↓ (cuando se acuerda una cita)
Agendado automático en Google Calendar
        ↓
Confirmación al cliente + Notificación a Karla
```

---

## Requisitos previos

- Python 3.11+
- Cuenta Meta Business con WhatsApp Business Cloud API
- API Key de Google AI (para Gemma 4)
- Proyecto en Google Cloud con Calendar API habilitada
- Servidor con IP pública (o ngrok para desarrollo)

---

## Paso 1: Instalación

```bash
cd /home/sjr/Documentos/Agente-Mama
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Paso 2: Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con los valores reales:

### WhatsApp Business Cloud API (Meta)

1. Ve a [developers.facebook.com](https://developers.facebook.com)
2. Crea una app de tipo **Business**
3. Agrega el producto **WhatsApp**
4. En *API Setup* encontrarás:
   - `WHATSAPP_ACCESS_TOKEN` — Token de acceso temporal (o permanente con System User)
   - `WHATSAPP_PHONE_NUMBER_ID` — ID del número de teléfono
   - `WHATSAPP_BUSINESS_ACCOUNT_ID` — ID de la cuenta de negocio
5. En *Webhooks*, configura la URL y el `WHATSAPP_VERIFY_TOKEN` (cualquier string secreto)

### Google AI (Gemma 4)

1. Ve a [aistudio.google.com](https://aistudio.google.com)
2. Crea una API Key
3. Cópiala en `GOOGLE_AI_API_KEY`

### Google Calendar

1. Ve a [Google Cloud Console](https://console.cloud.google.com)
2. Crea un proyecto nuevo o selecciona uno existente
3. Activa **Google Calendar API**
4. Ve a *APIs & Services → Credentials*
5. Crea credenciales **OAuth2 Client ID** de tipo **Desktop application**
6. Descarga el JSON y guárdalo como `credentials.json` en la raíz del proyecto
7. `GOOGLE_CALENDAR_ID` = el email del calendario de Karla (ej: `karla@gmail.com`)

---

## Paso 3: Autenticar Google Calendar (una sola vez)

```bash
source venv/bin/activate
python scripts/auth_calendar.py
```

Esto abrirá el navegador para que Karla autorice el acceso. El token se guarda en `token.json`.

---

## Paso 4: Configurar el Webhook de WhatsApp

### Desarrollo local (con ngrok)

```bash
# En otra terminal
ngrok http 8000
# Copia la URL https://xxxx.ngrok.io
```

En el dashboard de Meta, configura el webhook:
- **URL**: `https://xxxx.ngrok.io/webhook`
- **Verify Token**: el mismo que pusiste en `WHATSAPP_VERIFY_TOKEN`
- **Suscripciones**: `messages`

### Producción

Despliega en un servidor con dominio y SSL. Configura la URL del webhook en Meta.

---

## Paso 5: Iniciar el servidor

```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Paso 6: Probar el flujo

```bash
python scripts/test_flow.py
```

---

## Comandos especiales para Karla

Karla puede enviar estos comandos por WhatsApp al número del agente:

| Comando | Descripción |
|---------|-------------|
| `AGENDAR <número> <fecha> <hora> [tipo]` | Agenda una cita manualmente cuando ella atendió directamente |

**Ejemplo:**
```
AGENDAR 5215512345678 2024-12-20 10:00 terapia individual
```

---

## Personalizar el mensaje de bienvenida

Editar la función `build_auto_greeting` en `app/services/whatsapp.py`:

```python
def build_auto_greeting(customer_name: str | None = None) -> str:
    # Aquí va el mensaje textual que proporcione Karla
    ...
```

---

## Personalizar los parámetros de Ast-titox

Editar la constante `SYSTEM_PROMPT` en `app/services/ai_agent.py`.

---

## Estructura del proyecto

```
Agente-Mama/
├── app/
│   ├── main.py              # Servidor FastAPI + webhook
│   ├── config.py            # Variables de entorno
│   ├── database/
│   │   └── db.py            # Base de datos SQLite
│   ├── models/
│   │   └── conversation.py  # Modelos Pydantic
│   ├── services/
│   │   ├── whatsapp.py      # API de WhatsApp
│   │   ├── ai_agent.py      # Ast-titox (Gemma 4)
│   │   └── calendar.py      # Google Calendar
│   └── handlers/
│       ├── message_handler.py  # Flujo de mensajes
│       └── karla_handler.py    # Decisiones de Karla
├── scripts/
│   ├── auth_calendar.py     # Autenticación Calendar
│   └── test_flow.py         # Pruebas del flujo
├── requirements.txt
├── .env.example
└── SETUP.md
```
