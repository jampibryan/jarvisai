from unittest.mock import patch
from app.brain.intents import Intent
from app.brain.parser import CommandParser
from app.actions.productivity_actions import web_search


def test_parser_recognizes_web_search_commands() -> None:
    parser = CommandParser()
    examples = [
        ('busca en google ultimas noticias', 'ultimas noticias'),
        ('buscar en google recetas de cocina', 'recetas de cocina'),
        ('busca en internet clima de mañana', 'clima de mañana'),
        ('consulta en la red cotizacion del dolar', 'cotizacion del dolar'),
        ('googlea cursos de python gratis', 'cursos de python gratis'),
    ]

    for phrase, expected_query in examples:
        parsed = parser.parse(phrase)
        assert parsed.intent is Intent.WEB_SEARCH
        assert parsed.metadata.get('query') == expected_query


def test_parser_does_not_recognize_invalid_or_short_web_searches() -> None:
    parser = CommandParser()
    # Demasiado corto o no coincide con los prefijos correctos
    assert parser.parse('busca google').intent is not Intent.WEB_SEARCH
    assert parser.parse('busca en google a').intent is not Intent.WEB_SEARCH


@patch('webbrowser.open')
def test_web_search_action_success(mock_open) -> None:
    mock_open.return_value = True
    response = web_search('noticias de tecnologia')
    assert 'Buscando "noticias de tecnologia" en Google.' in response
    mock_open.assert_called_once_with('https://www.google.com/search?q=noticias%20de%20tecnologia', new=2)


@patch('webbrowser.open')
def test_web_search_action_failure(mock_open) -> None:
    mock_open.return_value = False
    response = web_search('python')
    assert 'No pude abrir el navegador' in response


def test_web_search_empty_query() -> None:
    response = web_search('')
    assert 'No me dijiste que buscar' in response
