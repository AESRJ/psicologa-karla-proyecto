"""
Script para autenticar con Google Calendar la primera vez.
Ejecutar una vez antes de iniciar el servidor.

Uso:
    python scripts/auth_calendar.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.calendar import get_calendar_service
from app.config import settings


def main():
    print("🔐 Iniciando autenticación con Google Calendar...")
    print(f"📁 Archivo de credenciales: {settings.google_credentials_file}")
    print(f"📁 Token se guardará en: {settings.google_token_file}")
    print()

    if not os.path.exists(settings.google_credentials_file):
        print(f"❌ No se encontró: {settings.google_credentials_file}")
        print()
        print("Para obtenerlo:")
        print("1. Ve a https://console.cloud.google.com/")
        print("2. Crea o selecciona un proyecto")
        print("3. Activa la API de Google Calendar")
        print("4. Ve a APIs & Services → Credentials")
        print("5. Crea credenciales OAuth2 de tipo 'Desktop app'")
        print("6. Descarga el JSON y renómbralo como 'credentials.json'")
        print("7. Colócalo en la raíz del proyecto")
        sys.exit(1)

    try:
        service = get_calendar_service()
        # Verificar acceso listando calendarios
        calendars = service.calendarList().list().execute()
        print("✅ Autenticación exitosa!")
        print()
        print("📅 Calendarios disponibles:")
        for cal in calendars.get("items", []):
            print(f"  - {cal['summary']} (ID: {cal['id']})")
        print()
        print(f"Asegúrate de que GOOGLE_CALENDAR_ID en .env sea uno de los IDs anteriores.")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
