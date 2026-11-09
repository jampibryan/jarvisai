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
    'abriendo',
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
    'exit': ('salir', 'terminar', 'cerrar asistente', 'cerrar jarvis', 'cierra jarvis', 'cierra el asistente'),
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
    'chatgpt': BuiltinCommand(
        entity='chatgpt',
        label='chatgpt',
        description='Abre ChatGPT en el navegador.',
        phrases=('chatgpt', 'chat gpt'),
    ),
    'youtube': BuiltinCommand(
        entity='youtube',
        label='youtube',
        description='Abre YouTube en el navegador.',
        phrases=('youtube', 'you tube'),
    ),
    'gmail': BuiltinCommand(
        entity='gmail',
        label='gmail',
        description='Abre Gmail en el navegador.',
        phrases=('gmail',),
    ),
    'github': BuiltinCommand(
        entity='github',
        label='github',
        description='Abre GitHub en el navegador.',
        phrases=('github', 'git hub'),
    ),
    'facebook': BuiltinCommand(
        entity='facebook',
        label='facebook',
        description='Abre Facebook en el navegador.',
        phrases=('facebook', 'face book'),
    ),
    'instagram': BuiltinCommand(
        entity='instagram',
        label='instagram',
        description='Abre Instagram en el navegador.',
        phrases=('instagram',),
    ),
    'tiktok': BuiltinCommand(
        entity='tiktok',
        label='tiktok',
        description='Abre TikTok en el navegador.',
        phrases=('tiktok', 'tik tok'),
    ),
    'x': BuiltinCommand(
        entity='x',
        label='x',
        description='Abre X en el navegador.',
        phrases=('x', 'twitter'),
    ),
    'linkedin': BuiltinCommand(
        entity='linkedin',
        label='linkedin',
        description='Abre LinkedIn en el navegador.',
        phrases=('linkedin', 'linked in'),
    ),
    'google_drive': BuiltinCommand(
        entity='google_drive',
        label='google drive',
        description='Abre Google Drive en el navegador.',
        phrases=('google drive', 'drive'),
    ),
    'google_maps': BuiltinCommand(
        entity='google_maps',
        label='google maps',
        description='Abre Google Maps en el navegador.',
        phrases=('google maps', 'maps'),
    ),
    'google_translate': BuiltinCommand(
        entity='google_translate',
        label='google translate',
        description='Abre Google Translate en el navegador.',
        phrases=('google translate', 'traductor', 'traductor google'),
    ),
    'netflix': BuiltinCommand(
        entity='netflix',
        label='netflix',
        description='Abre Netflix en el navegador.',
        phrases=('netflix',),
    ),
    'spotify': BuiltinCommand(
        entity='spotify',
        label='spotify',
        description='Abre Spotify en el navegador.',
        phrases=('spotify',),
    ),
    'discord': BuiltinCommand(
        entity='discord',
        label='discord',
        description='Abre Discord en el navegador.',
        phrases=('discord',),
    ),
    'telegram': BuiltinCommand(
        entity='telegram',
        label='telegram',
        description='Abre Telegram. Si dices "telegram web", lo abre en el navegador.',
        phrases=('telegram',),
    ),
    'notion': BuiltinCommand(
        entity='notion',
        label='notion',
        description='Abre Notion. Si dices "notion web", lo abre en el navegador.',
        phrases=('notion',),
    ),
    'canva': BuiltinCommand(
        entity='canva',
        label='canva',
        description='Abre Canva en el navegador.',
        phrases=('canva',),
    ),
    'google_calendar': BuiltinCommand(
        entity='google_calendar',
        label='google calendar',
        description='Abre Google Calendar en el navegador.',
        phrases=('google calendar', 'calendar'),
    ),
    'google_meet': BuiltinCommand(
        entity='google_meet',
        label='google meet',
        description='Abre Google Meet en el navegador.',
        phrases=('google meet', 'meet'),
    ),
    'claude': BuiltinCommand(
        entity='claude',
        label='claude',
        description='Abre Claude en el navegador.',
        phrases=('claude',),
    ),
    'gemini': BuiltinCommand(
        entity='gemini',
        label='gemini',
        description='Abre Gemini en el navegador.',
        phrases=('gemini',),
    ),
    'copilot': BuiltinCommand(
        entity='copilot',
        label='copilot',
        description='Abre Microsoft Copilot en el navegador.',
        phrases=('copilot',),
    ),
    'perplexity': BuiltinCommand(
        entity='perplexity',
        label='perplexity',
        description='Abre Perplexity en el navegador.',
        phrases=('perplexity',),
    ),
    'stack_overflow': BuiltinCommand(
        entity='stack_overflow',
        label='stack overflow',
        description='Abre Stack Overflow en el navegador.',
        phrases=('stack overflow', 'stackoverflow'),
    ),
    'reddit': BuiltinCommand(
        entity='reddit',
        label='reddit',
        description='Abre Reddit en el navegador.',
        phrases=('reddit',),
    ),
    'amazon': BuiltinCommand(
        entity='amazon',
        label='amazon',
        description='Abre Amazon en el navegador.',
        phrases=('amazon',),
    ),
    'mercado_libre': BuiltinCommand(
        entity='mercado_libre',
        label='mercado libre',
        description='Abre Mercado Libre en el navegador.',
        phrases=('mercado libre', 'mercadolibre'),
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
        description='Abre WhatsApp. Si dices "whatsapp web", lo abre en el navegador.',
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
    'jarvis, abre openai.com',
    'jarvis, anota comprar leche',
    'jarvis, pon un temporizador de 5 minutos para descansar',
    'jarvis, busca archivo presupuesto',
    'jarvis, abre este archivo',
    'jarvis, copia estos archivos a documentos',
    'jarvis, mueve este archivo a descargas',
    'jarvis, renombra este archivo como informe.pdf',
    'jarvis, manda este archivo a la papelera',
    'jarvis, quiero ver mis documentos',
    'jarvis, llevame a descargas',
    'jarvis, abre escritorio',
    'jarvis, abre imagenes',
    'jarvis, abre videos',
    'jarvis, abre musica',
    'jarvis, abre el disco d',
    'jarvis, abre chatgpt',
    'jarvis, abre youtube',
    'jarvis, pon la canción Bohemian Rhapsody en YouTube',
    'jarvis, pausa el video',
    'jarvis, revisa mis correos importantes',
    'jarvis, qué ventanas tengo abiertas',
    'jarvis, cierra esta pestaña',
    'jarvis, cierra Chrome',
    'jarvis, abre gmail',
    'jarvis, abre github',
    'jarvis, abre whatsapp',
    'jarvis, abre whatsapp web',
    'jarvis, abre facebook',
    'jarvis, abre instagram',
    'jarvis, abre tiktok',
    'jarvis, abre netflix',
    'jarvis, abre spotify',
    'jarvis, abre discord',
    'jarvis, abre telegram',
    'jarvis, abre telegram web',
    'jarvis, abre notion',
    'jarvis, abre canva',
    'jarvis, abre google calendar',
    'jarvis, abre google meet',
    'jarvis, abre claude',
    'jarvis, abre gemini',
    'jarvis, abre copilot',
    'jarvis, abre perplexity',
    'jarvis, abre stack overflow',
    'jarvis, abre reddit',
    'jarvis, abre amazon',
    'jarvis, abre mercado libre',
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
