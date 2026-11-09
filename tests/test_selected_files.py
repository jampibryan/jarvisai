import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.actions import selected_files
from app.actions.selected_files import FileActionError, execute_file_plan, plan_file_action
from app.brain.intents import Intent
from app.brain.parser import CommandParser


@pytest.mark.parametrize(('phrase', 'action', 'metadata'), [
    ('Jarvis, ábrelo', 'open', {'argument': ''}),
    ('copia estos archivos a Documentos', 'copy', {'folder_entity': 'documents'}),
    ('¿Puedes copiar este archivo a Documentos?', 'copy', {'folder_entity': 'documents'}),
    ('muévelo a El Proyecto', 'move', {'destination': r'D:\Mis Reportes'}),
    ('renombra este PDF como Informe Enero.pdf', 'rename', {'argument': 'Informe Enero.pdf'}),
    ('mándalo al tacho de la basura', 'recycle', {'argument': 'recycle'}),
    ('bórralo permanentemente', 'recycle', {'argument': ''}),
])
def test_file_selection_commands_are_local(phrase, action, metadata) -> None:
    command = CommandParser(custom_paths={'el proyecto': r'D:\Mis Reportes'}).parse(phrase)
    assert (command.intent, command.entity, command.metadata) == (Intent.FILE_SELECTION, action, metadata)


def test_explorer_prefers_foreground_and_rejects_ambiguous_views(monkeypatch, tmp_path) -> None:
    def view(handle, path):
        selection = SimpleNamespace(Count=1, Item=lambda _: SimpleNamespace(Path=str(path)))
        return SimpleNamespace(
            FullName=r'C:\Windows\explorer.exe', HWND=handle,
            Document=SimpleNamespace(SelectedItems=lambda: selection),
        )

    windows = [view(1, tmp_path / 'one.pdf'), view(2, tmp_path / 'two.pdf')]
    monkeypatch.setattr(selected_files, 'Dispatch', lambda _: SimpleNamespace(Windows=lambda: windows))
    monkeypatch.setattr(selected_files.win32gui, 'IsWindowVisible', lambda _: True)
    monkeypatch.setattr(selected_files.win32gui, 'IsIconic', lambda _: False)
    monkeypatch.setattr(selected_files.win32gui, 'GetForegroundWindow', lambda: 2)
    assert selected_files.explorer_selection() == (tmp_path / 'two.pdf',)

    monkeypatch.setattr(selected_files.win32gui, 'GetForegroundWindow', lambda: 3)
    with pytest.raises(FileActionError, match='una sola vista'):
        selected_files.explorer_selection()


def test_copy_move_and_rename_temporary_file(monkeypatch, tmp_path) -> None:
    source = tmp_path / 'Año 2026.txt'
    source.write_text('contenido', encoding='utf-8')
    destination = tmp_path / 'Destino'
    destination.mkdir()
    monkeypatch.setattr(selected_files, 'explorer_selection', lambda: (source,))

    execute_file_plan(plan_file_action('copy', destination=str(destination)))
    copied = destination / source.name
    assert source.exists()
    assert copied.read_text(encoding='utf-8') == 'contenido'

    execute_file_plan(plan_file_action('rename', argument='Informe'))
    renamed = source.with_name('Informe.txt')
    assert not source.exists()
    monkeypatch.setattr(selected_files, 'explorer_selection', lambda: (renamed,))
    execute_file_plan(plan_file_action('move', destination=str(destination)))
    assert not renamed.exists()
    assert (destination / 'Informe.txt').read_text(encoding='utf-8') == 'contenido'


def test_plan_refuses_changed_files_and_destinations_with_collisions(monkeypatch, tmp_path) -> None:
    source = tmp_path / 'source.txt'
    source.write_text('original', encoding='utf-8')
    monkeypatch.setattr(selected_files, 'explorer_selection', lambda: (source,))
    target = tmp_path / 'target.txt'
    plan = plan_file_action('rename', argument=target.name)
    target.write_text('existente', encoding='utf-8')
    with pytest.raises(FileActionError, match='Ya existe'):
        execute_file_plan(plan)
    assert target.read_text(encoding='utf-8') == 'existente'

    source.write_text('archivo cambiado', encoding='utf-8')
    with pytest.raises(FileActionError, match='cambió'):
        execute_file_plan(plan)
    assert source.exists()


def test_recycle_requests_windows_recycle_only_and_handles_abort(monkeypatch, tmp_path) -> None:
    source = tmp_path / 'source.txt'
    source.touch()
    monkeypatch.setattr(selected_files, 'explorer_selection', lambda: (source,))
    monkeypatch.setattr(selected_files.win32file, 'GetDriveType', lambda _: selected_files.win32con.DRIVE_FIXED)
    operation = Mock()
    operation.GetAnyOperationsAborted.return_value = True
    monkeypatch.setattr(selected_files.pythoncom, 'CoCreateInstance', Mock(return_value=operation))
    monkeypatch.setattr(selected_files.shell, 'SHCreateItemFromParsingName', Mock(return_value='shell-item'))
    with pytest.raises(FileActionError, match='Windows no confirmó'):
        execute_file_plan(plan_file_action('recycle', argument='recycle'))

    flags = operation.SetOperationFlags.call_args.args[0]
    assert flags & 0x00080000
    assert not flags & selected_files.shellcon.FOF_NOCONFIRMATION
    operation.DeleteItem.assert_called_once_with('shell-item', None)
    assert os.path.lexists(source)
