# JarvisAI

Asistente personal para Windows construido paso a paso.

## Estado actual

El proyecto ya tiene una V1 funcional orientada a comandos locales y memoria operativa.

Actualmente incluye:

- ejecucion en modo texto
- parser de comandos con lenguaje natural guiado
- apertura de rutas y aplicaciones
- alias personalizados persistentes
- mini base de datos SQLite para catalogo, historial y metricas
- confirmacion para acciones sensibles

La capa de voz todavia no forma parte de esta version. Esa sera la V2.

## Que puede hacer hoy

Jarvis ya puede:

- abrir rutas conocidas
- abrir aplicaciones conocidas
- responder la hora
- responder la fecha
- listar comandos disponibles
- mostrar metricas simples de uso
- aprender alias nuevos desde consola
- reemplazar alias existentes
- pedir confirmacion antes de acciones sensibles

## Ejemplos de uso

Comandos directos:

- `hora`
- `fecha`
- `documentos`
- `editor`
- `comandos`
- `metricas`
- `salir`

Frases mas naturales:

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

## Arquitectura actual

```text
JarvisAI/
|- main.py
|- requirements.txt
|- venv/
|- app/
|  |- actions/
|  |- brain/
|  |- memory/
|  |- utils/
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
  Orquesta el flujo principal del asistente, la confirmacion de acciones sensibles y la actualizacion del estado interno.

- `app/brain/parser.py`
  Convierte texto en intenciones y soporta comandos naturales, alias y aprendizaje guiado.

- `app/brain/router.py`
  Ejecuta la accion correcta para cada intencion.

- `app/memory/memory_manager.py`
  Administra alias persistentes, sincroniza el catalogo de comandos y registra historial y metricas en SQLite.

- `data/aliases.json`
  Guarda alias personalizados de rutas y aplicaciones.

- `data/history.db`
  Guarda catalogo de comandos, historial de ejecucion, exito o fallo, tipo de error y tiempos simples.

## Ejecucion

```powershell
.\venv\Scripts\python.exe main.py
```

## Persistencia y memoria

Jarvis usa dos fuentes locales:

- `data/aliases.json`
  Para alias editables y faciles de revisar manualmente.

- `data/history.db`
  Para informacion operativa del asistente:
  catalogo de comandos, historial, errores y metricas.

## Seguridad actual

- no guardes credenciales reales dentro del codigo
- no subas tokens, claves ni archivos privados al repositorio
- evita documentar informacion sensible en archivos del proyecto
- las acciones sensibles actualmente requieren confirmacion
- `safe_mode` sigue activo para evitar ejecuciones destructivas reales durante desarrollo

## Alcance de la V1

Esta version se enfoca en:

- comandos locales estables
- alias y memoria
- trazabilidad y metricas
- lenguaje de uso mas natural

## Siguiente etapa

La siguiente gran fase sera la V2:

- entrada por voz
- reconocimiento de comandos hablados
- salida por voz

La idea es que la capa de voz reutilice este cerebro de comandos ya estabilizado.
