from __future__ import annotations

import os
from ctypes import create_unicode_buffer, byref, windll, wintypes
from dataclasses import dataclass
from pathlib import Path

import pywintypes
import win32api
import win32con
import win32gui
import win32process


BROWSERS = {'chrome.exe', 'msedge.exe', 'brave.exe', 'firefox.exe', 'opera.exe'}
APPS = {
    'chrome': 'chrome.exe', 'edge': 'msedge.exe', 'microsoft edge': 'msedge.exe',
    'brave': 'brave.exe', 'firefox': 'firefox.exe', 'opera': 'opera.exe', 'word': 'winword.exe',
    'excel': 'excel.exe', 'powerpoint': 'powerpnt.exe', 'bloc de notas': 'notepad.exe',
    'notepad': 'notepad.exe', 'vscode': 'code.exe', 'visual studio code': 'code.exe',
    'explorador': 'explorer.exe', 'calculadora': 'calculatorapp.exe',
}


class WindowActionError(Exception):
    pass


@dataclass(frozen=True)
class Window:
    handle: int
    pid: int
    executable: str
    title: str


@dataclass(frozen=True)
class WindowPlan:
    window: Window
    tab: bool

    def preview(self) -> str:
        item = 'la pestaña activa del navegador' if self.tab else 'la ventana'
        return f'Voy a solicitar el cierre de {item} «{self.window.title}».'


def _window(handle: int) -> Window | None:
    if not handle or not win32gui.IsWindowVisible(handle):
        return None
    title = win32gui.GetWindowText(handle).strip()
    if not title or win32gui.GetClassName(handle) in {'Progman', 'WorkerW', 'Shell_TrayWnd'}:
        return None
    _, pid = win32process.GetWindowThreadProcessId(handle)
    if pid == os.getpid():
        return None
    try:
        process = win32api.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        try:
            query = windll.kernel32.QueryFullProcessImageNameW
            query.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, wintypes.LPDWORD)
            buffer = create_unicode_buffer(1024)
            length = wintypes.DWORD(len(buffer))
            if query(int(process), 0, buffer, byref(length)):
                return Window(handle, pid, Path(buffer.value).name.lower(), title)
        finally:
            process.Close()
    except pywintypes.error:
        pass
    return None


def list_windows() -> list[Window]:
    windows = []

    def collect(handle, _):
        try:
            window = _window(handle)
        except pywintypes.error:
            return True
        if window is not None:
            windows.append(window)
        return True

    win32gui.EnumWindows(collect, None)
    return windows


def prepare_window_close(target: str, *, tab: bool) -> WindowPlan:
    foreground = _window(win32gui.GetForegroundWindow())
    if tab:
        requested = APPS.get(target) if target else None
        if target and target != 'youtube' and requested not in BROWSERS:
            raise WindowActionError('Indica un navegador compatible o di «cierra esta pestaña».')
        if foreground is None or foreground.executable not in BROWSERS or (requested and foreground.executable != requested):
            raise WindowActionError('Deja en primer plano la pestaña del navegador que quieres cerrar y vuelve a pedírmelo por voz.')
        if target == 'youtube' and 'youtube' not in foreground.title.lower():
            raise WindowActionError('Pon la pestaña de YouTube en primer plano y vuelve a pedirme que la cierre.')
        return WindowPlan(foreground, True)
    if not target:
        if foreground is None:
            raise WindowActionError('Pon en primer plano la ventana que quieres cerrar o di el nombre del programa.')
        return WindowPlan(foreground, False)

    executable = APPS.get(target)
    if executable is None:
        raise WindowActionError('No reconocí ese programa. Puedes enfocar su ventana y decir «cierra esta ventana».')
    if foreground is not None and foreground.executable == executable:
        return WindowPlan(foreground, False)
    matches = [window for window in list_windows() if window.executable == executable]
    if len(matches) != 1:
        raise WindowActionError('No encontré una sola ventana de ese programa. Enfoca la que quieres cerrar y vuelve a pedírmelo.')
    return WindowPlan(matches[0], False)


def execute_window_close(plan: WindowPlan) -> str:
    try:
        if _window(plan.window.handle) != plan.window:
            raise WindowActionError('La ventana o su título cambió. Vuelve a pedirme el cierre.')
        if plan.tab:
            if win32gui.GetForegroundWindow() != plan.window.handle:
                raise WindowActionError('La pestaña ya no está en primer plano. No envié el atajo de cierre.')
            modifiers = (win32con.VK_CONTROL, win32con.VK_SHIFT, win32con.VK_MENU)
            if any(win32api.GetAsyncKeyState(key) & 0x8000 for key in modifiers):
                raise WindowActionError('Suelta las teclas y vuelve a pedir el cierre.')
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            try:
                win32api.keybd_event(ord('W'), 0, 0, 0)
                win32api.keybd_event(ord('W'), 0, win32con.KEYEVENTF_KEYUP, 0)
            finally:
                win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            return 'Le pedí al navegador que cierre la pestaña.'
        win32gui.PostMessage(plan.window.handle, win32con.WM_CLOSE, 0, 0)
        return 'Le pedí a la aplicación que cierre la ventana. Revisa si te solicita guardar cambios.'
    except pywintypes.error as exc:
        raise WindowActionError('Windows no aceptó la solicitud de cierre.') from exc
