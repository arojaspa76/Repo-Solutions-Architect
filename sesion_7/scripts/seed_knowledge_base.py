"""
scripts/seed_knowledge_base.py
================================
Puebla el índice de Azure AI Search con fragmentos de manuales IT de TechCorp.
Ejecutar UNA sola vez después de crear el índice (Admin endpoint /admin/create-index).

Uso:
    pip install openai azure-search-documents python-dotenv
    python seed_knowledge_base.py
"""

import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("RAG_API_URL", "http://localhost:8000")

# ── Base de conocimiento de ejemplo ─────────────────────────────────────────
KNOWLEDGE_BASE = [
    {
        "document_title": "Configuración VPN Windows 11",
        "document_content": """
Para configurar la VPN corporativa en Windows 11:
1. Ve a Configuración → Red e Internet → VPN.
2. Haz clic en 'Agregar VPN'.
3. Proveedor de VPN: Windows (integrado).
4. Nombre de la conexión: TechCorp-VPN.
5. Dirección del servidor: vpn.techcorp.com.
6. Tipo de VPN: L2TP/IPsec con clave previamente compartida.
7. Clave compartida: Solicitarla al equipo IT (ext. 1234).
8. Tipo de información de inicio de sesión: Usuario y contraseña.
9. Guarda y conéctate usando tus credenciales del dominio.
Nota: La VPN solo está disponible para empleados con equipos registrados en Azure AD.
        """.strip(),
        "source_file": "manual_vpn_windows11.pdf",
    },
    {
        "document_title": "Reseteo de contraseña del dominio",
        "document_content": """
Si olvidaste tu contraseña del dominio corporativo:
1. En la pantalla de inicio de sesión de Windows, haz clic en '¿Olvidaste tu contraseña?'.
2. Serás redirigido al portal de autoservicio: https://sspr.techcorp.com.
3. Ingresa tu correo corporativo (@techcorp.com).
4. Recibirás un código de verificación en tu teléfono registrado.
5. Ingresa el código y establece la nueva contraseña.
Requisitos de la contraseña:
- Mínimo 12 caracteres.
- Al menos 1 mayúscula, 1 minúscula, 1 número y 1 símbolo.
- No puede coincidir con las últimas 10 contraseñas.
Si no tienes acceso al teléfono registrado, contacta al equipo IT: it-support@techcorp.com.
        """.strip(),
        "source_file": "manual_gestion_cuentas.pdf",
    },
    {
        "document_title": "Solicitud de equipo de cómputo nuevo",
        "document_content": """
Para solicitar un equipo de cómputo nuevo en TechCorp:
1. Ingresa al portal de servicios: https://servicios.techcorp.com.
2. Selecciona 'Hardware' → 'Solicitar equipo nuevo'.
3. Completa el formulario:
   - Justificación del equipo (reemplazo / nuevo colaborador / actualización).
   - Especificaciones mínimas requeridas.
   - Fecha requerida.
4. El jefe directo recibirá un correo de aprobación.
5. Una vez aprobado, el equipo de compras gestiona la adquisición (plazo: 15-20 días hábiles).
Catálogo disponible: Dell Latitude 5540, ThinkPad E14, MacBook Pro M3 (para áreas de diseño).
        """.strip(),
        "source_file": "manual_solicitudes_hardware.pdf",
    },
    {
        "document_title": "Instalación de software corporativo",
        "document_content": """
Para instalar software en tu equipo corporativo:
- Software del catálogo aprobado: disponible en el Portal de Software (https://software.techcorp.com).
  Ejemplos: Microsoft 365, Adobe Acrobat Reader, 7-Zip, Zoom, Slack.
- Software no catalogado: solicitar mediante ticket en https://servicios.techcorp.com.
  Incluir: nombre del software, versión, justificación de uso y costo si es licenciado.
- NO instalar software descargado directamente de Internet sin autorización IT.
  Los equipos tienen restricciones de instalación; intentarlo puede bloquear tu cuenta.
- Antivirus: Microsoft Defender está preconfigurado. No instalar otro antivirus.
        """.strip(),
        "source_file": "manual_software_corporativo.pdf",
    },
    {
        "document_title": "Configuración de correo Outlook en dispositivos móviles",
        "document_content": """
Para configurar tu correo corporativo en tu smartphone:
Android:
1. Descarga 'Microsoft Outlook' desde Google Play.
2. Abre la app y selecciona 'Agregar cuenta'.
3. Ingresa tu correo @techcorp.com y contraseña del dominio.
4. Outlook detectará automáticamente Exchange Server: mail.techcorp.com.
5. Acepta la política de administración de dispositivos (MDM).

iPhone/iPad:
1. Descarga 'Microsoft Outlook' desde App Store.
2. Mismos pasos que Android.
3. Si se requiere, instala el certificado de seguridad de TechCorp.

Nota: Al registrar tu dispositivo móvil, IT podrá realizar borrado remoto si el equipo se pierde.
        """.strip(),
        "source_file": "manual_correo_movil.pdf",
    },
    {
        "document_title": "Resolución de problemas de impresora en red",
        "document_content": """
Si tu impresora no aparece en la red:
1. Verifica que estés conectado a la red corporativa (WiFi TechCorp-Internal o cable).
2. Abre el Panel de Control → Dispositivos e impresoras → Agregar impresora.
3. Selecciona 'La impresora que deseo no está en la lista'.
4. Elige 'Seleccionar impresora compartida por nombre' y escribe:
   \\\\printserver.techcorp.com\\[nombre-impresora]
   (El nombre se encuentra en el sticker de la impresora).
5. Instala el driver automáticamente.

Si el problema persiste:
- Ejecuta el solucionador de problemas: Configuración → Sistema → Solucionar problemas → Impresora.
- Verifica con tu jefe que tienes permisos de acceso a esa impresora.
- Abre ticket: https://servicios.techcorp.com → Categoría: Impresión.
        """.strip(),
        "source_file": "manual_impresoras.pdf",
    },
    {
        "document_title": "Acceso a SharePoint desde fuera de la oficina",
        "document_content": """
Para acceder a SharePoint de TechCorp desde casa o viaje:
1. Conecta la VPN corporativa primero (ver manual de VPN).
2. Accede desde el navegador: https://techcorp.sharepoint.com.
3. Usa tus credenciales del dominio (@techcorp.com).

Acceso sin VPN (solo lectura):
- Desde https://office.com → inicia sesión con tu cuenta corporativa.
- Disponible solo para documentos marcados como 'acceso externo permitido' por el dueño.

OneDrive corporativo:
- 1 TB de almacenamiento por usuario.
- Sincronización automática con la carpeta 'OneDrive - TechCorp' en tu PC.
- Los documentos confidenciales NO deben almacenarse en OneDrive personal.
        """.strip(),
        "source_file": "manual_sharepoint_onedrive.pdf",
    },
    {
        "document_title": "Equipo lento: diagnóstico y solución",
        "document_content": """
Si tu equipo está lento después de una actualización:
Diagnóstico rápido:
1. Abre el Administrador de tareas (Ctrl+Shift+Esc).
2. Revisa la pestaña 'Rendimiento': CPU, Memoria, Disco.
3. Si el disco está al 100%, es normal durante las primeras 2 horas después de una actualización.

Acciones recomendadas:
1. Reinicia el equipo después de que las actualizaciones completen.
2. Desactiva los programas de inicio innecesarios: Administrador de tareas → Inicio.
3. Ejecuta el Liberador de espacio en disco: Tecla Windows → busca 'Liberador de espacio'.
4. Asegúrate de tener al menos 10 GB libres en el disco C:.

Si el problema persiste más de 24 horas:
- Abre ticket: https://servicios.techcorp.com → Categoría: Rendimiento de equipo.
- Un técnico IT realizará diagnóstico remoto vía Microsoft Quick Assist.
        """.strip(),
        "source_file": "manual_rendimiento_equipos.pdf",
    },
]


def seed():
    """Indexa todos los documentos en el RAG Orchestrator."""
    with httpx.Client(timeout=30) as client:

        # 1. Crear el índice si no existe
        print("🔨 Creando índice vectorial en Azure AI Search...")
        r = client.post(f"{API_BASE}/admin/create-index")
        r.raise_for_status()
        print(f"   ✅ {r.json()['message']}")
        time.sleep(2)

        # 2. Indexar cada documento
        print(f"\n📚 Indexando {len(KNOWLEDGE_BASE)} fragmentos de conocimiento...")
        for i, doc in enumerate(KNOWLEDGE_BASE, 1):
            print(f"   [{i}/{len(KNOWLEDGE_BASE)}] {doc['document_title'][:60]}...")
            r = client.post(f"{API_BASE}/admin/index", json=doc)
            r.raise_for_status()
            time.sleep(0.5)   # Evitar throttling del embedding endpoint

        print(f"\n✅ Base de conocimiento lista con {len(KNOWLEDGE_BASE)} documentos.")
        print(f"   Prueba el chatbot: POST {API_BASE}/chat/")
        print(f'   Body: {{"question": "¿Cómo configuro la VPN en Windows 11?"}}')


if __name__ == "__main__":
    seed()
