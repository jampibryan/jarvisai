from __future__ import annotations

import math
import random
import tkinter as tk


MIDNIGHT = '#080d18'
GRAPHITE = '#151d2b'
CYAN = '#00d9ff'
VIOLET = '#8b5cf6'
ICE = '#eaf4ff'


def _blend(start: str, end: str, amount: float) -> str:
    channels = (round(int(start[i:i+2], 16) * (1-amount) + int(end[i:i+2], 16) * amount) for i in (1, 3, 5))
    return '#' + ''.join(f'{channel:02x}' for channel in channels)


class NeuralCore(tk.Canvas):
    """Render the core from live microphone levels and synthesis word timing."""

    def __init__(self, parent: tk.Misc, *, diameter: int = 176) -> None:
        super().__init__(parent, bg=MIDNIGHT, width=diameter + 50, height=diameter + 24, highlightthickness=0)
        self.diameter = diameter
        self.phase = 0.0
        self.level = 0.0
        self.waves: list[float] = []
        rng = random.Random(34)
        self.particles = [(rng.random() * math.tau, rng.uniform(0.70, 1.68), rng.uniform(0.1, 1)) for _ in range(30)]

    def pulse(self) -> None:
        self.waves.append(0.0)

    def render(self, state: str, microphone_level: float = 0.0) -> None:
        width, height = self.winfo_width(), self.winfo_height()
        if min(width, height) < 48:
            return
        self.delete('all')
        x, y = width / 2, height / 2
        radius = min(self.diameter / 2.2, width / 4.0, height / 2.5)
        thinking = state in {'Procesando', 'Reconociendo tu voz', 'Buscando archivos', 'Analizando documento',
                             'Buscando en YouTube', 'Consultando Gmail'}
        speaking = state == 'Respondiendo'
        listening = state == 'Escuchando' or state.startswith('Esperando')
        accent = VIOLET if thinking else CYAN
        self.phase = (self.phase + (6.4 if thinking else 2.1)) % 360
        radians = math.radians(self.phase)
        self.level = max(microphone_level if listening else 0.0, self.level * 0.72)
        breath = 1 + math.sin(radians) * 0.045 + self.level * 0.12
        r = radius * breath

        for layer in range(18, 0, -1):
            glow_radius = r * (0.44 + layer / 13)
            glow = _blend(MIDNIGHT, accent, 0.016 + (1-layer/18) ** 2 * (0.28 + self.level * 0.09))
            self.create_oval(x-glow_radius, y-glow_radius, x+glow_radius, y+glow_radius, fill=glow, outline='')
        for angle, distance, brightness in self.particles:
            drift = radians * 0.15 + angle
            px, py = x + math.cos(drift)*r*distance, y + math.sin(drift)*r*distance
            color = _blend(MIDNIGHT, accent, brightness * (0.42 + self.level * 0.25))
            self.create_oval(px-0.9, py-0.9, px+0.9, py+0.9, fill=color, outline='')
        for scale, shift, extent, opacity in ((1.14, 130, 72, 0.29), (1.14, -55, 36, 0.40),
                                               (0.86, 20, 107, 0.80), (0.86, 211, 79, 0.58)):
            orbit = r * scale
            self.create_arc(x-orbit, y-orbit, x+orbit, y+orbit, start=self.phase+shift, extent=extent,
                            style='arc', outline=_blend(MIDNIGHT, accent, opacity), width=2 if opacity > 0.5 else 1)
        for layer in range(22, 0, -1):
            core = r * layer / 42
            color = _blend(accent, ICE, (1-layer/22) ** 1.25)
            self.create_oval(x-core, y-core, x+core, y+core, fill=color, outline='')

        if speaking:
            for age in self.waves:
                wave = r * (0.57 + age * 0.85)
                self.create_oval(x-wave, y-wave, x+wave, y+wave, outline=_blend(MIDNIGHT, CYAN, 0.73 * (1-age)))
            self.waves = [age + 0.11 for age in self.waves if age + 0.11 < 1]
        else:
            self.waves.clear()
