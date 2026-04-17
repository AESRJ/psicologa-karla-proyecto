"""
Script de prueba para simular el flujo completo sin WhatsApp real.
Útil durante desarrollo para validar la lógica.

Uso:
    python scripts/test_flow.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.whatsapp import get_greeting, build_auto_greeting, build_karla_notification
from app.services.ai_agent import ast_titox


async def test_greeting():
    print("=== TEST: Saludo automático ===")
    print(f"Saludo: {get_greeting()}")
    print()
    print("Mensaje completo:")
    print(build_auto_greeting("María García"))
    print()


async def test_karla_notification():
    print("=== TEST: Notificación a Karla ===")
    notif = build_karla_notification(
        "5215512345678",
        "Juan Pérez",
        "Hola, me gustaría saber más sobre las terapias que ofrecen"
    )
    print(notif)
    print()


async def test_agent_conversation():
    print("=== TEST: Conversación con Ast-titox ===")
    history = []

    messages = [
        "Hola, ¿qué tipos de terapia ofrecen?",
        "Me interesa terapia individual. ¿Cuánto cuesta?",
        "Me gustaría agendar una cita para la próxima semana",
        "Soy Juan Pérez, me gustaría el martes 20 de enero a las 10am, terapia individual",
    ]

    for user_msg in messages:
        print(f"Cliente: {user_msg}")
        response, cita_lista = await ast_titox.respond(history, user_msg)
        print(f"Ast-titox: {response}")
        if cita_lista:
            print(">>> [SISTEMA] Datos de cita completos, procediendo a agendar <<<")
        print()

        # Actualizar historial
        history.append({"role": "user", "parts": [user_msg]})
        history.append({"role": "model", "parts": [response]})


async def main():
    print("🤖 Iniciando pruebas de Agente-Mama\n")
    print("=" * 50)

    await test_greeting()
    await test_karla_notification()

    # Prueba del agente requiere API key configurada
    if os.getenv("GOOGLE_AI_API_KEY"):
        await test_agent_conversation()
    else:
        print("⚠️  GOOGLE_AI_API_KEY no configurada. Saltando prueba del agente.")
        print("   Configura el .env y ejecuta de nuevo.")

    print("=" * 50)
    print("✅ Pruebas completadas")


if __name__ == "__main__":
    asyncio.run(main())
