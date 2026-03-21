from app.brain.intents import Intent
from app.brain.parser import CommandParser


def test_parser_recognizes_builtin_short_command() -> None:
    parser = CommandParser()

    parsed = parser.parse("documentos")

    assert parsed.intent is Intent.OPEN_PATH
    assert parsed.entity == "documents"


def test_parser_recognizes_custom_path_alias() -> None:
    parser = CommandParser(custom_paths={"reportes": r"D:\\Reportes"})

    parsed = parser.parse("abre reportes")

    assert parsed.intent is Intent.OPEN_PATH
    assert parsed.metadata["source"] == "custom_path"
    assert parsed.metadata["target"] == r"D:\\Reportes"


def test_parser_recognizes_custom_app_alias() -> None:
    parser = CommandParser(custom_apps={"mi navegador": "chrome"})

    parsed = parser.parse("mi navegador")

    assert parsed.intent is Intent.OPEN_APP
    assert parsed.metadata["source"] == "custom_app"
    assert parsed.metadata["target"] == "chrome"


def test_parser_recognizes_explicit_learn_alias_command() -> None:
    parser = CommandParser()

    parsed = parser.parse(r"aprende ruta reportes = D:\Reportes")

    assert parsed.intent is Intent.LEARN_ALIAS
    assert parsed.metadata["alias_kind"] == "ruta"
    assert parsed.metadata["label"] == "reportes"
    assert parsed.metadata["target"] == r"D:\Reportes"


def test_parser_recognizes_replace_alias_command() -> None:
    parser = CommandParser()

    parsed = parser.parse("reemplaza app editor = vscode")

    assert parsed.intent is Intent.REPLACE_ALIAS
    assert parsed.metadata["alias_kind"] == "app"
    assert parsed.metadata["label"] == "editor"
    assert parsed.metadata["target"] == "vscode"


def test_parser_recognizes_natural_path_learning() -> None:
    parser = CommandParser()

    parsed = parser.parse(r"jarvis, aprende que reportes abre D:\Reportes")

    assert parsed.intent is Intent.LEARN_ALIAS
    assert parsed.metadata["alias_kind"] == "ruta"
    assert parsed.metadata["label"] == "reportes"
    assert parsed.metadata["target"] == r"D:\Reportes"


def test_parser_recognizes_natural_app_learning() -> None:
    parser = CommandParser()

    parsed = parser.parse("jarvis recuerda que mi editor es vscode")

    assert parsed.intent is Intent.LEARN_ALIAS
    assert parsed.metadata["alias_kind"] == "app"
    assert parsed.metadata["label"] == "mi editor"
    assert parsed.metadata["target"] == "vscode"


def test_parser_accepts_assistant_prefix_for_regular_commands() -> None:
    parser = CommandParser()

    assert parser.parse("jarvis, hora").intent is Intent.GET_TIME
    assert parser.parse("jarvis abre documentos").intent is Intent.OPEN_PATH


def test_parser_recognizes_metrics_and_confirmation() -> None:
    parser = CommandParser()

    assert parser.parse("metricas").intent is Intent.SHOW_METRICS
    assert parser.parse("si").intent is Intent.CONFIRM
    assert parser.parse("no").intent is Intent.CANCEL
