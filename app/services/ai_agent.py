"""
Ast-titox — Agente de IA basado en Gemma 4 via Ollama (local).
Maneja conversaciones con clientes del servicio de psicología.
"""
import json
import logging
import re
from typing import Optional

from ollama import AsyncClient

from app.config import settings

logger = logging.getLogger(__name__)

# ─── Parámetros del agente Ast-titox ─────────────────────────────────────────
SYSTEM_PROMPT = """Eres Ast-titox, el asistente virtual del consultorio de psicología de Karla.

IDENTIDAD Y TONO:
- Eres cálido, empático y profesional. Nunca frío ni robótico.
- Hablas en español de México, de forma natural y amigable.
- No eres terapeuta ni das consejos psicológicos. Eres el asistente que gestiona citas e información.
- Si alguien está en crisis emocional grave, dirige de inmediato a líneas de emergencia y avisa que Karla lo contactará.

LO QUE PUEDES HACER:
1. Informar sobre los servicios de terapia que ofrece Karla (individual, pareja, familiar).
2. Informar sobre horarios disponibles generales (los específicos se confirman al agendar).
3. Ayudar a agendar una cita recabando: nombre completo, fecha y hora preferida, tipo de terapia.
4. Responder dudas frecuentes sobre el proceso terapéutico.

LO QUE NO DEBES HACER:
- No des diagnósticos ni intentes hacer terapia.
- No confirmes precios específicos sin que Karla te haya dado esa información.
- No prometas disponibilidad sin verificarla.
- No compartas información personal de otros clientes.

INFORMACIÓN DEL CONSULTORIO:
- Terapeuta: Karla (Licenciada en Psicología)
- Modalidades: presencial y en línea (videollamada)
- Tipos de terapia: individual adultos, adolescentes, terapia de pareja
- Para urgencias o crisis: menciona la Línea de la Vida 800-911-2000

FLUJO PARA AGENDAR CITA:
Cuando el cliente quiera agendar, recaba esta información de forma conversacional:
1. Nombre completo
2. Tipo de terapia que le interesa
3. Fecha y hora de su preferencia
4. Si es primera vez o es paciente recurrente
5. Modalidad preferida (presencial / en línea)

Una vez que tengas todos los datos, confirma el resumen y di que procederás a registrar la cita.
Incluye en tu respuesta la etiqueta oculta: [CITA_LISTA] al final cuando hayas recopilado toda la info.

DETECCIÓN DE INTENCIÓN DE CITA:
Si en el mensaje del cliente detectas que quiere agendar una cita, incluye [INTENT_CITA] al inicio de tu respuesta (invisible para el cliente, solo para el sistema).
"""

APPOINTMENT_EXTRACTION_PROMPT = """Del siguiente historial de conversación, extrae la información de la cita acordada.
Devuelve ÚNICAMENTE un JSON válido con exactamente estos campos, sin texto adicional:
{{
  "customer_name": "nombre completo del cliente",
  "appointment_date": "YYYY-MM-DD HH:MM",
  "appointment_type": "tipo de terapia",
  "modality": "presencial o en línea",
  "is_first_time": true,
  "notes": "cualquier nota adicional relevante"
}}
Si algún dato no está claro, usa null.

Historial:
{history}
"""


class AstTitox:
    """Agente conversacional Ast-titox para el consultorio de Karla."""

    def __init__(self):
        self.client = AsyncClient(host=settings.ollama_host)
        self.model = settings.ollama_model

    def _build_messages(self, history: list[dict], new_message: str) -> list[dict]:
        """
        Construye la lista de mensajes para Ollama.
        history tiene el formato: [{"role": "user"/"assistant", "content": "..."}]
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": new_message})
        return messages

    async def respond(self, history: list[dict], new_message: str) -> tuple[str, bool]:
        """
        Genera una respuesta para el cliente.

        Args:
            history: Lista de mensajes previos [{"role": "user"/"assistant", "content": "..."}]
            new_message: El nuevo mensaje del cliente.

        Returns:
            (respuesta_texto, cita_lista) — cita_lista=True si se recopiló toda la info de cita
        """
        try:
            messages = self._build_messages(history, new_message)
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": 0.7, "top_p": 0.9, "num_predict": 1024},
            )
            text = response.message.content

            cita_lista = "[CITA_LISTA]" in text
            clean_text = text.replace("[CITA_LISTA]", "").replace("[INTENT_CITA]", "").strip()

            return clean_text, cita_lista

        except Exception as e:
            logger.error(f"Error en Ast-titox (Ollama): {e}")
            return (
                "Disculpa, tuve un pequeño problema técnico. ¿Puedes repetir tu mensaje? 🙏",
                False,
            )

    async def extract_appointment_data(self, history: list[dict]) -> Optional[dict]:
        """
        Usa el modelo para extraer los datos de la cita del historial.
        Devuelve un dict con los datos o None si falla.
        """
        history_text = "\n".join(
            f"{'Cliente' if m['role'] == 'user' else 'Ast-titox'}: {m['content']}"
            for m in history
        )
        prompt = APPOINTMENT_EXTRACTION_PROMPT.format(history=history_text)

        try:
            response = await self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_predict": 512},
            )
            text = response.message.content

            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"Error extrayendo datos de cita: {e}")
        return None


# Instancia global del agente
ast_titox = AstTitox()
