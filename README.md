# JarvisAI · NEURAL OS

JarvisAI es un asistente personal para Windows que recibe instrucciones en español por voz o texto. Sirve para encontrar archivos, abrir aplicaciones, organizar tareas rápidas y consultar servicios como YouTube y Gmail desde una misma interfaz.

## Instalación en Windows

Necesitas Python 3.13 de 64 bits, Git si vas a clonar el repositorio y un micrófono si quieres usar comandos hablados. Para reproducir videos automáticamente, Jarvis usa Microsoft Edge o Google Chrome.

```powershell
git clone https://github.com/jampibryan/jarvisai.git
cd jarvisai
py -3.13 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
```

Si ya tienes un archivo `.env`, conserva tu configuración y agrega solo las variables que te falten. Las claves de API son opcionales para los comandos locales.

Abre `JarvisAI.bat` con doble clic. La primera vez crea **JarvisAI.lnk**, un acceso directo local con el icono de NEURAL OS. Puedes usar el acceso directo para los siguientes arranques. Si mueves la carpeta del proyecto, elimina el acceso directo anterior y ejecuta de nuevo el lanzador.

## Primer uso

NEURAL OS abre en **modo inmersivo**, con el núcleo animado y el estado del micrófono. Pulsa **Ver chat** o **Esc** para mostrar la barra de texto, el historial de la sesión en **Obsidian AI** y las herramientas del **Command Center**. En **Ajustes** puedes seleccionar el micrófono, probar una voz de Windows y elegir un estilo de habla.

Espera a que Jarvis indique **Escuchando** y prueba «Jarvis, dime la hora». Puedes decir la orden completa o decir «Jarvis», esperar «Te escucho» y continuar. Si te pide el nombre de un archivo o de una canción, puedes responder sin repetir la palabra de activación. Para escribir, usa la barra inferior. «Jarvis, salir» cierra el asistente.

| Tarea | Ejemplo |
| --- | --- |
| Buscar y abrir un archivo | «Jarvis, ¿dónde está mi tesis diapositivas?» y luego «abre el primero». |
| Abrir aplicaciones, carpetas o sitios | «Jarvis, abre la calculadora», «abre Documentos» o «abre Gmail». |
| Trabajar con archivos seleccionados | Con el Explorador en primer plano, di «Jarvis, copia este archivo a Documentos», «muévelo a Descargas», «renómbralo como Informe.pdf» o «mándalo a la Papelera». |
| Reproducir un video | «Jarvis, abre YouTube y busca Persiana americana y reprodúcela». Después puedes pedir una pausa o reanudar el video. |
| Revisar correos importantes | «Jarvis, revisa mis correos importantes no leídos». |
| Cerrar una ventana o pestaña | «Jarvis, cierra Word» o, con el navegador en primer plano, «cierra esta pestaña». Jarvis te pide confirmación. |
| Crear una nota o un temporizador | «Jarvis, anota revisar el informe» o `pon un temporizador de 5 minutos`. |
| Aprender un alias de carpeta | `aprende ruta reportes = D:\Reportes`. Luego puedes decir «abre reportes». |
| Consultar comandos o diagnóstico | «Jarvis, comandos» o «Jarvis, estado». |

Puedes arrastrar archivos a la ventana o usar **Adjuntar**. **Ver** muestra una vista previa local de los primeros 1600 caracteres de archivos de texto compatibles. **Abrir** usa la aplicación de Windows correspondiente al adjunto.

La búsqueda compara palabras del nombre y avisa cuando alcanza su límite de tiempo. Para priorizar carpetas, indica sus rutas en `JARVIS_SEARCH_ROOTS`, separadas por punto y coma. Para copiar o mover, el destino debe existir. Renombrar requiere seleccionar un solo archivo y la Papelera se limita a unidades locales fijas.

### Reconocimiento de voz

El modo `auto` usa **Whisper multilingüe** si encuentra el modelo local. De lo contrario, usa el reconocedor de Google a través de SpeechRecognition. Para preparar Whisper en un equipo nuevo, ejecuta una vez lo siguiente después de instalar las dependencias.

```powershell
.\venv\Scripts\python.exe -c "from faster_whisper.utils import download_model; download_model('base', output_dir='data/runtime/whisper-base')"
```

La descarga requiere Internet. Después, Whisper transcribe el audio en la PC. Puedes elegir `JARVIS_VOICE_ENGINE=whisper` para exigir el modelo local o `google` para usar el servicio en línea. La voz de respuesta se sintetiza localmente con Windows.

Por defecto, la captura admite unos 2,4 segundos de silencio entre palabras y hasta 28 segundos por intervención. Ajusta `JARVIS_VOICE_PAUSE_THRESHOLD` y `JARVIS_VOICE_PHRASE_TIME_LIMIT` si necesitas otro ritmo.

### Servicios opcionales

- **DeepSeek y Gemini.** Configura `JARVIS_AI_PROVIDER=deepseek` con `JARVIS_DEEPSEEK_API_KEY`, o `JARVIS_AI_PROVIDER=gemini` con `JARVIS_GEMINI_API_KEY`. Usa `JARVIS_AI_PROVIDER=off` para trabajar solo con comandos locales. El proveedor recibe las frases que el intérprete local no reconoce, junto con hasta cinco intercambios de conversación de la sesión. Las consultas pueden consumir saldo.
- **YouTube.** La reproducción automática usa un perfil de navegador dedicado de Edge o Chrome. Si el sitio impide la reproducción automática, Jarvis deja disponible la búsqueda o el video para que puedas continuarlo.
- **Gmail.** El comando de correos importantes abre Gmail con el filtro correspondiente. Para listar hasta cinco asuntos y remitentes en Jarvis, habilita la API de Gmail, guarda el cliente OAuth de tipo **Aplicación de escritorio** en `credentials/google_client_secret.json` y di «conecta Gmail». La autorización es de solo lectura. Los asuntos y remitentes quedan fuera del historial persistente y de las consultas al modelo.
- **Google Calendar.** El panel **Agenda** abre Google Calendar en el navegador.

## Cómo está construido

```text
main.py / JarvisAI.bat      Arranque y selección del modo de uso
app/
├── ui/                    NEURAL OS, núcleo animado, adjuntos y acceso directo
├── voice/                 Captura, transcripción y síntesis de voz
├── brain/                 Catálogo de comandos, intérprete y enrutador
├── actions/               Archivos, ventanas, aplicaciones y productividad
├── integrations/          DeepSeek, Gemini, YouTube y Gmail
├── memory/                Alias, historial y métricas locales
├── assistant.py           Coordinación de acciones, voz y confirmaciones
├── config.py              Carga de configuración y rutas
├── state.py               Contexto y confirmaciones pendientes de la sesión
└── utils/                 Registro de diagnóstico
tests/                     Pruebas automatizadas
```

La voz se convierte en texto y pasa por el mismo intérprete que la barra de chat. El intérprete identifica la intención y el enrutador ejecuta la acción correspondiente. El asistente mantiene el contexto necesario para respuestas como «ábrelo» y pide confirmación antes de aplicar operaciones sensibles. Si no encuentra una intención local y hay un proveedor conversacional configurado, le envía la consulta.

| Tecnología | Función en el proyecto |
| --- | --- |
| **Python 3.13** | Lógica del asistente, configuración, integraciones y pruebas. |
| **Tkinter y tkinterdnd2** | Interfaz de escritorio, animación del núcleo y recepción de archivos arrastrados. |
| **Space Grotesk e Inter** | Tipografía de la interfaz. Sus licencias se incluyen en `app/ui/fonts/`. |
| **PyAudio y SpeechRecognition** | Captura del micrófono, detección de pausas y acceso al reconocimiento de Google. |
| **faster-whisper y CTranslate2** | Transcripción local multilingüe en CPU con cuantización de 8 bits. |
| **pywin32 y SAPI** | Integración con el Explorador y ventanas, síntesis de voz y creación del acceso directo de Windows. |
| **SQLite y JSON** | Catálogo, historial y métricas en SQLite. Alias y preferencias de voz en JSON. |
| **Playwright** | Búsqueda, reproducción y control de videos en un navegador dedicado. |
| **Google OAuth 2.0** | Autorización opcional de solo lectura para consultar Gmail. |
| **APIs de DeepSeek y Gemini** | Respuestas conversacionales para consultas que quedan fuera del catálogo local. |
| **pytest** | Pruebas de interpretación, voz, acciones de Windows e integraciones. |

## Seguridad y datos locales

- El apagado y el reinicio se simulan de forma predeterminada con `JARVIS_SAFE_MODE=1`.
- Los cambios en archivos seleccionados muestran una vista previa de forma predeterminada. Usa `JARVIS_APPLY_FILE_CHANGES=1` para aplicarlos tras confirmar. El cierre de ventanas y pestañas también pide confirmación.
- `.env`, los tokens y credenciales de Google, `venv/`, `logs/`, el modelo de voz, el historial, las notas y el acceso directo generado están excluidos de Git.
- En el primer arranque, los alias iniciales de `data/aliases.json` se copian a `data/runtime/aliases.json`. Los cambios posteriores se guardan en la copia local. Revisa el archivo inicial si contiene rutas personales antes de compartirlo.
- Usa `JARVIS_RECORD_HISTORY=0` para dejar de guardar nuevos comandos y respuestas en SQLite. El historial de la ventana corresponde a la sesión abierta.

## Desarrollo y pruebas

```powershell
# Toda la suite automatizada
.\venv\Scripts\python.exe -m pytest

# Solo la interpretación de comandos
.\venv\Scripts\python.exe -m pytest tests/test_parser.py

# Consola de texto sin síntesis de voz
.\venv\Scripts\python.exe main.py --text --no-tts

# Consola de voz continua
.\venv\Scripts\python.exe main.py --voice --continuous --require-wake-word

# Interfaz de escritorio
.\JarvisAI.bat
```

Las pruebas verifican el intérprete, las confirmaciones, la memoria, las integraciones y el tratamiento de audio. Algunas simulan respuestas externas o usan archivos temporales. Para validar el micrófono y los altavoces de un equipo concreto, abre la aplicación y prueba un comando por voz.
