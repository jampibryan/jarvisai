from __future__ import annotations

"""Catalogo legible de comandos base para el cerebro de Jarvis.

La idea es mantener en un solo lugar las frases humanas que Jarvis entiende
sin obligarnos a leer todo el parser para descubrirlas.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuiltinCommand:
    entity: str
    label: str
    description: str
    phrases: tuple[str, ...]


OPEN_TRIGGERS = (
    'abre',
    'abrir',
    'abrirr',
    'abreme',
    'ejecuta',
    'inicia',
    'iniciar',
    'muestra',
    'mostrar',
    'entra a',
    'entra al',
    'entra a la',
    'entrar a',
    'entrar al',
)

LEARN_VERBS = {'aprende', 'agrega', 'recuerda'}
REPLACE_VERBS = {'reemplaza', 'actualiza', 'cambia'}

SYSTEM_PHRASES: dict[str, tuple[str, ...]] = {
    'confirm': ('si', 'confirmar', 'confirma', 'ok', 'aceptar'),
    'cancel': ('no', 'cancelar', 'cancela'),
    'exit': ('salir', 'terminar', 'cerrar asistente', 'cerrar jarvis'),
    'list_commands': (
        'comandos',
        'ayuda',
        'que puedes hacer',
        'que sabes hacer',
        'que comandos tienes',
        'muestrame los comandos',
        'ensename los comandos',
    ),
    'show_metrics': (
        'metricas',
        'metrica',
        'estadisticas',
        'resumen',
        'muestrame las metricas',
        'quiero ver las metricas',
    ),
    'show_status': (
        'estado',
        'diagnostico',
        'como estas',
        'estado del sistema',
        'como vas',
        'como te va',
        'como sigues',
    ),
    'get_time': ('hora', 'que hora es', 'dime la hora', 'me dices la hora'),
    'get_date': ('fecha', 'que fecha es', 'dime la fecha', 'me dices la fecha'),
    'restart': (
        'reinicia',
        'reiniciar',
        'reinicia el equipo',
        'reiniciar el equipo',
        'reinicia la laptop',
        'reiniciar la laptop',
        'reinicia mi laptop',
        'reiniciar mi laptop',
        'reinicia la computadora',
        'reiniciar la computadora',
        'reinicia mi computadora',
        'reiniciar mi computadora',
        'reinicia la pc',
        'reiniciar la pc',
        'reinicia mi pc',
        'reiniciar mi pc',
        'reinicia la compu',
        'reiniciar la compu',
        'reinicia mi compu',
        'reiniciar mi compu',
    ),
    'shutdown': (
        'apaga',
        'apagar',
        'apaga el equipo',
        'apagar el equipo',
        'apaga la laptop',
        'apagar la laptop',
        'apaga mi laptop',
        'apagar mi laptop',
        'apaga la computadora',
        'apagar la computadora',
        'apaga mi computadora',
        'apagar mi computadora',
        'apaga la pc',
        'apagar la pc',
        'apaga mi pc',
        'apagar mi pc',
        'apaga la compu',
        'apagar la compu',
        'apaga mi compu',
        'apagar mi compu',
    ),
}

BUILTIN_PATH_COMMANDS: dict[str, BuiltinCommand] = {
    'drive_d': BuiltinCommand(
        entity='drive_d',
        label='disco d',
        description='Abre la unidad D.',
        phrases=('disco d', 'unidad d', 'd', 'd:'),
    ),
    'downloads': BuiltinCommand(
        entity='downloads',
        label='descargas',
        description='Abre la carpeta de descargas.',
        phrases=('descargas', 'downloads', 'mis descargas'),
    ),
    'documents': BuiltinCommand(
        entity='documents',
        label='documentos',
        description='Abre la carpeta de documentos.',
        phrases=('documentos', 'documents', 'mis documentos'),
    ),
    'desktop': BuiltinCommand(
        entity='desktop',
        label='escritorio',
        description='Abre la carpeta del escritorio.',
        phrases=('escritorio', 'desktop', 'mi escritorio'),
    ),
    'pictures': BuiltinCommand(
        entity='pictures',
        label='imagenes',
        description='Abre la carpeta de imagenes.',
        phrases=('imagenes', 'fotos', 'pictures', 'mis imagenes'),
    ),
    'videos': BuiltinCommand(
        entity='videos',
        label='videos',
        description='Abre la carpeta de videos.',
        phrases=('videos', 'mis videos'),
    ),
    'music': BuiltinCommand(
        entity='music',
        label='musica',
        description='Abre la carpeta de musica.',
        phrases=('musica', 'mi musica'),
    ),
}

BUILTIN_APP_COMMANDS: dict[str, BuiltinCommand] = {
    'chrome': BuiltinCommand(
        entity='chrome',
        label='chrome',
        description='Abre Google Chrome.',
        phrases=('chrome', 'google chrome', 'navegador', 'chrome browser'),
    ),
    'brave': BuiltinCommand(
        entity='brave',
        label='brave',
        description='Abre Brave Browser.',
        phrases=('brave', 'brave browser', 'navegador brave'),
    ),
    'vscode': BuiltinCommand(
        entity='vscode',
        label='vscode',
        description='Abre Visual Studio Code.',
        phrases=('vscode', 'code', 'editor', 'visual studio code', 'vs code'),
    ),
    'cmd': BuiltinCommand(
        entity='cmd',
        label='cmd',
        description='Abre la consola clasica de Windows.',
        phrases=('cmd', 'terminal', 'consola', 'simbolo del sistema'),
    ),
    'notepad': BuiltinCommand(
        entity='notepad',
        label='bloc de notas',
        description='Abre el Bloc de notas.',
        phrases=('bloc de notas', 'notepad', 'notas'),
    ),
    'calculator': BuiltinCommand(
        entity='calculator',
        label='calculadora',
        description='Abre la Calculadora.',
        phrases=('calculadora', 'calculator'),
    ),
    'paint': BuiltinCommand(
        entity='paint',
        label='paint',
        description='Abre Microsoft Paint.',
        phrases=('paint', 'pintura', 'mspaint'),
    ),
    'task_manager': BuiltinCommand(
        entity='task_manager',
        label='administrador de tareas',
        description='Abre el Administrador de tareas.',
        phrases=('administrador de tareas', 'task manager', 'tareas'),
    ),
    'control_panel': BuiltinCommand(
        entity='control_panel',
        label='panel de control',
        description='Abre el Panel de control.',
        phrases=('panel de control', 'control panel'),
    ),
    'settings': BuiltinCommand(
        entity='settings',
        label='configuracion',
        description='Abre la configuracion de Windows.',
        phrases=('configuracion', 'ajustes', 'settings'),
    ),
    'excel': BuiltinCommand(
        entity='excel',
        label='excel',
        description='Abre Microsoft Excel.',
        phrases=('excel',),
    ),
    'power_bi': BuiltinCommand(
        entity='power_bi',
        label='power bi',
        description='Abre Power BI Desktop.',
        phrases=('power bi', 'powerbi'),
    ),
    'whatsapp': BuiltinCommand(
        entity='whatsapp',
        label='whatsapp',
        description='Abre WhatsApp.',
        phrases=('whatsapp',),
    ),
}

HUMAN_COMMAND_GUIDE: list[str] = [
    'jarvis, estado',
    'jarvis, como vas',
    'jarvis, hora',
    'jarvis, que hora es',
    'jarvis, fecha',
    'jarvis, comandos',
    'jarvis, muestrame las metricas',
    'jarvis, quiero ver mis documentos',
    'jarvis, llevame a descargas',
    'jarvis, abre escritorio',
    'jarvis, abre imagenes',
    'jarvis, abre videos',
    'jarvis, abre musica',
    'jarvis, abre el disco d',
    'jarvis, entra a chrome',
    'jarvis, entra a brave',
    'jarvis, necesito usar el editor',
    'jarvis, abre cmd',
    'jarvis, me gustaria abrir la calculadora',
    'jarvis, abre bloc de notas',
    'jarvis, abre paint',
    'jarvis, abre administrador de tareas',
    'jarvis, abre configuracion',
    'jarvis, quiero apagar la laptop',
    'jarvis, reiniciar',
    'jarvis, salir',
]

UNKNOWN_COMMAND_SUGGESTIONS = [
    'estado',
    'hora',
    'fecha',
    'documentos',
    'descargas',
    'chrome',
    'brave',
    'editor',
    'cmd',
    'comandos',
    'salir',
]


def find_builtin_command(catalog: dict[str, BuiltinCommand], text: str) -> BuiltinCommand | None:
    """Busca una coincidencia exacta dentro de un catalogo normalizado."""
    for command in catalog.values():
        if text in command.phrases:
            return command
    return None
