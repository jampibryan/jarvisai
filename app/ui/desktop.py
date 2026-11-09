from __future__ import annotations

import json
import logging
import math
import sys
import tkinter as tk
from pathlib import Path
from queue import Empty, Queue, SimpleQueue
from threading import Event, Thread
from tkinter import filedialog, font, ttk

from app.assistant import JarvisAssistant
from app.config import AppConfig
from app.ui.neural_core import CYAN, GRAPHITE, ICE, MIDNIGHT, VIOLET, NeuralCore
from app.voice.listener import VoiceListener
from app.voice.speaker import VOICE_STYLES


PANEL = '#101827'
BORDER = '#233148'
MUTED = '#a2b1c8'
SUBTLE = '#71849f'
WARNING = '#ffc184'
AUTOMATIC = 'Automática (Windows)'
WORKSPACE = {
    'agenda': ('Agenda', '01', 'Abre tu calendario de Google'),
    'tasks': ('Tareas y notas', '02', 'Anota ideas y revisa tus notas'),
    'projects': ('Proyectos', '03', 'Abre carpetas y busca archivos'),
    'automations': ('Automatizaciones', '04', 'Configura temporizadores por voz o texto'),
}


def create_desktop_root() -> tk.Tk:
    if sys.platform == 'win32':
        from ctypes import windll, wintypes

        font_dir = Path(__file__).with_name('fonts')
        add_font = windll.gdi32.AddFontResourceExW
        add_font.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPVOID)
        for filename in ('Inter.ttf', 'SpaceGrotesk.ttf'):
            path = font_dir / filename
            if path.is_file():
                add_font(str(path), 0x10, None)  # FR_PRIVATE
    root = tk.Tk()
    root.dnd_ready = False
    try:
        from tkinterdnd2 import TkinterDnD

        TkinterDnD.require(root)
        root.dnd_ready = True
    except (ImportError, RuntimeError):
        pass
    return root


class JarvisDesktop:
    def __init__(self, root: tk.Tk, config: AppConfig) -> None:
        self.root, self.config = root, config
        self.events: Queue[tuple[str, str]] = Queue()
        self.microphone_changes: SimpleQueue[int | None] = SimpleQueue()
        self.voice_controls: SimpleQueue[tuple[str, str]] = SimpleQueue()
        self.stop, self.microphone_paused = Event(), Event()
        self.stage = 'Preparando el micrófono'
        self.mic_level = 0.0
        self.immersive = False
        self.attachments: list[Path] = []
        self.drawer: tk.Toplevel | None = None
        self.splash: tk.Frame | None = None
        self.voice_options = {AUTOMATIC: ''}
        self.microphone_label = 'Predeterminado de Windows'
        self.invitation = f'Di «{config.voice_wake_word.title()}» o escribe tu instrucción.'
        if getattr(root, 'dnd_ready', False):
            self.invitation = f'Di «{config.voice_wake_word.title()}», escribe o arrastra un archivo.'
        self.preferences_path = config.aliases_path.parent / 'voice_preferences.json'
        self.voice_id, self.voice_style = self._load_voice_preferences()
        fonts = set(font.families(root))
        self.body_font = 'Inter' if 'Inter' in fonts else 'Segoe UI'
        self.title_font = 'Space Grotesk' if 'Space Grotesk' in fonts else self.body_font
        root.title('NEURAL OS · JarvisAI')
        width = min(1120, max(810, int(root.winfo_screenwidth() * 0.92)))
        height = min(720, max(570, int(root.winfo_screenheight() * 0.89)))
        root.geometry(f'{width}x{height}')
        root.minsize(810, 570)
        root.configure(bg=MIDNIGHT)
        root.protocol('WM_DELETE_WINDOW', self._request_close)
        root.bind('<Control-i>', lambda _: self._toggle_immersive())
        root.bind('<Escape>', self._escape)
        self.icon = tk.PhotoImage(width=32, height=32)
        for y in range(32):
            colors = []
            for x in range(32):
                distance = math.hypot(x - 15.5, y - 15.5)
                colors.append(ICE if distance < 4 else CYAN if distance < 7 else VIOLET if 10 < distance < 12 else MIDNIGHT)
            self.icon.put('{' + ' '.join(colors) + '}', to=(0, y))
        root.iconphoto(True, self.icon)
        icon_path = Path(__file__).with_name('neural.ico')
        if icon_path.is_file() and sys.platform == 'win32':
            root.iconbitmap(default=str(icon_path))
        self._build()
        self._toggle_immersive()

    def run(self) -> None:
        self._show_splash()
        Thread(target=self._run_assistant, name='jarvis-voice').start()
        self.root.after(40, self._poll)
        self.root.mainloop()

    def _label(
        self, parent: tk.Misc, text: str, *, size: int = 10, fg: str = ICE, bg: str = MIDNIGHT, bold: bool = False,
    ) -> tk.Label:
        return tk.Label(parent, text=text, bg=bg, fg=fg, padx=0, pady=0, borderwidth=0,
                        font=(self.title_font if bold else self.body_font, size, 'bold' if bold else 'normal'))

    def _button(self, parent: tk.Misc, text: str, callback, *, accent: bool = False) -> tk.Button:
        bg, fg = (CYAN, MIDNIGHT) if accent else (GRAPHITE, ICE)
        return tk.Button(parent, text=text, command=callback, bg=bg, fg=fg, activebackground='#23334d',
                         activeforeground=ICE, relief='flat', borderwidth=0, padx=11, pady=6,
                         font=(self.body_font, 9, 'bold'), cursor='hand2', highlightthickness=1,
                         highlightbackground=bg, highlightcolor=CYAN)

    def _build(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('Neural.TCombobox', padding=6, background=GRAPHITE, bordercolor=BORDER,
                        lightcolor=BORDER, darkcolor=BORDER, arrowcolor=CYAN)
        style.map('Neural.TCombobox', fieldbackground=[('readonly', GRAPHITE)], foreground=[('readonly', ICE)])
        style.configure('Neural.Vertical.TScrollbar', background=BORDER, troughcolor=PANEL, arrowcolor=MUTED,
                        bordercolor=PANEL, lightcolor=BORDER, darkcolor=BORDER, width=9)
        self.header = tk.Frame(self.root, bg=MIDNIGHT)
        self.header.pack(fill='x', padx=26, pady=(13, 10))
        self._label(self.header, '◉  NEURAL OS', size=15, bold=True).pack(side='left')
        self._label(self.header, 'JARVIS  /  ESPACIO PERSONAL', size=8, fg=SUBTLE).pack(side='left', padx=12)
        self.immersive_button = self._button(self.header, 'Modo inmersivo', self._toggle_immersive)
        self.immersive_button.pack(side='right')
        self.settings_button = self._button(self.header, 'Ajustes', lambda: self._open_panel('settings'))
        self.settings_button.pack(side='right', padx=(0, 7))

        self.composer = tk.Frame(self.root, bg=GRAPHITE, highlightbackground=BORDER, highlightthickness=1)
        self.composer.pack(side='bottom', fill='x', padx=26, pady=(8, 16))
        self.attach_button = self._button(self.composer, '+  Adjuntar', self._pick_attachments)
        self.attach_button.pack(side='left', padx=(8, 4), pady=6)
        self.attachments_button = self._button(self.composer, 'Adjuntos · 0', lambda: self._open_panel('attachments'))
        self.attachments_button.pack(side='left', padx=(0, 6), pady=6)
        self.send_button = self._button(self.composer, 'Enviar  ↑', self._submit, accent=True)
        self.send_button.pack(side='right', padx=(4, 8), pady=6)
        self.mic_button = self._button(self.composer, 'Micrófono activo', self._toggle_microphone)
        self.mic_button.pack(side='right', padx=(4, 1), pady=6)
        self.entry = tk.Entry(self.composer, bg=GRAPHITE, fg=ICE, insertbackground=CYAN, relief='flat',
                              font=(self.body_font, 11), borderwidth=0)
        self.entry.pack(side='left', fill='both', expand=True, padx=7, pady=10)
        self.entry.bind('<Return>', self._submit)
        self.placeholder = 'Pregúntame lo que quieras…'
        self.entry.bind('<FocusIn>', self._clear_placeholder)
        self.entry.bind('<FocusOut>', self._restore_placeholder)
        self._restore_placeholder()

        self.layout = tk.Frame(self.root, bg=MIDNIGHT)
        self.layout.pack(fill='both', expand=True, padx=26)
        self.layout.rowconfigure(0, weight=1)
        self.layout.columnconfigure(0, weight=3, minsize=365)
        self.layout.columnconfigure(1, weight=2, minsize=305)

        center = tk.Frame(self.layout, bg=MIDNIGHT, highlightbackground=BORDER, highlightthickness=1)
        center.grid(row=0, column=0, sticky='nsew', padx=(0, 13))
        self.tools = tk.Frame(center, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        self.tools.pack(side='bottom', fill='x', padx=11, pady=(0, 11))
        self._label(self.tools, 'COMMAND CENTER', size=8, fg=CYAN, bg=PANEL, bold=True).pack(anchor='w', padx=12, pady=(9, 0))
        self._label(self.tools, 'Tu espacio de trabajo', size=11, bg=PANEL, bold=True).pack(anchor='w', padx=12, pady=(2, 7))
        cards = tk.Frame(self.tools, bg=PANEL)
        cards.pack(fill='x', padx=10, pady=(0, 9))
        cards.columnconfigure((0, 1), weight=1, uniform='tools')
        for index, (panel, (label, number, _)) in enumerate(WORKSPACE.items()):
            card = self._button(cards, f'{number}    {label}', lambda name=panel: self._open_panel(name))
            card.configure(anchor='w', pady=5)
            card.grid(row=index // 2, column=index % 2, sticky='ew', padx=3, pady=3)

        self.hero = tk.Frame(center, bg=MIDNIGHT)
        self.hero.pack(fill='both', expand=True, padx=9, pady=(8, 4))
        self.hero_heading = tk.Frame(self.hero, bg=MIDNIGHT)
        self.hero_heading.pack(fill='x', pady=(8, 0))
        self._label(self.hero_heading, 'N E U R A L   C O R E', size=8, fg=SUBTLE, bold=True).pack()
        self._label(self.hero_heading, '¿En qué puedo ayudarte?', size=20, bold=True).pack(pady=(4, 0))
        self.status_group = tk.Frame(self.hero, bg=MIDNIGHT)
        self.status_group.pack(side='bottom', pady=(0, 9))
        self.status = self._label(self.status_group, self.stage, size=10, fg=CYAN, bold=True)
        self.status.pack()
        self.hint = self._label(self.status_group, self.invitation, size=9, fg=MUTED)
        self.hint.pack(pady=(3, 0))
        self.orb = NeuralCore(self.hero, diameter=195)
        self.orb.pack(fill='both', expand=True)

        self.conversation = tk.Frame(self.layout, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        self.conversation.grid(row=0, column=1, sticky='nsew')
        conversation_header = tk.Frame(self.conversation, bg=PANEL)
        conversation_header.pack(fill='x', padx=15, pady=(13, 10))
        self._label(conversation_header, 'O B S I D I A N   A I', size=8, fg=VIOLET, bg=PANEL, bold=True).pack(anchor='w')
        self._label(conversation_header, 'Conversación', size=15, bg=PANEL, bold=True).pack(anchor='w', pady=(3, 0))
        self._label(conversation_header, 'Historial de esta sesión', size=9, fg=SUBTLE, bg=PANEL).pack(anchor='w')
        tk.Frame(self.conversation, bg=BORDER, height=1).pack(fill='x')
        self.audio_warning = self._label(self.conversation, '', fg=WARNING, bg=PANEL, size=9)
        self.audio_warning.configure(wraplength=290, justify='left')
        history = tk.Frame(self.conversation, bg=PANEL)
        history.pack(fill='both', expand=True, padx=(11, 6), pady=10)
        self.chat = tk.Text(history, bg=PANEL, fg=ICE, font=(self.body_font, 10), width=1, height=1, wrap='word',
                            relief='flat', borderwidth=0, highlightthickness=0, state='disabled', cursor='arrow')
        for role, color, fill, alignment in (('assistant', CYAN, GRAPHITE, 'left'), ('user', '#c5b8ff', '#22233b', 'right')):
            self.chat.tag_configure(role + '_label', foreground=color, font=(self.body_font, 8, 'bold'),
                                    justify=alignment, lmargin1=8, rmargin=12, spacing1=5)
            self.chat.tag_configure(role, background=fill, justify=alignment, lmargin1=8, lmargin2=8, rmargin=12,
                                    spacing1=4, spacing3=5)
        scrollbar = ttk.Scrollbar(history, command=self.chat.yview, style='Neural.Vertical.TScrollbar')
        scrollbar.pack(side='right', fill='y')
        self.chat.configure(yscrollcommand=scrollbar.set)
        self.chat.pack(fill='both', expand=True)
        self._append_message('assistant', 'Puedo buscar archivos, abrir aplicaciones o conversar contigo. ¿Qué necesitas hoy?')

        if getattr(self.root, 'dnd_ready', False):
            from tkinterdnd2 import DND_FILES

            for target in (self.layout, self.composer, self.entry, self.chat):
                target.drop_target_register(DND_FILES)
                target.dnd_bind('<<Drop>>', self._on_drop)

    def _show_splash(self) -> None:
        self.splash = tk.Frame(self.root, bg=MIDNIGHT)
        self.splash.place(relwidth=1, relheight=1)
        panel = tk.Frame(self.splash, bg=MIDNIGHT)
        panel.place(relx=0.5, rely=0.49, anchor='center')
        self._label(panel, 'N E U R A L   O S', size=13, bold=True).pack()
        self.splash_orb = NeuralCore(panel, diameter=190)
        self.splash_orb.pack()
        self._label(panel, 'Tu mundo. Una inteligencia. Posibilidades ilimitadas.', size=15, bold=True).pack()
        self._label(panel, 'Sistema preparado', size=9, fg=CYAN).pack(pady=(8, 12))
        self._button(panel, 'Omitir', self._dismiss_splash).pack()
        self.root.after(1200, self._dismiss_splash)

    def _dismiss_splash(self) -> None:
        if self.splash is not None:
            self.splash.destroy()
            self.splash = None

    def _escape(self, _) -> None:
        if self.splash is not None:
            self._dismiss_splash()
        elif self.drawer is not None:
            self.drawer.destroy()
            self.drawer = None
        elif self.immersive:
            self._toggle_immersive()

    def _toggle_immersive(self) -> None:
        self._dismiss_splash()
        self.immersive = not self.immersive
        if self.immersive:
            if self.drawer is not None:
                self.drawer.destroy()
                self.drawer = None
            self.conversation.grid_remove()
            self.layout.columnconfigure(1, weight=0, minsize=0)
            self.tools.pack_forget()
            self.composer.pack_forget()
            self.hero_heading.pack_forget()
            self.settings_button.pack_forget()
            self.hint.configure(text='Esc para volver al espacio de trabajo')
            self.orb.diameter = 330
            self.immersive_button.configure(text='Ver chat')
        else:
            self.layout.columnconfigure(1, weight=2, minsize=305)
            self.conversation.grid()
            self.tools.pack(side='bottom', fill='x', padx=11, pady=(0, 11), before=self.hero)
            self.composer.pack(side='bottom', fill='x', padx=26, pady=(8, 16), before=self.layout)
            self.hero_heading.pack(fill='x', pady=(8, 0), before=self.status_group)
            self.settings_button.pack(side='right', padx=(0, 7))
            self.hint.configure(text=self.invitation)
            self.orb.diameter = 195
            self.immersive_button.configure(text='Modo inmersivo')

    def _submit(self, _=None) -> str:
        value = self.entry.get().strip()
        if value and value != self.placeholder:
            self.entry.delete(0, 'end')
            self.voice_controls.put(('command', value))
        return 'break'

    def _clear_placeholder(self, _=None) -> None:
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, 'end')
            self.entry.configure(fg=ICE)

    def _restore_placeholder(self, _=None) -> None:
        if not self.entry.get():
            self.entry.configure(fg=MUTED)
            self.entry.insert(0, self.placeholder)

    def _prefill(self, command: str) -> None:
        if self.drawer is not None:
            self.drawer.destroy()
            self.drawer = None
        self.entry.delete(0, 'end')
        self.entry.configure(fg=ICE)
        self.entry.insert(0, command)
        self.entry.focus_set()

    def _toggle_microphone(self) -> None:
        if self.microphone_paused.is_set():
            self.microphone_paused.clear()
            self.mic_button.configure(text='Micrófono activo')
        else:
            self.microphone_paused.set()
            self.mic_button.configure(text='Micrófono en pausa')

    def _pick_attachments(self) -> None:
        self._add_attachments(filedialog.askopenfilenames(parent=self.root, title='Adjuntar archivos'))

    def _on_drop(self, event) -> str:
        try:
            values = self.root.tk.splitlist(event.data)
        except tk.TclError:
            return 'refuse_drop'
        self._add_attachments(values)
        return 'copy'

    def _add_attachments(self, values: tuple[str, ...]) -> None:
        added = []
        for value in values:
            path = Path(value)
            if len(self.attachments) >= 12:
                break
            if path.is_absolute() and path.is_file() and path not in self.attachments:
                self.attachments.append(path)
                added.append(path.name)
        if added:
            self._append_message('user', 'Archivos adjuntos\n' + '\n'.join(added))
            self.attachments_button.configure(text=f'Adjuntos · {len(self.attachments)}')
            self._open_panel('attachments')

    def _open_panel(self, name: str) -> None:
        if self.immersive:
            self._toggle_immersive()
        if self.drawer is not None:
            self.drawer.destroy()
        drawer = tk.Toplevel(self.root, bg=PANEL)
        drawer.title('NEURAL OS · ' + (WORKSPACE[name][0] if name in WORKSPACE else 'Ajustes' if name == 'settings' else 'Adjuntos'))
        drawer.transient(self.root)
        drawer.resizable(True, False)
        drawer.geometry(f'+{self.root.winfo_rootx() + max(12, self.root.winfo_width() - 440)}+{self.root.winfo_rooty() + 70}')
        drawer.bind('<Escape>', lambda _: drawer.destroy())
        drawer.bind('<Destroy>', lambda event: self._drawer_closed(event, drawer))
        self.drawer = drawer
        body = tk.Frame(drawer, bg=PANEL, padx=16, pady=15)
        body.pack(fill='both', expand=True)
        self._label(body, 'O B S I D I A N   A I', size=8, fg=VIOLET, bg=PANEL, bold=True).pack(anchor='w')
        title = WORKSPACE[name][0] if name in WORKSPACE else 'Voz y micrófono' if name == 'settings' else 'Archivos adjuntos'
        self._label(body, title, size=15, bg=PANEL, bold=True).pack(anchor='w', pady=(4, 4))
        if name in WORKSPACE:
            self._label(body, WORKSPACE[name][2], size=9, fg=MUTED, bg=PANEL).pack(anchor='w', pady=(0, 9))
        if name == 'agenda':
            self._panel_button(body, 'Abrir Google Calendar', 'abre google calendar web')
        elif name == 'tasks':
            self._button(body, 'Escribir una nota', lambda: self._prefill('anota ')).pack(fill='x', pady=3)
            for note in sorted(self.config.notes_dir.glob('*.txt'), reverse=True)[:4]:
                self._button(body, note.stem[:44], lambda path=note: self.voice_controls.put(('preview_attachment', str(path)))).pack(fill='x', pady=3)
        elif name == 'projects':
            for label in ('Documentos', 'Descargas', 'Escritorio'):
                self._panel_button(body, f'Abrir {label}', f'abre {label}')
            self._panel_button(body, 'Buscar un archivo', 'busca un documento')
        elif name == 'automations':
            self._panel_button(body, 'Temporizador de 5 minutos', 'temporizador 5 minutos')
            self._button(body, 'Elegir duración', lambda: self._prefill('temporizador ')).pack(fill='x', pady=3)
        elif name == 'settings':
            self._build_settings(body)
        else:
            self._build_attachments(body)

    def _drawer_closed(self, event, drawer) -> None:
        if event.widget is drawer and self.drawer is drawer:
            self.drawer = None

    def _panel_button(self, parent: tk.Misc, label: str, command: str) -> None:
        self._button(parent, label, lambda: self.voice_controls.put(('command', command))).pack(fill='x', pady=3)

    def _build_attachments(self, body: tk.Misc) -> None:
        if self.attachments:
            description = 'Vista previa local para archivos de texto.'
        else:
            description = 'Arrastra archivos aquí o usa Adjuntar.' if getattr(self.root, 'dnd_ready', False) else 'Usa Adjuntar para elegir archivos.'
        self._label(body, description, size=9, fg=MUTED, bg=PANEL).pack(anchor='w', pady=(0, 7))
        for path in self.attachments:
            row = tk.Frame(body, bg=PANEL)
            row.pack(fill='x', pady=2)
            self._label(row, path.name[:38], size=9, bg=PANEL).pack(side='left', padx=(0, 6))
            for label, action in (('Ver', 'preview_attachment'), ('Abrir', 'open_attachment')):
                self._button(row, label, lambda operation=action, file=path: self.voice_controls.put((operation, str(file)))).pack(side='right', padx=2)
        if self.attachments:
            self._button(body, 'Quitar adjuntos de la sesión', self._clear_attachments).pack(fill='x', pady=(7, 0))

    def _clear_attachments(self) -> None:
        self.attachments.clear()
        self.attachments_button.configure(text='Adjuntos · 0')
        self._open_panel('attachments')

    def _picker(self, parent: tk.Misc, label: str, choices: tuple[str, ...], selected: str, callback) -> None:
        self._label(parent, label, size=9, fg=MUTED, bg=PANEL).pack(anchor='w', pady=(7, 2))
        picker = ttk.Combobox(parent, state='readonly', values=choices, style='Neural.TCombobox', width=37)
        picker.set(selected)
        picker.pack(fill='x')
        picker.bind('<<ComboboxSelected>>', lambda _: callback(picker.get()))

    def _build_settings(self, body: tk.Misc) -> None:
        voices = self.voice_options
        selected = next((name for name, value in voices.items() if value == self.voice_id), AUTOMATIC)
        self._picker(body, 'Voz de Windows', tuple(voices), selected, self._voice_changed)
        self._picker(body, 'Estilo', tuple(VOICE_STYLES), self.voice_style, self._style_changed)
        devices = {f'{label} [{index}]': index for index, label in VoiceListener.input_devices().items()}
        default = 'Predeterminado de Windows'
        selected_mic = self.microphone_label if self.microphone_label in devices else default
        self._picker(body, 'Micrófono', (default, *devices), selected_mic,
                     lambda name: self._microphone_changed(name, devices.get(name)))
        self._button(body, 'Probar voz', lambda: self.voice_controls.put(('preview', '')), accent=True).pack(fill='x', pady=(10, 0))

    def _load_voice_preferences(self) -> tuple[str, str]:
        try:
            data = json.loads(self.preferences_path.read_text(encoding='utf-8'))
            voice_id, style = data.get('voice_id', ''), data.get('style', '')
            if isinstance(voice_id, str) and isinstance(style, str):
                return voice_id, style if style in VOICE_STYLES else 'Natural'
        except (OSError, ValueError, AttributeError):
            pass
        return '', 'Natural'

    def _save_voice_preferences(self) -> None:
        try:
            self.preferences_path.write_text(json.dumps({'voice_id': self.voice_id, 'style': self.voice_style}), encoding='utf-8')
        except OSError:
            self._post('audio', 'El ajuste se aplica durante esta sesión. No pude guardarlo.')

    def _voice_changed(self, label: str) -> None:
        self.voice_id = self.voice_options[label]
        self.voice_controls.put(('voice', self.voice_id))
        self._save_voice_preferences()

    def _microphone_changed(self, label: str, index: int | None) -> None:
        self.microphone_label = label
        self.microphone_changes.put(index)

    def _style_changed(self, label: str) -> None:
        self.voice_style = label
        self.voice_controls.put(('style', label))
        self._save_voice_preferences()

    def _run_assistant(self) -> None:
        try:
            import pythoncom

            pythoncom.CoInitialize()
            try:
                assistant = JarvisAssistant(
                    self.config, on_event=self._post, stop_event=self.stop, microphone_changes=self.microphone_changes,
                    voice_controls=self.voice_controls, microphone_paused=self.microphone_paused,
                )
                assistant.speaker.configure(voice_id=self.voice_id, style=self.voice_style)
                options = {AUTOMATIC: ''}
                for voice_id, description in assistant.speaker.available_voices():
                    label = description if description not in options else f'{description} ({len(options)})'
                    options[label] = voice_id
                self.voice_options = options
                assistant.run(mode='voice')
                voice_exit = assistant.state.last_response == 'Cerrando JarvisAI.' or self.stop.is_set()
                del assistant
                self._post('closed' if voice_exit else 'unavailable', 'Cierra esta ventana para reiniciar la voz.')
            finally:
                pythoncom.CoUninitialize()
        except Exception:
            logging.getLogger('JarvisAI').exception('Error al iniciar NEURAL OS')
            self._post('unavailable', 'No pude iniciar el asistente. Consulta logs/jarvis.log.')

    def _post(self, kind: str, message: str) -> None:
        self.events.put((kind, message))

    def _request_close(self) -> None:
        self.stop.set()
        self.root.destroy()

    def _poll(self) -> None:
        microphone_peak = 0.0
        while True:
            try:
                kind, message = self.events.get_nowait()
            except Empty:
                break
            if kind == 'closed':
                self._request_close()
                return
            if kind in {'state', 'unavailable'}:
                warning = kind == 'unavailable' or 'Reintentando' in message
                if warning and message != self.stage:
                    self._append_message('assistant', message)
                self.stage = message if kind == 'state' else 'Voz no disponible'
                accent = VIOLET if self.stage in {'Procesando', 'Buscando archivos', 'Analizando documento', 'Reconociendo tu voz'} else CYAN
                self.status.configure(text=self.stage, fg=WARNING if warning else accent)
            elif kind == 'mic_level':
                microphone_peak = max(microphone_peak, float(message))
            elif kind == 'speech_pulse':
                self.orb.pulse()
            elif kind == 'command':
                self._append_message('user', message)
            elif kind == 'reply':
                self._append_message('assistant', message)
            elif kind == 'panel':
                self._open_panel(message)
            elif kind == 'audio':
                if message:
                    self.audio_warning.configure(text=message)
                    self.audio_warning.pack(side='bottom', anchor='w', padx=10, pady=7)
                else:
                    self.audio_warning.pack_forget()
        self.mic_level = max(microphone_peak, self.mic_level * 0.8)
        self.orb.render(self.stage, self.mic_level)
        if self.splash is not None:
            self.splash_orb.render('Inicio')
        self.root.after(42, self._poll)

    def _append_message(self, role: str, message: str) -> None:
        self.chat.configure(state='normal')
        self.chat.insert('end', ('Tú' if role == 'user' else 'Jarvis') + '\n', role + '_label')
        self.chat.insert('end', message + '\n', role)
        self.chat.insert('end', '\n')
        if int(self.chat.index('end-1c').split('.')[0]) > 500:
            self.chat.delete('1.0', '51.0')
        self.chat.configure(state='disabled')
        self.chat.see('end')
