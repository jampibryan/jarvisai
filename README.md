# JarvisAI

Base modular para construir un asistente personal en Windows paso a paso.

## Estado actual

Esta base inicial ya incluye:

- estructura modular del proyecto
- configuracion local centralizada en `app/config.py`
- logging basico
- modo texto para probar el flujo sin depender todavia del microfono
- parser y router iniciales para comandos simples

## Alcance de esta primera base

La primera version deja preparado el proyecto para:

- abrir rutas conocidas
- abrir aplicaciones configuradas
- consultar hora
- consultar fecha
- cerrar el asistente

## Estructura

```text
JarvisAI/
|- main.py
|- requirements.txt
|- venv/
|- app/
|- data/
|- credentials/
|- tests/
```

## Configuracion

Por ahora la configuracion base vive en `app/config.py`.
La idea en esta etapa es que el proyecto pueda arrancar sin depender de paquetes externos adicionales.

Mas adelante, cuando agreguemos integraciones como Google Calendar o Gmail, separaremos configuraciones sensibles y credenciales de una forma mas segura.

## Ejecucion

```powershell
.\venv\Scripts\python.exe main.py
```

## Nota de seguridad

- No guardes credenciales reales dentro del codigo.
- No subas tokens, claves ni archivos privados al repositorio.
- Evita documentar rutas personales o datos sensibles en archivos del proyecto.

## Siguiente paso sugerido

El siguiente avance natural es mejorar la V1 para que los comandos locales funcionen mejor y luego conectar la capa de voz.
