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
