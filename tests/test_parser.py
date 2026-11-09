from app.brain.intents import Intent
from app.brain.parser import CommandParser


def test_parser_recognizes_human_friendly_builtin_commands() -> None:
    parser = CommandParser()
    examples = {
        'estado': Intent.SHOW_STATUS,
        'como vas': Intent.SHOW_STATUS,
        'hora': Intent.GET_TIME,
        'que hora es': Intent.GET_TIME,
        'me dices la hora': Intent.GET_TIME,
        'fecha': Intent.GET_DATE,
        'que fecha es': Intent.GET_DATE,
        'comandos': Intent.LIST_COMMANDS,
        'que comandos tienes': Intent.LIST_COMMANDS,
        'metricas': Intent.SHOW_METRICS,
        'muestrame las metricas': Intent.SHOW_METRICS,
        'abre openai.com': Intent.OPEN_URL,
        'visita github.com': Intent.OPEN_URL,
        'abre chatgpt': Intent.OPEN_APP,
        'abre youtube': Intent.OPEN_APP,
        'abre gmail': Intent.OPEN_APP,
        'abre github': Intent.OPEN_APP,
        'abre whatsapp web': Intent.OPEN_APP,
        'abre notion web': Intent.OPEN_APP,
        'abre facebook': Intent.OPEN_APP,
        'abre instagram': Intent.OPEN_APP,
        'abre tiktok': Intent.OPEN_APP,
        'abre linkedin': Intent.OPEN_APP,
        'abre google drive': Intent.OPEN_APP,
        'abre google maps': Intent.OPEN_APP,
        'abre traductor': Intent.OPEN_APP,
        'abre netflix': Intent.OPEN_APP,
        'abre spotify': Intent.OPEN_APP,
        'abre discord': Intent.OPEN_APP,
        'abre telegram web': Intent.OPEN_APP,
        'abre notion': Intent.OPEN_APP,
        'abre canva': Intent.OPEN_APP,
        'abre google calendar': Intent.OPEN_APP,
        'abre google meet': Intent.OPEN_APP,
        'abre claude': Intent.OPEN_APP,
        'abre gemini': Intent.OPEN_APP,
        'abre copilot': Intent.OPEN_APP,
        'abre perplexity': Intent.OPEN_APP,
        'abre stack overflow': Intent.OPEN_APP,
        'abre reddit': Intent.OPEN_APP,
        'abre amazon': Intent.OPEN_APP,
        'abre mercado libre': Intent.OPEN_APP,
        'anota comprar leche': Intent.CREATE_NOTE,
        'nota revisar pendientes': Intent.CREATE_NOTE,
        'busca archivo presupuesto': Intent.SEARCH_FILE,
        'donde esta reporte': Intent.SEARCH_FILE,
        'temporizador 5 minutos': Intent.SET_TIMER,
        'pon timer de 10 segundos': Intent.SET_TIMER,
        'abre documentos': Intent.OPEN_PATH,
        'quiero ver mis documentos': Intent.OPEN_PATH,
        'llevame a descargas': Intent.OPEN_PATH,
        'abre escritorio': Intent.OPEN_PATH,
        'abre imagenes': Intent.OPEN_PATH,
        'abre videos': Intent.OPEN_PATH,
        'abre musica': Intent.OPEN_PATH,
        'abre el disco d': Intent.OPEN_PATH,
        'abre chrome': Intent.OPEN_APP,
        'quiero abrirr chrome': Intent.OPEN_APP,
        'puedes abrir chrome': Intent.OPEN_APP,
        'entra a chrome': Intent.OPEN_APP,
        'entra a brave': Intent.OPEN_APP,
        'necesito usar el editor': Intent.OPEN_APP,
        'abre cmd': Intent.OPEN_APP,
        'abrir cmd': Intent.OPEN_APP,
        'abriendo chrome': Intent.OPEN_APP,
        'abre la consola': Intent.OPEN_APP,
        'abre bloc de notas': Intent.OPEN_APP,
        'me gustaria abrir la calculadora': Intent.OPEN_APP,
        'me abres la calculadora': Intent.OPEN_APP,
        'abre paint': Intent.OPEN_APP,
        'abre administrador de tareas': Intent.OPEN_APP,
        'abre configuracion': Intent.OPEN_APP,
        'quiero reiniciar la laptop': Intent.RESTART_COMPUTER,
        'puedes apagar la computadora': Intent.SHUTDOWN_COMPUTER,
        'salir': Intent.EXIT,
    }

    for phrase, expected_intent in examples.items():
        assert parser.parse(phrase).intent is expected_intent, phrase


def test_parser_recognizes_builtin_entities() -> None:
    parser = CommandParser()

    assert parser.parse('documentos').entity == 'documents'
    assert parser.parse('quiero ver mi escritorio').entity == 'desktop'
    assert parser.parse('imagenes').entity == 'pictures'
    assert parser.parse('videos').entity == 'videos'
    assert parser.parse('musica').entity == 'music'
    assert parser.parse('cmd').entity == 'cmd'
    assert parser.parse('chatgpt').entity == 'chatgpt'
    assert parser.parse('youtube').entity == 'youtube'
    assert parser.parse('gmail').entity == 'gmail'
    assert parser.parse('github').entity == 'github'
    whatsapp_web = parser.parse('whatsapp web')
    assert whatsapp_web.entity == 'whatsapp'
    assert whatsapp_web.metadata['open_mode'] == 'web'
    assert parser.parse('facebook').entity == 'facebook'
    assert parser.parse('instagram').entity == 'instagram'
    assert parser.parse('tik tok').entity == 'tiktok'
    assert parser.parse('twitter').entity == 'x'
    assert parser.parse('linkedin').entity == 'linkedin'
    assert parser.parse('drive').entity == 'google_drive'
    assert parser.parse('maps').entity == 'google_maps'
    assert parser.parse('traductor').entity == 'google_translate'
    assert parser.parse('netflix').entity == 'netflix'
    assert parser.parse('spotify').entity == 'spotify'
    assert parser.parse('discord').entity == 'discord'
    telegram_web = parser.parse('telegram web')
    assert telegram_web.entity == 'telegram'
    assert telegram_web.metadata['open_mode'] == 'web'
    assert parser.parse('notion').entity == 'notion'
    notion_web = parser.parse('abre notion web')
    assert notion_web.entity == 'notion'
    assert notion_web.metadata['open_mode'] == 'web'
    assert parser.parse('canva').entity == 'canva'
    assert parser.parse('calendar').entity == 'google_calendar'
    assert parser.parse('meet').entity == 'google_meet'
    assert parser.parse('claude').entity == 'claude'
    assert parser.parse('gemini').entity == 'gemini'
    assert parser.parse('copilot').entity == 'copilot'
    assert parser.parse('perplexity').entity == 'perplexity'
    assert parser.parse('stackoverflow').entity == 'stack_overflow'
    assert parser.parse('reddit').entity == 'reddit'
    assert parser.parse('amazon').entity == 'amazon'
    assert parser.parse('mercado libre').entity == 'mercado_libre'
    assert parser.parse('bloc de notas').entity == 'notepad'
    assert parser.parse('calculadora').entity == 'calculator'
    assert parser.parse('paint').entity == 'paint'
    assert parser.parse('administrador de tareas').entity == 'task_manager'
    assert parser.parse('configuracion').entity == 'settings'
    assert parser.parse('brave').entity == 'brave'


def test_parser_prioritizes_custom_aliases_over_builtin_commands() -> None:
    parser = CommandParser(custom_apps={'editor': 'notepad'})

    parsed = parser.parse('abre editor')

    assert parsed.intent is Intent.OPEN_APP
    assert parsed.metadata['source'] == 'custom_app'
    assert parsed.metadata['target'] == 'notepad'


def test_parser_recognizes_custom_path_alias() -> None:
    parser = CommandParser(custom_paths={'reportes': r'D:\\Reportes'})

    parsed = parser.parse('abre reportes')

    assert parsed.intent is Intent.OPEN_PATH
    assert parsed.metadata['source'] == 'custom_path'
    assert parsed.metadata['target'] == r'D:\\Reportes'


def test_parser_recognizes_custom_app_alias() -> None:
    parser = CommandParser(custom_apps={'mi navegador': 'chrome'})

    parsed = parser.parse('mi navegador')

    assert parsed.intent is Intent.OPEN_APP
    assert parsed.metadata['source'] == 'custom_app'
    assert parsed.metadata['target'] == 'chrome'


def test_parser_recognizes_explicit_learn_alias_command() -> None:
    parser = CommandParser()

    parsed = parser.parse(r'aprende ruta reportes = D:\Reportes')

    assert parsed.intent is Intent.LEARN_ALIAS
    assert parsed.metadata['alias_kind'] == 'ruta'
    assert parsed.metadata['label'] == 'reportes'
    assert parsed.metadata['target'] == r'D:\Reportes'


def test_parser_recognizes_replace_alias_command() -> None:
    parser = CommandParser()

    parsed = parser.parse('reemplaza app editor = vscode')

    assert parsed.intent is Intent.REPLACE_ALIAS
    assert parsed.metadata['alias_kind'] == 'app'
    assert parsed.metadata['label'] == 'editor'
    assert parsed.metadata['target'] == 'vscode'


def test_parser_recognizes_natural_path_learning() -> None:
    parser = CommandParser()

    parsed = parser.parse(r'jarvis, aprende que reportes abre D:\Reportes')

    assert parsed.intent is Intent.LEARN_ALIAS
    assert parsed.metadata['alias_kind'] == 'ruta'
    assert parsed.metadata['label'] == 'reportes'
    assert parsed.metadata['target'] == r'D:\Reportes'


def test_parser_recognizes_natural_app_learning() -> None:
    parser = CommandParser()

    parsed = parser.parse('jarvis recuerda que mi editor es vscode')

    assert parsed.intent is Intent.LEARN_ALIAS
    assert parsed.metadata['alias_kind'] == 'app'
    assert parsed.metadata['label'] == 'mi editor'
    assert parsed.metadata['target'] == 'vscode'


def test_parser_recognizes_phrase_based_learning() -> None:
    parser = CommandParser()

    parsed = parser.parse(r'cuando diga reportes abre D:\Reportes')

    assert parsed.intent is Intent.LEARN_ALIAS
    assert parsed.metadata['alias_kind'] == 'ruta'
    assert parsed.metadata['label'] == 'reportes'
    assert parsed.metadata['target'] == r'D:\Reportes'


def test_parser_accepts_assistant_prefix_for_regular_commands() -> None:
    parser = CommandParser()

    assert parser.parse('jarvis, hora').intent is Intent.GET_TIME
    assert parser.parse('jarvis abre documentos').intent is Intent.OPEN_PATH
    assert parser.parse('jarvis, estado').intent is Intent.SHOW_STATUS
    assert parser.parse('jarvis, puedes abrir chrome').intent is Intent.OPEN_APP
    assert parser.parse('jarvis, entra a brave').intent is Intent.OPEN_APP
    assert parser.parse('jarvis, quiero apagar la laptop').intent is Intent.SHUTDOWN_COMPUTER


def test_parser_recognizes_metrics_and_confirmation() -> None:
    parser = CommandParser()

    assert parser.parse('metricas').intent is Intent.SHOW_METRICS
    assert parser.parse('si').intent is Intent.CONFIRM
    assert parser.parse('no').intent is Intent.CANCEL


def test_parser_extracts_productivity_metadata() -> None:
    parser = CommandParser()

    note = parser.parse('anota comprar pan y cafe')
    assert note.intent is Intent.CREATE_NOTE
    assert note.metadata['content'] == 'comprar pan y cafe'

    timer = parser.parse('pon un temporizador de 2 minutos para descansar')
    assert timer.intent is Intent.SET_TIMER
    assert timer.metadata['duration_seconds'] == '120'
    assert timer.metadata['label'] == 'descansar'

    file_search = parser.parse('busca archivo presupuesto final')
    assert file_search.intent is Intent.SEARCH_FILE
    assert file_search.metadata['query'] == 'presupuesto final'

    url = parser.parse('abre openai.com')
    assert url.intent is Intent.OPEN_URL
    assert url.metadata['url'] == 'https://openai.com'


def test_parser_recognizes_more_natural_shutdown_and_restart_variants() -> None:
    parser = CommandParser()

    assert parser.parse('quiero apagar mi pc').intent is Intent.SHUTDOWN_COMPUTER
    assert parser.parse('podrias reiniciar la compu').intent is Intent.RESTART_COMPUTER


def test_parser_does_not_treat_questions_as_sensitive_commands() -> None:
    parser = CommandParser()

    assert parser.parse('cómo apagar la computadora').intent is Intent.UNKNOWN
    assert parser.parse('me explicas cómo confirmar esto').intent is Intent.UNKNOWN
    assert parser.parse('no sé si debería').intent is Intent.UNKNOWN
    assert parser.parse('¿sí?').intent is Intent.UNKNOWN


def test_parser_corrects_common_typos_for_open_commands() -> None:
    parser = CommandParser()

    assert parser.parse('abir crome').intent is Intent.OPEN_APP
    assert parser.parse('avrir cmd').intent is Intent.OPEN_APP
    assert parser.parse('abrir configurasion').intent is Intent.OPEN_APP
    assert parser.parse('abre facebokk').entity == 'facebook'
