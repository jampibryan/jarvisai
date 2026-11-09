from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path

from app.actions.file_actions import open_path

try:
    import pythoncom
    import pywintypes
    import win32con
    import win32file
    import win32gui
    from win32com.client import Dispatch
    from win32com.shell import shell, shellcon
except ImportError:
    pythoncom = None


class FileActionError(Exception):
    pass


def explorer_selection() -> tuple[Path, ...]:
    if pythoncom is None:
        raise FileActionError('La selección requiere Windows y pywin32. Instala requirements.txt.')

    try:
        foreground = win32gui.GetForegroundWindow()
        windows = Dispatch('Shell.Application').Windows()
        views = []
        active = []
        for window in windows:
            if window is None or Path(window.FullName).name.lower() != 'explorer.exe':
                continue
            handle = window.HWND
            if win32gui.IsWindowVisible(handle) and not win32gui.IsIconic(handle):
                views.append(window)
                if handle == foreground:
                    active.append(window)
        candidates = active or views
        if len(candidates) != 1:
            raise FileActionError('Deja visible una sola vista del Explorador o activa la ventana con la selección.')

        selected = candidates[0].Document.SelectedItems()
        paths = tuple(Path(selected.Item(index).Path) for index in range(selected.Count))
    except (pywintypes.error, pywintypes.com_error, AttributeError) as exc:
        raise FileActionError('Abre Jarvis y el Explorador en la misma sesión de escritorio.') from exc

    if not paths:
        raise FileActionError('Selecciona uno o más archivos en el Explorador.')
    return paths


def _file_identity(path: Path) -> tuple[int, int, int, int, int]:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise FileActionError(f'Selecciona archivos normales. La selección incluye {path.name}.')
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


@dataclass(frozen=True)
class SelectedFile:
    path: Path
    identity: tuple[int, int, int, int, int]


@dataclass(frozen=True)
class FilePlan:
    action: str
    files: tuple[SelectedFile, ...]
    targets: tuple[Path, ...] = ()
    destination_identity: tuple[int, int] | None = None

    def preview(self) -> str:
        labels = {'copy': 'Copiar', 'move': 'Mover', 'rename': 'Renombrar', 'recycle': 'Enviar a la Papelera'}
        lines = [f'{labels[self.action]} {len(self.files)} archivo(s).']
        for index, file in enumerate(self.files):
            target = f' → {self.targets[index]}' if self.targets else ''
            lines.append(f'{file.path}{target}')
        return '\n'.join(lines)


def plan_file_action(action: str, *, destination: str = '', argument: str = '') -> FilePlan:
    if action in {'copy', 'move'} and not destination:
        raise FileActionError('Indica una carpeta existente, por ejemplo «copia este archivo a Documentos».')
    if action == 'recycle' and argument != 'recycle':
        raise FileActionError('Usa «manda este archivo a la Papelera» para un borrado recuperable.')

    files = []
    seen = set()
    for path in explorer_selection():
        if not path.is_absolute():
            raise FileActionError('La selección debe contener archivos de una carpeta de Windows.')
        identity = _file_identity(path)
        resolved = path.resolve(strict=True)
        if resolved not in seen:
            files.append(SelectedFile(resolved, identity))
            seen.add(resolved)

    targets = ()
    destination_identity = None
    if action == 'rename':
        if len(files) != 1:
            raise FileActionError('Selecciona un solo archivo para renombrar.')
        filename = _new_filename(files[0].path, argument)
        targets = (files[0].path.with_name(filename),)
    elif action in {'copy', 'move'}:
        folder = Path(os.path.expandvars(destination)).expanduser()
        if not folder.is_absolute() or not folder.is_dir():
            raise FileActionError(f'El destino debe ser una carpeta existente: {folder}')
        folder = folder.resolve(strict=True)
        info = folder.stat()
        destination_identity = (info.st_dev, info.st_ino)
        targets = tuple(folder / file.path.name for file in files)
    elif action == 'recycle':
        for file in files:
            if win32file.GetDriveType(file.path.anchor) != win32con.DRIVE_FIXED:
                raise FileActionError('La Papelera de Jarvis solo admite archivos de unidades locales fijas.')

    plan = FilePlan(action, tuple(files), targets, destination_identity)
    _check_plan(plan)
    return plan


def _new_filename(path: Path, name: str) -> str:
    if not name or name in {'.', '..'} or name.endswith(('.', ' ')) or re.search(r'[<>:"/\\|?*\x00-\x1f]', name):
        raise FileActionError('Indica un nombre válido, por ejemplo «renombra este archivo como Informe.pdf».')
    if not Path(name).suffix:
        name += path.suffix
    if os.path.isreserved(name):
        raise FileActionError('Ese nombre está reservado por Windows.')
    return name


def _check_plan(plan: FilePlan) -> None:
    for file in plan.files:
        _check_source(file)

    if len(set(plan.targets)) != len(plan.targets):
        raise FileActionError('Dos archivos seleccionados tendrían el mismo nombre en el destino.')
    for target in plan.targets:
        _check_target(target, plan.destination_identity)


def _check_source(file: SelectedFile) -> None:
    if file.path.resolve(strict=True) != file.path or _file_identity(file.path) != file.identity:
        raise FileActionError(f'El archivo cambió desde que se seleccionó: {file.path.name}. Vuelve a seleccionarlo.')


def _check_target(target: Path, folder_identity: tuple[int, int] | None) -> None:
    if target.parent.resolve(strict=True) != target.parent:
        raise FileActionError('La carpeta de destino cambió. Vuelve a solicitar la operación.')
    if folder_identity is not None:
        info = target.parent.stat()
        if (info.st_dev, info.st_ino) != folder_identity:
            raise FileActionError('La carpeta de destino cambió. Vuelve a solicitar la operación.')
    if os.path.lexists(target):
        raise FileActionError(f'Ya existe un archivo con ese nombre: {target}')


def execute_file_plan(plan: FilePlan) -> str:
    _check_plan(plan)
    if plan.action == 'open':
        return '\n'.join(open_path(str(file.path)) for file in plan.files)

    if plan.action == 'recycle':
        _send_to_recycle_bin(plan.files)
        return f'Archivos enviados a la Papelera: {len(plan.files)}.'

    completed = 0
    for file, target in zip(plan.files, plan.targets, strict=True):
        try:
            _check_source(file)
            _check_target(target, plan.destination_identity)
            if plan.action == 'copy':
                win32file.CopyFile(str(file.path), str(target), True)
            else:
                flags = win32con.MOVEFILE_COPY_ALLOWED if plan.action == 'move' else 0
                win32file.MoveFileEx(str(file.path), str(target), flags)
                if os.path.lexists(file.path):
                    raise FileActionError(f'El original sigue en {file.path}. Comprueba también el destino.')
        except (OSError, pywintypes.error, FileActionError) as exc:
            raise FileActionError(f'Se completaron {completed} de {len(plan.files)} cambios. {exc}') from exc
        completed += 1
    return f'Cambios de archivos completados: {completed}.'


def _send_to_recycle_bin(files: tuple[SelectedFile, ...]) -> None:
    try:
        operation = pythoncom.CoCreateInstance(
            shell.CLSID_FileOperation, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IFileOperation,
        )
        # FOFX_RECYCLEONDELETE requests recycling only. Never confirm permanent deletion.
        recycle_only = 0x00080000
        operation.SetOwnerWindow(win32gui.GetForegroundWindow())
        operation.SetOperationFlags(
            recycle_only | shellcon.FOF_NOERRORUI | shellcon.FOFX_EARLYFAILURE | shellcon.FOF_WANTNUKEWARNING
            | shellcon.FOF_NO_CONNECTED_ELEMENTS
        )
        for file in files:
            _check_source(file)
            item = shell.SHCreateItemFromParsingName(str(file.path), None, shell.IID_IShellItem)
            operation.DeleteItem(item, None)
        operation.PerformOperations()
        if operation.GetAnyOperationsAborted() or any(os.path.lexists(file.path) for file in files):
            raise FileActionError('Windows no confirmó toda la operación. Revisa los archivos y la Papelera.')
    except (pywintypes.error, pywintypes.com_error) as exc:
        raise FileActionError('Windows no pudo completar el envío a la Papelera. Revisa la selección y la Papelera.') from exc
