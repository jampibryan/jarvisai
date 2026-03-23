# JarvisAI

Asistente personal para Windows construido paso a paso.

## Estado actual

El proyecto ya tiene una V1 estable de comandos y memoria, y una V2 mas pulida para voz y diagnostico operativo.

Actualmente incluye:

- modo texto funcional
- modo voz inicial con activacion por tecla
- parser con lenguaje natural guiado
- apertura de rutas y aplicaciones
- alias personalizados persistentes
- mini base de datos SQLite para catalogo, historial y metricas
- confirmacion para acciones sensibles con mensajes mas claros
- diagnostico inicial al arrancar

## Que puede hacer hoy

Jarvis ya puede:

- abrir rutas conocidas de Windows
- abrir aplicaciones conocidas de Windows
- responder la hora
- responder la fecha
- listar comandos disponibles
- mostrar metricas simples de uso
- mostrar su propio estado y diagnostico
- aprender alias nuevos desde consola
- reemplazar alias existentes
- pedir confirmacion antes de acciones sensibles
- recibir comandos por voz en la V2 inicial

## Ejemplos de uso

Comandos rapidos:

- `estado`
- `hora`
- `fecha`
- `comandos`
- `metricas`
- `salir`

Rutas base:

- `abre documentos`
- `abre descargas`
- `abre escritorio`
- `abre imagenes`
- `abre videos`
- `abre musica`
- `abre el disco d`

Apps base:

- `abre chrome`
- `abre editor`
- `abre cmd`
- `abre explorador`
- `abre bloc de notas`
- `abre calculadora`
- `abre paint`
- `abre administrador de tareas`
- `abre configuracion`

Frases mas naturales:

- `jarvis, estado`
- `jarvis, hora`
- `jarvis abre documentos`
- `jarvis, aprende que reportes abre D:\Reportes`
- `jarvis recuerda que mi editor es vscode`
- `jarvis actualiza que reportes abre D:\Otros`

Acciones sensibles:

- `reiniciar`
- `apagar`
- `si`
- `no`

## Modo texto

```powershell
.\venv\Scripts\python.exe main.py
```

## Modo voz

```powershell
.\venv\Scripts\python.exe main.py --voice
```

En modo voz:

- presionas `Enter` para hablar por microfono
- tambien puedes escribir un comando manualmente si quieres probar rapido
- si la voz sintetizada no esta disponible, Jarvis sigue respondiendo por texto
- antes de una accion sensible, Jarvis te repite lo que entendio

## Comandos de desarrollo

```powershell
.\venv\Scripts\python.exe -m pytest
.\venv\Scripts\python.exe main.py
.\venv\Scripts\python.exe main.py --voice
```

## Dependencias

`requirements.txt` incluye las librerias base de esta etapa:

- `SpeechRecognition`
- `PyAudio`
- `pyttsx3`
- `pytest`

Nota importante:

- el reconocimiento de voz actual usa `recognize_google`, asi que necesita internet para transcribir
- la salida por voz con `pyttsx3` puede variar segun el entorno de Windows y sus permisos COM
- si faltan dependencias de voz, el modo texto sigue funcionando

## Arquitectura actual

```text
JarvisAI/
|- main.py
|- requirements.txt
|- pytest.ini
|- venv/
|- app/
|  |- actions/
|  |- brain/
|  |- memory/
|  |- utils/
|  |- voice/
|  |- assistant.py
|  |- config.py
|  |- state.py
|- data/
|  |- aliases.json
|  |- history.db
|- tests/
```

## Componentes importantes

- `app/assistant.py`
  Orquesta el flujo principal, el diagnostico inicial, la voz y la confirmacion de acciones sensibles.

- `app/brain/command_catalog.py`
  Centraliza las frases humanas, rutas base, apps base y sugerencias del asistente.

- `app/brain/parser.py`
  Convierte texto en intenciones y soporta comandos naturales, alias y aprendizaje guiado.

- `app/brain/router.py`
  Ejecuta la accion correcta para cada intencion.

- `app/memory/memory_manager.py`
  Administra alias persistentes, sincroniza el catalogo de comandos y registra historial y metricas en SQLite.

- `app/voice/listener.py`
  Escucha desde el microfono y prepara el audio de entrada.

- `app/voice/recognizer.py`
  Convierte audio a texto para reutilizar el mismo cerebro de comandos.

- `app/voice/speaker.py`
  Intenta sintetizar respuestas con voz y degrada de forma segura si no esta disponible.

## Seguridad actual

- no guardes credenciales reales dentro del codigo
- no subas tokens, claves ni archivos privados al repositorio
- evita documentar informacion sensible en archivos del proyecto
- las acciones sensibles requieren confirmacion
- `safe_mode` puede dejarse en `ON` durante desarrollo para evitar ejecuciones destructivas reales

## Alcance de la V2 actual

Esta V2 se enfoca en:

- capturar voz desde microfono
- transcribir comandos hablados
- reutilizar el mismo parser, router y memoria de la V1
- responder por texto y, cuando el entorno lo permita, tambien por voz
- mostrar diagnostico claro al arrancar
- reducir confusion en acciones sensibles y errores comunes
